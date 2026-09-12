# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ly-to-musicxml` is a Python CLI that converts LilyPond (`.ly`) scores to MusicXML 4.0. Its defining trait is that it is **compiler-assisted, not a static parser**: it runs LilyPond itself in a no-print extraction mode, lets LilyPond resolve `\include` files and embedded Scheme, dumps LilyPond's internal music tree to a custom XML, then translates that XML to MusicXML.

## Commands

Examples are Windows/PowerShell (this is a Windows-first dev environment).

Install editable:

```powershell
pip install -e .
```

Run a conversion (module form needs `src` on `PYTHONPATH`):

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m ly_to_musicxml "input.ly" -o "output.musicxml"
```

Run the full test module:

```powershell
python -m unittest tests.test_converter
```

Run a single test:

```powershell
python -m unittest tests.test_converter.ConverterTest.test_ottava_writes_true_pitches
```

Build sdist + wheel:

```powershell
python -m build
```

No linter or formatter is configured in `pyproject.toml`.

### LilyPond binary

Every conversion (and two of the three tests) shells out to LilyPond, an external runtime dependency not installed by pip. It is located in this order: `--lilypond-bin` CLI flag → `LY_TO_MUSICXML_LILYPOND_BIN` env var → a hardcoded Windows default path in `src/ly_to_musicxml/lilypond.py`. On a machine without that default path, set:

```powershell
$env:LY_TO_MUSICXML_LILYPOND_BIN = "C:\path\to\lilypond.exe"
```

## Architecture

Pipeline (see `docs/architecture.md`):

1. `lilypond.py` — resolve the LilyPond binary, generate a temporary wrapper `.ly` that `\include`s the vendored XML export helper and defines a Scheme `toplevel-book-handler`, run `lilypond -dno-print-pages` on it, and read back the emitted XML (`extract_lily_xml`).
2. `lily_xml.py` — parse that compiler-resolved XML into the dataclasses in `model.py` (`LilyXmlParser`). This is where LilyPond runtime constructs (`ContextSpeccedMusic`, `SequentialMusic`, `EventChord`, `TempoChangeEvent`, `TimeScaledMusic`, etc.) are mapped to a measure-oriented intermediate form.
3. `musicxml_writer.py` — serialize the intermediate model to MusicXML 4.0 (`write_score`).
4. `converter.py` — orchestration and output-file naming (`convert_file`), the public entry point alongside `cli.py`.

`model.py` holds the intermediate representation: `Score`/`Book`/`Part`/`Measure` plus `MeasureItem` subclasses (`NoteGroupItem`, `AttributesItem`, `DirectionItem`, `BarlineItem`).

The input to `lily_xml.py` is **not** MusicXML and **not** `.ly` source — it is LilyPond's own music tree serialized by the vendored `python-ly/ly/xml/xml-export.ily` script, using `<music name="...">` elements and `<property name="...">` children. When touching parsing, you are working against this format.

### Vendored trees (reference only — do not edit)

- `lilypond/` — a full LilyPond 2.26 source tree, vendored for reference. Not built here.
- `musicxml/` — MusicXML 4.0 spec documentation.
- `python-ly/` — the upstream `python-ly` library. Only `ly/xml/xml-export.ily` is used at runtime; `lilypond.py` locates it by walking up from the input file's directory. `xml-export-init.ly` was patched for 2.26 but is no longer used at runtime.

## Gotchas

- Tests `test_minimal_score_converts` and `test_ottava_writes_true_pitches` invoke LilyPond end-to-end, so they fail without a reachable LilyPond binary.
- Multi-score inputs write the first score to the requested path and additional scores to a sibling `stem.exports/` directory (`book-NN-score-NN.musicxml`). Rerunning clears that directory and any legacy flat `stem.bookNN.scoreNN.musicxml` files.
- Do not use LilyPond's bundled Python as the project interpreter — it lacks `pip`/`build`/`twine`.
- `docs/publishing.md` is gitignored; it is referenced by `docs/index.md` but intentionally not committed.
- Top-level `.ly`/`.musicxml` files (e.g. `Shostakovich-String-Quartet-8.ly`, `No005.ly`, `movement-*.ly`) are example inputs and generated outputs, not source code. `*.musicxml` and `*.exports/` are gitignored.
