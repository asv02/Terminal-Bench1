#!/usr/bin/env python3
"""
Validator for Gold Key Challenge - Logic Puzzle
"""

import sys
import json
from pathlib import Path

# The correct solution
CORRECT_SOLUTION = {
    "1": ["K, R, Q", "K, Q, R", "R, K, Q", "R, Q, K", "Q, K, R", "Q, R, K"],
    "2": "Esteem",
    "3": "V",
    "4": "Travel Agent"
}

def main():
    if len(sys.argv) < 2:
        print("Usage: python gold_validator.py <solution_file>")
        sys.exit(1)

    solution_file = Path(sys.argv[1])

    if not solution_file.exists():
        print(f"Solution file not found: {solution_file}")
        sys.exit(1)

    try:
        answer = json.loads(solution_file.read_text())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)

    # Check if all questions are answered
    required_keys = {"1", "2", "3", "4"}  # ✅ FIXED
    if set(answer.keys()) != required_keys:
        print(f"Missing or extra keys. Expected: {required_keys}, Got: {set(answer.keys())}")
        sys.exit(1)

    # Check each answer
    if answer["1"] not in CORRECT_SOLUTION["1"]:  # ✅ FIXED - Check if in list
        print("❌ Wrong answer for Q1")
        print(f"Expected one of: {CORRECT_SOLUTION['1']}")
        print(f"Got: {answer['1']}")
        sys.exit(1)
    
    if answer["2"] != CORRECT_SOLUTION["2"]:
        print("❌ Wrong answer for Q2")
        sys.exit(1)
    
    if answer["3"] != CORRECT_SOLUTION["3"]:
        print("❌ Wrong answer for Q3")
        sys.exit(1)
    
    if answer["4"] != CORRECT_SOLUTION["4"]:
        print("❌ Wrong answer for Q4")
        sys.exit(1)

    print("✅ Correct solution!")
    sys.exit(0)

if __name__ == '__main__':
    main()