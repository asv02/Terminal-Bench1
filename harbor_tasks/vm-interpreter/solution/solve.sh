#!/bin/bash
set -e

mkdir -p /app/solution

cat << 'EOF' > /app/solution/solve.py
import sys
import json
import os
import struct

INPUT_FILE = "/app/data/program.bin"
OUTPUT_FILE = "/app/output.json"

def solve():
    if not os.path.exists(INPUT_FILE):
        return

    with open(INPUT_FILE, "rb") as f:
        # MUST use bytearray for mutability
        memory = bytearray(f.read())

    stack = []
    registers = [0] * 4
    ip = 0
    length = len(memory)

    while ip < length:
        opcode = memory[ip]
        ip += 1

        if opcode == 0x0A: # PUSH_VAL
            if ip >= length: break
            val = struct.unpack("b", bytes([memory[ip]]))[0]
            stack.append(val)
            ip += 1
            
        elif opcode == 0x0B: # PUSH_REG
            if ip >= length: break
            reg_id = memory[ip]
            if 0 <= reg_id <= 3:
                stack.append(registers[reg_id])
            ip += 1

        elif opcode == 0x0C: # POP
            if ip >= length: break
            reg_id = memory[ip]
            # Check Underflow & Valid Reg
            if stack and 0 <= reg_id <= 3:
                registers[reg_id] = stack.pop()
            ip += 1

        elif opcode == 0x14: # ADD
            if len(stack) >= 2:
                a = stack.pop()
                b = stack.pop()
                stack.append(b + a)

        elif opcode == 0x1E: # JMP
            if ip >= length: break
            offset = struct.unpack("b", bytes([memory[ip]]))[0]
            ip += 1
            ip += offset

        elif opcode == 0x1F: # JZ
            if ip >= length: break
            offset = struct.unpack("b", bytes([memory[ip]]))[0]
            ip += 1
            if stack:
                if stack.pop() == 0:
                    ip += offset

        elif opcode == 0x32: # STORE_REL
            if ip >= length: break
            offset = struct.unpack("b", bytes([memory[ip]]))[0]
            ip += 1
            
            # Logic: Target Address = Current IP + Offset
            target_addr = ip + offset
            
            if stack:
                val = stack.pop()
                # Check Bounds
                if 0 <= target_addr < length:
                    # Write byte (handle signed int -> unsigned byte)
                    memory[target_addr] = struct.unpack("B", struct.pack("b", val))[0]
                else:
                    # OOB Write -> Stop
                    break

        elif opcode == 0x28: # HALT
            break
        
        else:
            # Unknown Opcode -> Stop
            break

    tos = stack[-1] if stack else None
    
    out = {
        "top_of_stack": tos,
        "registers": {str(i): r for i, r in enumerate(registers)}
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(out, f, indent=4)

if __name__ == "__main__":
    solve()
EOF

python3 /app/solution/solve.py