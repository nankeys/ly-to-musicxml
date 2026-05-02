# ly-to-musicxml

Compiler-assisted conversion from LilyPond `.ly` files to MusicXML 4.0.

This project has been manually validated from the local source tree, from TestPyPI, and from a real PyPI install.

## Quick start

Install the package:

```powershell
pip install ly-to-musicxml
```

Run a conversion:

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml"
```

If LilyPond is not on the expected path, pass it explicitly:

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml" --lilypond-bin "C:\path\to\lilypond.exe"
```

Installing with `pip` only installs the Python package and CLI. LilyPond remains an external runtime dependency.

## Requirements

- Python 3.10 or newer
- A working LilyPond installation available either through `--lilypond-bin`, `LY_TO_MUSICXML_LILYPOND_BIN`, or the default configured path

The converter executes LilyPond during every run, so a missing or incompatible LilyPond install is the most common setup problem.

For packaging, testing, and documentation tasks, use a standard CPython install or a normal virtual environment. Avoid using LilyPond's bundled Python as your main project interpreter because it does not include normal packaging tooling such as `pip`, `build`, or `twine`.

## Installation

Install from PyPI:

```powershell
pip install ly-to-musicxml
```

Install from source in editable mode:

```powershell
pip install -e .
```

Run directly from the repository without installation:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m ly_to_musicxml "input.ly" -o "output.musicxml"
```

## Usage

Console entry point:

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml"
```

Module entry point:

```powershell
python -m ly_to_musicxml "input.ly" -o "output.musicxml"
```

If `-o` is omitted, the converter writes the first output file next to the input using the same stem and a `.musicxml` extension.

## Approach

This converter does not statically parse LilyPond source and it does not use PDF or optical music recognition.
It runs LilyPond itself in a no-print extraction mode, lets LilyPond resolve `\include` files and embedded Scheme, exports LilyPond's internal music tree to XML, then translates that compiler-resolved XML into MusicXML.

Normal conversion does not generate PDF output.

## LilyPond Binary Selection

The converter looks for LilyPond in this order:

1. `--lilypond-bin`
2. `LY_TO_MUSICXML_LILYPOND_BIN`
3. The reference path from the project brief:
	`C:\Users\kkris\Documents\lilypond-2.26.0-mingw-x86_64\lilypond-2.26.0\bin\lilypond.exe`

Example:

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml" --lilypond-bin "C:\path\to\lilypond.exe"
```

Or via environment variable:

```powershell
$env:LY_TO_MUSICXML_LILYPOND_BIN = "C:\path\to\lilypond.exe"
ly-to-musicxml "input.ly" -o "output.musicxml"
```

This is usually the easiest way to make repeated CLI runs use the same LilyPond install.

## Multi-Score Inputs

If the input produces multiple non-empty scores or books, the converter preserves them by writing multiple MusicXML files.

- The first non-empty score is written to the requested output path.
- Additional non-empty scores are written into a sibling directory named `stem.exports/` using the pattern `book-NN-score-NN.musicxml`.
- Empty scores are skipped with warnings.

If you rerun the converter for the same output path, it clears the previous `stem.exports/` directory and any legacy `stem.bookNN.scoreNN.musicxml` files before writing fresh outputs.

Example output layout for a multi-score input:

```text
Shostakovich-String-Quartet-8.musicxml
Shostakovich-String-Quartet-8.exports/
	book-01-score-02.musicxml
	book-02-score-01.musicxml
	...
```

## What Is Currently Mapped

The current translator maps these runtime LilyPond constructs to MusicXML:

- Parts and staves
- Notes, rests, chords, tuplets, and unfolded repeats
- Key signatures, time signatures, pickups, and barlines
- Ties, slurs, dynamics, text directions, tempo marks, and wedges
- Breath marks, ottava shifts, fermatas, and common articulation/bowing marks

See [docs/ly-to-musicxml-limitations.md](docs/ly-to-musicxml-limitations.md) for the current boundary conditions and known gaps.

## Scheme Handling

If the source file contains embedded Scheme syntax, the converter emits a warning that the output reflects one compiler evaluation.
This is intentional: the converter uses the actual LilyPond runtime result instead of guessing what the Scheme might do.

## Troubleshooting

If the CLI reports that it cannot find LilyPond:

```powershell
$env:LY_TO_MUSICXML_LILYPOND_BIN = "C:\path\to\lilypond.exe"
ly-to-musicxml "input.ly" -o "output.musicxml"
```

If a conversion writes multiple files unexpectedly, check for a sibling `stem.exports/` directory next to the main output file. That directory contains additional non-empty scores extracted from the same LilyPond input.

If the output looks wrong in another notation program, first confirm you are opening the newly generated `.musicxml` file rather than an older export from a previous run.

If VS Code auto-selects LilyPond's bundled Python for this workspace, switch to a standard CPython interpreter or a normal venv before doing package builds, `pip install`, or `twine upload`. The bundled interpreter can run LilyPond internals but is not a good development environment for this project.

## Validation

Run the focused regression test with:

```powershell
python -m unittest tests.test_converter
```

Manual local-source smoke test:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m ly_to_musicxml --help
python -m ly_to_musicxml "Shostakovich-String-Quartet-8.ly" -o "local-manual-smoke.musicxml" --lilypond-bin "C:\Users\kkris\Documents\lilypond-2.26.0-mingw-x86_64\lilypond-2.26.0\bin\lilypond.exe"
```

Real PyPI smoke test:

```powershell
py -3.13 -m venv .pypi-venv
.\.pypi-venv\Scripts\python.exe -m pip install --upgrade pip
.\.pypi-venv\Scripts\python.exe -m pip install ly-to-musicxml
.\.pypi-venv\Scripts\ly-to-musicxml.exe "Shostakovich-String-Quartet-8.ly" -o "pypi-smoke.musicxml" --lilypond-bin "C:\Users\kkris\Documents\lilypond-2.26.0-mingw-x86_64\lilypond-2.26.0\bin\lilypond.exe"
```

TestPyPI smoke test:

```powershell
py -3.13 -m venv .testpypi-venv
.\.testpypi-venv\Scripts\python.exe -m pip install --upgrade pip
.\.testpypi-venv\Scripts\python.exe -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ly-to-musicxml
.\.testpypi-venv\Scripts\ly-to-musicxml.exe "Shostakovich-String-Quartet-8.ly" -o "testpypi-smoke.musicxml" --lilypond-bin "C:\Users\kkris\Documents\lilypond-2.26.0-mingw-x86_64\lilypond-2.26.0\bin\lilypond.exe"
```