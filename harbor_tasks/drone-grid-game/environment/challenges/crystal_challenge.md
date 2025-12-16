# Crystal Key Challenge: Sokoban Puzzle

## Problem Statement

Solve a Sokoban puzzle: push all boxes onto goal positions.

## Rules

- You control a player (@) on a grid
- Push boxes (B) onto goal positions (G)
- You can only PUSH boxes, not pull them
- You cannot push two boxes at once
- You cannot push a box into a wall
- A box is "solved" when it's on a goal position (shown as *)

## Level Layout

The level is defined in `/app/challenges/crystal_sokoban.txt`:

```
########
#      #
# B  G #
#      #
# @    #
#  B G #
#      #
########
```

Legend:
- `#` = Wall
- ` ` = Empty floor
- `@` = Player starting position
- `B` = Box
- `G` = Goal position
- `*` = Box on goal (during gameplay)

## Moves

- `U` = Move up
- `D` = Move down
- `L` = Move left
- `R` = Move right

When you move into a box, it pushes the box one square in that direction (if possible).

## Task

Find a sequence of moves that pushes all boxes onto goal positions.

## Output Format

Write your move sequence to `/app/solutions/crystal_moves.txt` as a single line of moves:

```
UURRDDLLUURRDL
```

## Constraints

- The puzzle has a solution
- Solutions under 100 moves exist
- Your solution will be validated by simulating the moves
- All boxes must be on goals at the end
- Invalid moves (into walls, pushing 2 boxes, etc.) will cause failure

## Example

For a simple puzzle:
```
####
#@B#
#  #
# G#
####
```

Solution: `DDDRUU` (push box right, then navigate and push it to goal)

**WARNING: Wrong answer or invalid moves = INSTANT DEATH!**
