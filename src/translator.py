import argparse
import logging
import sys

import alg
import asm
from isa import DumpWriter

logger = logging.getLogger("translator")


def main(source_file: str, target_file: str, lang: str | None = None) -> None:
    with open(source_file, encoding="utf-8") as f:
        source_code = f.read()

    if lang is None:
        lang = "alg" if source_file.endswith(".alg") else "asm"

    try:
        if lang == "alg":
            source_code = alg.generate(alg.parse(source_code))
        # else if lang == "asm":
        memory, start_address = asm.translate(source_code)
    except Exception as e:
        print(f"Compilation error:\n{e}")
        sys.exit(1)

    DumpWriter.write_dump(target_file, memory, start_address)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stack Machine Translator")
    parser.add_argument("code", help="Program code (.asm or .alg)")
    parser.add_argument("binary_file", help="Compiled code (.bin)")
    parser.add_argument(
        "--lang",
        choices=["asm", "alg"],
        default=None,
        help="Source language (default: from file extension)",
    )
    args = parser.parse_args()
    main(args.code, args.binary_file, args.lang)
