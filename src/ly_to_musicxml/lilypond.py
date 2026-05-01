from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import subprocess
import tempfile
import textwrap
import xml.etree.ElementTree as etree


LILYPOND_BIN_ENV = "LY_TO_MUSICXML_LILYPOND_BIN"
DEFAULT_LILYPOND_BIN = Path(
    r"C:\Users\kkris\Documents\lilypond-2.26.0-mingw-x86_64\lilypond-2.26.0\bin\lilypond.exe"
)


class LilyPondError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractionResult:
    lily_xml_text: str
    compiler_output: str
    warnings: tuple[str, ...]
    command: tuple[str, ...]
    input_path: Path
    contains_scheme: bool


def resolve_lilypond_binary(explicit_path: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env_path = os.environ.get(LILYPOND_BIN_ENV)
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(DEFAULT_LILYPOND_BIN)

    for candidate in candidates:
        expanded = candidate.expanduser()
        if expanded.exists():
            return expanded.resolve()

    attempted = "\n".join(str(path) for path in candidates)
    raise LilyPondError(
        "Unable to locate a LilyPond binary. Set LY_TO_MUSICXML_LILYPOND_BIN or pass --lilypond-bin.\n"
        f"Checked:\n{attempted}"
    )


def extract_lily_xml(input_path: str | Path, lilypond_bin: str | Path | None = None) -> ExtractionResult:
    score_path = Path(input_path).expanduser().resolve()
    if not score_path.exists():
        raise LilyPondError(f"Input file does not exist: {score_path}")

    lilypond_path = resolve_lilypond_binary(lilypond_bin)
    xml_export_path = _resolve_xml_export_path(score_path)
    contains_scheme = _score_contains_scheme(score_path)

    with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        output_path = temp_dir / "compiled-score.xml"
        wrapper_path = temp_dir / "extract-wrapper.ly"
        wrapper_path.write_text(
            _build_wrapper_source(score_path, output_path, xml_export_path),
            encoding="utf-8",
        )

        command = (
            str(lilypond_path),
            "-dno-print-pages",
            str(wrapper_path),
        )
        completed = subprocess.run(
            command,
            cwd=str(score_path.parent),
            text=True,
            capture_output=True,
            check=False,
        )

        compiler_output = completed.stdout
        if completed.stderr:
            compiler_output = f"{compiler_output}{completed.stderr}"

        if completed.returncode != 0:
            raise LilyPondError(
                f"LilyPond extraction failed with exit code {completed.returncode}.\n{compiler_output.strip()}"
            )

        if not output_path.exists():
            raise LilyPondError(
                "LilyPond completed successfully but did not produce extracted XML output.\n"
                f"Compiler output:\n{compiler_output.strip()}"
            )

        lily_xml_text = output_path.read_text(encoding="utf-8")
        if _xml_document_is_empty(lily_xml_text):
            raise LilyPondError(
                "LilyPond produced no top-level books or scores to convert.\n"
                f"Compiler output:\n{compiler_output.strip()}"
            )

    return ExtractionResult(
        lily_xml_text=lily_xml_text,
        compiler_output=compiler_output,
        warnings=tuple(_extract_warning_lines(compiler_output, contains_scheme)),
        command=command,
        input_path=score_path,
        contains_scheme=contains_scheme,
    )


def _resolve_xml_export_path(score_path: Path) -> Path:
    repo_root = score_path.parent
    while repo_root != repo_root.parent:
        candidate = repo_root / "python-ly" / "ly" / "xml" / "xml-export.ily"
        if candidate.exists():
            return candidate.resolve()
        repo_root = repo_root.parent
    raise LilyPondError(
        f"Unable to locate python-ly XML export script relative to {score_path}."
    )


def _build_wrapper_source(score_path: Path, output_path: Path, xml_export_path: Path) -> str:
    score_literal = _scheme_path_literal(score_path)
    output_literal = _scheme_path_literal(output_path)
    xml_export_literal = _scheme_path_literal(xml_export_path)
    return textwrap.dedent(
        f"""\
        \\version "2.26.0"

        #(define old-option-relative-includes (ly:get-option 'relative-includes))
        #(ly:set-option 'relative-includes #t)
        \\include "{xml_export_literal}"

        #(define xml-outputter
           (let* ((port (open-output-file "{output_literal}"))
                  (xml (XML port)))
             (ly:message (format #f "Writing XML to ~a..." "{output_literal}"))
             (xml 'declaration)
             (xml 'open-tag 'document)
             xml))

        #(define-public (xml-book-handler book)
           (obj->lily-xml book xml-outputter))

                #(define (flush-collected-top-level-books!)
                     (cond
                        ((pair? toplevel-bookparts)
                         (let ((book (ly:make-book $defaultpaper $defaultheader)))
                             (for-each (lambda (part)
                                                     (ly:book-add-bookpart! book part))
                                                 (reverse! toplevel-bookparts))
                             (set! toplevel-bookparts (list))
                             (if (pair? toplevel-scores)
                                     (for-each (lambda (score)
                                                             (ly:book-add-score! book score))
                                                         (reverse! toplevel-scores)))
                             (set! toplevel-scores (list))
                             (xml-book-handler book)))
                        ((pair? toplevel-scores)
                         (let ((book (apply ly:make-book $defaultpaper $defaultheader toplevel-scores)))
                             (set! toplevel-scores (list))
                             (xml-book-handler book)))))

                #(ly:parser-define! 'toplevel-book-handler xml-book-handler)

        \\include "{score_literal}"
                #(flush-collected-top-level-books!)
                #(xml-outputter 'close-tag)
                #(ly:message "Writing XML completed.")
        #(ly:set-option 'relative-includes old-option-relative-includes)
        """
    )


def _scheme_path_literal(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace('"', r'\"')


def _score_contains_scheme(score_path: Path) -> bool:
    text = score_path.read_text(encoding="utf-8", errors="ignore")
    return any(marker in text for marker in ("#(", "$(", "#{", "#'", "#\""))


def _xml_document_is_empty(lily_xml_text: str) -> bool:
    root = etree.fromstring(lily_xml_text)
    return root.tag == "document" and len(root) == 0


def _extract_warning_lines(compiler_output: str, contains_scheme: bool) -> list[str]:
    warnings: list[str] = []
    for line in compiler_output.splitlines():
        if re.search(r"(^warning:|: warning:)", line, re.IGNORECASE):
            warnings.append(line.strip())

    if contains_scheme:
        warnings.append(
            "Score contains embedded Scheme. Output reflects one compiler evaluation and may vary if the Scheme is nondeterministic."
        )

    return warnings