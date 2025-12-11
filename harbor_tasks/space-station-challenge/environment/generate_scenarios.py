import json
import random

random.seed(1337)

SCENARIO_IDS = ["alpha", "beta", "gamma", "epsilon", "zeta", "eta", "theta", "iota", "kappa", "lambda"]

def generate_case(case_id):
    n = random.randint(1, 10**5)

    return {
        "id": case_id,
        "hp": random.randint(1, 10**9),
        "damage": [random.randint(1, 10**4) for _ in range(n)],
        "requirement": [random.randint(1, 10**4) for _ in range(n)]
    }

scenarios = [generate_case(sid) for sid in SCENARIO_IDS]

output = {"scenarios": scenarios}

with open("/app/gauntlet_scenarios.json", "w") as f:
    json.dump(output, f, indent=4)