#!/usr/bin/env bash
set -euo pipefail

# Harbor/Terminal-Bench mounts solution contents at /solution.
# routecanon is vendored inside the solution bundle; data lives under /solution/data.
mkdir -p /app/app
cp -a /solution/app/routecanon /app/app/
export PYTHONPATH="/app/app:/solution/app:/solution:${PYTHONPATH:-}"

# Ensuring runtime deps are present (pinned).
python - <<'PY'
import importlib.util, subprocess, sys
needed = {
    "pandas": "pandas==2.3.3",
    "pyarrow": "pyarrow==22.0.0",
    "yaml": "pyyaml==6.0.3",
}
missing = [pkg for pkg, req in needed.items() if importlib.util.find_spec(pkg) is None]
if missing:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check", *[needed[m] for m in missing]],
        check=True,
    )
PY

python -m routecanon
