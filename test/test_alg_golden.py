import contextlib
import io
import logging
import os
import tempfile

import pytest

import alg
import machine
import translator

LOG_MAX = 1024


def truncate(log: str) -> str:
    if len(log.splitlines()) <= LOG_MAX:
        return log
    return "\n".join(log.splitlines()[:LOG_MAX]) + "\n..."


@pytest.mark.golden_test("golden/alg/*.yml")
def test_alg_pipeline(golden, caplog):
    """alg -> AST -> asm -> binary -> machine, checked end to end."""
    program = alg.parse(golden["in_source"])
    ast = alg.dump_ast(program)
    asm = alg.generate(program)

    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdir:
        asm_path = os.path.join(tmpdir, "program.asm")
        bin_path = os.path.join(tmpdir, "program.bin")
        input_path = os.path.join(tmpdir, "input.txt")
        dump_path = os.path.join(tmpdir, "program_dump.log")

        with open(asm_path, "w", encoding="utf-8") as f:
            f.write(asm)

        stdin_content = golden.get("in_stdin") or ""
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(stdin_content)

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(asm_path, bin_path)
            machine.main(bin_path, input_path if stdin_content else "")

        with open(dump_path, encoding="utf-8") as f:
            machine_code = f.read()

    trunc_logs = truncate("\n".join(record.getMessage() for record in caplog.records))

    assert golden.out["ast"] == ast
    assert golden.out["asm"] == asm
    assert golden.out["machine_code"] == machine_code
    assert golden.out["output"] == stdout.getvalue()
    assert golden.out["out_log"] == trunc_logs
