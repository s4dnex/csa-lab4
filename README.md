# Labwork 4. Experiment

> **ИСУ**: 467307
>
> **ФИО**: Рязанов Никита Сергеевич
>
> **Группа**: P3207
>
> **Вариант**: `alg | stack | neum | hw | tick | binary | trap | mem | cstr | prob2 | vector`

---

## Programming Language

### Assembler BNF

```bnf
<program>     ::= <line>*
<line>        ::= [<label> ":"] [<statement>] [<comment>] "\n"
<statement>   ::= <section_dir> | <org_dir> | <data_decl> | <instruction>

<section_dir> ::= ".data" | ".text"
<org_dir>     ::= ".org" <number>

<data_decl>   ::= ".word" <number> | ".str" <string>

<instruction> ::= <opcode> [<operand>]
<operand>     ::= <number> | <name>

<label>       ::= <name>
<name>        ::= { <letter> | <digit> }
<opcode>      ::= <letter>+

<number>      ::= ["-"] ( <decimal> | <hex> | <octal> | <binary> )
<decimal>     ::= <digit>+
<hex>         ::= "0x" <hex_digit>+
<octal>       ::= "0o" <oct_digit>+
<binary>      ::= "0b" <bin_digit>+

<letter>      ::= [a-zA-Z_]
<digit>       ::= [0-9]
<hex_digit>   ::= [0-9a-fA-F]
<oct_digit>   ::= [0-7]
<bin_digit>   ::= [01]

<string>      ::= <any character except '"'>*
<comment>     ::= ";" <any character except '\n'>*
```

### Semantics

**Evaluation strategy** - strictly sequential (imperative). Each instruction completes before the next one begins. Execution order is driven by the program counter `PC`. Control-flow instructions (e.g., `JUMP`, `BEQZ`, `BNEZ`, `BVS`, `CALL`) update `PC`.

**Scoping** - global. Labels are visible throughout the whole file.

**Typing** - none. All values are 32-bit signed integers. Characters are stored as `ord(char)`.

**Literals:**

- Numbers: decimal, hexadecimal (`0x…`), octal (`0o…`), binary (`0b…`). A literal may appear directly in an instruction operand (24-bit signed range: [−8_388_608; +8_388_607]). Values outside this range must be placed in the data section with the `.word` directive.

- Strings: stored only in data section via `.str` in C style. One machine word per character (`ord(c)`), terminated by a zero word (`\0`). Length is not stored, traversal stops at the zero word.

**Variables** - declared with `.word` in data section. Each occupies one 32-bit machine word.

**Procedures** - invoked with `CALL addr`. The return address is saved on the Return Stack. Finished with `RET`.

**Interrupts** - the interrupt vector is stored at address `0x0`. On interrupt, `PC` is pushed to the Return Stack and the `EI` flag is cleared. Handling of interruption ends with `IRET` which restores `PC` and `EI`.

**Example program:**

```asm
.data
message: .str "Hello, World!"
ptr: .word 0

.text
_start:
    push message
    popm ptr
loop:
    pushm ptr
    pushi
    beqz end
    push 65534
    pushm ptr
    pushi
    popi
    pushm ptr
    push 1
    add
    popm ptr
    jump loop
end:
    halt
```

---

## Memory Organization

### Memory Model

Von Neumann architecture - a single address space for instructions and data.

```mem
     Address     Description
  +-----------+----------------------------------+
  | 0x0       | interrupt vector (optional)      | 
  | ...       |                                  |
  | D         | start of .data                   | 
  | ...       | variables                        |
  | T         | start of .text                   | 
  | ...       | _start: instructions             |
  | 65533     | MMIO: INPUT                      | 
  | 65534     | MMIO: OUTPUT_SYMB                | 
  | 65535     | MMIO: OUTPUT_DEC                 |
  +-----------+----------------------------------+
```

**Size:** 65536 machine words of 32 bits each (65533 of which available for code and data).

**Stacks:**

- `Data Stack` - operand stack (depth up to 256). All computation goes through it.

- `Return Stack` - return-address stack (depth up to 256); holds return addresses for `CALL` / `RET` / `IRET`. Not manipulated directly by the programmer.

