import contextlib
import io
import logging
import os
import tempfile

import pytest

import machine
import translator

LOG_MAX = 1024


def truncate(log: str) -> str:
    if len(log.splitlines()) <= LOG_MAX:
        return log

    return "\n".join(log.splitlines()[:LOG_MAX]) + "\n..."


@pytest.mark.golden_test("golden/asm/*.yml")
def test_translator_and_machine(golden, caplog):
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = os.path.join(tmpdir, "source.asm")
        input_path = os.path.join(tmpdir, "input.txt")
        target_path = os.path.join(tmpdir, "output.bin")
        target_hex_path = os.path.join(tmpdir, "output_dump.log")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(golden["in_source"])

        stdin_content = golden.get("in_stdin") or ""
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(stdin_content)

        caplog.set_level(logging.DEBUG)

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source_path, target_path)
            machine.main(target_path, input_path if stdin_content else "")

        with open(target_hex_path, encoding="utf-8") as f:
            machine_code = f.read()

    trunc_logs = truncate("\n".join(record.getMessage() for record in caplog.records))

    assert golden.out["machine_code"] == machine_code
    assert golden.out["output"] == stdout.getvalue()
    assert golden.out["out_log"] == trunc_logs
