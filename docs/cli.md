# CLI reference

## Command

```powershell
ly-to-musicxml "input.ly" -o "output.musicxml"
```

## Arguments

- `input.ly`: input LilyPond file
- `-o`, `--output`: optional output MusicXML path
- `--lilypond-bin`: optional explicit LilyPond executable path

## Output behavior

If `--output` is omitted, the converter writes the first output next to the input file using the same stem and a `.musicxml` extension.

If the LilyPond input produces multiple non-empty scores, the converter writes:

- the first score to the requested output path
- additional scores to a sibling `stem.exports/` directory

Additional outputs use this pattern:

```text
stem.exports/book-NN-score-NN.musicxml
```

On rerun, the converter clears that `stem.exports/` directory and any legacy flat `stem.bookNN.scoreNN.musicxml` files for the same output stem before writing new output.