import argparse
import ast
import logging
import sys

from isa import _INSTRUCTIONS_WITH_OPERANDS, BinaryManager, Instruction, Opcode

logger = logging.getLogger("machine")

_DS_DISPLAY_MAX = 8
_MAX_TICKS = 1_000_000
_MASK32 = 0xFFFFFFFF


def signed32(x: int) -> int:
    x = x & _MASK32
    return x - 0x100000000 if x & 0x80000000 else x


def format_stack(stack: list[int]) -> str:
    if len(stack) <= _DS_DISPLAY_MAX:
        return str(stack)
    head = ", ".join(map(str, stack[:3]))
    tail = ", ".join(map(str, stack[-3:]))
    return f"[{head}, ..., {tail}] (total {len(stack)})"


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
        self.INPUT_ADDR = 2045
        self.SYM_OUTPUT_ADDR = 2046
        self.DEC_OUTPUT_ADDR = 2047

    def memory_read(self, addr: int) -> int:
        if addr == self.INPUT_ADDR:
            val = self.input_port
            self.input_port = None
            return val if val is not None else 0
        if 0 <= addr < self.memory_size:
            return self.memory[addr]
        raise IndexError(f"Memory read fault: address {addr} out of bounds")

    def memory_write(self, addr: int, val: int) -> None:
        if addr == self.SYM_OUTPUT_ADDR:
            self.output_buffer += chr(val % 256)
        elif addr == self.DEC_OUTPUT_ADDR:
            self.output_buffer += str(val)
        elif 0 <= addr < self.memory_size:
            self.memory[addr] = val
        else:
            raise IndexError(f"Memory write fault: address {addr} out of bounds")

    def push(self, val: int) -> None:
        if len(self.data_stack) >= self.MAX_STACK_SIZE:
            raise OverflowError("Data Stack overflow")
        self.data_stack.append(val)

    def pop(self) -> int:
        if not self.data_stack:
            raise IndexError("Data Stack underflow")
        return self.data_stack.pop()

    def alu_op(self, opcode: Opcode) -> None:
        b = self.pop()
        a = self.pop()
        a_u = a & _MASK32
        b_u = b & _MASK32

        if opcode == Opcode.ADD:
            res = a_u + b_u
            bits = res & _MASK32
            self.carry = res > _MASK32
            self.overflow = bool((a_u >> 31) == (b_u >> 31) and (bits >> 31) != (a_u >> 31))
            self.push(signed32(bits))

        elif opcode == Opcode.SUB:
            bits = (a_u - b_u) & _MASK32
            self.carry = a_u < b_u
            self.overflow = bool((a_u >> 31) != (b_u >> 31) and (bits >> 31) != (a_u >> 31))
            self.push(signed32(bits))

        elif opcode == Opcode.ADC:
            res = a_u + b_u + self.carry
            bits = res & _MASK32
            self.carry = res > _MASK32
            self.overflow = bool((a_u >> 31) == (b_u >> 31) and (bits >> 31) != (a_u >> 31))
            self.push(signed32(bits))

        elif opcode == Opcode.SBC:
            bits = (a_u - b_u - self.carry) & _MASK32
            self.carry = a_u < (b_u + self.carry)
            b_eff = (b_u + self.carry) & _MASK32
            self.overflow = bool((a_u >> 31) != (b_eff >> 31) and (bits >> 31) != (a_u >> 31))
            self.push(signed32(bits))

        elif opcode == Opcode.MUL:
            self.push(signed32(a * b))

        elif opcode == Opcode.MULH:
            self.push(signed32((a * b) >> 32))

        elif opcode == Opcode.DIV:
            if b == 0:
                raise ZeroDivisionError("DIV by zero")
            self.overflow = a == -2147483648 and b == -1
            self.push(signed32(int(a / b)))

        elif opcode == Opcode.MOD:
            if b == 0:
                raise ZeroDivisionError("MOD by zero")
            self.push(a % b)

        elif opcode == Opcode.CMP:
            self.push(1 if a == b else 0)

        elif opcode == Opcode.GT:
            self.push(1 if a > b else 0)

        elif opcode == Opcode.LT:
            self.push(1 if a < b else 0)


