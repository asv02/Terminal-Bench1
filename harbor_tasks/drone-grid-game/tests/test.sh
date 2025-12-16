#!/bin/bash
# CANARY_STRING: drone_exploration_2025

set -e

echo "========================================="
echo "Installing pytest (no root needed)..."
echo "========================================="

# Install to user directory (no root required)
pip install --user pytest==8.4.1

echo ""
echo "========================================="
echo "Running tests..."
echo "========================================="

# Use python -m to ensure correct pytest is found
python -m pytest /tests/test_outputs.py -rA -v
EXIT_CODE=$?

echo ""
echo "========================================="
echo "Writing results..."
echo "========================================="

mkdir -p /logs/verifier
if [ $EXIT_CODE -eq 0 ]; then
    echo '{"reward": 1.0}' > /logs/verifier/reward.json
    echo "✅ All tests passed!"
else
    echo '{"reward": 0.0}' > /logs/verifier/reward.json
    echo "❌ Tests failed!"
fi

exit $EXIT_CODE
