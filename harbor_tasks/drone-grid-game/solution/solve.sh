#!/bin/bash
# CANARY_STRING: drone_exploration_2025
# Generated optimal solution for Drone Exploration task

set -e  # Exit on any error

echo "=== Starting Drone Exploration Challenge ==="

# 1. Recon
/app/game_engine peek
/app/game_engine status

echo ""
echo "=== Phase 1: Ruby Key at (5, 8) ==="
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move E
/app/game_engine move S
/app/game_engine move S
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E

# FIXED: Pure Python solution (No 'import collections') to avoid Nuitka import errors
cat > /app/solutions/ruby_solution.py << 'RUBY_EOF'
def find_bridges(n, edges):
    # Pure python graph construction
    graph = {}
    for i in range(n):
        graph[i] = []
    for u, v in edges:
        graph[u].append(v)
        graph[v].append(u)
        
    visited = [False] * n
    disc = [0] * n
    low = [0] * n
    parent = [-1] * n
    bridges = []
    timer = [0]
    
    def dfs(u):
        visited[u] = True
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        
        for v in graph[u]:
            if not visited[v]:
                parent[v] = u
                dfs(v)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    # Ensure consistent ordering for validator
                    if u < v: bridges.append([u, v])
                    else: bridges.append([v, u])
            elif v != parent[u]:
                low[u] = min(low[u], disc[v])
                
    for i in range(n):
        if not visited[i]:
            dfs(i)
            
    # Sort for validator
    bridges.sort()
    return bridges
RUBY_EOF

/app/game_engine attempt_challenge ruby

echo ""
echo "=== Phase 2: Iron Key at (12, 22) ==="
/app/game_engine move S
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E

python3 << 'IRON_EOF'
from itertools import permutations

N = ["British","Swedish","Danish","Norwegian","Japanese"]
C = ["red","green","white","yellow","blue"]
P = ["dog","bird","cat","horse","fish"]
D = ["tea","coffee","milk","orange juice","water"]
M = ["GPT","Claude","Gemini","LLaMA","Mistral"]

for n in permutations(N):
    if n[0] != "Norwegian": continue
    for c in permutations(C):
        if c[n.index("British")] != "red": continue
        if c.index("green")+1 != c.index("white"): continue
        if abs(c.index("blue") - n.index("Norwegian")) != 1: continue
        for p in permutations(P):
            if p[n.index("Swedish")] != "dog": continue
            for d in permutations(D):
                if d[n.index("Danish")] != "tea": continue
                if d[c.index("green")] != "coffee": continue
                if d[2] != "milk": continue
                for m in permutations(M):
                    if m[c.index("yellow")] != "Claude": continue
                    if p[m.index("GPT")] != "bird": continue
                    if m[n.index("Japanese")] != "Mistral": continue
                    if d[m.index("LLaMA")] != "orange juice": continue
                    if abs(p.index("horse") - m.index("Claude")) != 1: continue
                    if abs(m.index("Gemini") - p.index("cat")) != 1: continue
                    if not any(abs(m.index("Gemini") - i)==1 and d[i]=="water" for i in range(5)): continue

                    owner = n[p.index("fish")]
                    open("/app/solutions/iron_answer.txt","w").write(owner)
                    exit()
IRON_EOF

/app/game_engine attempt_challenge iron


echo ""
echo "=== Phase 3: Gold Key at (28, 5) ==="
/app/game_engine move N
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move E
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move E
/app/game_engine move E
/app/game_engine move N

# 🔹 GOLD: Logic Puzzle Solver - Professions and Cars
python3 << 'GOLD_EOF'
import json
from itertools import permutations, combinations
from pathlib import Path

# People, professions, and cars
PEOPLE = ["P", "K", "R", "Q", "J", "V", "X"]
PROFESSIONS = ["Lawyer", "Travel Agent", "Air-hostess", "Doctor", "Professor", "Consultant", "Jeweller"]
CARS = ["Alto", "Corolla", "Santro", "Lancer", "Ikon", "Scorpio", "Esteem"]

