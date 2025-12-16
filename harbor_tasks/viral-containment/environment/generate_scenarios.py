import json
import random

random.seed(1337)

BATCH_IDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa"]

# Constraint: letters must be between 'a' and 'j'
VALID_CHARS = "abcdefghij"

def generate_batch(batch_id):
    n = random.randint(50000, 100000)
        
    marker = random.choice(VALID_CHARS)
    
    fragments = [
        random.choice(VALID_CHARS) + random.choice(VALID_CHARS) 
        for _ in range(n)
    ]

    return {
        "id": batch_id,
        "fragments": fragments,
        "marker": marker
    }

scenarios = [generate_batch(bid) for bid in BATCH_IDS]

# Write to the file expected by instruction.md
with open("/app/restoration_batches.json", "w") as f:
    json.dump(scenarios, f, indent=4)