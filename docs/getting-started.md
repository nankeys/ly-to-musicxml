# Getting started

## Requirements

- Python 3.10 or newer
- A working LilyPond installation

The converter shells out to LilyPond during every conversion. The Python package alone is not enough to run it.

## Install from source

```powershell
pip install -e .
```

Or run it directly from the repository without installation:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m ly_to_musicxml.cli "input.ly" -o "output.musicxml"
```

## Install from PyPI

```powershell
pip install ly-to-musicxml
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