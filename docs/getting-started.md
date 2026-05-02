# Getting started

## Requirements

- Python 3.10 or newer
- A working LilyPond installation

The converter shells out to LilyPond during every conversion. The Python package alone is not enough to run it.

Use a standard CPython install or a normal virtual environment for project work. Do not use LilyPond's bundled Python as the main interpreter for this repository because it does not ship with the usual packaging tools.

## Install from source

```powershell
pip install -e .
```

Or run it directly from the repository without installation:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m ly_to_musicxml "input.ly" -o "output.musicxml"
```

Recommended Windows setup:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

## Install from PyPI

```powershell
pip install ly-to-musicxml
```

TestPyPI install example:

```powershell
py -3.13 -m venv .testpypi-venv
.\.testpypi-venv\Scripts\python.exe -m pip install --upgrade pip
.\.testpypi-venv\Scripts\python.exe -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ly-to-musicxml
```

## First run

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml"
```

If LilyPond is not on the expected path, pass it explicitly:

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml" --lilypond-bin "C:\path\to\lilypond.exe"
```

Or configure it with an environment variable:

```powershell
$env:LY_TO_MUSICXML_LILYPOND_BIN = "C:\path\to\lilypond.exe"
ly-to-musicxml "input.ly" -o "output.musicxml"
```

## Manual verification

The current project state has been manually checked with both of these flows:

- local source invocation with `PYTHONPATH=src`
- installed package invocation from a clean TestPyPI virtual environment