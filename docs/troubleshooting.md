# Troubleshooting

## LilyPond not found

If the CLI reports that LilyPond cannot be located, set the binary path explicitly:

```powershell
$env:LY_TO_MUSICXML_LILYPOND_BIN = "C:\path\to\lilypond.exe"
ly-to-musicxml "input.ly" -o "output.musicxml"
```

Alternatively, set it in the CLI call:

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml" --lilypond-bin "C:\path\to\lilypond.exe"
```

## Multiple output files

If you expect one output file but see several, inspect the sibling `stem.exports/` directory. The input likely produced multiple non-empty scores or books.

## Output looks stale

Open the newest generated `.musicxml` file, not an older export left open in another application. For multi-score inputs, also make sure you are opening the intended file from `stem.exports/`.

## Import looks wrong in another notation program

The converter writes standard MusicXML, but applications differ in how they render less common notation. If the MusicXML structure looks correct and the notation still renders incorrectly, the remaining issue may be importer-specific rather than converter-specific.

## Scheme in the source file

If the LilyPond source contains embedded Scheme, warnings may note that the output reflects one runtime evaluation. That is expected behavior for this converter.