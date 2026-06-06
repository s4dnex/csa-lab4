"""
tokenize -> parse (recursive descent) -> AST -> code generation into asm
"""

import argparse
import re
import sys
from dataclasses import dataclass, field

# Lexer
KEYWORDS = frozenset({"let", "if", "else", "while", "func", "return", "interrupt"})

TOKEN_RE = re.compile(
    r"""
      (?P<ws>\s+)
    | (?P<comment>//[^\n]*)
    | (?P<number>0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+)
    | (?P<string>"(?:[^"\\]|\\.)*")
    | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<op>==|!=|<=|>=|[+\-*/%<>=(){}\[\],;])
    """,
    re.VERBOSE,
)


@dataclass
class Token:
    kind: str  # "number" | "string" | "name" | "keyword" | "op" | "eof"
    value: str
    pos: int


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(source):
        match = TOKEN_RE.match(source, pos)
        if match is None:
            raise SyntaxError(f"Unexpected character {source[pos]!r} at position {pos}")
        pos = match.end()
        kind = match.lastgroup
        text = match.group()
        if kind in ("ws", "comment"):
            continue
        if kind == "name" and text in KEYWORDS:
            kind = "keyword"
        assert kind is not None
        tokens.append(Token(kind, text, match.start()))
    tokens.append(Token("eof", "", len(source)))
    return tokens


# AST
class Node:
    """Base class. Subclasses are dataclasses used both as AST and for dumping."""


@dataclass
class Num(Node):
    value: int


@dataclass
class Str(Node):
    value: str


@dataclass
class Var(Node):
    name: str


@dataclass
class BinOp(Node):
    op: str
    left: Node
    right: Node


@dataclass
class UnaryOp(Node):
    op: str
    operand: Node


@dataclass
class Call(Node):
    name: str
    args: list[Node]


@dataclass
class ArrayLit(Node):
    elements: list[Node]


@dataclass
class Index(Node):
    name: str
    index: Node


@dataclass
class IndexAssign(Node):
    name: str
    index: Node
    expr: Node


@dataclass
class Let(Node):
    name: str
    expr: Node


@dataclass
class Assign(Node):
    name: str
    expr: Node


@dataclass
class If(Node):
    cond: Node
    then_body: list[Node]
    else_body: list[Node]


@dataclass
class While(Node):
    cond: Node
    body: list[Node]


@dataclass
class Return(Node):
    expr: Node | None


@dataclass
class ExprStmt(Node):
    expr: Node


@dataclass
class FuncDef(Node):
    name: str
    body: list[Node]


@dataclass
class Program(Node):
    functions: list[FuncDef] = field(default_factory=list)
    interrupt: list[Node] | None = None
    body: list[Node] = field(default_factory=list)


