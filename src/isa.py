import struct
from enum import IntEnum


class Opcode(IntEnum):
    # Data Movement Instructions
    PUSH = 0x01
    PUSH_M = 0x02
    PUSH_IND = 0x03
    POP = 0x04
    POP_M = 0x05
    POP_IND = 0x06
    DUP = 0x07

    # Arithmetic Instructions
    ADD = 0x09
    SUB = 0x0A
    MUL = 0x0B
    MULH = 0x0C
    ADC = 0x0D
    SBC = 0x0E
    DIV = 0x0F
    MOD = 0x10
    CMP = 0x11
    GT = 0x12
    LT = 0x13

    # Branching Instructions
    JMP = 0x14
    JZ = 0x15
    JNZ = 0x16
    JO = 0x17

    # Control Flow Instructions
    CALL = 0x18
    RET = 0x19
    IRET = 0x1A
    HALT = 0x1B


_INSTRUCTIONS_WITH_OPERANDS = frozenset(
    {
        Opcode.PUSH,
        Opcode.PUSH_M,
        Opcode.POP_M,
        Opcode.JMP,
        Opcode.JZ,
        Opcode.JNZ,
        Opcode.JO,
        Opcode.CALL,
    }
)


class Instruction:
    def __init__(self, opcode: Opcode, operand: int):
        self.opcode = opcode
        self.operand = operand

    def encode(self) -> int:
        """Упаковывает инструкцию в 32 битное слово:
        [8 битный опкод] [24 битный операнд]"""
        return ((self.opcode.value & 0xFF) << 24) | (self.operand & 0xFFFFFF)

    @classmethod
    def decode(cls, machine_word: int) -> "Instruction | int":
        """Распаковывает 32 битное слово в объект Instruction.
        Если опкод неизвестен - возвращает сырые данные"""
        opcode_raw = (machine_word >> 24) & 0xFF
        operand = machine_word & 0xFFFFFF
        if operand & 0x800000:
            operand -= 0x1000000
        try:
            return cls(Opcode(opcode_raw), operand)
        except ValueError:
            return machine_word


class BinaryManager:
    @staticmethod
    def write_binary(bin_filepath: str, memory: list[int], start_address: int) -> None:
        """Записывает дамп памяти в .bin и рядом кладёт текстовый дамп _dump.log."""

        def flush_zeros(zero_end: int) -> None:
            if zero_end == zero_start:
                log_f.write(f"{zero_start:04d} - 00000000 - 0\n")
            else:
                log_f.write(f"{zero_start:04d}-{zero_end:04d} - 00000000 - 0\n")

        log_filepath = bin_filepath.replace(".bin", "_dump.log")
        zero_start = None

        with open(bin_filepath, "wb") as bin_f, open(log_filepath, "w", encoding="utf-8") as log_f:
            bin_f.write(struct.pack(">i", start_address))
            log_f.write(f"START: {start_address:04d}\n\n")

            for addr, word in enumerate(memory):
                bin_f.write(struct.pack(">i", word))

                if word == 0:
                    if zero_start is None:
                        zero_start = addr
                    continue

                if zero_start is not None:
                    flush_zeros(addr - 1)
                    zero_start = None

                hex_str = f"{word & 0xFFFFFFFF:08X}"
                instruction = Instruction.decode(word)

                if isinstance(instruction, Instruction):
                    opcode = instruction.opcode
                    if opcode in _INSTRUCTIONS_WITH_OPERANDS:
                        instr_str = f"{opcode.name} {instruction.operand}"
                    else:
                        instr_str = opcode.name
                else:
                    instr_str = f"DATA ({word})"

                log_f.write(f"{addr:04d} - {hex_str} - {instr_str}\n")

            if zero_start is not None:
                flush_zeros(len(memory) - 1)

    @staticmethod
    def read_binary(filepath: str) -> tuple[list[int], int]:
        """Читает .bin: первые 4 байта — адрес старта, далее — память."""
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
