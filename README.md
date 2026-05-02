# ly-to-musicxml

Compiler-assisted conversion from LilyPond `.ly` files to MusicXML 4.0.

## Approach

This converter does not statically parse LilyPond source and it does not use PDF or optical music recognition.
It runs LilyPond itself in a no-print extraction mode, lets LilyPond resolve `\include` files and embedded Scheme, exports LilyPond's internal music tree to XML, then translates that compiler-resolved XML into MusicXML.

Normal conversion does not generate PDF output.

## Installation

Install the project in editable mode:

```powershell
pip install -e .
```

You can also run it without installation:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m ly_to_musicxml.cli "input.ly" -o "output.musicxml"
```

Install from PyPI once published:

```powershell
pip install ly-to-musicxml
```

This package depends on an external LilyPond installation at runtime. Installing with `pip` only installs the Python package and CLI; it does not install LilyPond itself.

## Usage

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml"
```

If `-o` is omitted, the converter writes the first output file next to the input using the same stem and a `.musicxml` extension.

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

## Multi-Score Inputs

If the input produces multiple non-empty scores or books, the converter preserves them by writing multiple MusicXML files.

- The first non-empty score is written to the requested output path.
- Additional non-empty scores are written into a sibling directory named `stem.exports/` using the pattern `book-NN-score-NN.musicxml`.
- Empty scores are skipped with warnings.

If you rerun the converter for the same output path, it clears the previous `stem.exports/` directory and any legacy `stem.bookNN.scoreNN.musicxml` files before writing fresh outputs.

For the provided `Shostakovich-String-Quartet-8.ly`, this means the quartet score and the extracted part books are written as separate MusicXML files.

## What Is Currently Mapped

The current translator maps these runtime LilyPond constructs to MusicXML:

- Parts and staves
- Notes, rests, chords, tuplets, and unfolded repeats
- Key signatures, time signatures, pickups, and barlines
- Ties, slurs, dynamics, text directions, tempo marks, and wedges
- Breath marks, ottava shifts, fermatas, and common articulation/bowing marks

## Scheme Handling

If the source file contains embedded Scheme syntax, the converter emits a warning that the output reflects one compiler evaluation.
This is intentional: the converter uses the actual LilyPond runtime result instead of guessing what the Scheme might do.

## Test

Run the focused regression test with:

```powershell
python -m unittest tests.test_converter
```

## Build And Publish

Build distributable artifacts for PyPI with:

```powershell
python -m build
```

This should produce both a wheel and an sdist in `dist/`.

Upload them to PyPI with:

```powershell
python -m twine upload dist/*
```