def check_solution(person_prof, person_car, ladies):
    """Check if assignment satisfies all constraints"""
    
    def prof(p): return person_prof[p]
    def car(p): return person_car[p]
    
    # Constraint: None of the ladies is a Consultant or a Lawyer
    for lady in ladies:
        if prof(lady) in ["Consultant", "Lawyer"]:
            return False
    
    # Constraint: R is an Air-hostess (she) and owns Ikon
    if prof("R") != "Air-hostess" or car("R") != "Ikon":
        return False
    if "R" not in ladies:  # R is explicitly "she"
        return False
    
    # Constraint: P owns Scorpio
    if car("P") != "Scorpio":
        return False
    
    # Constraint: K is not a Doctor
    if prof("K") == "Doctor":
        return False
    
    # Constraint: J is a Jeweller (he) and owns Corolla
    if prof("J") != "Jeweller" or car("J") != "Corolla":
        return False
    if "J" in ladies:  # J is explicitly "he" - MALE
        return False
    
    # Constraint: V is a Lawyer and does not own Alto
    if prof("V") != "Lawyer" or car("V") == "Alto":
        return False
    
    # Constraint: X is a Consultant and owns Santro
    if prof("X") != "Consultant" or car("X") != "Santro":
        return False
    
    # Constraint: The Doctor owns Esteem car
    doctor = [p for p in PEOPLE if prof(p) == "Doctor"]
    if len(doctor) != 1 or car(doctor[0]) != "Esteem":
        return False
    
    # Constraint: The Professor owns Scorpio
    professor = [p for p in PEOPLE if prof(p) == "Professor"]
    if len(professor) != 1 or car(professor[0]) != "Scorpio":
        return False
    
    # Constraint: The Travel Agent owns Alto
    travel_agent = [p for p in PEOPLE if prof(p) == "Travel Agent"]
    if len(travel_agent) != 1 or car(travel_agent[0]) != "Alto":
        return False
    
    # Constraint: None of the ladies owns Scorpio
    for lady in ladies:
        if car(lady) == "Scorpio":
            return False
    
    # Constraint: 3 ladies, 4 men
    if len(ladies) != 3:
        return False
    
    return True

# Pre-assign known facts
fixed_prof = {"R": "Air-hostess", "J": "Jeweller", "V": "Lawyer", "X": "Consultant"}
fixed_car = {"R": "Ikon", "P": "Scorpio", "J": "Corolla", "X": "Santro"}

remaining_people = [p for p in PEOPLE if p not in fixed_prof]
remaining_profs = [pr for pr in PROFESSIONS if pr not in fixed_prof.values()]
remaining_cars_people = [p for p in PEOPLE if p not in fixed_car]
remaining_cars = [c for c in CARS if c not in fixed_car.values()]

print("Searching for solution...")
solutions = []

# Try all possible lady combinations (3 out of 7)
for ladies in combinations(PEOPLE, 3):
    ladies = set(ladies)
    
    # Try all profession assignments
    for prof_perm in permutations(remaining_profs):
        person_prof = fixed_prof.copy()
        for i, person in enumerate(remaining_people):
            person_prof[person] = prof_perm[i]
        
        # Try all car assignments
        for car_perm in permutations(remaining_cars):
            person_car = fixed_car.copy()
            for i, person in enumerate(remaining_cars_people):
                person_car[person] = car_perm[i]
            
            if check_solution(person_prof, person_car, ladies):
                solutions.append({
                    "ladies": sorted(ladies),
                    "professions": person_prof,
                    "cars": person_car
                })

if len(solutions) != 1:
    print(f"Found {len(solutions)} solutions:")
    for sol in solutions:
        print(sol)
    raise RuntimeError(f"Expected 1 solution, found {len(solutions)}")

# Extract the unique solution
sol = solutions[0]
print(f"\n✅ Found unique solution!")
print(f"Ladies: {', '.join(sol['ladies'])}")
print(f"\nProfessions: {sol['professions']}")
print(f"Cars: {sol['cars']}")

# Answer the questions
ladies_str = ", ".join(sorted(sol['ladies']))
q_car = sol['cars']['Q']
lancer_owner = [p for p, c in sol['cars'].items() if c == "Lancer"][0]
k_profession = sol['professions']['K']

answer = {
    "1": ladies_str,
    "2": q_car,
    "3": lancer_owner,
    "4": k_profession
}

# Write solution
Path("/app/solutions").mkdir(parents=True, exist_ok=True)
with open("/app/solutions/gold_answer.json", "w") as f:
    json.dump(answer, f, indent=2)

print(f"\n📝 Answer written:")
print(json.dumps(answer, indent=2))
GOLD_EOF