class ControlUnit:
    def __init__(self, data_path: DataPath, start_address: int,
                 trap_schedule: list[tuple[int, str]]):
        self.dp = data_path
        self.pc = start_address
        self.ticks = 0
        self.interrupt_vector = 0x000
        self.ei = True
        self.irq = False
        self.halted = False
        self.trap_schedule = trap_schedule
        self.instructions_executed = 0

    def tick(self) -> None:
        self.ticks += 1
        while self.trap_schedule and self.ticks == self.trap_schedule[0][0]:
            _, char = self.trap_schedule.pop(0)
            if self.dp.input_port is None:
                self.dp.input_port = ord(char)
                self.irq = True
                logger.debug(
                    f"Tick: {self.ticks:04d} | TRAP DELIVERED {char!r} "
                    f"(0x{ord(char):02x}) -> input_port"
                )
            else:
                logger.debug(
                    f"Tick: {self.ticks:04d} | TRAP {char!r} DROPPED (port busy)"
                )

    def check_interrupt(self) -> None:
        if self.irq and self.ei:
            self.ei = False
            self.irq = False
            if len(self.dp.return_stack) >= self.dp.MAX_STACK_SIZE:
                raise OverflowError("Return Stack overflow during interrupt")
            self.dp.return_stack.append(self.pc)
            self.pc = self.interrupt_vector
            self.tick()
            logger.debug(
                f"Tick: {self.ticks:04d} | INTERRUPT TRAP TRIGGERED | "
                f"pc <- {self.interrupt_vector:#05x}"
            )

    def fetch(self) -> tuple[Opcode, int]:
        addr = self.pc
        self.tick()
        word = self.dp.memory_read(addr)
        self.tick()
        self.pc += 1
        self.tick()

        instruction = Instruction.decode(word)
        if not isinstance(instruction, Instruction):
            raise ValueError(f"Unknown instruction: {word:#010x}")
        return instruction.opcode, instruction.operand

    def execute_instruction(self, opcode: Opcode, operand: int) -> None:
        self.instructions_executed += 1

        if opcode == Opcode.HALT:
            self.halted = True
            self.tick()

        elif opcode == Opcode.PUSH:
            self.dp.push(operand)
            self.tick()

        elif opcode == Opcode.PUSH_M:
            self.tick()
            val = self.dp.memory_read(operand)
            self.tick()
            self.dp.push(val)
            self.tick()

        elif opcode == Opcode.POP:
            self.dp.pop()
            self.tick()

        elif opcode == Opcode.POP_M:
            val = self.dp.pop()
            self.tick()
            self.dp.memory_write(operand, val)
            self.tick()

        elif opcode == Opcode.DUP:
            val = self.dp.data_stack[-1]
            self.tick()
            self.dp.push(val)
            self.tick()

        elif opcode == Opcode.PUSH_IND:
            addr = self.dp.pop()
            self.tick()
            val = self.dp.memory_read(addr)
            self.tick()
            self.dp.push(val)
            self.tick()

        elif opcode == Opcode.POP_IND:
            val = self.dp.pop()
            addr = self.dp.pop()
            self.tick()
            self.dp.memory_write(addr, val)
            self.tick()

        elif opcode in (
            Opcode.ADD, Opcode.SUB, Opcode.ADC, Opcode.SBC,
            Opcode.MUL, Opcode.MULH, Opcode.DIV, Opcode.MOD,
            Opcode.CMP, Opcode.GT, Opcode.LT,
        ):
            self.dp.alu_op(opcode)
            self.tick()

        elif opcode == Opcode.JMP:
            self.pc = operand
            self.tick()

        elif opcode == Opcode.JZ:
            if self.dp.pop() == 0:
                self.pc = operand
            self.tick()

        elif opcode == Opcode.JNZ:
            if self.dp.pop() != 0:
                self.pc = operand
            self.tick()

        elif opcode == Opcode.JO:
            if self.dp.overflow:
                self.pc = operand
            self.tick()

        elif opcode == Opcode.CALL:
            if len(self.dp.return_stack) >= self.dp.MAX_STACK_SIZE:
                raise OverflowError("Return Stack overflow")
            self.dp.return_stack.append(self.pc)
            self.pc = operand
            self.tick()

        elif opcode == Opcode.RET:
            if not self.dp.return_stack:
                raise IndexError("Return Stack underflow")
            self.pc = self.dp.return_stack.pop()
            self.tick()

        elif opcode == Opcode.IRET:
            if not self.dp.return_stack:
                raise IndexError("Return Stack underflow")
            self.pc = self.dp.return_stack.pop()
            self.ei = True
            self.tick()

    def run(self) -> None:
        try:
            while not self.halted:
                if self.ticks > _MAX_TICKS:
                    logger.error(f"Simulation stopped: NUMBER OF TICKS > ({_MAX_TICKS})")
                    break
                self.check_interrupt()

                opcode, operand = self.fetch()

                isr_tag = "[ISR] " if not self.ei else ""
                instr_str = (
                    f"{opcode.name} {operand}"
                    if opcode in _INSTRUCTIONS_WITH_OPERANDS
                    else opcode.name)
                logger.debug(
                    f"{isr_tag}Tick: {self.ticks:04d} | pc: {self.pc:04X}"
                    f" | DS: {format_stack(self.dp.data_stack)}"
                    f" | EI: {int(self.ei)} | carry: {self.dp.carry}"
                    f" | Instr: {instr_str}"
                )

                self.execute_instruction(opcode, operand)

        except Exception as e:
            logger.error(f"CPU FAULT at tick = {self.ticks}, pc = {self.pc:#06x}: {e}")


def main(code_file: str, trap_schedule_filepath: str) -> None:
    prog_memory, start_address = BinaryManager.read_binary(code_file)

    trap_schedule: list[tuple[int, str]] = []
    if trap_schedule_filepath:
        try:
            with open(trap_schedule_filepath, encoding="utf-8") as f:
                data = f.read().strip()
                if data:
                    trap_schedule = ast.literal_eval(data)
        except FileNotFoundError:
            logging.warning(f"Trap schedule file '{trap_schedule_filepath}' not found.")
            sys.exit(1)

    dp = DataPath(2048, prog_memory)
    cu = ControlUnit(dp, start_address, trap_schedule)
    cu.run()
    print(f"Output: {dp.output_buffer}")
    print(f"Overall quantity of ticks: {cu.ticks}")
    print(f"Instructions executed: {cu.instructions_executed}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    parser = argparse.ArgumentParser(description="Stack machine CPU simulator")
    parser.add_argument("code", help="Compiled binary file (.bin)")
    parser.add_argument("schedule", nargs="?", default="", help="Trap schedule file (.txt)")
    args = parser.parse_args()
    main(args.code, args.schedule)
