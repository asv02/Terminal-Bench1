import pytest
import json
import os
import subprocess

# --- Constants ---
OP_PUSH_VAL  = 0x0A
OP_PUSH_REG  = 0x0B
OP_POP       = 0x0C
OP_ADD       = 0x14
OP_JMP       = 0x1E
OP_JZ        = 0x1F
OP_HALT      = 0x28
OP_STORE_REL = 0x32

INPUT_FILE = "/app/data/program.bin"
SOLVE_SCRIPT = "/app/solution/solve.py"
OUTPUT_FILE = "/app/output.json"

def run_vm_simulation(bytecode):
    """Helper to run simulation and return parsed JSON."""
    os.makedirs(os.path.dirname(INPUT_FILE), exist_ok=True)
    with open(INPUT_FILE, "wb") as f:
        f.write(bytecode)
    if os.path.exists(OUTPUT_FILE): 
        os.remove(OUTPUT_FILE)
    
    result = subprocess.run(["python3", SOLVE_SCRIPT], capture_output=True, text=True)
    if result.returncode != 0: 
        pytest.fail(f"Script crashed: {result.stderr}")
    if not os.path.exists(OUTPUT_FILE): 
        pytest.fail("No output file.")
    
    with open(OUTPUT_FILE, "r") as f: 
        return json.load(f)

# --- Behavior Tests ---

def test_registers_and_pop():
    """Verify POP to register, PUSH_REG, and register output state."""
    # Program: PUSH 42 -> POP R3 -> PUSH_REG R3 -> HALT
    code = b''
    code += bytes([OP_PUSH_VAL, 42])
    code += bytes([OP_POP, 3])
    code += bytes([OP_PUSH_REG, 3])
    code += bytes([OP_HALT])
    
    data = run_vm_simulation(code)
    
    # Check R3 state in JSON output
    assert data["registers"]["3"] == 42, "Register R3 failed to update."
    # Check Stack state (should have 42 pushed back from R3)
    assert data["top_of_stack"] == 42

def test_invalid_register_id():
    """
    Verify handling of invalid Register IDs (e.g., 99).
    Rule: Ignore instruction, DO NOT POP stack.
    """
    # Program: PUSH 55 -> POP 99 (Invalid) -> HALT
    code = b''
    code += bytes([OP_PUSH_VAL, 55])
    code += bytes([OP_POP, 99])
    code += bytes([OP_HALT])

    data = run_vm_simulation(code)
    # 1. Stack must still have 55 (Atomicity check)
    assert data["top_of_stack"] == 55, "Stack was popped despite invalid register ID."

    # 2. Registers must be 0
    assert data["registers"]["0"] == 0
    assert data["registers"]["3"] == 0

def test_control_flow_jumps():
    """Verify JMP (unconditional) and JZ (conditional)."""
    # Logic:
    # 1. JMP to Step 3
    # 2. HALT (Skipped)
    # 3. Step 3: PUSH 0 -> JZ (Jump if Zero) to Step 5
    # 4. HALT (Skipped)
    # 5. Step 5: PUSH 99 -> HALT
    
    code = b''
    # 0: JMP 2 (Skip 2 bytes to index 4)
    code += bytes([OP_JMP, 2])
    # 2: HALT (Should skip)
    code += bytes([OP_HALT, 0]) # Filler byte
    # 4: PUSH 0
    code += bytes([OP_PUSH_VAL, 0])
    # 6: JZ 2 (Skip 2 bytes to index 10)
    code += bytes([OP_JZ, 2])
    # 8: HALT (Should skip)
    code += bytes([OP_HALT, 0])
    # 10: PUSH 99
    code += bytes([OP_PUSH_VAL, 99])
    # 12: HALT
    code += bytes([OP_HALT])
    
    data = run_vm_simulation(code)
    assert data["top_of_stack"] == 99, "Control flow JMP/JZ failed."

def test_out_of_bounds_halt():
    """Verify VM stops if IP goes OOB (Instruction 5 rule)."""
    # Program: PUSH 77. No HALT.
    code = bytes([OP_PUSH_VAL, 77])
    data = run_vm_simulation(code)
    assert data["top_of_stack"] == 77

def test_self_modification():
    """
    Test STORE_REL (Instruction 50).
    Logic: Overwrite a future HALT with ADD.
    1. PUSH 20 (Opcode for ADD)
    2. STORE_REL 4 (Write '20' to index [IP+4])
    3. PUSH 5, PUSH 5
    4. HALT (Overwritten to become ADD)
    5. HALT
    """
    code = b''
    code += bytes([OP_PUSH_VAL, 0x14]) # 0x14 = 20 = ADD
    # Offset calc: IP after STORE_REL is at index 4.
    # PUSH 5 (2 bytes) + PUSH 5 (2 bytes) = 4 bytes distance.
    code += bytes([OP_STORE_REL, 4]) 
    code += bytes([OP_PUSH_VAL, 5, OP_PUSH_VAL, 5])
    code += bytes([OP_HALT]) # Will become ADD
    code += bytes([OP_HALT])
    
    data = run_vm_simulation(code)
    assert data["top_of_stack"] == 10, "Self-modification failed. Expected 5+5=10."


def test_store_rel_oob():
    """
    Verify VM stops IMMEDIATELY if STORE_REL target is OOB.
    """
    # Logic:
    # 1. PUSH 55
    # 2. PUSH 10
    # 3. STORE_REL 100 (Way out of bounds). Should STOP here.
    # 4. PUSH 99 (Should NOT run)
    # 5. HALT

    code = b''
    code += bytes([OP_PUSH_VAL, 55])
    code += bytes([OP_PUSH_VAL, 10]) # Value to write (irrelevant)
    code += bytes([OP_STORE_REL, 100]) # OOB Write
    code += bytes([OP_PUSH_VAL, 99]) # Trap
    code += bytes([OP_HALT])
    
    data = run_vm_simulation(code)
    # If it stopped at STORE_REL, stack has [55]. (10 was popped by STORE_REL).
    # If it continued, stack would have [55, 99].
    assert data["top_of_stack"] == 55, "VM did not stop immediately on OOB STORE_REL."

def test_underflow_robustness():
    """Verify 'ignore instruction' on underflow."""
    # 1. POP (Empty) -> Should ignore and NOT update Register 0
    # 2. ADD (Empty) -> Ignore
    # 3. PUSH 5 -> ADD (Only 1 item) -> Ignore
    # 4. HALT
    code = b''
    code += bytes([OP_POP, 0])
    code += bytes([OP_ADD])
    code += bytes([OP_PUSH_VAL, 5])
    code += bytes([OP_ADD])
    code += bytes([OP_HALT])
    
    data = run_vm_simulation(code)
    assert data["top_of_stack"] == 5, "Underflow handling failed."

    # Assert register state (Key check for reviewer)
    assert data["registers"]["0"] == 0, "Register 0 was modified despite POP underflow."

def test_empty_stack_null():
    """Verify null output for empty stack."""
    code = bytes([OP_HALT])
    data = run_vm_simulation(code)
    assert data["top_of_stack"] is None