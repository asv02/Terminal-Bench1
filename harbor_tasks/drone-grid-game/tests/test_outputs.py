"""
Test suite for Drone Exploration task

This test suite validates all behaviors described in instruction.md:
- All 5 keys acquired by solving challenges correctly
- All 3 coins collected from correct chests
- Returned to starting position (0, 0)
- No fatal failures (wrong keys, failed challenges)
- Game won condition met
"""

import json
import pytest
from pathlib import Path


def test_game_state_file_exists():
    """Verify that /app/game_state.json was created by the game engine."""
    state_file = Path('/app/game_state.json')
    assert state_file.exists(), "game_state.json not found - game may not have started"


def test_inventory_file_exists():
    """Verify that /app/inventory.json was created by the game engine."""
    inventory_file = Path('/app/inventory.json')
    assert inventory_file.exists(), "inventory.json not found - game may not have started"


def test_game_not_failed():
    """
    Verify agent did not trigger fatal failure conditions.

    Checks that game_over is not true unless game was won.
    Fatal failures include: wrong challenge answers,
    using wrong key on chest.
    """
    state_file = Path('/app/game_state.json')
    assert state_file.exists(), "Game state file not found"

    with open(state_file, 'r') as f:
        state = json.load(f)

    # Check that game is not over due to failure
    if state.get('game_over', False) and not state.get('game_won', False):
        reason = state.get('game_over_reason', 'Unknown reason')
        pytest.fail(f"Game ended in failure: {reason}")


def test_game_won():
    """
    Verify agent successfully won the game.

    The game_won flag is set to true when all success criteria are met:
    - All 3 coins collected
    - Returned to (0, 0)
    - No fatal errors
    """
    import json
    import subprocess
    result = subprocess.check_output(
        ["/app/game_engine", "verify"],
        text=True
    )
    state = json.loads(result)

    assert state.get("game_won", False), "Agent did not win the game"


def test_all_coins_collected():
    """
    Verify agent collected all 3 required coins.

    Coins are obtained by unlocking the correct chests (ruby, iron, crystal).
    Gold and silver chests are empty.
    """
    inventory_file = Path('/app/inventory.json')

    with open(inventory_file, 'r') as f:
        inventory = json.load(f)

    coins_needed = inventory.get('coins_needed', 3)
    coins_collected = inventory.get('coins', 0)

    assert coins_collected >= coins_needed,         f"Not enough coins collected: {coins_collected}/{coins_needed}"


def test_returned_to_start():
    """
    Verify agent returned to starting position (0, 0).

    This is a required success criterion - agent must be at coordinates [0, 0]
    at the end of the game.
    """
    state_file = Path('/app/game_state.json')

    with open(state_file, 'r') as f:
        state = json.load(f)

    position = state.get('position', [])
    assert position == [0, 0],         f"Agent not at start position. Current: {position}, Expected: [0, 0]"


def test_all_keys_acquired():
    """
    Verify agent acquired all 5 keys by solving challenges.

    Keys are obtained by:
    1. Navigating to key location
    2. Creating solution file in /app/solutions/
    3. Calling attempt_challenge command
    4. Passing all validator tests

    Required keys: ruby, iron, gold, silver, crystal
    """
    inventory_file = Path('/app/inventory.json')

    with open(inventory_file, 'r') as f:
        inventory = json.load(f)

    keys = set(inventory.get('keys', []))
    expected_keys = {'ruby', 'iron', 'gold', 'silver', 'crystal'}

    assert keys == expected_keys,         f"Missing keys: {expected_keys - keys}, Extra keys: {keys - expected_keys}"


def test_coin_chests_unlocked():
    """
    Verify agent unlocked all coin-containing chests.

    Coin chests: ruby, iron, crystal
    Agent must use matching key on matching chest (wrong key = instant death).
    """
    state_file = Path('/app/game_state.json')

    with open(state_file, 'r') as f:
        state = json.load(f)

    unlocked = set(state.get('chests_unlocked', []))
    coin_chests = {'ruby', 'iron', 'crystal'}

    assert coin_chests.issubset(unlocked),         f"Not all coin chests unlocked. Missing: {coin_chests - unlocked}"


