# route-config-canonicalizer

Canonical API gateway route normalizer with rollout window awareness.

## Goal
Read service route configs from YAML, normalize them, resolve conflicts deterministically, and write three structured outputs under `/app/output`:
- `routes.parquet`: canonical winner per `{service, environment, method, path}`.
- `conflicts.csv`: one row per conflicting key with metadata about the chosen winner.
- `stats.json`: compact (<1KB) summary counts consistent with the other outputs.

All behavior below is mandatory and fully covered by tests.

## Reference date
Use `REFERENCE_DATE = "2024-11-15"` for activation checks.

## Input layout and schema
- Location: `/app/data/config/services/*.yaml`. A copy is also provided in the solution bundle at `/solution/data/config/services` for convenience; prefer `/app/data` when present.
- Each YAML file:
  - `service`: string (e.g., `"billing"`)
  - `environment`: one of `dev|staging|prod`
  - `routes`: list of route objects with fields:
    - `path`: string (may lack a leading `/`, may contain duplicate slashes, may end with `/`)
    - `method`: string HTTP verb in any case
    - `upstream`: string
    - `version`: string like `"v1"`; numeric suffix drives ordering
    - `priority`: integer
    - `tags`: list of strings
    - `internal_only`: boolean
    - `auth`: `"none" | "jwt" | "m2m"`
    - `ratelimit`: `"none" | "low" | "medium" | "high"`
    - `enabled`: boolean
    - `notes`: string or null
    - `activation` (optional object):
      - `start_date`: optional `"YYYY-MM-DD"`
      - `end_date`: optional `"YYYY-MM-DD"`

## Normalization and filtering
1. Drop any route with `enabled == false`.
2. Normalize `path`:
   - Ensure leading `/`.
   - Collapse repeated `/` into a single `/`.
   - Remove trailing `/` except when the path is exactly `/`.
3. Normalize `method` to uppercase.
4. Derived booleans:
   - `public = (internal_only == False) and ("internal" not in tags)`
   - `auth_required = (auth != "none")`
5. Activation:
   - If `activation` is missing: `activation_start_date = None`, `activation_end_date = None`, `active_on_reference_date = True`.
   - Otherwise: `start = activation.start_date or "1970-01-01"`, `end = activation.end_date or "9999-12-31"`, `active_on_reference_date = (start <= REFERENCE_DATE <= end)`.

## Conflict grouping
Group normalized variants by `(service, environment, method, path)`.
- Deprecated handling: drop variants that include `"deprecated"` in `tags` unless **all** variants for the key are deprecated; in that case keep them all.
- Winner selection (after deprecation filtering):
  1. Highest `version` numeric suffix (e.g., `v10` > `v2` > `v1`; non-numeric -> 0).
  2. Tie-breaker: higher `priority`.
  3. Tie-breaker: lexicographically smallest `upstream`.
- Conflict detection: if more than one filtered variant exists for a key, emit a conflict row.
  - `conflict_type`:
    - `"version_conflict"` if versions differ.
    - `"priority_conflict"` if versions match but priorities differ.
    - `"upstream_conflict"` if versions and priorities match but upstreams differ.
  - `has_mixed_activation = True` if at least one variant is active on the reference date and at least one is not.

## Outputs
All outputs are deterministic and overwrite previous runs. No temp files under `/app/output/tmp`.

### routes.parquet
- Location: `/app/output/routes.parquet`
- Column order (all lowercase): `service, environment, method, path, upstream, version, priority, public, auth_required, ratelimit_bucket, stable_route_id, activation_start_date, activation_end_date, active_on_reference_date`
- Types: strings for text fields, integers for priority, booleans for flags, `None` allowed for activation dates.
- Row content: the chosen winner for each grouped key after deprecation filtering.
- Sorting: by `service`, then environment order (`dev` < `staging` < `prod`), then `path`, then `method`.
- `stable_route_id = "{service}:{method}:{path}"`.

### conflicts.csv
- Location: `/app/output/conflicts.csv`
- Header exactly: `service,environment,method,path,conflict_type,num_variants,chosen_version,chosen_priority,chosen_upstream,has_mixed_activation`
- One row per conflicting key (post-deprecation).
- `num_variants` counts filtered variants.
- `has_mixed_activation` written as lowercase `"true"` / `"false"`.
- Sorting: by `service`, then environment order (`dev` < `staging` < `prod`), then `method`, then `path`.

### stats.json
- Location: `/app/output/stats.json`
- JSON object with compact separators (no extra whitespace), size < 1024 bytes.
- Keys:
  - `total_routes`
  - `total_public_routes`
  - `per_service_counts` (map of service -> count)
  - `per_environment_counts` (keys `dev`, `staging`, `prod`)
  - `num_conflicts`
  - `reference_date` (always `"2024-11-15"`)
  - `active_routes_on_reference_date`
  - `per_environment_active_counts` (keys `dev`, `staging`, `prod`)
- Values must be consistent with the rows in `routes.parquet` and `conflicts.csv` (cross-validated in tests).

