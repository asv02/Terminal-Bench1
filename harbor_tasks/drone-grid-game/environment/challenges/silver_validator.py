#!/usr/bin/env python3
"""
Validator for Silver Key Challenge - RSA Small Exponent Attack
"""

import sys
from pathlib import Path

# The plaintext message
CORRECT_PLAINTEXT = "CRYSTAL_CLEAR_SECRET"

def main():
    if len(sys.argv) < 2:
        print("Usage: python silver_validator.py <solution_file>")
        sys.exit(1)

    solution_file = Path(sys.argv[1])

    if not solution_file.exists():
        print(f"Solution file not found: {solution_file}")
        sys.exit(1)

    answer = solution_file.read_text().strip()

    if answer == CORRECT_PLAINTEXT:
        print(f"✅ Correct! Decrypted message: {CORRECT_PLAINTEXT}")
        sys.exit(0)
    else:
        print("❌ Wrong plaintext")
        print(f"Expected: {CORRECT_PLAINTEXT}")
        print(f"Got: {answer}")
        sys.exit(1)

if __name__ == '__main__':
    main()