**Addressing modes:**

| Mode        | Example             | Description                                      |
|-------------|---------------------|--------------------------------------------------|
| Immediate   | `PUSH <immediate>`  | Load constant from the instruction operand       |
| Direct      | `PUSHM <address>`   | Read from memory by address in the operand       |
| Indirect    | `PUSHI`             | Read from memory by address on the stack top     |

**Mapping to memory:**

- `.word N` - one word initialized with value N.

- `.str "str"` -> `len(str) + 1` words: one word per character, last word is the null terminator.

- Instructions - one 32-bit word (8-bit opcode + 24-bit operand).

- Fixed address `0x0` that should contain `JUMP` to the interrupt handler.

---

## Instruction Set Architecture

### Processor Features

- **Architecture:** stack. No general-purpose registers - all computation uses the `Data Stack`. The Return Stack is managed by hardware for `CALL` / `RET` / `IRET`.

- **I/O:** memory-mapped I/O (cell addresses 65533–65535). Access via `PUSHM` / `PUSHI` / `POPM` / `POPI`.

- **Interrupts:** a single `input_port` cell holds the incoming character. Each **tick**, the interrupt schedule is checked: if the scheduled tick has arrived and the **port is empty**, the character is written to `input_port` and `irq` is set. If the port is busy, the new character is **dropped**. The handler runs **between instructions**: before fetch, `irq && ei` is tested - if true, `PC` is pushed to the Return Stack, `PC <- 0x0`, `ei <- 0` and `irq <- 0`. `IRET` restores `PC` and sets `ei <- 1`. `input_port` is cleared when read at `INPUT_ADDR`.

- **Nested interrupts** are not allowed (`ei = 0`). If a character arrives while `ei = 0` but the port is already empty (the handler has read it), the character is placed in `input_port` and `irq` is set. After `IRET`, it will be serviced again because interrupts are re-enabled. If the port is still busy, the character is lost.

- **Flags:**
  - `carry` (C) - unsigned carry:
    - ADD: set if the result does not fit in 32 bits
    - SUB: set if the minuend is less than the subtrahend (unsigned)
    - ADDC, SUBC: same rules, also accounting for the previous carry on input
  - `overflow` (V) - signed overflow:
    - ADD, ADDC: set if both operands have the same sign and the result has the opposite sign
    - SUB, SUBC: set if operands have opposite signs and the result does not match the minuend's sign
    - DIV: set when dividing INT_MIN by −1

  ADD, SUB, ADDC, and SUBC update both flags. Bitwise instructions (`NOT`, `AND`, `OR`) and branches do not modify flags.

### Instruction Encoding

Each instruction is one 32-bit machine word:

```inst
31       24 23                    0
+----------+----------------------+
|  opcode  |       operand        |
| (8 bits) |      (24 bits)       |
+----------+----------------------+
```

The operand is sign-extended to 32 bits when decoded.

### Instruction Set

Full instruction cycle = 3 fetch cycles + n execute cycles.