# Parser
COMPARES = frozenset({"==", "!=", "<", ">", "<=", ">="})
ADDOPS = frozenset({"+", "-"})
MULOPS = frozenset({"*", "/", "%"})


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    @property
    def cur(self) -> Token:
        return self.tokens[self.i]

    def advance(self) -> Token:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def expect(self, value: str) -> Token:
        if self.cur.value != value:
            raise SyntaxError(f"Expected {value!r} but got {self.cur.value!r} at {self.cur.pos}")
        return self.advance()

    def parse_program(self) -> Program:
        prog = Program()
        while self.cur.kind != "eof":
            if self.cur.value == "func":
                prog.functions.append(self.parse_func())
            elif self.cur.value == "interrupt":
                if prog.interrupt is not None:
                    raise SyntaxError("Only one interrupt handler is allowed")
                self.advance()
                prog.interrupt = self.parse_block()
            else:
                prog.body.append(self.parse_statement())
        return prog

    def parse_func(self) -> FuncDef:
        self.expect("func")
        name = self.advance().value
        self.expect("(")
        self.expect(")")  # no parameters in this minimal language
        body = self.parse_block()
        return FuncDef(name, body)

    def parse_block(self) -> list[Node]:
        self.expect("{")
        body: list[Node] = []
        while self.cur.value != "}":
            body.append(self.parse_statement())
        self.expect("}")
        return body

    def parse_statement(self) -> Node:
        tok = self.cur
        if tok.value == "let":
            return self.parse_let()
        if tok.value == "if":
            return self.parse_if()
        if tok.value == "while":
            return self.parse_while()
        if tok.value == "return":
            return self.parse_return()
        # assignment `name = expr;`, indexed assignment `name[i] = expr;`,
        # or a bare expression statement
        if tok.kind == "name" and self.tokens[self.i + 1].value == "=":
            name = self.advance().value
            self.expect("=")
            expr = self.parse_expr()
            self.expect(";")
            return Assign(name, expr)
        if tok.kind == "name" and self.tokens[self.i + 1].value == "[":
            name = self.advance().value
            self.expect("[")
            index = self.parse_expr()
            self.expect("]")
            self.expect("=")
            expr = self.parse_expr()
            self.expect(";")
            return IndexAssign(name, index, expr)
        expr = self.parse_expr()
        self.expect(";")
        return ExprStmt(expr)

    def parse_let(self) -> Let:
        self.expect("let")
        name = self.advance().value
        self.expect("=")
        expr = self.parse_expr()
        self.expect(";")
        return Let(name, expr)

    def parse_if(self) -> If:
        self.expect("if")
        self.expect("(")
        cond = self.parse_expr()
        self.expect(")")
        then_body = self.parse_block()
        else_body: list[Node] = []
        if self.cur.value == "else":
            self.advance()
            # else-if chains as a single nested if, otherwise a normal block
            else_body = [self.parse_if()] if self.cur.value == "if" else self.parse_block()
        return If(cond, then_body, else_body)

    def parse_while(self) -> While:
        self.expect("while")
        self.expect("(")
        cond = self.parse_expr()
        self.expect(")")
        body = self.parse_block()
        return While(cond, body)

    def parse_return(self) -> Return:
        self.expect("return")
        expr = None if self.cur.value == ";" else self.parse_expr()
        self.expect(";")
        return Return(expr)

    # Expression grammar (lowest to highest precedence):
    #   comparison -> additive ((== | != | < | > | <= | >=) additive)*
    #   additive   -> term ((+ | -) term)*
    #   term       -> unary ((* | / | %) unary)*
    #   unary      -> "-" unary | primary
    #   primary    -> number | string | name | name "(" args ")" | "(" expr ")"

    def parse_expr(self) -> Node:
        return self.parse_comparison()

    def parse_comparison(self) -> Node:
        node = self.parse_additive()
        while self.cur.value in COMPARES:
            op = self.advance().value
            node = BinOp(op, node, self.parse_additive())
        return node

    def parse_additive(self) -> Node:
        node = self.parse_term()
        while self.cur.value in ADDOPS:
            op = self.advance().value
            node = BinOp(op, node, self.parse_term())
        return node

    def parse_term(self) -> Node:
        node = self.parse_unary()
        while self.cur.value in MULOPS:
            op = self.advance().value
            node = BinOp(op, node, self.parse_unary())
        return node

    def parse_unary(self) -> Node:
        if self.cur.value == "-":
            self.advance()
            operand = self.parse_unary()
            if isinstance(operand, Num):  # constant-fold negative literals
                return Num(-operand.value)
            return UnaryOp("-", operand)
        return self.parse_primary()

    def parse_primary(self) -> Node:
        tok = self.cur
        if tok.kind == "number":
            self.advance()
            return Num(int(tok.value, 0))
        if tok.kind == "string":
            self.advance()
            return Str(tok.value[1:-1])
        if tok.value == "(":
            self.advance()
            node = self.parse_expr()
            self.expect(")")
            return node
        if tok.value == "[":
            self.advance()
            elements: list[Node] = []
            if self.cur.value != "]":
                elements.append(self.parse_expr())
                while self.cur.value == ",":
                    self.advance()
                    elements.append(self.parse_expr())
            self.expect("]")
            return ArrayLit(elements)
        if tok.kind == "name":
            self.advance()
            if self.cur.value == "(":
                self.advance()
                args: list[Node] = []
                if self.cur.value != ")":
                    args.append(self.parse_expr())
                    while self.cur.value == ",":
                        self.advance()
                        args.append(self.parse_expr())
                self.expect(")")
                return Call(tok.value, args)
            if self.cur.value == "[":
                self.advance()
                index = self.parse_expr()
                self.expect("]")
                return Index(tok.value, index)
            return Var(tok.value)
        raise SyntaxError(f"Unexpected token {tok.value!r} at {tok.pos}")


