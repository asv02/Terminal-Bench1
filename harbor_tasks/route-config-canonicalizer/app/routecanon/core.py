from __future__ import annotations

import csv
import json
import re
import os
from collections import defaultdict, Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml


REFERENCE_DATE = "2024-11-15"


@dataclass
class RouteVariant:
    service: str
    environment: str
    method: str
    path: str
    upstream: str
    version: str
    version_num: int
    priority: int
    tags: List[str]
    internal_only: bool
    auth: str
    ratelimit_bucket: str
    public: bool
    auth_required: bool
    activation_start_date: str | None
    activation_end_date: str | None
    active_on_reference_date: bool
    stable_route_id: str


def normalize_path(raw: str) -> str:
    if not raw:
        raw = "/"
    if not raw.startswith("/"):
        raw = "/" + raw
    # collapse multiple slashes
    raw = re.sub(r"/+", "/", raw)
    # remove trailing slash except for root
    if raw != "/" and raw.endswith("/"):
        raw = raw[:-1]
    return raw


def parse_version_num(version: str) -> int:
    # Extract integer suffix from strings like "v1", "v10", "V2"
    # Fallback to 0 if parse fails
    s = version.strip()
    # Strip leading non-digit chars
    i = 0
    while i < len(s) and not s[i].isdigit():
        i += 1
    num_part = s[i:] or "0"
    try:
        return int(num_part)
    except ValueError:
        return 0


def load_raw_routes(config_dir: Path) -> List[Dict[str, Any]]:
    routes: List[Dict[str, Any]] = []
    for path in sorted(config_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        service = data.get("service")
        environment = data.get("environment")
        for r in data.get("routes", []) or []:
            entry = dict(r)
            entry["_service"] = service
            entry["_environment"] = environment
            routes.append(entry)
    return routes


def build_variants(raw_routes: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str, str], List[RouteVariant]]:
    groups: Dict[Tuple[str, str, str, str], List[RouteVariant]] = defaultdict(list)

    for r in raw_routes:
        enabled = r.get("enabled", True)
        if not enabled:
            continue

        service = r.get("_service")
        environment = r.get("_environment")
        if not service or not environment:
            # Skip malformed entries
            continue

        raw_path = r.get("path", "/")
        norm_path = normalize_path(str(raw_path))

        raw_method = r.get("method", "GET")
        method = str(raw_method).upper()

        upstream = str(r.get("upstream", "") or "")
        version = str(r.get("version", "v0") or "v0")
        priority = int(r.get("priority", 0))

        tags = list(r.get("tags", []) or [])
        internal_only = bool(r.get("internal_only", False))
        auth = str(r.get("auth", "none") or "none")
        ratelimit_bucket = str(r.get("ratelimit", "none") or "none")

        public = (not internal_only) and ("internal" not in tags)
        auth_required = (auth != "none")

        activation = r.get("activation")
        if activation is None:
            activation_start_date = None
            activation_end_date = None
            active_on_reference_date = True
        else:
            activation_start_date = activation.get("start_date")
            activation_end_date = activation.get("end_date")
            start = activation_start_date or "1970-01-01"
            end = activation_end_date or "9999-12-31"
            active_on_reference_date = (start <= REFERENCE_DATE <= end)

        stable_route_id = f"{service}:{method}:{norm_path}"

        variant = RouteVariant(
            service=service,
            environment=environment,
            method=method,
            path=norm_path,
            upstream=upstream,
            version=version,
            version_num=parse_version_num(version),
            priority=priority,
            tags=tags,
            internal_only=internal_only,
            auth=auth,
            ratelimit_bucket=ratelimit_bucket,
            public=public,
            auth_required=auth_required,
            activation_start_date=activation_start_date,
            activation_end_date=activation_end_date,
            active_on_reference_date=active_on_reference_date,
            stable_route_id=stable_route_id,
        )

        key = (service, environment, method, norm_path)
        groups[key].append(variant)

    return groups


