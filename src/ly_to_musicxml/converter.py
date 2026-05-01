from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .lily_xml import parse_lily_xml
from .lilypond import extract_lily_xml
from .musicxml_writer import write_score


@dataclass(slots=True)
class ConversionResult:
    written_files: list[Path]
    warnings: list[str] = field(default_factory=list)


def convert_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    lilypond_bin: str | Path | None = None,
) -> ConversionResult:
    input_file = Path(input_path).resolve()
    primary_output = Path(output_path).resolve() if output_path else input_file.with_suffix(".musicxml")

    extraction = extract_lily_xml(input_file, lilypond_bin=lilypond_bin)
    parsed = parse_lily_xml(extraction.lily_xml_text, input_file)

    warnings = list(extraction.warnings)
    warnings.extend(parsed.warnings)

    scores_to_write = []
    for book in parsed.books:
        for score_index, score in enumerate(book.scores, start=1):
            if score.is_empty:
                warnings.append(
                    f"Skipping empty score from book {book.index}, score {score_index}."
                )
                continue
            scores_to_write.append((book.index, score_index, score))

    if not scores_to_write:
        raise RuntimeError("No non-empty scores were produced from the LilyPond input.")

    written_files: list[Path] = []
    for output_index, (book_index, score_index, score) in enumerate(scores_to_write):
        if output_index == 0:
            target_path = primary_output
        else:
            target_path = primary_output.with_name(
                f"{primary_output.stem}.book{book_index:02d}.score{score_index:02d}{primary_output.suffix}"
            )
            warnings.append(
                f"Input contains multiple scores; wrote an additional MusicXML file to {target_path.name}."
            )
        write_score(score, target_path)
        written_files.append(target_path)

    return ConversionResult(written_files=written_files, warnings=warnings)