def test_no_environment_deaths():
    """
    Verify agent never died due to environment movement.

    Since pits are removed, no move action should result in a fatal
    environment-related failure.
    """
    log_file = Path('/app/game_log.json')

    if not log_file.exists():
        pytest.fail("Game log missing — agent must use engine actions")

    with open(log_file, 'r') as f:
        log = json.load(f)

    for action in log.get('actions', []):
        if action.get('action') == 'move':
            result = action.get('details', {}).get('result', '')
            assert result not in {
                'fell_into_pit',
                'invalid_move',
                'hit_hazard'
            }, f"Fatal move detected: {action['details']}"


def test_engine_verification():
    """
    Final authority: engine verify must confirm win.
    """
    import subprocess
    import json

    result = subprocess.check_output(
        ['/app/game_engine', 'verify'],
        text=True
    )

    data = json.loads(result)
    assert data.get('game_won') is True, "Engine did not verify win"


def test_no_wrong_key_attempts():
    """
    Verify agent never used wrong key on wrong chest.

    Each chest requires its matching key (e.g., ruby key for ruby chest).
    Using wrong key results in instant death with result "WRONG_KEY_FATAL".
    """
    log_file = Path('/app/game_log.json')

    if not log_file.exists():
        pytest.skip("Game log not found")

    with open(log_file, 'r') as f:
        log = json.load(f)

    for action in log.get('actions', []):
        if action.get('action') == 'unlock_chest':
            result = action.get('details', {}).get('result', '')
            assert result != 'WRONG_KEY_FATAL', f"Agent used wrong key on chest: {action['details']}"


def test_all_challenges_attempted():
    """
    Verify agent attempted all 5 challenges.

    Each key requires solving a challenge:
    - Ruby: Graph bridges algorithm
    - Iron: Einstein's riddle logic puzzle
    - Gold: Knights & Knaves logic puzzle
    - Silver: RSA cryptography attack
    - Crystal: Sokoban planning puzzle
    """
    state_file = Path('/app/game_state.json')

    with open(state_file, 'r') as f:
        state = json.load(f)

    challenges = set(state.get('challenges_attempted', []))
    expected = {'ruby', 'iron', 'gold', 'silver', 'crystal'}

    assert challenges == expected,         f"Not all challenges attempted. Missing: {expected - challenges}"


def test_ruby_solution_file_exists():
    """Verify Ruby challenge solution file was created at /app/solutions/ruby_solution.py"""
    solution_file = Path('/app/solutions/ruby_solution.py')
    assert solution_file.exists(), "Ruby solution file not found"


def test_iron_solution_file_exists():
    """Verify Iron challenge solution file was created at /app/solutions/iron_answer.txt"""
    solution_file = Path('/app/solutions/iron_answer.txt')
    assert solution_file.exists(), "Iron solution file not found"


def test_gold_solution_file_exists():
    """Verify Gold challenge solution file was created at /app/solutions/gold_answer.json"""
    solution_file = Path('/app/solutions/gold_answer.json')
    assert solution_file.exists(), "Gold solution file not found"


def test_silver_solution_file_exists():
    """Verify Silver challenge solution file was created at /app/solutions/silver_answer.txt"""
    solution_file = Path('/app/solutions/silver_answer.txt')
    assert solution_file.exists(), "Silver solution file not found"


def test_crystal_solution_file_exists():
    """Verify Crystal challenge solution file was created at /app/solutions/crystal_answer.txt"""
    solution_file = Path('/app/solutions/crystal_answer.txt')
    assert solution_file.exists(), "Crystal solution file not found"


def test_gold_solution_valid_json():
    """
    Verify Gold challenge solution has valid JSON format.

    Required format:
    {
      "1": "K, Q, R",
      "2": "Esteem",
      "3": "P",
      "4": "Air-hostess"
    }
    """
    solution_file = Path('/app/solutions/gold_answer.json')

    if not solution_file.exists():
        pytest.skip("Gold solution file not found")

    try:
        with open(solution_file, 'r') as f:
            data = json.load(f)

        # Check required keys
        required_keys = {'1', '2', '3', '4'}
        assert set(data.keys()) == required_keys,             f"Invalid keys in JSON. Expected: {required_keys}, Got: {set(data.keys())}"

    except json.JSONDecodeError as e:
        pytest.fail(f"Gold solution is not valid JSON: {e}")