| Mnemonic   | Opcode | Operand     | Operation                                    | Execute cycles |
|------------|--------|-------------|----------------------------------------------|----------------|
| `PUSH`     | 0x01   | `immediate` | `DS.push(imm)`                               | 1              |
| `PUSHM`    | 0x02   | `address`   | `DS.push(MEM[addr])`                         | 2              |
| `PUSHI`    | 0x03   | -           | `DS.push(MEM[DS.pop()])`                     | 3              |
| `POP`      | 0x04   | -           | `DS.pop()`                                   | 1              |
| `POPM`     | 0x05   | `address`   | `MEM[addr] = DS.pop()`                       | 2              |
| `POPI`     | 0x06   | -           | `val=DS.pop(); addr=DS.pop(); MEM[addr]=val` | 3              |
| `DUP`      | 0x07   | -           | `DS.push(DS[-1])`                            | 2              |
| `ADD`      | 0x09   | -           | `DS.push(DS.pop() + DS.pop())` ; C, V        | 1              |
| `SUB`      | 0x0A   | -           | `DS.push(DS.pop() − DS.pop())` ; C, V        | 1              |
| `MUL`      | 0x0B   | -           | `DS.push((DS.pop() * DS.pop()) & 0xFFFFFFFF)`| 1              |
| `MULH`     | 0x0C   | -           | `DS.push((DS.pop() * DS.pop()) >> 32)`       | 1              |
| `ADDC`     | 0x0D   | -           | `DS.push(DS.pop() + DS.pop() + C)` ; C, V    | 1              |
| `SUBC`     | 0x0E   | -           | `DS.push(DS.pop() − DS.pop() − C)` ; C, V    | 1              |
| `DIV`      | 0x0F   | -           | `DS.push(DS.pop() / DS.pop())`               | 1              |
| `MOD`      | 0x10   | -           | `DS.push(DS.pop() % DS.pop())`               | 1              |
| `CMP`      | 0x11   | -           | `DS.push(DS.pop() == DS.pop() ? 1 : 0)`      | 1              |
| `GT`       | 0x12   | -           | `DS.push(DS.pop() > DS.pop() ? 1 : 0)`       | 1              |
| `LT`       | 0x13   | -           | `DS.push(DS.pop() < DS.pop() ? 1 : 0)`       | 1              |
| `NOT`      | 0x14   | -           | `DS.push(~DS.pop())`                         | 1              |
| `AND`      | 0x15   | -           | `DS.push(DS.pop() & DS.pop())`               | 1              |
| `OR`       | 0x16   | -           | `DS.push(DS.pop() \| DS.pop())`              | 1              |
| `JUMP`     | 0x17   | `address`   | `PC = addr`                                  | 1              |
| `BEQZ`     | 0x18   | `address`   | `if DS.pop() == 0: PC = addr`                | 1              |
| `BNEZ`     | 0x19   | `address`   | `if DS.pop() != 0: PC = addr`                | 1              |
| `BVS`      | 0x1A   | `address`   | `if V: PC = addr`                            | 1              |
| `BVC`      | 0x1B   | `address`   | `if !V: PC = addr`                           | 1              |
| `BCS`      | 0x1C   | `address`   | `if C: PC = addr`                            | 1              |
| `BCC`      | 0x1D   | `address`   | `if !C: PC = addr`                           | 1              |
| `CALL`     | 0x1E   | `address`   | `RS.push(PC); PC = addr`                     | 1              |
| `RET`      | 0x1F   | -           | `PC = RS.pop()`                              | 1              |
| `IRET`     | 0x20   | -           | `PC = RS.pop(); EI = 1`                      | 1              |
| `HALT`     | 0x21   | -           | Halt                                         | 1              |
---

## Translator

### Command-Line Interface

```sh
python src\translator.py <source.asm> <output.bin>
```

Produces two files:

- `<output.bin>` - binary file. First 4 bytes: start address (`_start`), followed by 2048 × 4 bytes of memory.

- `<output>_dump.log` - text dump in the form `<addr> - <HEXCODE> - <mnemonic>`.

Example:

```sh
python src\translator.py examples\hello_world.asm out\hello_world.bin
```

Example dump:

```text
START: 0015

0000 - 00000048 - DATA (72)
0001 - 00000065 - DATA (101)
0002 - 0000006C - DATA (108)
0003 - 0000006C - DATA (108)
0004 - 0000006F - DATA (111)
0005 - 0000002C - DATA (44)
0006 - 00000020 - DATA (32)
0007 - 00000057 - DATA (87)
0008 - 0000006F - DATA (111)
0009 - 00000072 - DATA (114)
0010 - 0000006C - DATA (108)
0011 - 00000064 - DATA (100)
0012 - 00000021 - DATA (33)
0013-0014 - 00000000 - 0
0015 - 01000000 - PUSH 0
0016 - 0500000E - POPM 14
0017 - 0200000E - PUSHM 14
0018 - 03000000 - PUSHI
0019 - 1800001D - BEQZ 29
0020 - 0100FFFE - PUSH 65534
0021 - 0200000E - PUSHM 14
0022 - 03000000 - PUSHI
0023 - 06000000 - POPI
0024 - 0200000E - PUSHM 14
0025 - 01000001 - PUSH 1
0026 - 09000000 - ADD
0027 - 0500000E - POPM 14
0028 - 17000011 - JUMP 17
0029 - 21000000 - HALT
0030-65535 - 00000000 - 0
```

