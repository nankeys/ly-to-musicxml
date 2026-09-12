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

    def test_fingering_writes_technical_fingering(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "fingering.ly"
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            output = Path(temp_dir) / "fingering.musicxml"
            result = convert_file(fixture, output)

            self.assertEqual([output], result.written_files)
            root = etree.parse(output).getroot()

            fingerings = [
                note.findtext("notations/technical/fingering")
                for note in root.findall(".//note")
            ]
            self.assertEqual(["1", "2", "3", "5", "1"], fingerings)

    def test_volta_writes_repeat_barlines_and_chord_slur_stop(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "repeat.ly"
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            output = Path(temp_dir) / "repeat.musicxml"
            result = convert_file(fixture, output)

            self.assertEqual([output], result.written_files)
            root = etree.parse(output).getroot()

            part = root.find("part")
            measures = part.findall("measure")

            # Body is written once, with repeat marks, not unfolded.
            self.assertEqual(2, len(measures))
            self.assertEqual(9, len(part.findall(".//note")))

            left = measures[0].find("barline[@location='left']")
            self.assertEqual("forward", left.find("repeat").get("direction"))
            self.assertEqual("heavy-light", left.findtext("bar-style"))

            right = measures[1].find("barline[@location='right']")
            self.assertEqual("backward", right.find("repeat").get("direction"))

            # Slur starts on the first note and stops on the chord's first note.
            first_note = measures[0].find("note")
            self.assertEqual("1", first_note.find("notations/slur").get("number"))
            self.assertEqual("start", first_note.find("notations/slur").get("type"))

            chord_first = measures[1].find("note")
            self.assertEqual("G", chord_first.findtext("pitch/step"))
            self.assertEqual("stop", chord_first.find("notations/slur").get("type"))
            self.assertEqual("1", chord_first.find("notations/slur").get("number"))

    def test_pianostaff_merges_staves_into_one_part(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "pianostaff.ly"
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            output = Path(temp_dir) / "pianostaff.musicxml"
            result = convert_file(fixture, output)

            self.assertEqual([output], result.written_files)
            root = etree.parse(output).getroot()

            parts = root.findall("part")
            self.assertEqual(1, len(parts))
            self.assertEqual("Piano", root.findtext(".//part-list/score-part/part-name"))

            measure = parts[0].find("measure")
            self.assertEqual("2", measure.findtext("attributes/staves"))

            clefs = measure.findall("attributes/clef")
            self.assertEqual(["1", "2"], [clef.get("number") for clef in clefs])
            self.assertEqual(["G", "F"], [clef.findtext("sign") for clef in clefs])

            notes = measure.findall("note")
            self.assertEqual(8, len(notes))
            self.assertEqual(["1"] * 4, [note.findtext("staff") for note in notes[:4]])
            self.assertEqual(["2"] * 4, [note.findtext("staff") for note in notes[4:]])

            self.assertEqual("4", measure.findtext("backup/duration"))

            # Slur numbers are unique across the merged part.
            slur_numbers = sorted(
                {
                    int(slur.get("number"))
                    for note in notes
                    for slur in note.findall("notations/slur")
                }
            )
            self.assertEqual([1, 2], slur_numbers)
            right_start = notes[0].find("notations/slur")
            left_start = notes[4].find("notations/slur")
            self.assertEqual("1", right_start.get("number"))
            self.assertEqual("2", left_start.get("number"))

    def test_dim_is_dynamic_text_not_wedge(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "dim.ly"
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            output = Path(temp_dir) / "dim.musicxml"
            result = convert_file(fixture, output)

            self.assertEqual([output], result.written_files)
            root = etree.parse(output).getroot()

            other_dynamics = [
                direction.findtext("direction-type/dynamics/other-dynamics")
                for direction in root.findall(".//direction")
                if direction.findtext("direction-type/dynamics/other-dynamics") is not None
            ]
            self.assertEqual(["dim."], other_dynamics)

            dim_direction = next(
                direction
                for direction in root.findall(".//direction")
                if direction.findtext("direction-type/dynamics/other-dynamics") is not None
            )
            self.assertEqual("below", dim_direction.get("placement"))

            wedges = [wedge.get("type") for wedge in root.findall(".//wedge")]
            self.assertEqual(["crescendo", "stop"], wedges)

    def test_tempo_range_writes_metronome_range(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "tempo.ly"
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            output = Path(temp_dir) / "tempo.musicxml"
            result = convert_file(fixture, output)

            self.assertEqual([output], result.written_files)
            root = etree.parse(output).getroot()

            metronome = root.find(".//direction/direction-type/metronome")
            self.assertEqual("quarter", metronome.findtext("beat-unit"))
            self.assertEqual("80 - 100", metronome.findtext("per-minute"))

            sound = root.find(".//direction/sound")
            self.assertEqual("80", sound.get("tempo"))
            self.assertEqual("Moderato", root.findtext(".//direction/direction-type/words"))

    def test_top_level_markup_becomes_credit(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "markup.ly"
        with tempfile.TemporaryDirectory(prefix="ly-to-musicxml-test-") as temp_dir:
            output = Path(temp_dir) / "markup.musicxml"
            result = convert_file(fixture, output)

            self.assertEqual([output], result.written_files)
            root = etree.parse(output).getroot()

            credits = root.findall("credit")
            self.assertEqual(1, len(credits))
            self.assertEqual("1", credits[0].get("page"))
            self.assertEqual("提示：尾部注释文本", credits[0].findtext("credit-words"))

            children = [child.tag for child in root]
            self.assertLess(children.index("credit"), children.index("part-list"))
            self.assertGreater(children.index("credit"), children.index("identification"))


if __name__ == "__main__":
    unittest.main()