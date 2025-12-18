import json
import random

random.seed(1234)

SCENARIO_IDS = [
    "sector-core-critical-mass",
    "sector-thermal-runaway",   
    "sector-magnetic-flux",     
    "sector-plasma-instability",
    "sector-containment-breach",
    "sector-harmonic-resonance",
    "sector-entropy-spike",     
    "sector-field-distortion"   
]

def generate_palindrome(limit):
    while True:

        bit_len = random.randint(1, 30)

        half_len = (bit_len + 1) // 2
        half_val = random.randint(1 << (half_len - 1), (1 << half_len) - 1)
        
        s = bin(half_val)[2:]
        if bit_len % 2 == 1:
            full_s = s + s[:-1][::-1]
        else:
            full_s = s + s[::-1]
        
        val = int(full_s, 2)
        if val <= limit:
            return val

def generate_case(case_id):
    n = 10000
    
    max_val = 10**9
    
    frequencies = []

    if case_id == "sector-core-critical-mass":
        frequencies = [max_val for _ in range(n)]

    elif case_id == "sector-thermal-runaway":
        frequencies = [random.randint(1, max_val) for _ in range(n)]

    elif case_id == "sector-magnetic-flux":
        frequencies = [max_val if i % 2 == 0 else 1 for i in range(n)]

    elif case_id == "sector-plasma-instability":
        lower_bound = int(max_val * 0.99)
        frequencies = [random.randint(lower_bound, max_val) for _ in range(n)]

    elif case_id == "sector-containment-breach":
        frequencies = [random.choice(range(200000, max_val, 2)) for _ in range(n)]

    elif case_id == "sector-harmonic-resonance":
        frequencies = [generate_palindrome(max_val) for _ in range(n)]

    elif case_id == "sector-entropy-spike":

        mid = max_val // 2
        span = 50000
        frequencies = [random.randint(mid - span, mid + span) for _ in range(n)]

    elif case_id == "sector-field-distortion":

        start = random.randint(100000, max_val - n)
        frequencies = list(range(start, start + n))
    
    else:

        frequencies = [random.randint(1, max_val) for _ in range(n)]

    return {
        "id": case_id,
        "frequencies": frequencies
    }

scenarios_list = [generate_case(sid) for sid in SCENARIO_IDS]

output = {"scenarios": scenarios_list}

with open("reactor_status.json", "w") as f:
    json.dump(output, f, indent=4)