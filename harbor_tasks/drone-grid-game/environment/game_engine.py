#!/usr/bin/env python3
"""
Drone Exploration Game Engine
A 30x30 grid-based exploration game with challenges, keys, and chests.
"""
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

# Game Constants
GRID_SIZE = 30
START_POS = (0, 0)

# Cell Types
EMPTY = '.'
KEY = 'K'
CHEST = 'C'
PLAYER = '@'

# Key-Chest Mapping
KEY_TYPES = {
    'ruby': {'symbol': '💎', 'color': 'red'},
    'iron': {'symbol': '⚙️', 'color': 'gray'},
    'gold': {'symbol': '👑', 'color': 'yellow'},
    'silver': {'symbol': '⭐', 'color': 'white'},
    'crystal': {'symbol': '💠', 'color': 'blue'}
}

# Fixed positions for keys and chests on 30x30 grid
FIXED_KEYS = {
    'ruby': (5, 8),
    'iron': (12, 22),
    'gold': (28, 5),
    'silver': (18, 15),
    'crystal': (7, 28)
}

FIXED_CHESTS = {
    'ruby': (25, 12),
    'iron': (3, 25),
    'gold': (15, 3),
    'silver': (29, 28),
    'crystal': (10, 18)
}

# Which chests contain coins (3 out of 5)
COIN_CHESTS = {'ruby', 'iron', 'crystal'}  # gold and silver are empty
_ENGINE_SECRET = "drone-grid-secret-v1"