def resolve_conflicts(
    groups: Dict[Tuple[str, str, str, str], List[RouteVariant]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    canonical_rows: List[Dict[str, Any]] = []
    conflict_rows: List[Dict[str, Any]] = []

    env_rank = {"dev": 0, "staging": 1, "prod": 2}

    for key, variants in groups.items():
        service, environment, method, path = key

        # Drop deprecated unless all are deprecated
        all_deprecated = all("deprecated" in v.tags for v in variants)
        if all_deprecated:
            filtered = list(variants)
        else:
            filtered = [v for v in variants if "deprecated" not in v.tags]

        if not filtered:
            # Should not happen, but guard anyway
            continue

        # Winner selection: version_num desc, priority desc, upstream asc
        sorted_variants = sorted(
            filtered,
            key=lambda v: (-v.version_num, -v.priority, v.upstream),
        )
        winner = sorted_variants[0]

        # Canonical row
        canonical_rows.append(
            {
                "service": winner.service,
                "environment": winner.environment,
                "method": winner.method,
                "path": winner.path,
                "upstream": winner.upstream,
                "version": winner.version,
                "priority": int(winner.priority),
                "public": bool(winner.public),
                "auth_required": bool(winner.auth_required),
                "ratelimit_bucket": winner.ratelimit_bucket,
                "stable_route_id": winner.stable_route_id,
                "activation_start_date": winner.activation_start_date,
                "activation_end_date": winner.activation_end_date,
                "active_on_reference_date": bool(winner.active_on_reference_date),
            }
        )

        if len(filtered) > 1:
            # Determine conflict_type
            versions = {v.version for v in filtered}
            priorities = {v.priority for v in filtered}
            upstreams = {v.upstream for v in filtered}

            if len(versions) > 1:
                conflict_type = "version_conflict"
            elif len(priorities) > 1:
                conflict_type = "priority_conflict"
            elif len(upstreams) > 1:
                conflict_type = "upstream_conflict"
            else:
                # Fallback (shouldn't really happen)
                conflict_type = "version_conflict"

            # Mixed activation
            active_flags = {v.active_on_reference_date for v in filtered}
            has_mixed_activation = (True in active_flags) and (False in active_flags)

            conflict_rows.append(
                {
                    "service": service,
                    "environment": environment,
                    "method": method,
                    "path": path,
                    "conflict_type": conflict_type,
                    "num_variants": len(filtered),
                    "chosen_version": winner.version,
                    "chosen_priority": int(winner.priority),
                    "chosen_upstream": winner.upstream,
                    "has_mixed_activation": has_mixed_activation,
                }
            )

    # Sort canonical rows
    canonical_rows.sort(
        key=lambda r: (
            r["service"],
            env_rank.get(r["environment"], 99),
            r["path"],
            r["method"],
        )
    )

    # Sort conflicts
    conflict_rows.sort(
        key=lambda r: (
            r["service"],
            env_rank.get(r["environment"], 99),
            r["method"],
            r["path"],
        )
    )

    return canonical_rows, conflict_rows


def write_routes_parquet(output_dir: Path, rows: List[Dict[str, Any]]) -> None:
    routes_path = output_dir / "routes.parquet"
    columns = [
        "service",
        "environment",
        "method",
        "path",
        "upstream",
        "version",
        "priority",
        "public",
        "auth_required",
        "ratelimit_bucket",
        "stable_route_id",
        "activation_start_date",
        "activation_end_date",
        "active_on_reference_date",
    ]
    if rows:
        df = pd.DataFrame(rows, columns=columns)
        df.to_parquet(routes_path, index=False)
    else:
        df = pd.DataFrame(columns=columns)
        df.to_parquet(routes_path, index=False)


def write_conflicts_csv(output_dir: Path, conflicts: List[Dict[str, Any]]) -> None:
    conflicts_path = output_dir / "conflicts.csv"
    header = [
        "service",
        "environment",
        "method",
        "path",
        "conflict_type",
        "num_variants",
        "chosen_version",
        "chosen_priority",
        "chosen_upstream",
        "has_mixed_activation",
    ]
    with conflicts_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in conflicts:
            writer.writerow(
                {
                    "service": row["service"],
                    "environment": row["environment"],
                    "method": row["method"],
                    "path": row["path"],
                    "conflict_type": row["conflict_type"],
                    "num_variants": int(row["num_variants"]),
                    "chosen_version": row["chosen_version"],
                    "chosen_priority": int(row["chosen_priority"]),
                    "chosen_upstream": row["chosen_upstream"],
                    "has_mixed_activation": "true" if row["has_mixed_activation"] else "false",
                }
            )


def write_stats_json(output_dir: Path, routes: List[Dict[str, Any]], conflicts: List[Dict[str, Any]]) -> None:
    stats_path = output_dir / "stats.json"

    total_routes = len(routes)
    total_public_routes = sum(1 for r in routes if r["public"])

    per_service_counts = Counter(r["service"] for r in routes)
    per_environment_counts = Counter(r["environment"] for r in routes)
    envs = ["dev", "staging", "prod"]

    active_routes_on_reference_date = sum(
        1 for r in routes if r["active_on_reference_date"]
    )
    per_env_active = Counter(
        r["environment"] for r in routes if r["active_on_reference_date"]
    )

    obj = {
        "total_routes": total_routes,
        "total_public_routes": total_public_routes,
        "per_service_counts": dict(per_service_counts),
        "per_environment_counts": {e: int(per_environment_counts.get(e, 0)) for e in envs},
        "num_conflicts": len(conflicts),
        "reference_date": REFERENCE_DATE,
        "active_routes_on_reference_date": active_routes_on_reference_date,
        "per_environment_active_counts": {
            e: int(per_env_active.get(e, 0)) for e in envs
        },
    }

    stats_path.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")


def run() -> None:
    output_dir = Path("/app") / "output"

    # Prefer /app/data, then explicit env override, then /solution/data.
    candidate_roots = [Path("/app")]
    env_root = os.environ.get("ROUTECANON_DATA_ROOT")
    if env_root:
        candidate_roots.append(Path(env_root))
    candidate_roots.append(Path("/solution"))
    config_dir = None
    for root in candidate_roots:
        candidate = root / "data" / "config" / "services"
        if candidate.exists():
            config_dir = candidate
            break
    if config_dir is None:
        config_dir = Path("/app/data/config/services")

    output_dir.mkdir(parents=True, exist_ok=True)

    # No tmp dirs or stray files; everything is written deterministically.
    raw_routes = load_raw_routes(config_dir)
    groups = build_variants(raw_routes)
    canonical_rows, conflict_rows = resolve_conflicts(groups)

    write_routes_parquet(output_dir, canonical_rows)
    write_conflicts_csv(output_dir, conflict_rows)
    write_stats_json(output_dir, canonical_rows, conflict_rows)
