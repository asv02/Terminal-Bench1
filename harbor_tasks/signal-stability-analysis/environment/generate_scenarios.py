import json
import random

random.seed(42)

SCENARIO_IDS = [
    "net-log-saturation-heavy",   
    "net-log-packet-storm",       
    "net-log-latency-spike",      
    "net-log-signal-decay",       
    "net-log-buffer-bloat",       
    "net-log-jitter-high",        
    "net-log-collision-dups",     
    "net-log-sequence-drift"      
]

def generate_case(case_id):
    n = 100000 
    
    stream = []
    k = random.randint(n // 10, n // 2)

    if case_id == "net-log-saturation-heavy":
        stream = [random.randint(1, 10**9) for _ in range(n)]
        k = 25000

    elif case_id == "net-log-packet-storm":
        stream = [random.randint(1, 10**9) for _ in range(n)]
        k = 90000

    elif case_id == "net-log-latency-spike":
        stream = list(range(n, 0, -1))
        k = 10000

    elif case_id == "net-log-signal-decay":
        stream = list(range(n))
        k = 10000

    elif case_id == "net-log-buffer-bloat":
        stream = [random.randint(1, 10**9) for _ in range(n)]
        k = 500

    elif case_id == "net-log-jitter-high":
        stream = [10**9 if i % 2 == 0 else 1 for i in range(n)]
        k = 5000

    elif case_id == "net-log-collision-dups":
        stream = [random.choice([10, 20, 30, 40, 50]) for _ in range(n)]
        k = 10000

    elif case_id == "net-log-sequence-drift":
        stream = [random.randint(1, 1000) for _ in range(n)]
        k = 20000
    
    else:
        stream = [random.randint(1, 10**9) for _ in range(n)]

    return {
        "id": case_id,
        "stream": stream,
        "window_size": k
    }

scenarios_list = [generate_case(sid) for sid in SCENARIO_IDS]

output = scenarios_list

with open("transmission_logs.json", "w") as f:
    json.dump(output, f, indent=4)