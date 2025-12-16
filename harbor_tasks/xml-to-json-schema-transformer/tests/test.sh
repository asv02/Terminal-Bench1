#!/bin/bash

# Install uv
apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh
source $HOME/.local/bin/env

# Check working directory
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    exit 1
fi

# Create test venv and install pytest
uv venv .tbench-testing
source .tbench-testing/bin/activate
uv pip install pytest==8.4.1

# Run tests
uv run pytest /tests/test_outputs.py -rA

# Record result
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