class GameEngine:
    def __init__(self):
        self.grid = self._initialize_grid()
        self.state_file = Path('/app/game_state.json')
        self.inventory_file = Path('/app/inventory.json')
        self.log_file = Path('/app/game_log.json')
        self.grid_width = 30
        self.grid_height = 30
        self._state = {
            "position": (0, 0),
            "keys": set(),
            "coins": 0,
            "challenges_attempted": set(),
            "chests_unlocked": set(),
            "fatal_error": False,
        }
        # Load or initialize state
        if self.state_file.exists():
            self.load_state()
        else:
            self.initialize_new_game()

    def _initialize_grid(self) -> List[List[str]]:
        """Create the fixed 30x30 grid with all elements."""
        grid = [[EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]


        # Place keys
        for key_type, (x, y) in FIXED_KEYS.items():
            grid[y][x] = f'K_{key_type}'

        # Place chests
        for chest_type, (x, y) in FIXED_CHESTS.items():
            grid[y][x] = f'C_{chest_type}'

        return grid

    def _state_digest(self):
        payload = json.dumps({
            "position": self.state["position"],
            "coins": self.inventory["coins"],
            "keys": sorted(self.inventory["keys"]),
            "chests": sorted(self.state["chests_unlocked"]),
            "fatal": self.state.get("fatal_error", False),
        }, sort_keys=True)
        return hashlib.sha256(
            (_ENGINE_SECRET + payload).encode()
        ).hexdigest()

    def initialize_new_game(self):
        """Initialize a fresh game state."""
        self.state = {
            'position': list(START_POS),
            'revealed': {},
            'game_over': False,
            'game_won': False,
            'game_over_reason': None,
            'challenges_attempted': [],
            'chests_unlocked': []
        }

        self.inventory = {
            'keys': [],
            'coins': 0,
            'coins_needed': len(COIN_CHESTS)
        }

        self.log = {
            'actions': [],
            'total_moves': 0
        }

        # Reveal starting position
        self.reveal_area(START_POS[0], START_POS[1])

        self.save_state()

    def reveal_area(self, x, y):
        """Reveal a cell in the grid."""
        if not (0 <= x < self.grid_width and 0 <= y < self.grid_height):
            return
        
        # Get grid coordinates
        ny, nx = y, x  # or however your code defines these
        
        # Auto-create nested dict if row doesn't exist
        if ny not in self.state['revealed']:
            self.state['revealed'][ny] = {}
        
        # Now safe to set the value
        self.state['revealed'][ny][nx] = True

    def save_state(self):
        """Save current game state to files."""
        self.state["_digest"] = self._state_digest()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

        with open(self.inventory_file, 'w') as f:
            json.dump(self.inventory, f, indent=2)

        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=2)

    def load_state(self):
        """Load existing game state or reinitialize if corrupted/empty."""
        try:
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)

            with open(self.inventory_file, 'r') as f:
                self.inventory = json.load(f)

            with open(self.log_file, 'r') as f:
                self.log = json.load(f)

        except (json.JSONDecodeError, FileNotFoundError):
            # State files exist but are empty or corrupted
            self.initialize_new_game()


    def log_action(self, action: str, details: Dict):
        """Log an action to the game log."""
        self.log['actions'].append({
            'action': action,
            'details': details,
            'position': self.state['position'].copy()
        })
        self.save_state()

    def game_over(self, reason: str):
        """End the game with a failure reason."""
        self.state['game_over'] = True
        self.state['game_over_reason'] = reason
        self.save_state()
        print(f"💀 GAME OVER: {reason}")
        sys.exit(1)

    def check_win_condition(self):
        """Check if player has won."""
        if (self.inventory['coins'] >= self.inventory['coins_needed'] and 
            tuple(self.state['position']) == START_POS):
            self.state['game_won'] = True
            self.state["fatal_error"] = False
            self.save_state()
            print("🎉 YOU WIN! All coins collected and returned to start!")
            return True
        return False

    def move(self, direction: str):
        """Move the player in a direction."""
        if self.state['game_over']:
            print("Game is already over!")
            return

        x, y = self.state['position']

        moves = {
            'N': (0, -1),
            'S': (0, 1),
            'E': (1, 0),
            'W': (-1, 0)
        }

        if direction not in moves:
            print(f"Invalid direction: {direction}. Use N, S, E, or W")
            return

        dx, dy = moves[direction]
        new_x, new_y = x + dx, y + dy

        # Check bounds
        if not (0 <= new_x < GRID_SIZE and 0 <= new_y < GRID_SIZE):
            print("Cannot move outside the grid!")
            return


        # Move player
        self.state['position'] = [new_x, new_y]
        self.log['total_moves'] += 1


        self.log_action('move', {'direction': direction, 'from': [x, y], 'to': [new_x, new_y]})
        self.save_state()
        self.check_win_condition()
        print(f"Moved {direction} to ({new_x}, {new_y})")

    def peek(self):
        """Reveal 3x3 area around current position."""
        if self.state['game_over']:
            print("Game is already over!")
            return

        x, y = self.state['position']
        self.reveal_area(x, y)

        # Show what's visible
        print(f"\n📡 PEEK at position ({x}, {y}):")
        print("=" * 40)

        visible_items = []
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                    cell = self.grid[ny][nx]

                    if cell.startswith('K_'):
                        key_type = cell.split('_')[1]
                        visible_items.append(f"  🔑 {key_type.upper()} KEY at ({nx}, {ny})")
                    elif cell.startswith('C_'):
                        chest_type = cell.split('_')[1]
                        symbol = KEY_TYPES[chest_type]['symbol']
                        color = KEY_TYPES[chest_type]['color']
                        print(color)
                        visible_items.append(f"  📦 CHEST at ({nx}, {ny}) - requires {chest_type.upper()} KEY {symbol}")

        if visible_items:
            print("\n".join(visible_items))
        else:
            print("  Nothing special nearby - just empty terrain")

        print("=" * 40)

        self.log_action('peek', {'position': [x, y]})
        self.save_state()

    def view_inventory(self):
        """Display current inventory."""
        print("\n🎒 INVENTORY:")
        print("=" * 40)
        print(f"Keys acquired: {len(self.inventory['keys'])}/5")
        for key in self.inventory['keys']:
            symbol = KEY_TYPES[key]['symbol']
            print(f"  🔑 {key.upper()} KEY {symbol}")
        print(f"\nCoins collected: {self.inventory['coins']}/{self.inventory['coins_needed']}")
        print("=" * 40)

    def status(self):
        """Show game status."""
        x, y = self.state['position']
        print("\n📊 STATUS:")
        print("=" * 40)
        print(f"Position: ({x}, {y})")
        print(f"Start position: {START_POS}")
        print(f"Keys: {len(self.inventory['keys'])}/5")
        print(f"Coins: {self.inventory['coins']}/{self.inventory['coins_needed']}")
        print(f"Total moves: {self.log['total_moves']}")
        print(f"Challenges attempted: {len(self.state['challenges_attempted'])}")
        print(f"Chests unlocked: {len(self.state['chests_unlocked'])}")
        print("=" * 40)

    def view_challenge(self, key_type: str):
        """Display challenge problem statement."""
        if key_type not in KEY_TYPES:
            print(f"Invalid key type: {key_type}")
            return

        challenge_file = Path(f'/app/challenges/{key_type}_challenge.md')
        if challenge_file.exists():
            print(f"\n📜 {key_type.upper()} KEY CHALLENGE:")
            print("=" * 60)
            print(challenge_file.read_text())
            print("=" * 60)
        else:
            print(f"Challenge file not found: {challenge_file}")

    def attempt_challenge(self, key_type: str):
        """Attempt to solve a challenge and acquire a key."""
        if self.state['game_over']:
            print("Game is already over!")
            return

        if key_type not in KEY_TYPES:
            print(f"Invalid key type: {key_type}")
            return

        # Already have key
        if key_type in self.inventory['keys']:
            print(f"You already have the {key_type.upper()} KEY!")
            return

        # Must be at key location
        x, y = self.state['position']
        if (x, y) != FIXED_KEYS[key_type]:
            print(f"You must be at the {key_type.upper()} KEY location {FIXED_KEYS[key_type]} to attempt this challenge!")
            print(f"Current position: ({x}, {y})")
            return

        # Determine solution file
        if key_type == "ruby":
            solution_file = Path(f"/app/solutions/{key_type}_solution.py")
        elif key_type == "gold":
            solution_file = Path(f"/app/solutions/{key_type}_answer.json")
        else:
            solution_file = Path(f"/app/solutions/{key_type}_answer.txt")

        if not solution_file.exists():
            print(f"❌ No solution file found at {solution_file}")
            print("Please create your solution first!")
            return

        # Locate validator (compiled preferred, python fallback)
        validator_bin = Path(f"/app/challenges/{key_type}_validator")
        validator_py = Path(f"/app/challenges/{key_type}_validator.py")

        if validator_bin.exists():
            cmd = [str(validator_bin), str(solution_file)]
        elif validator_py.exists():
            cmd = ["python3", str(validator_py), str(solution_file)]
        else:
            # This should NEVER happen in final submission
            print("❌ Validator missing — challenge system broken")
            self.game_over("Validator missing — cannot verify solution")
            return

        # Run validator
        import subprocess
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            self.inventory['keys'].append(key_type)
            self.state['challenges_attempted'].append(key_type)
            self.log_action(
                'attempt_challenge',
                {'key_type': key_type, 'result': 'success'}
            )
            self.save_state()
            print(f"✅ Challenge completed! Acquired {key_type.upper()} KEY {KEY_TYPES[key_type]['symbol']}!")
        else:
            self.log_action(
                'attempt_challenge',
                {
                    'key_type': key_type,
                    'result': 'failed',
                    'error': result.stderr.strip()
                }
            )
            self.game_over(
                f"Failed {key_type.upper()} challenge:\n{result.stderr}"
            )


    def unlock_chest(self, key_type: str):
        """Unlock a chest using a key - WRONG KEY = INSTANT DEATH."""
        if self.state['game_over']:
            print("Game is already over!")
            return

        if key_type not in KEY_TYPES:
            print(f"Invalid key type: {key_type}")
            return

        # Check if have the key
        if key_type not in self.inventory['keys']:
            print(f"You don't have the {key_type.upper()} KEY!")
            return

        # Get current position
        x, y = self.state['position']

        # CRITICAL: Check if trying to use wrong key on wrong chest (INSTANT DEATH)
        for chest_type, chest_pos in FIXED_CHESTS.items():
            if (x, y) == chest_pos:
                # Found a chest at current position
                if chest_type != key_type:
                    # WRONG KEY - FATAL ERROR!
                    self.log_action('unlock_chest', {
                        'attempted_key': key_type,
                        'actual_chest_type': chest_type,
                        'position': [x, y],
                        'result': 'WRONG_KEY_FATAL'
                    })
                    self.game_over(
                        f"Used {key_type.upper()} KEY on {chest_type.upper()} CHEST at ({x}, {y})! "
                        f"Wrong key = INSTANT DEATH!"
                    )
                    return

        # Check if at correct chest location
        chest_pos = FIXED_CHESTS[key_type]

        if (x, y) != chest_pos:
            print(f"No {key_type.upper()} CHEST at current position!")
            print(f"You must be at {chest_pos} to unlock the {key_type.upper()} CHEST")
            print(f"Current position: ({x}, {y})")
            return

        # Check if already unlocked
        if key_type in self.state['chests_unlocked']:
            print("This chest has already been unlocked!")
            return

        # SUCCESS: Correct key on correct chest
        self.state['chests_unlocked'].append(key_type)

        # Check if contains coin
        if key_type in COIN_CHESTS:
            self.inventory['coins'] += 1
            print(f"✅ Unlocked {key_type.upper()} CHEST with {key_type.upper()} KEY!")
            print(f"🪙 Found a COIN! Total coins: {self.inventory['coins']}/{self.inventory['coins_needed']}")
        else:
            print(f"✅ Unlocked {key_type.upper()} CHEST with {key_type.upper()} KEY!")
            print("📭 Chest was empty - no coin inside")

        self.log_action('unlock_chest', {
            'key_type': key_type,
            'position': [x, y],
            'contained_coin': key_type in COIN_CHESTS,
            'result': 'SUCCESS'
        })
        self.save_state()

        # Check win condition
        self.check_win_condition()

    def verify_game(self):
        import json

        expected = self._state_digest()
        stored = self.state.get("_digest")

        if stored != expected:
            print(json.dumps({
                "game_won": False,
                "fatal_error": True,
                "tampered": True
            }))
            return

        coins = self.inventory["coins"]
        returned = (self.state["position"] == [0, 0])

        print(json.dumps({
            "game_won": coins == 3 and returned,
            "coins_collected": coins,
            "returned_to_origin": returned,
            "fatal_error": False
        }))




