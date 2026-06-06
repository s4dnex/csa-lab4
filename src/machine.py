import argparse
import ast
import logging
import sys

from isa import (
    ALU_BINARY_OPERATIONS,
    ALU_UNARY_OPERATIONS,
    INSTRUCTIONS_WITH_OPERANDS,
    DumpWriter,
    Instruction,
    Opcode,
)

logger = logging.getLogger("machine")

DATA_STACK_LOG_SIZE = 3
MAX_TICKS = 65536
WORD_MASK = 0xFFFFFFFF


def to_signed32(x: int) -> int:
    x = x & WORD_MASK
    return x - 0x100000000 if x & 0x80000000 else x


class DataPath:
    def __init__(self, memory_size: int, prog_memory: list[int]):
        self.memory: list[int] = prog_memory + [0] * (memory_size - len(prog_memory))
        self.memory_size = memory_size
        self.carry = False
        self.overflow = False
        self.data_stack: list[int] = []
        self.return_stack: list[int] = []
        self.MAX_STACK_SIZE = 256
        self.input_port: int | None = None
        self.output_buffer = ""
        self.INPUT_ADDR = 65533
        self.SYM_OUTPUT_ADDR = 65534
        self.DEC_OUTPUT_ADDR = 65535

    def push(self, val: int) -> None:
        if len(self.data_stack) >= self.MAX_STACK_SIZE:
            raise OverflowError("Data Stack: Overflow")
        self.data_stack.append(val)

    def pop(self) -> int:
        if not self.data_stack:
            raise IndexError("Data Stack: Underflow")
        return self.data_stack.pop()

    def read_memory(self, addr: int) -> int:
        if addr == self.INPUT_ADDR:
            val = self.input_port
            self.input_port = None
            return val if val is not None else 0
        if 0 <= addr < self.memory_size:
            return self.memory[addr]
        raise IndexError(f"Memory Read: Address {addr} out of bounds")

    def write_memory(self, addr: int, val: int) -> None:
        if addr == self.SYM_OUTPUT_ADDR:
            self.output_buffer += chr(val % 256)
        elif addr == self.DEC_OUTPUT_ADDR:
            self.output_buffer += str(val)
        elif 0 <= addr < self.memory_size:
            self.memory[addr] = val
        else:
            raise IndexError(f"Memory Write: Address {addr} out of bounds")

    def alu_binary_op(self, opcode: Opcode) -> None:
        b = self.pop()
        a = self.pop()
        a_u = a & WORD_MASK
        b_u = b & WORD_MASK

        if opcode == Opcode.ADD:
            res = a_u + b_u
            bits = res & WORD_MASK
            self.carry = res > WORD_MASK
            self.overflow = bool((a_u >> 31) == (b_u >> 31) and (bits >> 31) != (a_u >> 31))
            self.push(to_signed32(bits))

        elif opcode == Opcode.SUB:
            bits = (a_u - b_u) & WORD_MASK
            self.carry = a_u < b_u
            self.overflow = bool((a_u >> 31) != (b_u >> 31) and (bits >> 31) != (a_u >> 31))
            self.push(to_signed32(bits))

        elif opcode == Opcode.ADDC:
            res = a_u + b_u + self.carry
            bits = res & WORD_MASK
            self.carry = res > WORD_MASK
            self.overflow = bool((a_u >> 31) == (b_u >> 31) and (bits >> 31) != (a_u >> 31))
            self.push(to_signed32(bits))

        elif opcode == Opcode.SUBC:
            bits = (a_u - b_u - self.carry) & WORD_MASK
            self.carry = a_u < (b_u + self.carry)
            b_eff = (b_u + self.carry) & WORD_MASK
            self.overflow = bool((a_u >> 31) != (b_eff >> 31) and (bits >> 31) != (a_u >> 31))
            self.push(to_signed32(bits))

        elif opcode == Opcode.AND:
            self.push(to_signed32(a_u & b_u))

        elif opcode == Opcode.OR:
            self.push(to_signed32(a_u | b_u))

        elif opcode == Opcode.MUL:
            self.push(to_signed32(a * b))

        elif opcode == Opcode.MULH:
            self.push(to_signed32((a * b) >> 32))

        elif opcode == Opcode.DIV:
            if b == 0:
                raise ZeroDivisionError("Division by zero")
            self.overflow = a == -2147483648 and b == -1
            self.push(to_signed32(int(a / b)))

        elif opcode == Opcode.MOD:
            if b == 0:
                raise ZeroDivisionError("Division by zero")
            self.push(to_signed32(a - b * int(a / b)))

        elif opcode == Opcode.CMP:
            self.push(1 if a == b else 0)

        elif opcode == Opcode.GT:
            self.push(1 if a > b else 0)

        elif opcode == Opcode.LT:
            self.push(1 if a < b else 0)

    def alu_unary_op(self, opcode: Opcode) -> None:
        a = self.pop()
        if opcode == Opcode.NOT:
            self.push(to_signed32((~a) & WORD_MASK))


