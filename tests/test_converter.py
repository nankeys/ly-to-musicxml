from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as etree


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ly_to_musicxml.converter import _additional_output_path, _cleanup_previous_outputs, convert_file  # noqa: E402


class ConverterTest(unittest.TestCase):
    def test_additional_outputs_use_exports_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            root = Path(temp_dir)
            primary = root / "score.musicxml"
            export_dir = root / "score.exports"
            legacy = root / "score.book02.score01.musicxml"

            export_dir.mkdir()
            (export_dir / "book-02-score-01.musicxml").write_text("new", encoding="utf-8")
            legacy.write_text("old", encoding="utf-8")

            target = _additional_output_path(primary, 2, 1)
            self.assertEqual(export_dir / "book-02-score-01.musicxml", target)

            _cleanup_previous_outputs(primary)

            self.assertFalse(export_dir.exists())
            self.assertFalse(legacy.exists())

    def test_minimal_score_converts(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "minimal.ly"
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            output = Path(temp_dir) / "minimal.musicxml"
            result = convert_file(fixture, output)

            self.assertEqual([output], result.written_files)
            root = etree.parse(output).getroot()

            self.assertEqual("score-partwise", root.tag)
            self.assertEqual("4.0", root.attrib.get("version"))
            self.assertEqual(1, len(root.findall("part")))
            self.assertGreater(len(root.findall(".//note")), 0)

    def test_ottava_writes_true_pitches(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "ottava.ly"
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            output = Path(temp_dir) / "ottava.musicxml"
            result = convert_file(fixture, output)

            self.assertEqual([output], result.written_files)
            root = etree.parse(output).getroot()

            octaves = [note.findtext("pitch/octave") for note in root.findall(".//note")]
            shifts = [direction.attrib for direction in root.findall(".//direction-type/octave-shift")]

            self.assertEqual(["4", "5", "4"], octaves)
            self.assertEqual(
                [
                    {"type": "down", "size": "8"},
                    {"type": "stop", "size": "8"},
                ],
                shifts,
            )


if __name__ == "__main__":
    unittest.main()