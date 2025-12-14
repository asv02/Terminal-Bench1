#!/bin/bash

set -e

# Safety check: Don't run from root directory
if [ "$PWD" = "/" ]; then 
    echo "Error: Cannot run from root directory" >&2
    exit 1
fi

# Install uv (fast Python package manager)
echo "Installing uv package manager..."
apt-get update && apt-get install -y curl
curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh
source $HOME/.local/bin/env

# Create virtual environment for testing
echo "Creating test virtual environment..."
uv venv .tbench-testing
source .tbench-testing/bin/activate

# Install test dependencies with pinned versions
echo "Installing test dependencies..."
uv pip install pytest==8.3.4

# Run pytest tests
echo "Running test suite..."
uv run pytest /tests/test_outputs.py -v -rA
EXIT_CODE=$?

# Create logs directory if it doesn't exist
mkdir -p /logs/verifier

# Generate reward.json based on test results
if [ $EXIT_CODE -eq 0 ]; then
    echo "All tests passed! Generating success reward..."
    echo '{"reward": 1.0}' > /logs/verifier/reward.json
else
    echo "Tests failed. Generating failure reward..."
    echo '{"reward": 0.0}' > /logs/verifier/reward.json
fi

echo "Test execution complete. Exit code: $EXIT_CODE"
exit $EXIT_CODE
