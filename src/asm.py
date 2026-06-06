"""
asm code -> machine code
"""

import argparse
import logging
import re
import sys

from isa import DumpWriter, Instruction, Opcode

logger = logging.getLogger("asm")

MEMORY_SIZE = 65536

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"'}


def unescape(text: str) -> str:
    """Process C-style escape sequences (\\n, \\t, \\r, \\0, \\\\, \\\") in a string literal."""
    result = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            result.append(ESCAPES.get(text[i + 1], text[i + 1]))
            i += 2
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def translate(source_code: str) -> tuple[list[int], int]:
    """Translate assembler source code to machine code."""
    code_lines = source_code.splitlines()

    labels = {}
    memory = [0] * MEMORY_SIZE

    pc = 0
    section = ".text"
    parsed_instructions = []

    for line in code_lines:
        # remove comments and whitespaces
        line = line.split(";")[0].strip()
        if not line:
            continue

        if line in (".data", ".text"):
            section = line
            continue

        if line.startswith(".org"):
            pc = int(line.split()[1], 0)
            continue

        # take labels and corresponding program counter
        if ":" in line and '"' not in line.split(":")[0]:
            label, rest = line.split(":", 1)
            labels[label.strip()] = pc
            line = rest.strip()
            if not line:
                continue

        # write numbers and strings
        if section == ".data":
            if line.startswith(".word"):
                val_str = line.split(maxsplit=1)[1].strip()
                memory[pc] = int(val_str, 0)
                pc += 1

            elif line.startswith(".str"):
                match = re.search(r'"(.*)"', line)
                if match:
                    for char in unescape(match.group(1)):
                        memory[pc] = ord(char)
                        pc += 1
                    memory[pc] = 0
                    pc += 1
            continue

        # decode instructions
        if section == ".text":
            parts = line.split(maxsplit=1)
            opcode = parts[0].upper()
            operand_str = parts[1].strip() if len(parts) > 1 else ""

            parsed_instructions.append((pc, opcode, operand_str))
            pc += 1

    # replace labels
    for addr, opcode, operand_str in parsed_instructions:
        operand_val = 0

        if operand_str:
            if operand_str in labels:
                operand_val = labels[operand_str]
            else:
                try:
                    operand_val = int(operand_str, 0)
                except ValueError:
                    raise ValueError(
                        f"Unknown label or invalid integer: '{operand_str}' at pc={addr}"
                    ) from None

        try:
            opcode_obj = Opcode[opcode]
        except KeyError:
            raise ValueError(f"Unknown instruction: '{opcode}' at pc={addr}") from None

        memory[addr] = Instruction(opcode_obj, operand_val).encode()

    if "_start" not in labels:
        raise ValueError("Start label '_start' is missed!")

    return memory, labels["_start"]


def main(source_file: str, target_file: str) -> None:
    with open(source_file, encoding="utf-8") as f:
        source_code = f.read()

    try:
        memory, start_address = translate(source_code)
    except Exception as e:
        print(f"Compilation error:\n{e}")
        sys.exit(1)

    DumpWriter.write_dump(target_file, memory, start_address)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="asm -> binary assembler")
    parser.add_argument("source", help="Source program (.asm)")
    parser.add_argument("binary_file", help="Compiled code (.bin)")
    args = parser.parse_args()
    main(args.source, args.binary_file)
