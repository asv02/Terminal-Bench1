#!/usr/bin/env python3
"""
Validator for Crystal Key Challenge - Sokoban
"""

import sys
from pathlib import Path

# Level definition
LEVEL = [
    "########",
    "#      #",
    "# B  G #",
    "#      #",
    "# @    #",
    "#  B G #",
    "#      #",
    "########"
]

def parse_level(level_lines):
    """Parse level and extract positions."""
    player = None
    boxes = []
    goals = []
    walls = set()

    for y, line in enumerate(level_lines):
        for x, ch in enumerate(line):
            if ch == '#':
                walls.add((x, y))
            elif ch == '@':
                player = (x, y)
            elif ch == 'B':
                boxes.append((x, y))
            elif ch == 'G':
                goals.append((x, y))
            elif ch == '*':  # Box on goal
                boxes.append((x, y))
                goals.append((x, y))

    return player, boxes, set(goals), walls

def simulate_sokoban(level_lines, moves):
    """Simulate Sokoban moves and check if puzzle is solved."""
    player, boxes, goals, walls = parse_level(level_lines)
    boxes = set(boxes)

    move_delta = {
        'U': (0, -1),
        'D': (0, 1),
        'L': (-1, 0),
        'R': (1, 0)
    }

    for move in moves:
        if move not in move_delta:
            return False, f"Invalid move: {move}"

        dx, dy = move_delta[move]
        new_player = (player[0] + dx, player[1] + dy)

        # Check if moving into wall
        if new_player in walls:
            return False, f"Moved into wall at {new_player}"

        # Check if pushing a box
        if new_player in boxes:
            box_new = (new_player[0] + dx, new_player[1] + dy)

            # Check if box can be pushed
            if box_new in walls:
                return False, f"Pushed box into wall at {box_new}"
            if box_new in boxes:
                return False, "Cannot push two boxes at once"

            # Move box
            boxes.remove(new_player)
            boxes.add(box_new)

        # Move player
        player = new_player

    # Check if all goals are covered
    if boxes == goals:
        return True, "Solved!"
    else:
        return False, f"Not all boxes on goals. Boxes: {boxes}, Goals: {goals}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python crystal_validator.py <solution_file>")
        sys.exit(1)

    solution_file = Path(sys.argv[1])

    if not solution_file.exists():
        print(f"Solution file not found: {solution_file}")
        sys.exit(1)

    moves = solution_file.read_text().strip()

    # Validate moves
    valid_moves = set('UDLR')
    if not all(m in valid_moves for m in moves):
        print(f"Invalid moves in solution: {moves}")
        sys.exit(1)

    success, message = simulate_sokoban(LEVEL, moves)

    if success:
        print(f"✅ {message} (in {len(moves)} moves)")
        sys.exit(0)
    else:
        print(f"❌ {message}")
        sys.exit(1)

if __name__ == '__main__':
    main()
