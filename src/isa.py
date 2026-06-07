import struct
from enum import IntEnum
from itertools import groupby


class Opcode(IntEnum):
    # Data Movement Instructions
    PUSH = 0x01
    PUSHM = 0x02
    PUSHI = 0x03
    POP = 0x04
    POPM = 0x05
    POPI = 0x06
    DUP = 0x07

    # Arithmetic Instructions
    ADD = 0x09
    SUB = 0x0A
    MUL = 0x0B
    MULH = 0x0C
    ADDC = 0x0D
    SUBC = 0x0E
    DIV = 0x0F
    MOD = 0x10
    CMP = 0x11
    GT = 0x12
    LT = 0x13

    # Bitwise Instructions
    NOT = 0x14
    AND = 0x15
    OR = 0x16

    # Control Flow Instructions
    JUMP = 0x17
    BEQZ = 0x18
    BNEZ = 0x19
    BVS = 0x1A
    BVC = 0x1B
    BCS = 0x1C
    BCC = 0x1D
    CALL = 0x1E
    RET = 0x1F
    IRET = 0x20
    HALT = 0x21

    # Interrupt Control Instructions
    EI = 0x22
    DI = 0x23


INSTRUCTIONS_WITH_OPERANDS = frozenset(
    {
        Opcode.PUSH,
        Opcode.PUSHM,
        Opcode.POPM,
        Opcode.JUMP,
        Opcode.BEQZ,
        Opcode.BNEZ,
        Opcode.BVS,
        Opcode.BVC,
        Opcode.BCS,
        Opcode.BCC,
        Opcode.CALL,
    }
)

ALU_UNARY_OPERATIONS = frozenset({Opcode.NOT})

ALU_BINARY_OPERATIONS = frozenset(
    {
        Opcode.ADD,
        Opcode.SUB,
        Opcode.ADDC,
        Opcode.SUBC,
        Opcode.MUL,
        Opcode.MULH,
        Opcode.DIV,
        Opcode.MOD,
        Opcode.CMP,
        Opcode.GT,
        Opcode.LT,
        Opcode.AND,
        Opcode.OR,
    }
)


class Instruction:
    def __init__(self, opcode: Opcode, operand: int):
        self.opcode = opcode
        self.operand = operand

    def encode(self) -> int:
        """Pack instruction into a 32-bit word: [8-bit opcode] [24-bit operand]."""
        return ((self.opcode.value & 0xFF) << 24) | (self.operand & 0xFFFFFF)

    @classmethod
    def decode(cls, machine_word: int) -> "Instruction | int":
        """Decode a 32-bit word into an Instruction or return raw machine word if unknown."""
        opcode_raw = (machine_word >> 24) & 0xFF
        operand = machine_word & 0xFFFFFF
        if operand & 0x800000:
            operand -= 0x1000000
        try:
            return cls(Opcode(opcode_raw), operand)
        except ValueError:
            return machine_word


class DumpWriter:
    @staticmethod
    def _mnemonic(word: int) -> str:
        """Convert memory word to an instruction mnemonic, or just data if not an opcode."""
        instruction = Instruction.decode(word)
        if not isinstance(instruction, Instruction):
            return f"DATA ({word})"
        if instruction.opcode in INSTRUCTIONS_WITH_OPERANDS:
            return f"{instruction.opcode.name} {instruction.operand}"
        return instruction.opcode.name

    @staticmethod
    def write_dump(bin_filepath: str, memory: list[int], start_address: int) -> None:
        """Write the binary image and a human-readable dump alongside it."""

        # trim trailing zeros
        end = len(memory)
        while end > 0 and memory[end - 1] == 0:
            end -= 1
        image = memory[:end]

        # binary dump: big-endian 32-bit
        with open(bin_filepath, "wb") as bin_f:
            bin_f.write(struct.pack(">i", start_address))
            for word in image:
                bin_f.write(struct.pack(">i", word))

        # hex dump
        dump_filepath = bin_filepath.replace(".bin", ".dump")
        with open(dump_filepath, "w", encoding="utf-8") as log_f:
            log_f.write(f"START: {start_address:04d}\n\n")
            addr = 0
            for is_zero, group in groupby(image, key=lambda word: word == 0):
                words = list(group)
                if is_zero:
                    last = addr + len(words) - 1
                    span = f"{addr:04d}" if last == addr else f"{addr:04d}-{last:04d}"
                    log_f.write(f"{span} - 00000000 - 0\n")
                    addr = last + 1
                else:
                    for word in words:
                        hex_str = f"{word & 0xFFFFFFFF:08X}"
                        log_f.write(f"{addr:04d} - {hex_str} - {DumpWriter._mnemonic(word)}\n")
                        addr += 1

    @staticmethod
    def read_binary(filepath: str) -> tuple[list[int], int]:
        """Read binary file where first 4 bytes are start address, other - memory words."""
        memory: list[int] = []
        start_address = 0
        with open(filepath, "rb") as f:
            raw = f.read(4)
            if len(raw) == 4:
                start_address = struct.unpack(">i", raw)[0]
            while part := f.read(4):
                if len(part) == 4:
                    memory.append(struct.unpack(">i", part)[0])
        return memory, start_address
