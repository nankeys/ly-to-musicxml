# ly-to-musicxml limitations

Scope note: this audit covers the converter surface reviewed in this prompt, not the full LilyPond or MusicXML vendor submodules.

| File path | Audit status | Date last audited |
| --- | --- | --- |
| README.md | audited | 2026-04-30 |
| pyproject.toml | audited | 2026-04-30 |
| src/ly_to_musicxml/__init__.py | audited | 2026-04-30 |
| src/ly_to_musicxml/__main__.py | audited | 2026-04-30 |
| src/ly_to_musicxml/cli.py | audited | 2026-04-30 |
| src/ly_to_musicxml/converter.py | audited | 2026-04-30 |
| src/ly_to_musicxml/lilypond.py | audited | 2026-04-30 |
| src/ly_to_musicxml/lily_xml.py | audited | 2026-04-30 |
| src/ly_to_musicxml/model.py | audited | 2026-04-30 |
| src/ly_to_musicxml/musicxml_writer.py | audited | 2026-04-30 |
| python-ly/ly/xml/xml-export-init.ly | audited | 2026-04-30 |
| tests/fixtures/minimal.ly | audited | 2026-04-30 |
| tests/test_converter.py | audited | 2026-04-30 |
| ly-to-musicxml-limitations.md | audited | 2026-04-30 |

## README.md

Documents the compiler-assisted approach, LilyPond binary selection, CLI usage, multi-score output behavior, Scheme warning behavior, and the focused test command.

## pyproject.toml

Provides package metadata and the `ly-to-musicxml` console script entry point. It has not yet been exercised through an actual wheel build.

## src/ly_to_musicxml/__init__.py

Re-exports the main extraction, parsing, and conversion entry points.

## src/ly_to_musicxml/__main__.py

Lets the package run as `python -m ly_to_musicxml`.

## src/ly_to_musicxml/cli.py

Implements the command-line interface. It supports the required input and output flow plus explicit LilyPond binary selection.

## src/ly_to_musicxml/converter.py

Orchestrates extraction, parsing, score selection, and output writing. Multi-score inputs preserve additional non-empty scores as sibling files instead of silently dropping them.

## src/ly_to_musicxml/lilypond.py

Runs LilyPond in a wrapper-driven extraction mode that resolves includes and Scheme before translation. It warns when Scheme syntax is present because the output reflects one runtime evaluation.

## src/ly_to_musicxml/lily_xml.py

Parses the compiler-resolved Lily XML into a measure-oriented intermediate representation. The current implementation is intentionally narrow around the runtime shapes observed in the provided scores.

Pitch accidentals are converted from LilyPond's internal alteration units to MusicXML semitone alter values before serialization.

Known limits:

- Simultaneous voice branches inside a single staff are warned and only the first time-advancing branch is kept.
- Nested tuplets are warned and only the innermost tuplet ratio is emitted.
- Clef recovery currently uses the source origin line around `\clef` rather than a full decode of LilyPond's internal clef state.

## src/ly_to_musicxml/model.py

Holds the converter's score, measure, note, direction, and attribute dataclasses.

## src/ly_to_musicxml/musicxml_writer.py

Serializes the intermediate representation to MusicXML 4.0. The writer currently focuses on playback-relevant content and common notation signals used by the provided scores.

Known limits:

- Tuplet timing is preserved through `time-modification`, but explicit MusicXML tuplet bracket notation is not emitted yet.
- The writer emits additional directions in each part rather than deduplicating globally shared directions across a score.

## python-ly/ly/xml/xml-export-init.ly

Patched for LilyPond 2.26 compatibility during this prompt. The converter no longer depends on this file at runtime because it uses its own wrapper-based extraction path, but the compatibility fixes were retained because the original init script was broken on the installed LilyPond.

## tests/fixtures/minimal.ly

A focused single-score regression fixture used to validate the basic end-to-end pipeline quickly.

## tests/test_converter.py

Focused regression test covering a minimal conversion and verifying that a MusicXML partwise document with note content is written.

## ly-to-musicxml-limitations.md

Tracks the audited converter surface and the currently known limits from this prompt.