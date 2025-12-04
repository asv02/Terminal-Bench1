#!/bin/bash
# Script to run Claude Code review locally before pushing to GitHub
# To run this script, you need to have the ANTHROPIC_API_KEY environment variable set.
# Usage: ./scripts_bash/local-claude-code-review.sh <task-name>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <task-name>"
    echo "Example: $0 hello-world"
    exit 1
fi

TASK="$1"

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY environment variable not set"
    echo ""
    echo "Set it with:"
    echo "  export ANTHROPIC_API_KEY='your-api-key'"
    exit 1
fi

# Check if task exists
if [ ! -d "tasks/$TASK" ]; then
    echo "❌ Error: Task 'tasks/$TASK' not found"
    exit 1
fi

# Check if skill file exists
SKILL_PATH=".claude/skills/terminal_bench_task_reviewer/SKILL.md"
if [ ! -f "$SKILL_PATH" ]; then
    echo "❌ Error: Skill file not found at $SKILL_PATH"
    exit 1
fi

echo "🔍 Reviewing task: $TASK"
echo "📁 Task path: tasks/$TASK"
echo "📝 Skill path: $SKILL_PATH"
echo ""

# Install dependencies if needed
if ! python3 -c "import claude_agent_sdk" 2>/dev/null; then
    echo "📦 Installing claude-agent-sdk package..."
    pip install claude-agent-sdk
    echo ""
fi

# Run the review
echo "🤖 Running Claude review..."
python3 scripts_python/review_task_with_claude.py "$TASK" \
    --output "local-review-$TASK.md"

echo ""
echo "✅ Review complete!"
echo "📄 Output saved to: local-review-$TASK.md"
echo ""
echo "To view the review:"
echo "  cat local-review-$TASK.md"
echo ""
echo "Or open it in your editor:"
echo "  \$EDITOR local-review-$TASK.md"