def main():
    if len(sys.argv) < 2:
        print("Usage: python game_engine.py <command> [args]")
        print("Commands: move, peek, inventory, status, view_challenge, attempt_challenge, unlock_chest")
        sys.exit(1)

    engine = GameEngine()
    command = sys.argv[1].lower()

    if command == 'move':
        if len(sys.argv) < 3:
            print("Usage: python game_engine.py move <N|S|E|W>")
            sys.exit(1)
        engine.move(sys.argv[2].upper())

    elif command == 'peek':
        engine.peek()

    elif command == 'inventory':
        engine.view_inventory()

    elif command == 'status':
        engine.status()

    elif command == 'view_challenge':
        if len(sys.argv) < 3:
            print("Usage: python game_engine.py view_challenge <ruby|iron|gold|silver|crystal>")
            sys.exit(1)
        engine.view_challenge(sys.argv[2].lower())

    elif command == 'attempt_challenge':
        if len(sys.argv) < 3:
            print("Usage: python game_engine.py attempt_challenge <ruby|iron|gold|silver|crystal>")
            sys.exit(1)
        engine.attempt_challenge(sys.argv[2].lower())

    elif command == 'unlock_chest':
        if len(sys.argv) < 3:
            print("Usage: python game_engine.py unlock_chest <ruby|iron|gold|silver|crystal>")
            sys.exit(1)
        engine.unlock_chest(sys.argv[2].lower())
    
    elif command == "verify":
        engine.verify_game()


    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