def parse(source: str) -> Program:
    return Parser(tokenize(source)).parse_program()


# AST dump (human-readable)
def ast_dump(node: object, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(node, list):
        if not node:
            return f"{pad}[]"
        return "\n".join(ast_dump(item, indent) for item in node)
    if isinstance(node, Node):
        name = type(node).__name__
        fields = vars(node)
        if not fields:
            return f"{pad}{name}"
        lines = [f"{pad}{name}"]
        for key, value in fields.items():
            if isinstance(value, Node | list):
                lines.append(f"{pad}  {key}:")
                lines.append(ast_dump(value, indent + 2))
            else:
                lines.append(f"{pad}  {key}: {value!r}")
        return "\n".join(lines)
    return f"{pad}{node!r}"


# Code generation (alg AST -> asm text)
OUTPUT_DEC = 65535
OUTPUT_SYM = 65534

# comparison operator -> asm snippet producing a 0/1 value (operands already pushed)
COMPARE_OPS = {
    "==": ["cmp"],
    "<": ["lt"],
    ">": ["gt"],
    "!=": ["cmp", "push 0", "cmp"],  # invert: (a == b) == 0
    "<=": ["gt", "push 0", "cmp"],  # not (a > b)
    ">=": ["lt", "push 0", "cmp"],  # not (a < b)
}
ARITH_OPS = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod"}
# two-operand built-ins that map straight to one ALU instruction
ALU_BUILTINS = {"addc": "addc", "subc": "subc", "mulh": "mulh"}
INPUT_ADDR = 65533


class CodeGen:
    def __init__(self, program: Program):
        self.program = program
        self.text: list[str] = []
        self.variables: dict[str, str] = {}  # scalar name -> data label
        self.arrays: dict[str, list[int]] = {}  # array name -> initial values
        self.strings: list[tuple[str, str]] = []  # (label, raw text)
        self.label_id = 0
        self.uses_print_str = False
        self.functions = {f.name for f in program.functions}
        self._collect_arrays()

    def _collect_arrays(self) -> None:
        """Pre-pass: every `let x = [..]` declares an array, regardless of order."""
        blocks = [self.program.body, self.program.interrupt or []]
        blocks += [f.body for f in self.program.functions]
        for block in blocks:
            for stmt in self._walk(block):
                if isinstance(stmt, Let) and isinstance(stmt.expr, ArrayLit):
                    values = [self._const(e) for e in stmt.expr.elements]
                    self.arrays[stmt.name] = values

    def _walk(self, block: list[Node]) -> list[Node]:
        out: list[Node] = []
        for node in block:
            out.append(node)
            if isinstance(node, If):
                out += self._walk(node.then_body) + self._walk(node.else_body)
            elif isinstance(node, While):
                out += self._walk(node.body)
        return out

    @staticmethod
    def _const(node: Node) -> int:
        if isinstance(node, Num):
            return node.value
        raise ValueError("Array literal elements must be integer constants")

    def new_label(self, base: str) -> str:
        self.label_id += 1
        return f"__{base}_{self.label_id}"

    def var_label(self, name: str) -> str:
        if name not in self.variables:
            self.variables[name] = f"v_{name}"
        return self.variables[name]

    def emit(self, line: str) -> None:
        self.text.append(line)

    # Expressions
    def gen_expr(self, node: Node) -> None:
        if isinstance(node, Num):
            self.emit(f"push {node.value}")
        elif isinstance(node, Var):
            if node.name in self.arrays:  # bare array name -> base address
                self.emit(f"push {self.var_label(node.name)}")
            else:
                self.emit(f"pushm {self.var_label(node.name)}")
        elif isinstance(node, Index):
            self.gen_address(node)
            self.emit("pushi")
        elif isinstance(node, UnaryOp):
            self.gen_expr(node.operand)
            self.emit("push -1")
            self.emit("mul")
        elif isinstance(node, BinOp):
            self.gen_expr(node.left)
            self.gen_expr(node.right)
            if node.op in ARITH_OPS:
                self.emit(ARITH_OPS[node.op])
            else:
                for line in COMPARE_OPS[node.op]:
                    self.emit(line)
        elif isinstance(node, Call):
            self.gen_call(node)
        else:
            raise ValueError(f"Cannot evaluate node {node!r} as an expression")

    def gen_address(self, node: Index) -> None:
        """Push the address of array element node.name[index]."""
        if node.name not in self.arrays:
            raise ValueError(f"{node.name!r} is not an array")
        self.emit(f"push {self.var_label(node.name)}")
        self.gen_expr(node.index)
        self.emit("add")

    def gen_call(self, node: Call) -> None:
        if node.name == "print":
            self.gen_print(node)
            return
        if node.name == "putc":
            self.check_args(node, 1)
            self.gen_expr(node.args[0])
            self.emit(f"popm {OUTPUT_SYM}")
            return
        if node.name == "input":
            self.check_args(node, 0)
            self.emit(f"pushm {INPUT_ADDR}")
            return
        if node.name == "halt":
            self.check_args(node, 0)
            self.emit("halt")
            return
        if node.name == "len":
            self.check_args(node, 1)
            arg = node.args[0]
            if not isinstance(arg, Var) or arg.name not in self.arrays:
                raise ValueError("len() expects an array name")
            self.emit(f"push {len(self.arrays[arg.name])}")
            return
        if node.name in ALU_BUILTINS:
            self.check_args(node, 2)
            self.gen_expr(node.args[0])
            self.gen_expr(node.args[1])
            self.emit(ALU_BUILTINS[node.name])
            return
        if node.name in self.functions:
            self.check_args(node, 0)
            self.emit(f"call f_{node.name}")
            return
        raise ValueError(f"Unknown function {node.name!r}")

    def gen_print(self, node: Call) -> None:
        self.check_args(node, 1)
        arg = node.args[0]
        if isinstance(arg, Str):
            label = self.new_label("str")
            self.strings.append((label, arg.value))
            self.emit(f"push {label}")
            self.emit("call __print_str")
            self.uses_print_str = True
        else:
            self.gen_expr(arg)
            self.emit(f"popm {OUTPUT_DEC}")

    @staticmethod
    def check_args(node: Call, count: int) -> None:
        if len(node.args) != count:
            raise ValueError(f"{node.name!r} expects {count} argument(s), got {len(node.args)}")

    # Statements

    def gen_stmt(self, node: Node) -> None:
        if isinstance(node, Let) and isinstance(node.expr, ArrayLit):
            return  # array storage is emitted in the .data section; no runtime init
        if isinstance(node, Let | Assign):
            self.gen_expr(node.expr)
            self.emit(f"popm {self.var_label(node.name)}")
        elif isinstance(node, IndexAssign):
            self.gen_address(Index(node.name, node.index))
            self.gen_expr(node.expr)
            self.emit("popi")
        elif isinstance(node, ExprStmt):
            if isinstance(node.expr, Call):
                self.gen_call(node.expr)
            else:
                self.gen_expr(node.expr)
                self.emit("pop")
        elif isinstance(node, If):
            self.gen_if(node)
        elif isinstance(node, While):
            self.gen_while(node)
        elif isinstance(node, Return):
            if node.expr is not None:
                self.gen_expr(node.expr)
            self.emit("ret")
        else:
            raise ValueError(f"Unsupported statement {node!r}")

    def gen_if(self, node: If) -> None:
        self.gen_expr(node.cond)
        if node.else_body:
            else_label = self.new_label("else")
            end_label = self.new_label("endif")
            self.emit(f"beqz {else_label}")
            for stmt in node.then_body:
                self.gen_stmt(stmt)
            self.emit(f"jump {end_label}")
            self.emit(f"{else_label}:")
            for stmt in node.else_body:
                self.gen_stmt(stmt)
            self.emit(f"{end_label}:")
        else:
            end_label = self.new_label("endif")
            self.emit(f"beqz {end_label}")
            for stmt in node.then_body:
                self.gen_stmt(stmt)
            self.emit(f"{end_label}:")

    def gen_while(self, node: While) -> None:
        start_label = self.new_label("while")
        end_label = self.new_label("endwhile")
        self.emit(f"{start_label}:")
        self.gen_expr(node.cond)
        self.emit(f"beqz {end_label}")
        for stmt in node.body:
            self.gen_stmt(stmt)
        self.emit(f"jump {start_label}")
        self.emit(f"{end_label}:")

    # Whole program

    def generate(self) -> str:
        # Generate all code first, so variable/string/array usage is collected.
        body_text: list[str] = []
        self.text = body_text
        for stmt in self.program.body:
            self.gen_stmt(stmt)
        self.emit("halt")

        func_text: list[str] = []
        for func in self.program.functions:
            func_text.append(f"f_{func.name}:")
            self.text = func_text
            for stmt in func.body:
                self.gen_stmt(stmt)
            if not func.body or not isinstance(func.body[-1], Return):
                self.emit("ret")

        isr_text: list[str] = []
        if self.program.interrupt is not None:
            isr_text.append("__isr:")
            self.text = isr_text
            for stmt in self.program.interrupt:
                self.gen_stmt(stmt)
            self.emit("iret")

        lines: list[str] = []
        if self.program.interrupt is not None:  # interrupt vector at address 0x0
            lines += [".text", ".org 0x0", "    jump __isr", ""]

        lines.append(".data")
        for name, label in self.variables.items():
            if name not in self.arrays:
                lines.append(f"{label}: .word 0")
        for name, values in self.arrays.items():
            lines.append(f"{self.var_label(name)}: .word {values[0]}")
            lines.extend(f".word {v}" for v in values[1:])
        if self.uses_print_str:
            lines.append("__sp: .word 0")
        for label, text in self.strings:
            lines.append(f'{label}: .str "{text}"')

        lines += ["", ".text", "_start:"]
        lines.extend(self.indent(body_text))
        lines.extend(self.indent(func_text))
        lines.extend(self.indent(isr_text))
        if self.uses_print_str:
            lines.extend(self.print_str_routine())
        return "\n".join(lines) + "\n"

    @staticmethod
    def indent(lines: list[str]) -> list[str]:
        return [line if line.endswith(":") else f"    {line}" for line in lines]

    @staticmethod
    def print_str_routine() -> list[str]:
        return [
            "__print_str:",
            "    popm __sp",
            "__print_str_loop:",
            "    pushm __sp",
            "    pushi",
            "    beqz __print_str_end",
            f"    push {OUTPUT_SYM}",
            "    pushm __sp",
            "    pushi",
            "    popi",
            "    pushm __sp",
            "    push 1",
            "    add",
            "    popm __sp",
            "    jump __print_str_loop",
            "__print_str_end:",
            "    ret",
        ]


def generate(program: Program) -> str:
    return CodeGen(program).generate()


def main(source_file: str, asm_file: str) -> None:
    with open(source_file, encoding="utf-8") as f:
        source = f.read()

    try:
        program = parse(source)
        asm = generate(program)
    except (SyntaxError, ValueError) as e:
        print(f"Compilation error:\n{e}")
        sys.exit(1)

    with open(asm_file, "w", encoding="utf-8") as f:
        f.write(asm)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="alg -> asm translator")
    parser.add_argument("source", help="Source program (.alg)")
    parser.add_argument("output", help="Output assembler file (.asm)")
    parser.add_argument("--ast", action="store_true", help="Print the AST to stdout")
    args = parser.parse_args()
    if args.ast:
        with open(args.source, encoding="utf-8") as src:
            print(ast_dump(parse(src.read())))
    main(args.source, args.output)
