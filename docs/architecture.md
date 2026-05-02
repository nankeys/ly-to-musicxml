# Architecture

## Pipeline

The converter is compiler-assisted rather than text-only.

1. Resolve the LilyPond executable.
2. Generate a temporary wrapper score that includes the xml export helper.
3. Run LilyPond in extraction mode.
4. Parse the extracted Lily XML into an intermediate representation.
5. Serialize that representation to MusicXML 4.0.

## Main modules

- `src/ly_to_musicxml/lilypond.py`: LilyPond invocation and XML extraction
- `src/ly_to_musicxml/lily_xml.py`: Lily XML to intermediate model parsing
- `src/ly_to_musicxml/model.py`: dataclasses for score, measure, note, and direction state
- `src/ly_to_musicxml/musicxml_writer.py`: MusicXML serialization
- `src/ly_to_musicxml/converter.py`: end-to-end orchestration and output naming
- `src/ly_to_musicxml/cli.py`: command-line interface

LilyPond input may contain `\include`, Scheme, and other runtime constructs that are hard to convert correctly with static parsing alone.

By letting LilyPond evaluate the score first, the converter works from the compiler-resolved music tree instead of treating the file as static.