/app/game_engine attempt_challenge gold

echo ""
echo "=== Phase 4: Silver Key at (18, 15) ==="
/app/game_engine move S
/app/game_engine move W
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S

# Silver challenge: Decrypt RSA (System Python can be used here)
cat > /tmp/decrypt_silver.py << 'SILVER_EOF'
with open('/app/challenges/silver_rsa.txt', 'r') as f:
    lines = f.readlines()
    N = int(lines[0].split(' = ')[1])
    e = int(lines[1].split(' = ')[1])
    ciphertext = int(lines[2].split(' = ')[1])
def integer_cube_root(n):
    if n == 0: return 0
    low, high = 0, n
    while low <= high:
        mid = (low + high) // 2
        cube = mid ** 3
        if cube == n: return mid
        elif cube < n: low = mid + 1
        else: high = mid - 1
    return high
m = integer_cube_root(ciphertext)
plaintext = m.to_bytes((m.bit_length() + 7) // 8, 'big').decode('ascii')
with open('/app/solutions/silver_answer.txt', 'w') as f:
    f.write(plaintext)
SILVER_EOF

python3 /tmp/decrypt_silver.py
/app/game_engine attempt_challenge silver

echo ""
echo "=== Phase 5: Crystal Key at (7, 28) ==="
/app/game_engine move W
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move W
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
# 🔹 CRYSTAL: Sokoban Solver - Fixed with State-Based BFS
python3 << 'CRYSTAL_EOF'
from collections import deque
from pathlib import Path

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

def parse_level():
    """Parse level and extract positions."""
    player = None
    boxes = set()
    goals = set()
    walls = set()
    
    for y, line in enumerate(LEVEL):
        for x, ch in enumerate(line):
            if ch == '#':
                walls.add((x, y))
            elif ch == '@':
                player = (x, y)
            elif ch == 'B':
                boxes.add((x, y))
            elif ch == 'G':
                goals.add((x, y))
    
    return player, frozenset(boxes), frozenset(goals), walls

def solve_sokoban():
    """Solve using state-based BFS."""
    player, boxes, goals, walls = parse_level()
    
    # BFS on game states (player_pos, boxes)
    initial_state = (player, boxes)
    queue = deque([(initial_state, "")])
    visited = {initial_state}
    
    moves = {'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0)}
    
    while queue:
        (player, boxes), path = queue.popleft()
        
        # Check if solved
        if boxes == goals:
            return path
        
        # Try all 4 directions
        for move_char, (dx, dy) in moves.items():
            new_player = (player[0] + dx, player[1] + dy)
            
            # Skip if moving into wall
            if new_player in walls:
                continue
            
            new_boxes = boxes
            
            # If pushing a box
            if new_player in boxes:
                box_new = (new_player[0] + dx, new_player[1] + dy)
                
                # Skip if box can't be pushed
                if box_new in walls or box_new in boxes:
                    continue
                
                # Move the box
                new_boxes = frozenset((b if b != new_player else box_new) for b in boxes)
            
            # New state
            new_state = (new_player, new_boxes)
            
            # Skip if already visited
            if new_state in visited:
                continue
            
            visited.add(new_state)
            queue.append((new_state, path + move_char))
    
    return None  # No solution found

# Solve the puzzle
solution = solve_sokoban()

if solution:
    Path("/app/solutions").mkdir(parents=True, exist_ok=True)
    Path("/app/solutions/crystal_answer.txt").write_text(solution)
    print(f"✅ Solution found in {len(solution)} moves: {solution}")
else:
    print("❌ No solution found!")
    raise RuntimeError("Puzzle unsolvable")

CRYSTAL_EOF
/app/game_engine attempt_challenge crystal

echo ""
echo "=== Phase 6: Ruby Chest at (25, 12) ==="
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move E
/app/game_engine move E
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine unlock_chest ruby

echo ""
echo "=== Phase 7: Iron Chest at (3, 25) ==="
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move S
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine unlock_chest iron

echo ""
echo "=== Phase 8: Crystal Chest at (10, 18) ==="
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move E
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move E
/app/game_engine unlock_chest crystal

echo ""
echo "=== Phase 9: Return to Start (0, 0) ==="
/app/game_engine move W
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move W
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move W
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N
/app/game_engine move N

echo ""
echo "=== Mission Complete! ==="
/app/game_engine status
/app/game_engine inventory