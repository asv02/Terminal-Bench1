import csv
import json
import os
import subprocess
from pathlib import Path

import pandas as pd


OUTPUT_DIR = Path("/app/output")
ROUTES_PATH = OUTPUT_DIR / "routes.parquet"
CONFLICTS_PATH = OUTPUT_DIR / "conflicts.csv"
STATS_PATH = OUTPUT_DIR / "stats.json"


def run_routecanon(env_extra: dict | None = None) -> None:
    """Run routecanon using the container python with proper PYTHONPATH set."""
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", "/solution/app:/solution")
    if env_extra:
        env.update(env_extra)
    subprocess.run(
        ["/usr/local/bin/python", "-m", "routecanon"],
        check=True,
        env=env,
    )


def test_output_files_exist():
    """All three required outputs are materialized in /app/output."""
    assert ROUTES_PATH.is_file()
    assert CONFLICTS_PATH.is_file()
    assert STATS_PATH.is_file()


def test_routes_schema_and_sort_and_content():
    """routes.parquet has the exact schema, sort order, and canonical rows for the seeded configs."""
    df = pd.read_parquet(ROUTES_PATH)

    expected_columns = [
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
    assert list(df.columns) == expected_columns

    # Expected 6 canonical routes
    assert len(df) == 6

    # Sorting check against the declared sort key
    env_rank = {"dev": 0, "staging": 1, "prod": 2}
    sorted_df = df.sort_values(
        by=["service", "environment", "path", "method"],
        key=lambda col: col.map(env_rank) if col.name == "environment" else col,
    ).reset_index(drop=True)
    assert df.reset_index(drop=True).equals(sorted_df)

    # Check sorting: by service, environment (dev<staging<prod), path, method
    row0 = df.iloc[0].to_dict()
    row1 = df.iloc[1].to_dict()
    row2 = df.iloc[2].to_dict()
    row3 = df.iloc[3].to_dict()
    row4 = df.iloc[4].to_dict()
    row5 = df.iloc[5].to_dict()

    # Row 0: analytics staging /events GET (priority tie-breaker)
    assert row0["service"] == "analytics"
    assert row0["environment"] == "staging"
    assert row0["method"] == "GET"
    assert row0["path"] == "/events"
    assert row0["upstream"] == "events-high"
    assert row0["version"] == "v1"
    assert row0["priority"] == 15
    assert row0["public"] is True
    assert row0["auth_required"] is True
    assert row0["ratelimit_bucket"] == "medium"
    assert row0["stable_route_id"] == "analytics:GET:/events"
    assert row0["activation_start_date"] is None
    assert row0["activation_end_date"] is None
    assert row0["active_on_reference_date"] is True

    # Row 1: billing dev /api/v1/users GET (version conflict; inactive window)
    assert row1["service"] == "billing"
    assert row1["environment"] == "dev"
    assert row1["method"] == "GET"
    assert row1["path"] == "/api/v1/users"
    assert row1["upstream"] == "users-v2"
    assert row1["version"] == "v2"
    assert row1["priority"] == 20
    assert row1["public"] is True
    assert row1["auth_required"] is True
    assert row1["ratelimit_bucket"] == "high"
    assert row1["stable_route_id"] == "billing:GET:/api/v1/users"
    assert row1["activation_start_date"] == "2024-10-01"
    assert row1["activation_end_date"] == "2024-10-31"
    assert row1["active_on_reference_date"] is False

    # Row 2: billing dev /internal/metrics GET (single variant)
    assert row2["service"] == "billing"
    assert row2["environment"] == "dev"
    assert row2["method"] == "GET"
    assert row2["path"] == "/internal/metrics"
    assert row2["upstream"] == "metrics"
    assert row2["version"] == "v1"
    assert row2["priority"] == 5
    assert row2["public"] is False
    assert row2["auth_required"] is True
    assert row2["ratelimit_bucket"] == "low"
    assert row2["stable_route_id"] == "billing:GET:/internal/metrics"
    assert row2["activation_start_date"] is None
    assert row2["activation_end_date"] is None
    assert row2["active_on_reference_date"] is True

    # Row 3: legacy dev /v1/items POST (all-deprecated kept)
    assert row3["service"] == "legacy"
    assert row3["environment"] == "dev"
    assert row3["method"] == "POST"
    assert row3["path"] == "/v1/items"
    assert row3["upstream"] == "items-b"
    assert row3["version"] == "v2"
    assert row3["priority"] == 5
    assert row3["public"] is True
    assert row3["auth_required"] is False
    assert row3["ratelimit_bucket"] == "none"
    assert row3["stable_route_id"] == "legacy:POST:/v1/items"
    assert row3["activation_start_date"] is None
    assert row3["activation_end_date"] is None
    assert row3["active_on_reference_date"] is True

    # Row 4: logs prod /sink PUT (upstream tie-breaker)
    assert row4["service"] == "logs"
    assert row4["environment"] == "prod"
    assert row4["method"] == "PUT"
    assert row4["path"] == "/sink"
    assert row4["upstream"] == "sink-a"
    assert row4["version"] == "v1"
    assert row4["priority"] == 1
    assert row4["public"] is True
    assert row4["auth_required"] is False
    assert row4["ratelimit_bucket"] == "low"
    assert row4["stable_route_id"] == "logs:PUT:/sink"
    assert row4["activation_start_date"] is None
    assert row4["activation_end_date"] is None
    assert row4["active_on_reference_date"] is True

    # Row 5: payments prod /api/v1/charge POST (single variant)
    assert row5["service"] == "payments"
    assert row5["environment"] == "prod"
    assert row5["method"] == "POST"
    assert row5["path"] == "/api/v1/charge"
    assert row5["upstream"] == "charge-v1"
    assert row5["version"] == "v1"
    assert row5["priority"] == 50
    assert row5["public"] is True
    assert row5["auth_required"] is True
    assert row5["ratelimit_bucket"] == "medium"
    assert row5["stable_route_id"] == "payments:POST:/api/v1/charge"
    assert row5["activation_start_date"] is None
    assert row5["activation_end_date"] is None
    assert row5["active_on_reference_date"] is True


def test_conflicts_csv_contents():
    """conflicts.csv captures all conflicts with correct header, ordering, and winner metadata."""
    with CONFLICTS_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        expected_header = [
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
        assert header == expected_header

        rows = list(reader)

    # Expected four conflicts sorted by service/env/method/path
    assert len(rows) == 4

    # Sorting check against the declared sort key
    env_rank = {"dev": 0, "staging": 1, "prod": 2}
    sorted_rows = sorted(
        rows,
        key=lambda r: (
            r["service"],
            env_rank.get(r["environment"], 99),
            r["method"],
            r["path"],
        ),
    )
    assert rows == sorted_rows

    row0, row1, row2, row3 = rows

    # analytics staging /events priority conflict
    assert row0["service"] == "analytics"
    assert row0["environment"] == "staging"
    assert row0["method"] == "GET"
    assert row0["path"] == "/events"
    assert row0["conflict_type"] == "priority_conflict"
    assert int(row0["num_variants"]) == 2
    assert row0["chosen_version"] == "v1"
    assert int(row0["chosen_priority"]) == 15
    assert row0["chosen_upstream"] == "events-high"
    assert row0["has_mixed_activation"] == "false"

    # billing dev /api/v1/users version conflict with mixed activation
    assert row1["service"] == "billing"
    assert row1["environment"] == "dev"
    assert row1["method"] == "GET"
    assert row1["path"] == "/api/v1/users"
    assert row1["conflict_type"] == "version_conflict"
    assert int(row1["num_variants"]) == 2
    assert row1["chosen_version"] == "v2"
    assert int(row1["chosen_priority"]) == 20
    assert row1["chosen_upstream"] == "users-v2"
    assert row1["has_mixed_activation"] == "true"

    # legacy dev /v1/items all-deprecated still kept
    assert row2["service"] == "legacy"
    assert row2["environment"] == "dev"
    assert row2["method"] == "POST"
    assert row2["path"] == "/v1/items"
    assert row2["conflict_type"] == "version_conflict"
    assert int(row2["num_variants"]) == 2
    assert row2["chosen_version"] == "v2"
    assert int(row2["chosen_priority"]) == 5
    assert row2["chosen_upstream"] == "items-b"
    assert row2["has_mixed_activation"] == "false"

    # logs prod /sink upstream conflict
    assert row3["service"] == "logs"
    assert row3["environment"] == "prod"
    assert row3["method"] == "PUT"
    assert row3["path"] == "/sink"
    assert row3["conflict_type"] == "upstream_conflict"
    assert int(row3["num_variants"]) == 2
    assert row3["chosen_version"] == "v1"
    assert int(row3["chosen_priority"]) == 1
    assert row3["chosen_upstream"] == "sink-a"
    assert row3["has_mixed_activation"] == "false"


def test_stats_json_consistency():
    """stats.json matches derived counts from routes.parquet and conflicts.csv and stays compact."""
    df = pd.read_parquet(ROUTES_PATH)
    with CONFLICTS_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        conflicts = list(reader)

    stats = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    stats_text = STATS_PATH.read_text(encoding="utf-8")

    # Totals
    assert stats["total_routes"] == len(df)
    assert stats["total_routes"] == 6

    total_public = int((df["public"] == True).sum())  # noqa: E712
    assert stats["total_public_routes"] == total_public
    assert stats["total_public_routes"] == 5

    # per_service_counts
    per_service = df.groupby("service").size().to_dict()
    assert stats["per_service_counts"] == {k: int(v) for k, v in per_service.items()}
    assert stats["per_service_counts"]["analytics"] == 1
    assert stats["per_service_counts"]["billing"] == 2
    assert stats["per_service_counts"]["legacy"] == 1
    assert stats["per_service_counts"]["logs"] == 1
    assert stats["per_service_counts"]["payments"] == 1

    # per_environment_counts
    per_env = df.groupby("environment").size().to_dict()
    expected_env_counts = {e: int(per_env.get(e, 0)) for e in ["dev", "staging", "prod"]}
    assert stats["per_environment_counts"] == expected_env_counts
    assert stats["per_environment_counts"]["dev"] == 3
    assert stats["per_environment_counts"]["staging"] == 1
    assert stats["per_environment_counts"]["prod"] == 2

    # conflicts count
    assert stats["num_conflicts"] == len(conflicts)
    assert stats["num_conflicts"] == 4

    # reference_date
    assert stats["reference_date"] == "2024-11-15"

    # active routes
    active_mask = df["active_on_reference_date"] == True  # noqa: E712
    active_total = int(active_mask.sum())
    assert stats["active_routes_on_reference_date"] == active_total
    assert stats["active_routes_on_reference_date"] == 5

    active_env_counts = (
        df[active_mask].groupby("environment").size().to_dict()
        if active_total > 0
        else {}
    )
    expected_active_env = {
        e: int(active_env_counts.get(e, 0)) for e in ["dev", "staging", "prod"]
    }
    assert stats["per_environment_active_counts"] == expected_active_env
    assert stats["per_environment_active_counts"]["dev"] == 2
    assert stats["per_environment_active_counts"]["staging"] == 1
    assert stats["per_environment_active_counts"]["prod"] == 2

    # size constraint: less than 1024 bytes
    assert STATS_PATH.stat().st_size < 1024
    # Compact JSON (no extra spaces)
    assert stats_text == json.dumps(stats, separators=(",", ":"))


def test_idempotence_and_no_tmp():
    """Re-running the CLI is deterministic and leaves no stray tmp output."""
    # Snapshot current outputs
    orig_routes = ROUTES_PATH.read_bytes()
    orig_conflicts = CONFLICTS_PATH.read_text(encoding="utf-8")
    orig_stats = STATS_PATH.read_text(encoding="utf-8")

    # Re-run
    run_routecanon()

    # Compare
    assert ROUTES_PATH.read_bytes() == orig_routes
    assert CONFLICTS_PATH.read_text(encoding="utf-8") == orig_conflicts
    assert STATS_PATH.read_text(encoding="utf-8") == orig_stats

    tmp_dir = OUTPUT_DIR / "tmp"
    assert not tmp_dir.exists() or not any(tmp_dir.iterdir())


def test_app_data_preferred_over_solution():
    """Default run should use /app/data even if /solution/data is modified."""
    solution_file = Path("/solution/data/config/services/billing-dev-a.yaml")
    if solution_file.exists():
        original = solution_file.read_text(encoding="utf-8")
        try:
            solution_file.write_text(original.replace("v1", "v9"), encoding="utf-8")
            run_routecanon()
        finally:
            solution_file.write_text(original, encoding="utf-8")

    df = pd.read_parquet(ROUTES_PATH)
    billing_users = df[
        (df["service"] == "billing")
        & (df["environment"] == "dev")
        & (df["path"] == "/api/v1/users")
    ].iloc[0]
    assert billing_users["version"] == "v2"
    assert billing_users["upstream"] == "users-v2"


def test_data_mutation_changes_outputs():
    """Modifying /app data must change outputs, preventing hardcoding."""
    candidate_roots = [Path("/app"), Path("/solution")]
    target_root = None
    target_file = None
    for root in candidate_roots:
        candidate = root / "data" / "config" / "services" / "billing-dev-b.yaml"
        if candidate.exists():
            target_root = root
            target_file = candidate
            break
    if target_file is None:
        raise FileNotFoundError("billing-dev-b.yaml not found in /app or /solution data roots")

    original = target_file.read_text(encoding="utf-8")
    try:
        mutated = original.replace("users-v2", "users-hacked").replace("v2", "v9", 1)
        target_file.write_text(mutated, encoding="utf-8")
        run_routecanon(env_extra={"ROUTECANON_DATA_ROOT": str(target_root)})

        df = pd.read_parquet(ROUTES_PATH)
        billing_users = df[
            (df["service"] == "billing")
            & (df["environment"] == "dev")
            & (df["path"] == "/api/v1/users")
        ].iloc[0]
        assert billing_users["version"] == "v9"
        assert billing_users["upstream"] == "users-hacked"
    finally:
        target_file.write_text(original, encoding="utf-8")
        run_routecanon(env_extra={"ROUTECANON_DATA_ROOT": str(target_root)})