## Seeded dataset (deterministic and required)
Data is pre-mounted inside the container; **no downloads or synthesis are needed**. Primary location is `/app/data/config/services/`. An identical mirror is available at `/solution/data/config/services/` for convenience or fallback. Always prefer `/app/data` when it exists. Directory layout in the container:

```
/app/data/config/services/
  billing-dev-a.yaml
  billing-dev-b.yaml
  analytics-staging.yaml
  legacy-dev.yaml
  logs-prod.yaml
  payments-prod.yaml
```

These six files are **always present at runtime** via the task bundle. Do not read from any other directories and do not invent additional inputs. You must honor them exactly; no additional discovery or filtering:

- `/app/data/config/services/billing-dev-a.yaml`
- `/app/data/config/services/billing-dev-b.yaml`
- `/app/data/config/services/analytics-staging.yaml`
- `/app/data/config/services/legacy-dev.yaml`
- `/app/data/config/services/logs-prod.yaml`
- `/app/data/config/services/payments-prod.yaml`

From these inputs, after applying all rules above, the outputs must contain:

### Canonical routes (6 rows, sorted as specified)
1. `analytics, staging, GET, /events` → upstream `events-high`, version `v1`, priority `15`, public `true`, auth_required `true`, ratelimit `medium`, active_on_reference_date `true`, activation dates `None`.
2. `billing, dev, GET, /api/v1/users` → upstream `users-v2`, version `v2`, priority `20`, public `true`, auth_required `true`, ratelimit `high`, active_on_reference_date `false`, activation `2024-10-01` to `2024-10-31`.
3. `billing, dev, GET, /internal/metrics` → upstream `metrics`, version `v1`, priority `5`, public `false`, auth_required `true`, ratelimit `low`, active_on_reference_date `true`, no activation window.
4. `legacy, dev, POST, /v1/items` → upstream `items-b`, version `v2`, priority `5`, public `true`, auth_required `false`, ratelimit `none`, active_on_reference_date `true`, no activation window (all variants were deprecated but kept).
5. `logs, prod, PUT, /sink` → upstream `sink-a`, version `v1`, priority `1`, public `true`, auth_required `false`, ratelimit `low`, active_on_reference_date `true`, no activation window (upstream tie-breaker).
6. `payments, prod, POST, /api/v1/charge` → upstream `charge-v1`, version `v1`, priority `50`, public `true`, auth_required `true`, ratelimit `medium`, active_on_reference_date `true`, no activation window.

### Conflicts (4 rows, sorted as specified)
1. `analytics, staging, GET, /events` → `conflict_type="priority_conflict"`, `num_variants=2`, chosen `v1/priority 15/upstream events-high`, `has_mixed_activation=false`.
2. `billing, dev, GET, /api/v1/users` → `conflict_type="version_conflict"`, `num_variants=2`, chosen `v2/priority 20/upstream users-v2`, `has_mixed_activation=true`.
3. `legacy, dev, POST, /v1/items` → `conflict_type="version_conflict"` (all deprecated but kept), `num_variants=2`, chosen `v2/priority 5/upstream items-b`, `has_mixed_activation=false`.
4. `logs, prod, PUT, /sink` → `conflict_type="upstream_conflict"`, `num_variants=2`, chosen `v1/priority 1/upstream sink-a`, `has_mixed_activation=false`.

### Required aggregates (stats.json)
- `total_routes = 6`
- `total_public_routes = 5`
- `per_service_counts = {"analytics":1,"billing":2,"legacy":1,"logs":1,"payments":1}`
- `per_environment_counts = {"dev":3,"staging":1,"prod":2}`
- `num_conflicts = 4`
- `reference_date = "2024-11-15"`
- `active_routes_on_reference_date = 5`
- `per_environment_active_counts = {"dev":2,"staging":1,"prod":2}`

Any deviation from these counts/rows indicates an incorrect implementation. Idempotence is required: re-running `python -m routecanon` must leave the outputs identical, with no temp files (especially none under `/app/output/tmp`).

## Determinism and idempotence
- Running `python -m routecanon` multiple times must produce identical outputs.
- No reliance on system time beyond `REFERENCE_DATE`.
- No network or external resources.

## Execution entrypoint
- The Python package `routecanon` lives under `/solution/app/routecanon`. Before invoking, set `PYTHONPATH="/solution/app:/app/app:$PYTHONPATH"` (solve.sh also copies the package to `/app/app` to ensure availability).
- Run `python -m routecanon` from anywhere; the code reads configs from `/app/data/...` when present, otherwise `/solution/data/...`, and always writes outputs under `/app/output`.
- Runtime dependencies (pandas, pyarrow, pyyaml) are preinstalled in the container; tests install their own tools (pytest + the same IO libs) inside a virtual environment.
- Package layout (already provided; do not reinvent it):
  - `/solution/app/routecanon/__init__.py`
  - `/solution/app/routecanon/__main__.py` (entrypoint calling `core.run()`)
  - `/solution/app/routecanon/core.py` (implements all logic and writes outputs)
  - The solution runner copies `/solution/app/routecanon` into `/app/app/routecanon` so `python -m routecanon` always works when `PYTHONPATH` includes `/app/app` or `/solution/app`.
