## Background
You are building a runtime for a **Self-Modifying** Stack Virtual Machine. Unlike typical VMs, this architecture allows the running program to overwrite its own bytecode during execution.

## Goal
Write a Python script at `/app/solution/solve.py` that executes the bytecode from `/app/data/program.bin` and outputs the final state.

## VM Specification

### Architecture
1.  **Memory:** The `program.bin` is loaded into a mutable memory buffer starting at index 0.
2.  **Stack:** Unbounded list of signed integers.
3.  **Registers:** 4 General Purpose Registers (R0-R3), initialized to 0.
4.  **Instruction Pointer (IP):** Starts at 0.

### Instruction Set
Instructions are variable length (either 1 or 2 bytes).

| Opcode | Hex | Mnemonic | Bytes | Operand | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 10 | `0x0A` | **PUSH_VAL** | 2 | Value | Push *Value* onto stack. |
| 11 | `0x0B` | **PUSH_REG** | 2 | RegID | Push value of Register *RegID*. |
| 12 | `0x0C` | **POP** | 2 | RegID | Pop stack into Register *RegID*. |
| 20 | `0x14` | **ADD** | 1 | - | Pop A, Pop B. Push (B + A). |
| 30 | `0x1E` | **JMP** | 2 | Offset | `IP = IP + Offset`. |
| 31 | `0x1F` | **JZ** | 2 | Offset | Pop stack. If 0, `IP = IP + Offset`. Else continue. |
| 40 | `0x28` | **HALT** | 1 | - | Stop execution immediately. |
| 50 | `0x32` | **STORE_REL**| 2 | Offset | **Self-Modification**. Pop value `V`. Write byte `V` to `Memory[IP + Offset]`. |

### Execution Rules
1.  **Mutable Code:** The binary file is not static. `STORE_REL` can change instructions that haven't executed yet.
2.  **Relative Addressing:**
    * Offsets are signed 8-bit integers (-128 to 127).
    * **Crucial:** For `JMP`, `JZ`, and `STORE_REL`, the `Offset` is applied to the **IP immediately following** the instruction (including its operand if it has one).
    * Example: `[0x1E, 0x05]` (JMP 5). Opcode 0x1E consumes 1 byte. Operand 0x05 consumes 1 byte. IP is at index 2. New IP = 2 + 5 = 7.
3.  **Integers:** All values are treated as Python integers (no overflow).

### Error Handling (Atomic Operations)
* **Stack Underflow:** Operations must be **atomic**. You must check if the stack has enough items **before** removing any.
    * If an operation needs items (e.g., `ADD`, `POP`) but the stack has insufficient count, **ignore the instruction completely**.
    * The stack remains unchanged.
    * **For POP:** The target register **remains unchanged**.
* **Invalid Register:** If RegID is not 0-3, ignore the instruction (do not pop stack).
* **Out of Bounds:** If IP or a `STORE_REL` target is outside memory limits, stop execution immediately.

## Input
File: `/app/data/program.bin`

## Output
File: `/app/output.json`
```json
{
  "top_of_stack": 42,
  "registers": { "0": 0, "1": 0, "2": 0, "3": 0 }
}
```
* top_of_stack: null if empty.

## Execution
python3 /app/solution/solve.py