from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as etree


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ly_to_musicxml.converter import convert_file  # noqa: E402


class ConverterTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()