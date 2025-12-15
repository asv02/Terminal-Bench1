#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.

set -euo pipefail

python3 << 'EOF'
import json

def calculate_min_moves_greedy(balances: list[int]) -> int:
    current_balances = balances[:]
    num_houses = len(current_balances)

    deficit_house_index = -1
    for i, balance in enumerate(current_balances):
        if balance < 0:
            deficit_house_index = i
            break

    if deficit_house_index == -1:
        return 0

    if sum(current_balances) < 0:
        return -1

    total_moves = 0
    distance = 0

    while current_balances[deficit_house_index] < 0:
        distance += 1

        right_neighbor_index = (deficit_house_index + distance) % num_houses
        left_neighbor_index = (deficit_house_index - distance) % num_houses

        potential_supply = (current_balances[right_neighbor_index] +
                            current_balances[left_neighbor_index])

        remaining_deficit = -current_balances[deficit_house_index]
        amount_to_transfer = min(remaining_deficit, potential_supply)

        total_moves += amount_to_transfer * distance

        current_balances[deficit_house_index] += potential_supply

    return total_moves


INPUT_FILE = "cargo_balance.json"
OUTPUT_FILE = "cargo_report.txt"

with open(INPUT_FILE, 'r') as f:
    data = json.load(f)

scenario_results = []

for scenario in data.get("scenarios", []):
    scenario_id = scenario.get("id")
    balance_list = scenario.get("balance")

    if scenario_id and balance_list is not None:
        moves_required = calculate_min_moves_greedy(balance_list)
        scenario_results.append((scenario_id, moves_required))

scenario_results.sort(key=lambda item: item[0])

with open(OUTPUT_FILE, "w") as f:
    for scenario_id, moves_required in scenario_results:
        f.write(f"{scenario_id} {moves_required}\n")

EOF
