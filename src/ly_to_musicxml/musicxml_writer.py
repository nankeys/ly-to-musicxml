from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as etree

from .model import AttributesItem, BarlineItem, DirectionItem, Measure, MeasureItem, MetronomeMark, Note, NoteGroupItem, OctaveShift, Part, Pitch, Score


def write_score(score: Score, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = build_musicxml_tree(score)
    etree.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def build_musicxml_tree(score: Score) -> etree.ElementTree:
    root = etree.Element("score-partwise", version="4.0")
    _append_header(root, score)
    for credit_text in score.credits:
        credit = etree.SubElement(root, "credit", page="1")
        credit_words = etree.SubElement(credit, "credit-words")
        credit_words.text = credit_text
    part_list = etree.SubElement(root, "part-list")
    for part in score.parts:
        score_part = etree.SubElement(part_list, "score-part", id=part.identifier)
        part_name = etree.SubElement(score_part, "part-name")
        part_name.text = part.name

    for part in score.parts:
        _append_part(root, part)

    return etree.ElementTree(root)


def _append_header(root: etree.Element, score: Score) -> None:
    title = score.header.get("title") or score.header.get("movement-title")
    if title:
        movement_title = etree.SubElement(root, "movement-title")
        movement_title.text = title

    identification = etree.SubElement(root, "identification")
    encoding = etree.SubElement(identification, "encoding")
    software = etree.SubElement(encoding, "software")
    software.text = "ly-to-musicxml"

    composer = score.header.get("composer")
    if composer:
        creator = etree.SubElement(identification, "creator", type="composer")
        creator.text = composer

    lyricist = score.header.get("poet") or score.header.get("lyricist")
    if lyricist:
        creator = etree.SubElement(identification, "creator", type="lyricist")
        creator.text = lyricist

    rights = score.header.get("copyright")
    if rights:
        rights_elem = etree.SubElement(identification, "rights")
        rights_elem.text = rights


def _append_part(root: etree.Element, part: Part) -> None:
    part_elem = etree.SubElement(root, "part", id=part.identifier)
    current_divisions = 1
    has_emitted_clef = False
    for measure in part.measures:
        measure_elem = etree.SubElement(part_elem, "measure", number=str(measure.number))
        if measure.implicit:
            measure_elem.set("implicit", "yes")

        staff_streams = _split_measure_by_staff(measure.items)

        opening_attributes = AttributesItem()
        opening_clefs: dict[int, AttributesItem] = {}
        opening_directions: list[DirectionItem] = []

        for staff_number, items in staff_streams.items():
            index = 0
            while index < len(items):
                item = items[index]
                if isinstance(item, AttributesItem):
                    if item.divisions is not None:
                        current_divisions = item.divisions
                    if item.clef_sign is not None:
                        opening_clefs[staff_number] = item
                    _merge_attributes(opening_attributes, item)
                    index += 1
                    continue
                if isinstance(item, DirectionItem):
                    opening_directions.append(item)
                    index += 1
                    continue
                break
            staff_streams[staff_number] = items[index:]

        if not has_emitted_clef:
            for staff_number in staff_streams:
                opening_clefs.setdefault(staff_number, _default_clef_item(staff_number))
            has_emitted_clef = True

        if _attributes_have_content(opening_attributes) or opening_clefs:
            _append_attributes(measure_elem, opening_attributes, part.staves, opening_clefs)

        for direction in _dedupe_directions(opening_directions, part.staves):
            _append_direction(measure_elem, direction, part.staves)

        staff_numbers = sorted(staff_streams)
        backup_duration = _measure_duration_divisions(measure, current_divisions)
        for position, staff_number in enumerate(staff_numbers):
            if position > 0:
                backup = etree.SubElement(measure_elem, "backup")
                duration = etree.SubElement(backup, "duration")
                duration.text = str(backup_duration)

            items = staff_streams[staff_number]
            index = 0
            while index < len(items):
                item = items[index]
                if isinstance(item, AttributesItem):
                    merged = AttributesItem()
                    clefs: dict[int, AttributesItem] = {}
                    while index < len(items) and isinstance(items[index], AttributesItem):
                        current = items[index]
                        if current.divisions is not None:
                            current_divisions = current.divisions
                        if current.clef_sign is not None:
                            clefs[current.staff] = current
                        _merge_attributes(merged, current)
                        index += 1
                    if _attributes_have_content(merged) or clefs:
                        _append_attributes(measure_elem, merged, part.staves, clefs)
                    continue

                _append_measure_item(measure_elem, item, current_divisions, part.staves)
                index += 1

        if measure.left_repeat:
            barline = etree.SubElement(measure_elem, "barline", location="left")
            style = etree.SubElement(barline, "bar-style")
            style.text = "heavy-light"
            etree.SubElement(barline, "repeat", direction="forward")

        if measure.right_barline or measure.right_repeat:
            barline = etree.SubElement(measure_elem, "barline", location="right")
            style_text = measure.right_barline or ("light-heavy" if measure.right_repeat else None)
            if style_text:
                style = etree.SubElement(barline, "bar-style")
                style.text = style_text
            if measure.right_repeat:
                etree.SubElement(barline, "repeat", direction="backward")


def _append_measure_item(measure_elem: etree.Element, item: MeasureItem, divisions: int, part_staves: int) -> None:
    if isinstance(item, AttributesItem):
        _append_attributes(measure_elem, item, part_staves)
        return
    if isinstance(item, DirectionItem):
        _append_direction(measure_elem, item, part_staves)
        return
    if isinstance(item, NoteGroupItem):
        _append_note_group(measure_elem, item, divisions, part_staves)
        return
    if isinstance(item, BarlineItem):
        return
    raise TypeError(f"Unsupported measure item: {type(item)!r}")


def _split_measure_by_staff(items: list[MeasureItem]) -> dict[int, list[MeasureItem]]:
    streams: dict[int, list[MeasureItem]] = {}
    for item in items:
        streams.setdefault(item.staff, []).append(item)
    return streams


def _default_clef_item(staff_number: int) -> AttributesItem:
    if staff_number == 1:
        return AttributesItem(clef_sign="G", clef_line=2)
    return AttributesItem(clef_sign="F", clef_line=4)


def _dedupe_directions(directions: list[DirectionItem], part_staves: int) -> list[DirectionItem]:
    if part_staves <= 1:
        return directions
    result: list[DirectionItem] = []
    seen: set[tuple] = set()
    for direction in directions:
        metronome = direction.metronome
        octave_shift = direction.octave_shift
        key = (
            direction.words,
            tuple(direction.dynamics),
            tuple(direction.other_dynamics),
            direction.wedge,
            metronome.beat_unit if metronome is not None else None,
            metronome.per_minute if metronome is not None else None,
            direction.placement,
            octave_shift.shift_type if octave_shift is not None else None,
            octave_shift.size if octave_shift is not None else None,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(direction)
    return result


def _measure_duration_divisions(measure: Measure, divisions: int) -> int:
    per_staff: dict[int, Fraction] = {}
    for item in measure.items:
        if isinstance(item, NoteGroupItem):
            per_staff[item.staff] = per_staff.get(item.staff, Fraction(0)) + item.duration
    duration = max(per_staff.values()) if per_staff else Fraction(0)
    return int(duration * 4 * divisions)


def _append_attributes(
    measure_elem: etree.Element,
    item: AttributesItem,
    part_staves: int = 1,
    clefs: dict[int, AttributesItem] | None = None,
) -> None:
    if clefs is None and item.clef_sign is not None:
        clefs = {item.staff: item}
    attributes = etree.SubElement(measure_elem, "attributes")
    if item.divisions is not None:
        divisions = etree.SubElement(attributes, "divisions")
        divisions.text = str(item.divisions)
    if item.key_fifths is not None:
        key = etree.SubElement(attributes, "key")
        fifths = etree.SubElement(key, "fifths")
        fifths.text = str(item.key_fifths)
        if item.key_mode:
            mode = etree.SubElement(key, "mode")
            mode.text = item.key_mode
    if item.beats is not None and item.beat_type is not None:
        time = etree.SubElement(attributes, "time")
        beats = etree.SubElement(time, "beats")
        beats.text = str(item.beats)
        beat_type = etree.SubElement(time, "beat-type")
        beat_type.text = str(item.beat_type)
    if part_staves > 1:
        staves = etree.SubElement(attributes, "staves")
        staves.text = str(part_staves)
    for staff_number, clef_item in sorted((clefs or {}).items()):
        clef = etree.SubElement(attributes, "clef")
        if part_staves > 1:
            clef.set("number", str(staff_number))
        sign = etree.SubElement(clef, "sign")
        sign.text = clef_item.clef_sign
        line = etree.SubElement(clef, "line")
        line.text = str(clef_item.clef_line)
        if clef_item.clef_octave_change is not None:
            octave_change = etree.SubElement(clef, "clef-octave-change")
            octave_change.text = str(clef_item.clef_octave_change)


def _merge_attributes(target: AttributesItem, source: AttributesItem) -> None:
    if source.divisions is not None:
        target.divisions = source.divisions
    if source.key_fifths is not None:
        target.key_fifths = source.key_fifths
    if source.key_mode is not None:
        target.key_mode = source.key_mode
    if source.beats is not None:
        target.beats = source.beats
    if source.beat_type is not None:
        target.beat_type = source.beat_type


def _attributes_have_content(item: AttributesItem) -> bool:
    return any(
        value is not None
        for value in (
            item.divisions,
            item.key_fifths,
            item.key_mode,
            item.beats,
            item.beat_type,
            item.clef_sign,
            item.clef_line,
            item.clef_octave_change,
        )
    )


def _append_direction(measure_elem: etree.Element, item: DirectionItem, part_staves: int = 1) -> None:
    if not any([item.words, item.dynamics, item.other_dynamics, item.wedge, item.metronome, item.octave_shift]):
        return
    direction = etree.SubElement(measure_elem, "direction")
    if item.placement:
        direction.set("placement", item.placement)

    if item.words:
        direction_type = etree.SubElement(direction, "direction-type")
        words = etree.SubElement(direction_type, "words")
        words.text = item.words

    if item.dynamics or item.other_dynamics:
        direction_type = etree.SubElement(direction, "direction-type")
        dynamics = etree.SubElement(direction_type, "dynamics")
        for dynamic in item.dynamics:
            etree.SubElement(dynamics, dynamic)
        for other_dynamic in item.other_dynamics:
            other = etree.SubElement(dynamics, "other-dynamics")
            other.text = other_dynamic

    if item.metronome is not None:
        direction_type = etree.SubElement(direction, "direction-type")
        _append_metronome(direction_type, item.metronome)

    if item.wedge:
        direction_type = etree.SubElement(direction, "direction-type")
        etree.SubElement(direction_type, "wedge", type=item.wedge)

    if item.octave_shift is not None:
        direction_type = etree.SubElement(direction, "direction-type")
        _append_octave_shift(direction_type, item.octave_shift)

    if part_staves > 1 and item.staff is not None:
        staff = etree.SubElement(direction, "staff")
        staff.text = str(item.staff)

    if item.metronome is not None and item.metronome.sound_tempo is not None:
        sound = etree.SubElement(direction, "sound")
        sound.set("tempo", f"{item.metronome.sound_tempo:g}")


def _append_metronome(direction_type: etree.Element, metronome_mark: MetronomeMark) -> None:
    metronome = etree.SubElement(direction_type, "metronome")
    beat_unit = etree.SubElement(metronome, "beat-unit")
    beat_unit.text = metronome_mark.beat_unit
    for _ in range(metronome_mark.beat_unit_dots):
        etree.SubElement(metronome, "beat-unit-dot")
    per_minute = etree.SubElement(metronome, "per-minute")
    per_minute.text = metronome_mark.per_minute


def _append_octave_shift(direction_type: etree.Element, octave_shift: OctaveShift) -> None:
    etree.SubElement(
        direction_type,
        "octave-shift",
        type=octave_shift.shift_type,
        size=str(octave_shift.size),
    )


def _append_note_group(measure_elem: etree.Element, item: NoteGroupItem, divisions: int, part_staves: int) -> None:
    staff_number = item.staff if part_staves > 1 else None
    for index, note in enumerate(item.notes):
        _append_note(measure_elem, note, divisions, is_chord=index > 0, staff_number=staff_number)


def _append_note(
    measure_elem: etree.Element,
    note: Note,
    divisions: int,
    is_chord: bool,
    staff_number: int | None = None,
) -> None:
    note_elem = etree.SubElement(measure_elem, "note")
    if is_chord:
        etree.SubElement(note_elem, "chord")

    if note.is_rest:
        etree.SubElement(note_elem, "rest")
    else:
        _append_pitch(note_elem, note.pitch)

    duration = etree.SubElement(note_elem, "duration")
    duration.text = str(int(note.duration * 4 * divisions))

    if note.tie_stop:
        etree.SubElement(note_elem, "tie", type="stop")
    if note.tie_start:
        etree.SubElement(note_elem, "tie", type="start")

    voice = etree.SubElement(note_elem, "voice")
    voice.text = str(note.voice)

    if note.type_name:
        type_elem = etree.SubElement(note_elem, "type")
        type_elem.text = note.type_name

    for _ in range(note.dots):
        etree.SubElement(note_elem, "dot")

    if note.tuplet_actual is not None and note.tuplet_normal is not None:
        time_mod = etree.SubElement(note_elem, "time-modification")
        actual_notes = etree.SubElement(time_mod, "actual-notes")
        actual_notes.text = str(note.tuplet_actual)
        normal_notes = etree.SubElement(time_mod, "normal-notes")
        normal_notes.text = str(note.tuplet_normal)

    if staff_number is not None:
        staff = etree.SubElement(note_elem, "staff")
        staff.text = str(staff_number)

    _append_note_notations(note_elem, note)


def _append_pitch(note_elem: etree.Element, pitch: Pitch | None) -> None:
    if pitch is None:
        return
    pitch_elem = etree.SubElement(note_elem, "pitch")
    step = etree.SubElement(pitch_elem, "step")
    step.text = pitch.step
    if pitch.alter:
        alter = etree.SubElement(pitch_elem, "alter")
        alter.text = _fraction_to_decimal_string(pitch.alter)
    octave = etree.SubElement(pitch_elem, "octave")
    octave.text = str(pitch.octave)


def _append_note_notations(note_elem: etree.Element, note: Note) -> None:
    needs_notations = any(
        [
            note.tie_start,
            note.tie_stop,
            note.slur_starts,
            note.slur_stops,
            note.articulations,
            note.technicals,
            note.fingerings,
            note.fermata,
            note.breath_mark,
        ]
    )
    if not needs_notations:
        return

    notations = etree.SubElement(note_elem, "notations")
    if note.tie_stop:
        etree.SubElement(notations, "tied", type="stop")
    if note.tie_start:
        etree.SubElement(notations, "tied", type="start")
    for number in note.slur_stops:
        etree.SubElement(notations, "slur", type="stop", number=str(number))
    for number in note.slur_starts:
        etree.SubElement(notations, "slur", type="start", number=str(number))

    if note.technicals or note.fingerings:
        technical = etree.SubElement(notations, "technical")
        for technical_name in note.technicals:
            etree.SubElement(technical, technical_name.replace("upbow", "up-bow").replace("downbow", "down-bow"))
        for fingering in note.fingerings:
            fingering_elem = etree.SubElement(technical, "fingering")
            fingering_elem.text = fingering

    if note.articulations or note.breath_mark:
        articulations = etree.SubElement(notations, "articulations")
        for articulation in note.articulations:
            if articulation == "portato":
                other = etree.SubElement(articulations, "other-articulation")
                other.text = "portato"
            else:
                etree.SubElement(articulations, articulation)
        if note.breath_mark:
            etree.SubElement(articulations, "breath-mark")

    if note.fermata:
        fermata = etree.SubElement(notations, "fermata")
        fermata.text = "normal"

def _fraction_to_decimal_string(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{float(value):g}"