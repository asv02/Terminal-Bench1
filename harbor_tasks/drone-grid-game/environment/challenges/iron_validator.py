#!/usr/bin/env python3
"""
Validator for Iron Key Challenge - Einstein's Riddle
"""

import sys
from pathlib import Path

# The correct answer
CORRECT_ANSWER = "Japanese"

def main():
    if len(sys.argv) < 2:
        print("Usage: python iron_validator.py <solution_file>")
        sys.exit(1)

    solution_file = Path(sys.argv[1])

    if not solution_file.exists():
        print(f"Solution file not found: {solution_file}")
        sys.exit(1)

    answer = solution_file.read_text().strip()

    if answer == CORRECT_ANSWER:
        print(f"✅ Correct! The {CORRECT_ANSWER} researcher has the fish.")
        sys.exit(0)
    else:
        print(f"❌ Wrong answer: {answer}")
        print(f"Expected: {CORRECT_ANSWER}")
        sys.exit(1)

if __name__ == '__main__':
    main()
