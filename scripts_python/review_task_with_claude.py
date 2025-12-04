#!/usr/bin/env python3
"""
Script to review Terminal-Bench tasks using Claude Agent SDK with the task reviewer skill.
The agent will automatically load the skill from .claude/skills/ and use tools to read files.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)


async def review_task_with_claude_agent(task_name: str, workspace_root: Path) -> str:
    """
    Use Claude Agent SDK to review a task using the reviewer skill.
    
    Args:
        task_name: Name of the task to review
        workspace_root: Path to the workspace root
    
    Returns:
        The review output from Claude
    """
    # Construct the review request
    # The agent will automatically use the terminal-bench-task-reviewer skill
    # and can read files from the task directory using tools
    task_path = f"snorkel-tb-tasks/tasks/{task_name}"
    
    user_message = f"""Use the terminal-bench-task-reviewer skill to review the task located at {task_path}.

IMPORTANT FORMATTING REQUIREMENTS:
1. Provide ONLY the final review report in your response
2. Do NOT include: intermediate steps, tool outputs, file listings, or debugging info
3. Use paths relative to workspace root that include the repository name
   - Format: 'snorkel-tb-tasks/tasks/hello-world/task.yaml'
   - NOT: '/home/runner/work/snorkel-tb-tasks/snorkel-tb-tasks/tasks/...'
   - NOT: 'tasks/hello-world/task.yaml' (missing repo name)
4. For ALL issues, warnings, and suggestions:
   - Show the exact file path and line numbers
   - Include "Current code:" with a code block showing the actual problematic code
   - Include "Required fix:" or "Suggested fix:" with a code block showing the corrected code
   - Provide an explanation of why the change is needed

The review must include these sections:
1. Status (PASS/WARNING/FAIL)
2. Summary
3. Critical Issues (with before/after code examples)
4. Warnings (with before/after code examples)
5. Suggestions (with before/after code examples)
6. Overall Assessment

Example format for issues:
**Issue Title**
- **File:** `snorkel-tb-tasks/tasks/task-name/file.ext` (lines X-Y)
- **Problem:** Description

**Current code:**
```language
actual problematic code here
```

**Required fix:**
```language
corrected code here
```

**Explanation:** Why this is needed"""

    # Configure agent options with project settings to enable skill discovery
    options = ClaudeAgentOptions(
        setting_sources=["user", "project"],  # Enable skill discovery from .claude/skills/
        max_turns=20,  # Should be enough for a review
        permission_mode="bypassPermissions",  # Auto-approve tool uses
    )
    
    # Run the agent and collect the review
    review_parts = []
    
    async with ClaudeSDKClient(options=options) as client:
        # Send the review request
        await client.query(user_message)
        
        # Collect text content from assistant messages
        async for msg in client.receive_response():
            # Extract text from AssistantMessage blocks
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        review_parts.append(block.text)
    
    # Join all text parts
    all_text = "\n\n".join(review_parts)
    
    # Extract the review report section (remove tool usage traces)
    review_markers = [
        "## Review Report:",
        "# Review Report:",
        "Review Report:",
    ]
    
    review_text = all_text
    for marker in review_markers:
        if marker in all_text:
            idx = all_text.find(marker)
            review_text = all_text[idx:]
            break
    
    return review_text


def format_for_github(review_output: str, task_name: str) -> str:
    """Format the review output for GitHub PR comments"""
    formatted = f"""## Task Review Report: `{task_name}`

---

{review_output}

---

<!-- claude-task-review-end -->
"""
    return formatted


async def main_async():
    """Async main function."""
    parser = argparse.ArgumentParser(
        description="Review Terminal-Bench tasks using Claude Agent SDK with the task reviewer skill"
    )
    parser.add_argument(
        "task",
        type=str,
        help="Task ID or path (e.g., 'my-task' or 'tasks/my-task')"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="task-review-comment.md",
        help="Output file for the review (default: task-review-comment.md)"
    )
    parser.add_argument(
        "--workspace-root",
        type=str,
        default=".",
        help="Path to the workspace root"
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Resolve paths
    workspace_root = Path(args.workspace_root).resolve()
    
    # Normalize task path
    task_name = args.task.replace("tasks/", "").strip()
    task_path = workspace_root / "tasks" / task_name
    
    if not task_path.exists():
        print(f"Error: Task directory not found at {task_path}", file=sys.stderr)
        print(f"Workspace root: {workspace_root}", file=sys.stderr)
        print(f"Task name: '{task_name}'", file=sys.stderr)
        print(f"Looking for: {task_path}", file=sys.stderr)
        print("\nAvailable tasks:", file=sys.stderr)
        tasks_dir = workspace_root / "tasks"
        if tasks_dir.exists():
            for item in sorted(tasks_dir.iterdir()):
                if item.is_dir():
                    print(f"  - {item.name}", file=sys.stderr)
        else:
            print(f"  ERROR: tasks/ directory not found at {tasks_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Reviewing task: {task_name}")
    print(f"Task path: {task_path}")
    print(f"Workspace root: {workspace_root}")
    print("Skills will be loaded automatically from .claude/skills/")
    
    try:
        review_output = await review_task_with_claude_agent(task_name, workspace_root)
    except Exception as e:
        print(f"Error running Claude Agent: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Format for GitHub
    formatted_review = format_for_github(review_output, task_name)
    
    # Write output
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(formatted_review)
    
    print(f"\n✅ Review completed and saved to {output_path}")
    
    # Also print to stdout for debugging
    print("\n" + "="*80)
    print("REVIEW OUTPUT")
    print("="*80)
    print(formatted_review)
    
    return 0


def main():
    """Main entry point that runs the async main function."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())