class ControlUnit:
    def __init__(
        self, data_path: DataPath, start_address: int, interrupt_schedule: list[tuple[int, str]]
    ):
        self.dp = data_path
        self.pc = start_address
        self.ticks = 0
        self.interrupt_vector = 0x0
        self.ei = True
        self.irq = False
        self.halted = False
        self.interrupt_schedule = interrupt_schedule
        self.instructions_executed = 0

    def tick(self) -> None:
        self.ticks += 1
        while self.interrupt_schedule and self.ticks == self.interrupt_schedule[0][0]:
            _, char = self.interrupt_schedule.pop(0)
            if self.dp.input_port is None:
                self.dp.input_port = ord(char)
                self.irq = True
                self.log(f"Interrupt input of {char!r}")
            else:
                self.log(f"Interrupt input of {char!r} WAS DROPPED")

    def check_interrupt(self) -> None:
        if self.irq and self.ei:
            self.ei = False
            self.irq = False
            if len(self.dp.return_stack) >= self.dp.MAX_STACK_SIZE:
                raise OverflowError("Return Stack: Overflow during interrupt")
            self.dp.return_stack.append(self.pc)
            self.pc = self.interrupt_vector
            self.tick()
            self.log("Interrupt trigger")

    def fetch(self) -> tuple[Opcode, int]:
        addr = self.pc
        word = self.dp.read_memory(addr)
        self.pc += 1
        self.tick()

        instruction = Instruction.decode(word)
        if not isinstance(instruction, Instruction):
            raise ValueError(f"Unknown Instruction: {word:#010x}")
        return instruction.opcode, instruction.operand

    def execute_instruction(self, opcode: Opcode, operand: int) -> None:
        self.instructions_executed += 1

        if opcode == Opcode.PUSH:
            self.dp.push(operand)

        elif opcode == Opcode.PUSHM:
            val = self.dp.read_memory(operand)
            self.tick()
            self.dp.push(val)

        elif opcode == Opcode.PUSHI:
            addr = self.dp.pop()
            self.tick()
            val = self.dp.read_memory(addr)
            self.tick()
            self.dp.push(val)

        elif opcode == Opcode.POP:
            self.dp.pop()

        elif opcode == Opcode.POPM:
            val = self.dp.pop()
            self.tick()
            self.dp.write_memory(operand, val)

        elif opcode == Opcode.POPI:
            val = self.dp.pop()
            self.tick()
            addr = self.dp.pop()
            self.tick()
            self.dp.write_memory(addr, val)

        elif opcode == Opcode.DUP:
            val = self.dp.data_stack[-1]
            self.tick()
            self.dp.push(val)

        elif opcode in ALU_UNARY_OPERATIONS:
            self.dp.alu_unary_op(opcode)

        elif opcode in ALU_BINARY_OPERATIONS:
            self.dp.alu_binary_op(opcode)

        elif opcode == Opcode.JUMP:
            self.pc = operand

        elif opcode == Opcode.BEQZ:
            if self.dp.pop() == 0:
                self.pc = operand

        elif opcode == Opcode.BNEZ:
            if self.dp.pop() != 0:
                self.pc = operand

        elif opcode == Opcode.BVS:
            if self.dp.overflow:
                self.pc = operand

        elif opcode == Opcode.BVC:
            if not self.dp.overflow:
                self.pc = operand

        elif opcode == Opcode.BCS:
            if self.dp.carry:
                self.pc = operand

        elif opcode == Opcode.BCC:
            if not self.dp.carry:
                self.pc = operand

        elif opcode == Opcode.CALL:
            if len(self.dp.return_stack) >= self.dp.MAX_STACK_SIZE:
                raise OverflowError("Return Stack: Overflow")
            self.dp.return_stack.append(self.pc)
            self.pc = operand

        elif opcode == Opcode.RET:
            if not self.dp.return_stack:
                raise IndexError("Return Stack: Underflow")
            self.pc = self.dp.return_stack.pop()

        elif opcode == Opcode.IRET:
            if not self.dp.return_stack:
                raise IndexError("Return Stack: Underflow")
            self.pc = self.dp.return_stack.pop()
            self.ei = True

        elif opcode == Opcode.HALT:
            self.halted = True

        self.tick()

    def run(self) -> None:
        try:
            logger.debug(
                f"{'ISR':^5} | {'Tick':^5} | {'PC':^4} | {'Data Stack':^20} | {'EI':^2} | C | V | "
            )

            while not self.halted:
                if self.ticks > MAX_TICKS:
                    logger.error(f"Simulation Stopped: Limit of ticks is reached ({MAX_TICKS})")
                    break

                self.check_interrupt()
                opcode, operand = self.fetch()

                instruction_str = (
                    f"{opcode.name} {operand}"
                    if opcode in INSTRUCTIONS_WITH_OPERANDS
                    else opcode.name
                )
                self.log(instruction_str)

                self.execute_instruction(opcode, operand)

        except Exception as e:
            logger.error(f"Unexpected Error: {e}. Tick = {self.ticks}, PC = {self.pc:#06x}")

    def log(self, message: str) -> None:
        isr_str = "ISR" if not self.ei else "---"
        ds_str = format_stack(self.dp.data_stack)

        logger.debug(
            f"{isr_str:^5} | "
            f"{self.ticks:05d} | "
            f"{self.pc:04X} | "
            f"{ds_str:<20} | "
            f"{int(self.ei):^2} | "
            f"{int(self.dp.carry)} | "
            f"{int(self.dp.overflow)} | "
            f"{message}"
        )


