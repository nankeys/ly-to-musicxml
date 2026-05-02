# ly-to-musicxml limitations

Scope note: this audit covers the converter surface reviewed in this prompt, not the full LilyPond or MusicXML vendor submodules.

| File path | Audit status | Date last audited |
| --- | --- | --- |
| README.md | audited | 2026-05-02 |
| pyproject.toml | audited | 2026-04-30 |
| src/ly_to_musicxml/__init__.py | audited | 2026-04-30 |
| src/ly_to_musicxml/__main__.py | audited | 2026-05-02 |
| src/ly_to_musicxml/cli.py | audited | 2026-05-02 |
| src/ly_to_musicxml/converter.py | audited | 2026-05-02 |
| src/ly_to_musicxml/lilypond.py | audited | 2026-05-02 |
| src/ly_to_musicxml/lily_xml.py | audited | 2026-05-02 |
| src/ly_to_musicxml/model.py | audited | 2026-04-30 |
| src/ly_to_musicxml/musicxml_writer.py | audited | 2026-05-02 |
| python-ly/ly/xml/xml-export-init.ly | audited | 2026-04-30 |
| tests/fixtures/minimal.ly | audited | 2026-04-30 |
| tests/fixtures/ottava.ly | audited | 2026-05-02 |
| tests/test_converter.py | audited | 2026-05-02 |
| docs/index.md | audited | 2026-05-02 |
| docs/getting-started.md | audited | 2026-05-02 |
| docs/cli.md | audited | 2026-05-02 |
| docs/architecture.md | audited | 2026-05-02 |
| docs/troubleshooting.md | audited | 2026-05-02 |
| docs/publishing.md | audited | 2026-05-02 |
| docs/ly-to-musicxml-limitations.md | audited | 2026-05-02 |

## README.md

Documents the compiler-assisted approach, LilyPond binary selection, CLI usage, multi-score output behavior, interpreter guidance, and both local-source and TestPyPI validation flows.

## pyproject.toml

Provides package metadata and the `ly-to-musicxml` console script entry point. It has been exercised through both local build artifacts and an installed TestPyPI wheel.

## src/ly_to_musicxml/__init__.py

Re-exports the main extraction, parsing, and conversion entry points.

## src/ly_to_musicxml/__main__.py

Lets the package run as `python -m ly_to_musicxml`.

## src/ly_to_musicxml/cli.py

Implements the command-line interface. It supports the required input and output flow plus explicit LilyPond binary selection.

## src/ly_to_musicxml/converter.py

Orchestrates extraction, parsing, score selection, cleanup, and output writing. Multi-score inputs preserve additional non-empty scores in a sibling `stem.exports/` directory instead of silently dropping them.

Known limits:

- Additional outputs are still identified generically as `book-NN-score-NN` because the Lily runtime metadata available here does not reliably expose human-friendly movement or layout names for every emitted score.

## src/ly_to_musicxml/lilypond.py

Runs LilyPond in a wrapper-driven extraction mode that resolves includes and Scheme before translation. It warns when Scheme syntax is present because the output reflects one runtime evaluation.

The current extraction path is independent of the legacy `python-ly` init hook used in earlier experiments.

## src/ly_to_musicxml/lily_xml.py

Parses the compiler-resolved Lily XML into a measure-oriented intermediate representation. The current implementation is intentionally narrow around the runtime shapes observed in the provided scores.

Pitch accidentals are converted from LilyPond's internal alteration units to MusicXML semitone alter values before serialization.

Ottava is mapped using MusicXML semantic direction rules: true pitches are preserved and the emitted `<octave-shift>` direction carries the printed 8va/8vb behavior expected by MusicXML consumers.

Known limits:

- Simultaneous voice branches inside a single staff are warned and only the first time-advancing branch is kept.
- Nested tuplets are warned and only the innermost tuplet ratio is emitted.
- Clef recovery still depends on a mixture of runtime property state and source-origin fallback rather than a full decode of every LilyPond clef-related runtime detail.

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

## tests/fixtures/ottava.ly

Focused regression fixture that protects the current ottava mapping behavior: true note pitches plus semantic MusicXML octave-shift directions.

## tests/test_converter.py

Focused regression tests covering output cleanup, minimal conversion, and ottava emission behavior.

## docs/index.md

Entry point for the documentation set.

## docs/getting-started.md

Documents source installs, PyPI and TestPyPI installs, and the preferred interpreter setup.

## docs/cli.md

Documents the console and module entry points plus multi-score output layout.

## docs/architecture.md

Documents the wrapper-based compiler-assisted pipeline and the current module split.

## docs/troubleshooting.md

Documents LilyPond path issues, stale-output confusion, and VS Code interpreter-selection problems.

## docs/publishing.md

Documents manual builds, TestPyPI uploads, trusted publishing, and post-publish smoke tests.