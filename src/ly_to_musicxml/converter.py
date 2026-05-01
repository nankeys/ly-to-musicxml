from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil

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

    _cleanup_previous_outputs(primary_output)

    written_files: list[Path] = []
    for output_index, (book_index, score_index, score) in enumerate(scores_to_write):
        if output_index == 0:
            target_path = primary_output
        else:
            target_path = _additional_output_path(primary_output, book_index, score_index)
            warnings.append(
                f"Input contains multiple scores; wrote an additional MusicXML file to {target_path.relative_to(primary_output.parent)}."
            )
        write_score(score, target_path)
        written_files.append(target_path)

    return ConversionResult(written_files=written_files, warnings=warnings)


def _additional_output_path(primary_output: Path, book_index: int, score_index: int) -> Path:
    export_dir = primary_output.parent / f"{primary_output.stem}.exports"
    return export_dir / f"book-{book_index:02d}-score-{score_index:02d}{primary_output.suffix}"


def _cleanup_previous_outputs(primary_output: Path) -> None:
    export_dir = primary_output.parent / f"{primary_output.stem}.exports"
    if export_dir.exists():
        shutil.rmtree(export_dir)

    legacy_pattern = f"{primary_output.stem}.book*.score*{primary_output.suffix}"
    for legacy_file in primary_output.parent.glob(legacy_pattern):
        if legacy_file.is_file():
            legacy_file.unlink()