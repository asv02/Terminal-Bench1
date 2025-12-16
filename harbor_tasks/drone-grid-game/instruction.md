# Game Instructions (Pits references removed)

You are controlling a drone in a 30×30 grid environment with limited visibility.
Your mission is to explore the grid, solve challenges to acquire keys, unlock chests
to collect coins, and return to the starting position.

## Environment

* **Grid size**: 30×30 cells
* **Starting position**: (0, 0)
* **Visibility**: You can only see a 3×3 area around your current position using PEEK

### Visibility and Exploration

Using `peek` reveals all hazards, keys, and chests within the 3×3 area centered on your current position.

You should assume:

* Moving into an unrevealed cell without peeking first is unsafe.
* Systematic exploration (peek → move → peek) is required to explore the map safely.

### Fixed Locations

The locations of all keys and chests are fixed and deterministic.

## Objective

Your goal is to:

1. Explore the grid to locate 5 keys and 5 chests
2. Solve the challenge associated with each key to acquire it
3. Match each key to its corresponding chest (using symbol matching)
4. Unlock all coin-containing chests (3 out of 5 chests contain coins)
5. Return to the starting position (0, 0) with all 3 coins

## Keys and Chests

There are 5 types of keys and chests, each with a unique symbol:

* **Ruby** (💎) - Red themed
* **Iron** (⚙️) - Gray themed
* **Gold** (👑) - Yellow themed
* **Silver** (⭐) - White themed
* **Crystal** (💠) - Blue themed

When you PEEK near a chest, you will see its symbol. You MUST use the matching key
to unlock each chest. Using the wrong key on a chest will result in INSTANT DEATH.

## Challenges

Each key requires solving a difficult challenge:

1. **Ruby Key** - Solve a hard graph algorithm problem (finding bridges in a network)
2. **Iron Key** - Solve Einstein's Riddle (a complex logic puzzle with 15 clues)
3. **Gold Key** - Solve a logical reasoning puzzle
4. **Silver Key** - Exploit a cryptographic vulnerability (RSA small exponent attack)
5. **Crystal Key** - Solve a Sokoban planning puzzle

You must navigate to each key's location before attempting its challenge.
Challenge descriptions are in `/app/challenges/<key>_challenge.md`.

## Commands

Use the game engine via: `/app/game_engine <command> [args]`

Available commands:

* `move <N|S|E|W>` - Move one step in a direction (North/South/East/West)
* `peek` - Reveal the 3×3 area around your current position
* `inventory` - View your acquired keys and collected coins
* `status` - Show your current position and game statistics
* `view_challenge <key_type>` - Read a challenge description (ruby|iron|gold|silver|crystal)
* `attempt_challenge <key_type>` - Submit your solution for a challenge (must be at key location)
* `unlock_chest <key_type>` - Unlock a chest with the specified key (must be at chest location)

## Solution File Requirements

For each challenge, you must create a solution file in `/app/solutions/`:

### Ruby Challenge

* **File**: `/app/solutions/ruby_solution.py`
* **Format**: Python file with function `find_bridges(n, edges)` that returns list of bridges
* **Example**:

  ```python
  def find_bridges(n, edges):
      # Your algorithm here
      return [[u, v], [x, y]]  # List of bridge edges
  ```

### Iron Challenge

* **File**: `/app/solutions/iron_answer.txt`
* **Format**: Single line with nationality (British, Swedish, Danish, Norwegian, or Japanese)
* **Example**: `Japanese`

### Gold Challenge

* **File**: `/app/solutions/gold_answer.json`
* **Format**: JSON object with answers to 4 questions about a logic puzzle
* **Exact Schema**:

```json
  {
    "1": "answer to question 1",
    "2": "answer to question 2",
    "3": "answer to question 3",
    "4": "answer to question 4"
  }
```

* **Required keys**: "1", "2", "3", "4" (exactly these 4 strings)
* **Question 1**: Who are the three ladies in the group? (format: "Name1, Name2, Name3" - any ordering is valid)
* **Question 2**: What car does Q own? (single car name)
* **Question 3**: Who owns the car Lancer? (single person name)
* **Question 4**: What is the profession of K? (single profession name)
* **Valid person names**: P, K, R, Q, J, V, X (case-sensitive)
* **Valid cars**: Alto, Corolla, Santro, Lancer, Ikon, Scorpio, Esteem (case-sensitive)
* **Valid professions**: Lawyer, Travel Agent, Air-hostess, Doctor, Professor, Consultant, Jeweller (case-sensitive)

### Silver Challenge

* **File**: `/app/solutions/silver_answer.txt`
* **Format**: Single line with decrypted plaintext string (ASCII text)
* **Example**: `CRYSTAL_CLEAR_SECRET`

### Crystal Challenge

* **File**: `/app/solutions/crystal_answer.txt`
* **Format**: Single line with move sequence using letters U (up), D (down), L (left), R (right)
* **Example**: `UURRDDLLUURR`

## Game State Files

The game maintains state in these JSON files (you can read them to check progress):

* **/app/game_state.json** - Current position, revealed areas, game_over flag, game_won flag
* **/app/inventory.json** - Acquired keys list and collected coins count
* **/app/game_log.json** - Complete action history with timestamps

### Coin Distribution

Out of the 5 chests, exactly 3 contain coins.

### Internal State (Informational)

The engine internally tracks:

* challenges_attempted
* chests_unlocked
* inventory (keys, coins)

These fields are used for verification and logging.
Agents must not modify these files manually.

`/app/game_engine verify`
Outputs a JSON summary verifying whether the agent has won the game.
This command is used for automated evaluation.

## Fatal Failure Conditions

The game will immediately end (`game_over = true` in `/app/game_state.json`) if you:

* Step into a revealed hazard cell (instant death)
* Submit a wrong answer for any challenge (no retries)
* Use the wrong key on a chest (e.g., using Ruby key on Iron chest)

When any fatal condition occurs:

* The `game_over` flag is set to true in `/app/game_state.json`
* The `game_over_reason` field contains the specific failure reason
* No further commands will be accepted

## Navigation Guarantees and Safety Rules

  This environment is deterministic and solvable with careful planning.
  **HINT** -Start with exploring the grid completely and finding the coordinates of keys and chests.Then return back to origin (0,0) and use A* algorithm to find a path that has all the keys as well chests for you to access them.

The following guarantees apply:

1. **There exists at least one safe path** from the start position (0, 0) to every key and chest.
2. The grid layout is fixed for the duration of the game.

You are expected to:

* Use `peek` very frequently (there is no limit to how many times you can use `peek`). Try using it every time you move.
* Maintain an internal memory of observed hazards
* Avoid moving into unrevealed cells without first peeking

## Success Criteria

You win when ALL of the following are true:

* All 5 keys have been acquired (by solving all 5 challenges correctly)
* All 3 coins have been collected (from ruby, iron, and crystal chests)
* You have returned to the starting position (0, 0)
* No fatal errors occurred during the game
* The existence of corresponding solution files for challenges (ruby_solution.py, gold_answer.json, silver_answer.txt, crystal_answer.txt) is checked by the test suite.

The game will set `game_won: true` in `/app/game_state.json` when these conditions are met.