### Translation Stages

```text
Source code (.asm)
      |
      V
First pass: layout
Parse .data / .text / .org, assign label addresses,
write data (.word, .str) into the memory array,
collect instructions with their addresses (mnemonic + operand)
      |
      V
Second pass: encoding
Resolve label addresses in operands,
encode each instruction as a 32-bit word,
write into the memory array
      |
      V
Write .bin and _dump.log
```

**Translator limitations:**

- Operands: labels or numeric literals only (no expressions).

- No type or operand-range checking.

---

## Processor Model

### DataPath

![datapath.svg](img/datapath.svg)


### ControlUnit

![controlunit.svg](img/controlunit.svg)

#### Fetch Cycle

The instruction fetch cycle is the same for all instructions and takes 2 cycles:

1. `PC -> MUX_ADDR -> MUX_AR -> MEM[PC] -> DR` (`DR Latch`)
2. `DR -> IR` (`IR Latch`)

After fetch, the execute phase runs.
Between instructions, `irq && ei` is checked. If true, **one additional cycle** pushes PC to the Return Stack, `PC <- 0x0`, `EI <- 0`.

### Simulator Implementation Notes

- **Cycle-accurate.** Fetch always takes **2 cycles**. Execute takes 1–3 cycles depending on the operation.
- Main Loop: `check_interrupt() -> fetch() -> execute_instruction()`. After each cycle, `tick()` advances the global tick counter and checks the interrupt schedule.
- Two hardware stacks: `Data Stack` and `Return Stack`. Overflow raises an exception and stops the machine.
- MMIO: access type is determined by address. `memory_read(65533)` returns the current `input_port` value and clears the port. `memory_write(65534, v)` appends ASCII to `output_buffer`. `memory_write(65535, v)` appends a decimal value to `output_buffer`.

---

## Testing

### Toolchain

```text
<name>.asm
       |  python src\translator.py <name.asm> <output.bin>
       V
<name>.bin + <name>_dump.log
       |  python src\machine.py <binary.bin> [input.txt]
       V
stdout: tick log + output
```

**Example:**

```sh
python src\translator.py examples\hello_world.asm out\hello_world.bin
python src\machine.py out\hello_world.bin

 ISR  | Tick  |  PC  |      Data Stack      | EI | C | V | 
 ---  | 00003 | 0010 | []                   | 1  | 0 | 0 | PUSH 0
 ---  | 00007 | 0011 | [0]                  | 1  | 0 | 0 | POPM 14
 ...

Output:       Hello, World!
Ticks:        809
Instructions: 162
```

In the log, `Tick` marks the start of the execute phase of the current instruction (after the 3-cycle fetch). Lines with `ISR` mean execution inside the interrupt handler. Input delivery and loss are logged separately: 

- `Interrupt input of <char>` 
- `Interrupt input of <char> WAS DROPPED`

### Golden Tests

Tests are contained in `tests` folder. Run:

```sh
pytest -v                     # normal run
pytest -v --update-goldens    # regenerate snapshots
```

| Test          | Algorithm                                                                 |
|---------------|---------------------------------------------------------------------------|
| `array_sum`   | Sum array elements with step-by-step intermediate output                  |
| `cat_fail`    | Character loss under a dense interrupt schedule                           |
| `cat`         | Echo input characters to output                                           |
| `double_math` | 64-bit arithmetic                                                         |
| `hello_user`  | Prompt for a name, read it, print a greeting                              |
| `hello_world` | Print hello world                                                         |
| `prob2`       | Euler #6: difference of square of sum and sum of squares for 1..100       |
| `sort`        | Bubble sort of an array                                                   |

**Golden file layout:**

```text
tests/golden/<name>.yml
    in_source - algorithm source code
    output - program output without the tick log
    machine_code - machine code and data dump
    out_log - tick log
    in_stdin - input data
```
