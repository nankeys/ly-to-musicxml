from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .converter import convert_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert LilyPond files to MusicXML.")
    parser.add_argument("input_file", help="Path to the input .ly file")
    parser.add_argument("-o", "--output", help="Path to the output .musicxml file")
    parser.add_argument(
        "--lilypond-bin",
        help="Path to the LilyPond executable. Overrides LY_TO_MUSICXML_LILYPOND_BIN.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = convert_file(
            args.input_file,
            output_path=args.output,
            lilypond_bin=args.lilypond_bin,
        )
    except Exception as exc:  # pragma: no cover - CLI surface
        print(str(exc), file=sys.stderr)
        return 1

    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    for path in result.written_files:
        print(path)

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI surface
    raise SystemExit(main())