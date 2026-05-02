# Architecture

## Pipeline

The converter is compiler-assisted rather than text-only.

1. Resolve the LilyPond executable.
2. Generate a temporary wrapper score that includes the xml export helper.
3. Run LilyPond in extraction mode.
4. Parse the extracted Lily XML into an intermediate representation.
5. Serialize that representation to MusicXML 4.0.

The wrapper-based extraction path is intentionally repo-owned rather than delegated to a legacy runtime init hook. This keeps the extraction flow stable on the currently used LilyPond 2.26 installation.

## Main modules

- `src/ly_to_musicxml/lilypond.py`: LilyPond invocation and XML extraction
- `src/ly_to_musicxml/lily_xml.py`: Lily XML to intermediate model parsing
- `src/ly_to_musicxml/model.py`: dataclasses for score, measure, note, and direction state
- `src/ly_to_musicxml/musicxml_writer.py`: MusicXML serialization
- `src/ly_to_musicxml/converter.py`: end-to-end orchestration and output naming
- `src/ly_to_musicxml/cli.py`: command-line interface

## Behavioral notes

- The parser consumes compiler-resolved LilyPond XML rather than raw source tokens.
- Ottava is written as semantic MusicXML: note pitches stay at true pitch and `<octave-shift>` carries the printed shift direction required by MusicXML consumers.
- Additional non-empty scores are preserved in `stem.exports/` rather than being dropped.

LilyPond input may contain `\include`, Scheme, and other runtime constructs that are hard to convert correctly with static parsing alone.

By letting LilyPond evaluate the score first, the converter works from the compiler-resolved music tree instead of treating the file as static.