def load_interrupt_schedule(schedule_filepath: str) -> list[tuple[int, str]]:
    if not schedule_filepath:
        return []

    try:
        with open(schedule_filepath, encoding="utf-8") as f:
            data = f.read().strip()
    except FileNotFoundError:
        logging.error(f"Interrupt schedule file '{schedule_filepath}' not found.")
        sys.exit(1)
    if not data:
        logging.warning(f"Interrupt schedule file '{schedule_filepath}' is empty.")
        return []

    try:
        interrupt_schedule = ast.literal_eval(data)
    except (SyntaxError, ValueError) as e:
        logging.error(f"Invalid interrupt schedule in '{schedule_filepath}': {e}")
        sys.exit(1)
    if not isinstance(interrupt_schedule, list):
        logging.error("Interrupt schedule must be a list of (tick, char) pairs.")
        sys.exit(1)

    return interrupt_schedule


def format_stack(stack: list[int]) -> str:
    if len(stack) <= DATA_STACK_LOG_SIZE:
        return str(stack)
    return f"{str(stack[:DATA_STACK_LOG_SIZE])[:-1]}, ...]"


def main(code_file: str, schedule_filepath: str) -> None:
    prog_memory, start_address = DumpWriter.read_binary(code_file)
    interrupt_schedule = load_interrupt_schedule(schedule_filepath)

    dp = DataPath(65536, prog_memory)
    cu = ControlUnit(dp, start_address, interrupt_schedule)
    cu.run()
    prefix = "Output:       "
    indent = " " * len(prefix)
    aligned = dp.output_buffer.replace("\n", "\n" + indent)
    if aligned.endswith("\n" + indent):
        aligned = aligned[: -len(indent)]
    print(f"{prefix}{aligned}")
    print(f"Ticks:        {cu.ticks}")
    print(f"Instructions: {cu.instructions_executed}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    parser = argparse.ArgumentParser(description="Stack Machine Simulator")
    parser.add_argument("code", help="Compiled binary file (.bin)")
    parser.add_argument("schedule", nargs="?", default="", help="Interrupt schedule file (.txt)")
    args = parser.parse_args()
    main(args.code, args.schedule)
