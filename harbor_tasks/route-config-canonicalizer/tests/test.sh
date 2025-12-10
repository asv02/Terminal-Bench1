#!/usr/bin/env bash
set -u

TEST_DIR="${TEST_DIR:-/app/tests}"
cd "$TEST_DIR"

mkdir -p /logs/verifier

export PYTHONPATH="/solution/app:/solution:${PYTHONPATH:-}"

status=0

python -m venv .venv || status=$?

if [ $status -eq 0 ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate || status=$?
fi

if [ $status -eq 0 ]; then
  pip install --upgrade pip==24.2 || status=$?
fi

if [ $status -eq 0 ]; then
  pip install \
    pytest==8.3.3 \
    pandas==2.3.3 \
    pyarrow==22.0.0 \
    pyyaml==6.0.3 || status=$?
fi

if [ $status -eq 0 ]; then
  # Capture full pytest output (including summary) for Harbor parsers.
  set +e
  pytest -rA test_outputs.py | tee /logs/verifier/test-stdout.txt
  status=${PIPESTATUS[0]}
  set -e
fi

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
