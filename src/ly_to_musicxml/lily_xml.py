from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from math import gcd
from pathlib import Path
import re
import xml.etree.ElementTree as etree

from .model import (
    AttributesItem,
    BarlineItem,
    Book,
    DirectionItem,
    Measure,
    MeasureItem,
    MetronomeMark,
    Note,
    NoteGroupItem,
    OctaveShift,
    ParsedDocument,
    Part,
    Pitch,
    Score,
)


NOTE_TYPE_NAMES = {
    -3: "maxima",
    -2: "long",
    -1: "breve",
    0: "whole",
    1: "half",
    2: "quarter",
    3: "eighth",
    4: "16th",
    5: "32nd",
    6: "64th",
    7: "128th",
    8: "256th",
}
NOTE_STEPS = {0: "C", 1: "D", 2: "E", 3: "F", 4: "G", 5: "A", 6: "B"}
STANDARD_DYNAMICS = {
    "p",
    "pp",
    "ppp",
    "pppp",
    "ppppp",
    "pppppp",
    "f",
    "ff",
    "fff",
    "ffff",
    "fffff",
    "ffffff",
    "mp",
    "mf",
    "sf",
    "sfp",
    "sfpp",
    "fp",
    "rf",
    "rfz",
    "sfz",
    "sffz",
    "fz",
}
CLEF_MAP = {
    "treble": ("G", 2, None),
    "bass": ("F", 4, None),
    "alto": ("C", 3, None),
    "tenor": ("C", 4, None),
}
START_SPAN = Fraction(-1)
STOP_SPAN = Fraction(1)


@dataclass(slots=True)
class TraversalContext:
    tuplet_actual: int | None = None
    tuplet_normal: int | None = None


@dataclass(slots=True)
class PartState:
    identifier: str
    source_lookup: "SourceLookup"
    warnings: list[str]
    name: str | None = None
    pending_partial: Fraction | None = None
    items: list[MeasureItem] = field(default_factory=list)
    active_ties: set[str] = field(default_factory=set)
    active_slurs: list[int] = field(default_factory=list)
    next_slur_number: int = 1
    last_note_group: NoteGroupItem | None = None
    pending_clef_glyph: str | None = None
    pending_clef_position: int | None = None
    pending_clef_transposition: int | None = None

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def add_item(self, item: MeasureItem) -> None:
        self.items.append(item)
        if isinstance(item, NoteGroupItem):
            self.last_note_group = item

    def assign_slur_numbers(self, start_count: int, stop_count: int) -> tuple[list[int], list[int]]:
        stop_numbers: list[int] = []
        for _ in range(stop_count):
            if self.active_slurs:
                stop_numbers.append(self.active_slurs.pop())
            else:
                self.warn("Encountered slur stop without an active slur.")

        start_numbers: list[int] = []
        for _ in range(start_count):
            number = self.next_slur_number
            self.next_slur_number += 1
            self.active_slurs.append(number)
            start_numbers.append(number)
        return start_numbers, stop_numbers

    def apply_tie_state(self, note: Note) -> None:
        if note.pitch is None:
            return
        pitch_key = f"{note.pitch.step}:{note.pitch.alter}:{note.pitch.octave}"
        if pitch_key in self.active_ties:
            note.tie_stop = True
        if note.tie_start:
            self.active_ties.add(pitch_key)
        else:
            self.active_ties.discard(pitch_key)

    def build_part(self) -> Part:
        measures = _build_measures(self.items, self.pending_partial, self.warnings)
        return Part(
            identifier=self.identifier,
            name=self.name or self.identifier,
            measures=measures,
        )

    def take_pending_clef(self) -> tuple[str, int, int | None] | None:
        if not self.pending_clef_glyph:
            return None

        sign = _clef_sign_from_glyph(self.pending_clef_glyph)
        if sign is None:
            return None

        line = _clef_line_from_position(sign, self.pending_clef_position)
        octave_change = _clef_octave_change_from_transposition(self.pending_clef_transposition)

        self.pending_clef_glyph = None
        self.pending_clef_position = None
        self.pending_clef_transposition = None

        return sign, line, octave_change


class SourceLookup:
    def __init__(self) -> None:
        self._line_cache: dict[Path, list[str]] = {}

    def line_for_music(self, music: etree.Element) -> str | None:
        origin = music.find("origin")
        if origin is None:
            return None

        filename = origin.attrib.get("filename")
        line_number = origin.attrib.get("line")
        if not filename or line_number is None:
            return None

        path = Path(filename)
        try:
            lines = self._line_cache[path]
        except KeyError:
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                return None
            self._line_cache[path] = lines

        index = int(line_number) - 1
        if 0 <= index < len(lines):
            return lines[index]
        return None


class LilyXmlParser:
    def __init__(self, input_path: str | Path) -> None:
        self.input_path = Path(input_path).resolve()
        self.source_lookup = SourceLookup()
        self.warnings: list[str] = []

    def parse(self, lily_xml_text: str) -> ParsedDocument:
        root = etree.fromstring(lily_xml_text)
        books: list[Book] = []

        for book_index, book_elem in enumerate(root.findall("book"), start=1):
            books.append(self._parse_book(book_elem, book_index))

        if not books:
            fallback_scores = root.findall("score")
            if fallback_scores:
                books.append(
                    Book(
                        index=1,
                        header={},
                        scores=[
                            self._parse_score(score_elem, {}, 1, score_index)
                            for score_index, score_elem in enumerate(fallback_scores, start=1)
                        ],
                    )
                )

        return ParsedDocument(books=books, warnings=self.warnings)

    def _parse_book(self, book_elem: etree.Element, book_index: int) -> Book:
        header = _parse_header(book_elem.find("header"))
        scores = [
            self._parse_score(score_elem, header, book_index, score_index)
            for score_index, score_elem in enumerate(book_elem.findall("score"), start=1)
        ]
        return Book(index=book_index, header=header, scores=scores)

    def _parse_score(
        self,
        score_elem: etree.Element,
        book_header: dict[str, str],
        book_index: int,
        score_index: int,
    ) -> Score:
        header = dict(book_header)
        header.update(_parse_header(score_elem.find("header")))

        music_elem = score_elem.find("music")
        if music_elem is None:
            self.warnings.append(f"Book {book_index} score {score_index} has no music body.")
            return Score(identifier=f"book{book_index:02d}-score{score_index:02d}", header=header, parts=[])

        staff_nodes = self._collect_staff_nodes(music_elem)
        if not staff_nodes:
            staff_nodes = [music_elem]

        parts: list[Part] = []
        score_warnings_start = len(self.warnings)
        for part_index, staff_node in enumerate(staff_nodes, start=1):
            state = PartState(
                identifier=f"P{part_index}",
                source_lookup=self.source_lookup,
                warnings=self.warnings,
            )
            self._emit_music(staff_node, state, TraversalContext())
            part = state.build_part()
            if part.measures:
                parts.append(part)

        score_warnings = self.warnings[score_warnings_start:]
        return Score(
            identifier=f"book{book_index:02d}-score{score_index:02d}",
            header=header,
            parts=parts,
            warnings=score_warnings,
        )

    def _collect_staff_nodes(self, music: etree.Element) -> list[etree.Element]:
        name = _music_name(music)
        if name == "ContextSpeccedMusic":
            context_type = _symbol_property(music, "context-type")
            if context_type == "Staff":
                return [music]
            inner = _element_music(music)
            return self._collect_staff_nodes(inner) if inner is not None else []

        if name in {"SequentialMusic", "SimultaneousMusic"}:
            staff_nodes: list[etree.Element] = []
            for child in _elements_music(music):
                staff_nodes.extend(self._collect_staff_nodes(child))
            return staff_nodes

        if name in {"RelativeOctaveMusic", "TimeScaledMusic", "UnfoldedRepeatedMusic"}:
            inner = _element_music(music)
            return self._collect_staff_nodes(inner) if inner is not None else []

        return []

    def _emit_music(self, music: etree.Element | None, state: PartState, ctx: TraversalContext) -> None:
        if music is None:
            return

        name = _music_name(music)

        if name == "ContextSpeccedMusic":
            context_type = _symbol_property(music, "context-type")
            inner = _element_music(music)

            if context_type == "Staff":
                if inner is not None and _music_name(inner) == "PropertySet":
                    self._handle_property_set(inner, state)
                    return
                self._emit_music(inner, state, ctx)
                return

            if context_type in {"Voice", "Score", "Timing", "StaffGroup"}:
                self._emit_music(inner, state, ctx)
                return

            state.warn(f"Unsupported context type '{context_type}' in {state.identifier}.")
            self._emit_music(inner, state, ctx)
            return

        if name == "SequentialMusic":
            for child in _elements_music(music):
                self._emit_music(child, state, ctx)
            return

        if name == "SimultaneousMusic":
            advancing_seen = False
            for child in _elements_music(music):
                child_advances = _subtree_advances_time(child)
                if child_advances and advancing_seen:
                    state.warn(f"Skipping unsupported simultaneous voice branch in {state.identifier}.")
                    continue
                if child_advances:
                    advancing_seen = True
                self._emit_music(child, state, ctx)
            return

        if name == "RelativeOctaveMusic":
            self._emit_music(_element_music(music), state, ctx)
            return

        if name == "TimeScaledMusic":
            numerator = _number_property(music, "numerator")
            denominator = _number_property(music, "denominator")
            if ctx.tuplet_actual is not None:
                state.warn("Nested tuplets are not fully supported; using the innermost tuplet ratio.")
            self._emit_music(
                _element_music(music),
                state,
                TraversalContext(
                    tuplet_actual=int(denominator) if denominator is not None else None,
                    tuplet_normal=int(numerator) if numerator is not None else None,
                ),
            )
            return

        if name == "UnfoldedRepeatedMusic":
            repeat_count = _number_property(music, "repeat-count") or 0
            inner = _element_music(music)
            for _ in range(int(repeat_count)):
                self._emit_music(inner, state, ctx)
            return

        if name == "PropertySet":
            self._handle_property_set(music, state)
            return

        if name == "TempoChangeEvent":
            state.add_item(self._parse_tempo_direction(music))
            return

        if name == "ReferenceTimeSignatureMusic":
            time_pair = _pair_property(music, "time-signature")
            if time_pair is None:
                state.warn("Encountered a time signature change without a time-signature value.")
                return
            beats, beat_type = time_pair
            state.add_item(AttributesItem(beats=beats, beat_type=beat_type))
            return

        if name == "KeyChangeEvent":
            fifths = _key_fifths_from_pitch_alist(_list_property(music, "pitch-alist"))
            mode = _parse_key_mode_from_origin(self.source_lookup.line_for_music(music))
            state.add_item(AttributesItem(key_fifths=fifths, key_mode=mode))
            return

        if name == "ApplyContext":
            clef = state.take_pending_clef() or _parse_clef_from_origin(self.source_lookup.line_for_music(music))
            if clef is not None:
                sign, line, octave_change = clef
                state.add_item(
                    AttributesItem(
                        clef_sign=sign,
                        clef_line=line,
                        clef_octave_change=octave_change,
                    )
                )
            return

        if name == "PartialSet":
            duration_elem = music.find("duration")
            state.pending_partial = (
                _duration_fraction_from_element(duration_elem) if duration_elem is not None else _duration_length(music)
            )
            return

        if name == "BarEvent":
            bar_type = _string_property(music, "bar-type")
            style = _barline_style(bar_type)
            if style is not None:
                state.add_item(BarlineItem(style=style))
            else:
                state.warn(f"Unsupported barline style '{bar_type}'.")
            return

        if name == "BarCheckEvent":
            return

        if name == "BreathingEvent":
            self._attach_breath_mark(state)
            return

        if name == "OttavaEvent":
            direction = _parse_ottava_direction(music, self.source_lookup)
            if direction is not None:
                state.add_item(direction)
            return

        if name == "AbsoluteDynamicEvent":
            state.add_item(self._dynamic_direction_from_text(_string_property(music, "text")))
            return

        if name == "TextScriptEvent":
            direction = self._text_direction_from_markup(music)
            if direction is not None:
                state.add_item(direction)
            return

        if name in {"CrescendoEvent", "DecrescendoEvent"}:
            state.add_item(_wedge_direction(name, _number_property(music, "span-direction")))
            return

        if name == "EventChord":
            for item in self._parse_event_chord(music, state, ctx):
                state.add_item(item)
            return

        if name == "NoteEvent":
            for item in self._parse_single_note(music, state, ctx):
                state.add_item(item)
            return

        if name == "RestEvent":
            state.add_item(self._parse_rest(music, ctx))
            return

        state.warn(f"Unsupported music node '{name}' in {state.identifier}.")

    def _handle_property_set(self, music: etree.Element, state: PartState) -> None:
        symbol = _symbol_property(music, "symbol")
        if symbol == "instrumentName":
            value = _property_text(music, "value")
            if value:
                state.name = value
        elif symbol == "clefGlyph":
            state.pending_clef_glyph = _property_text(music, "value")
        elif symbol == "clefPosition":
            value = _property_text(music, "value")
            state.pending_clef_position = int(Fraction(value)) if value is not None else None
        elif symbol == "clefTransposition":
            value = _property_text(music, "value")
            state.pending_clef_transposition = int(Fraction(value)) if value is not None else None
        elif symbol == "tempoWholesPerMinute":
            return
        else:
            return

    def _parse_tempo_direction(self, music: etree.Element) -> DirectionItem:
        text = _string_property(music, "text")
        tempo_unit = music.find("property[@name='tempo-unit']/duration")
        metronome_count = _number_property(music, "metronome-count")

        metronome = None
        if tempo_unit is not None and metronome_count is not None:
            beat_unit = _duration_type_name(tempo_unit)
            dots = int(tempo_unit.attrib.get("dots", "0"))
            unit_length = _duration_fraction_from_element(tempo_unit)
            sound_tempo = float(Fraction(metronome_count) * unit_length * 4)
            metronome = MetronomeMark(
                beat_unit=beat_unit,
                beat_unit_dots=dots,
                per_minute=str(metronome_count),
                sound_tempo=sound_tempo,
            )

        return DirectionItem(words=text, metronome=metronome)

    def _dynamic_direction_from_text(self, text: str | None) -> DirectionItem:
        if not text:
            return DirectionItem()
        if text in STANDARD_DYNAMICS:
            return DirectionItem(dynamics=[text])
        return DirectionItem(words=text)

    def _text_direction_from_markup(self, music: etree.Element) -> DirectionItem | None:
        text_node = music.find("property[@name='text']/*")
        text = _flatten_text(text_node)
        if not text:
            return None
        placement = _placement_from_direction(_number_property(music, "direction"))
        return DirectionItem(words=text, placement=placement)

    def _parse_event_chord(
        self,
        music: etree.Element,
        state: PartState,
        ctx: TraversalContext,
    ) -> list[MeasureItem]:
        directions: list[MeasureItem] = []
        notes: list[Note] = []
        chord_level_events: list[etree.Element] = []

        for child in _elements_music(music):
            child_name = _music_name(child)
            if child_name == "NoteEvent":
                note, extra_directions = self._build_note(child, state, ctx)
                notes.append(note)
                directions.extend(extra_directions)
            elif child_name == "RestEvent":
                directions.extend([])
                rest_group = self._parse_rest(child, ctx)
                return directions + [rest_group]
            else:
                chord_level_events.append(child)

        if not notes:
            state.warn("Encountered an EventChord without note or rest content.")
            return directions

        extra_note, chord_directions = self._apply_attachment_events(chord_level_events, state, None, ctx)
        directions.extend(chord_directions)
        if extra_note is not None:
            notes[0] = _merge_note_attachments(notes[0], extra_note)

        duration = _duration_length(music)
        note_group = NoteGroupItem(notes=notes, duration=duration)
        return directions + [note_group]

    def _parse_single_note(
        self,
        music: etree.Element,
        state: PartState,
        ctx: TraversalContext,
    ) -> list[MeasureItem]:
        note, directions = self._build_note(music, state, ctx)
        return directions + [NoteGroupItem(notes=[note], duration=note.duration)]

    def _build_note(
        self,
        music: etree.Element,
        state: PartState,
        ctx: TraversalContext,
    ) -> tuple[Note, list[MeasureItem]]:
        pitch_elem = music.find("pitch")
        duration_elem = music.find("duration")

        if pitch_elem is None or duration_elem is None:
            raise ValueError("NoteEvent is missing required pitch or duration data.")

        note = Note(
            pitch=Pitch(
                step=NOTE_STEPS[int(pitch_elem.attrib["notename"])],
                octave=int(pitch_elem.attrib["octave"]) + 4,
                alter=_musicxml_alter_from_lily(pitch_elem.attrib.get("alteration", "0")),
            ),
            is_rest=False,
            duration=_duration_length(music),
            type_name=_duration_type_name(duration_elem),
            dots=int(duration_elem.attrib.get("dots", "0")),
            tuplet_actual=ctx.tuplet_actual,
            tuplet_normal=ctx.tuplet_normal,
        )

        attachment_note, directions = self._apply_attachment_events(
            _articulation_children(music),
            state,
            note,
            ctx,
        )
        if attachment_note is not None:
            note = attachment_note
        state.apply_tie_state(note)
        return note, directions

    def _parse_rest(self, music: etree.Element, ctx: TraversalContext) -> NoteGroupItem:
        duration_elem = music.find("duration")
        if duration_elem is None:
            raise ValueError("RestEvent is missing duration data.")

        note = Note(
            pitch=None,
            is_rest=True,
            duration=_duration_length(music),
            type_name=_duration_type_name(duration_elem),
            dots=int(duration_elem.attrib.get("dots", "0")),
            tuplet_actual=ctx.tuplet_actual,
            tuplet_normal=ctx.tuplet_normal,
        )
        return NoteGroupItem(notes=[note], duration=note.duration)

    def _apply_attachment_events(
        self,
        events: list[etree.Element],
        state: PartState,
        note: Note | None,
        ctx: TraversalContext,
    ) -> tuple[Note | None, list[MeasureItem]]:
        directions: list[MeasureItem] = []
        start_slurs = 0
        stop_slurs = 0

        for event in events:
            name = _music_name(event)
            if name == "TieEvent":
                if note is not None:
                    note.tie_start = True
            elif name == "SlurEvent":
                span_direction = _number_property(event, "span-direction")
                if span_direction == START_SPAN:
                    start_slurs += 1
                elif span_direction == STOP_SPAN:
                    stop_slurs += 1
            elif name == "ArticulationEvent":
                if note is not None:
                    _apply_articulation(note, _symbol_property(event, "articulation-type"))
            elif name == "AbsoluteDynamicEvent":
                directions.append(self._dynamic_direction_from_text(_string_property(event, "text")))
            elif name == "TextScriptEvent":
                direction = self._text_direction_from_markup(event)
                if direction is not None:
                    directions.append(direction)
            elif name in {"CrescendoEvent", "DecrescendoEvent"}:
                directions.append(_wedge_direction(name, _number_property(event, "span-direction")))
            elif name == "BreathingEvent":
                if note is not None:
                    note.breath_mark = True
                else:
                    self._attach_breath_mark(state)
            elif name == "OttavaEvent":
                direction = _parse_ottava_direction(event, self.source_lookup)
                if direction is not None:
                    directions.append(direction)
            else:
                state.warn(f"Unsupported attachment event '{name}' in {state.identifier}.")

        if note is not None and (start_slurs or stop_slurs):
            slur_starts, slur_stops = state.assign_slur_numbers(start_slurs, stop_slurs)
            note.slur_starts.extend(slur_starts)
            note.slur_stops.extend(slur_stops)

        return note, directions

    def _attach_breath_mark(self, state: PartState) -> None:
        if state.last_note_group and state.last_note_group.notes:
            state.last_note_group.notes[0].breath_mark = True
        else:
            state.warn("Encountered a breath mark that could not be attached to a note.")


def parse_lily_xml(lily_xml_text: str, input_path: str | Path) -> ParsedDocument:
    return LilyXmlParser(input_path).parse(lily_xml_text)


def _build_measures(
    items: list[MeasureItem],
    pending_partial: Fraction | None,
    warnings: list[str],
) -> list[Measure]:
    divisions = _compute_divisions(items)
    measures: list[Measure] = [Measure(number=1, implicit=pending_partial is not None)]
    current_measure = measures[0]
    current_measure.items.append(AttributesItem(divisions=divisions))
    current_time = (4, 4)
    current_capacity = pending_partial or Fraction(current_time[0], current_time[1])
    elapsed = Fraction(0)
    measure_number = 1

    for item in items:
        if elapsed == current_capacity and elapsed > 0:
            measure_number += 1
            current_measure = Measure(number=measure_number)
            measures.append(current_measure)
            elapsed = Fraction(0)
            current_capacity = Fraction(current_time[0], current_time[1])

        if isinstance(item, AttributesItem):
            if item.beats is not None and item.beat_type is not None:
                current_time = (item.beats, item.beat_type)
                if elapsed == 0:
                    current_capacity = (
                        pending_partial if measure_number == 1 and pending_partial is not None else Fraction(*current_time)
                    )
            current_measure.items.append(item)
            continue

        if isinstance(item, BarlineItem):
            current_measure.right_barline = item.style
            continue

        current_measure.items.append(item)
        if isinstance(item, NoteGroupItem):
            elapsed += item.duration
            if elapsed > current_capacity:
                warnings.append(
                    f"Measure {measure_number} overfilled by {elapsed - current_capacity}; preserving note order in output."
                )

    return [measure for measure in measures if measure.items or measure.right_barline]


def _compute_divisions(items: list[MeasureItem]) -> int:
    divisions = 1
    for item in items:
        if not isinstance(item, NoteGroupItem):
            continue
        quarter_duration = item.duration * 4
        divisions = _lcm(divisions, quarter_duration.denominator)
    return max(divisions, 1)


def _lcm(left: int, right: int) -> int:
    return abs(left * right) // gcd(left, right)


def _music_name(music: etree.Element) -> str:
    return music.attrib.get("name", "")


def _elements_music(music: etree.Element) -> list[etree.Element]:
    elements = music.find("elements")
    return list(elements.findall("music")) if elements is not None else []


def _element_music(music: etree.Element) -> etree.Element | None:
    element = music.find("element")
    return element.find("music") if element is not None else None


def _articulation_children(music: etree.Element) -> list[etree.Element]:
    articulations = music.find("articulations")
    return list(articulations.findall("music")) if articulations is not None else []


def _find_property(music: etree.Element, name: str) -> etree.Element | None:
    for prop in music.findall("property"):
        if prop.attrib.get("name") == name:
            return prop
    return None


def _property_child(music: etree.Element, name: str) -> etree.Element | None:
    prop = _find_property(music, name)
    return next(iter(prop), None) if prop is not None and len(prop) else None


def _number_property(music: etree.Element, name: str) -> Fraction | None:
    child = _property_child(music, name)
    if child is None or child.tag != "number" or child.text is None:
        return None
    return _fraction_from_text(child.text)


def _string_property(music: etree.Element, name: str) -> str | None:
    child = _property_child(music, name)
    if child is None:
        return None
    return _flatten_text(child)


def _property_text(music: etree.Element, name: str) -> str | None:
    return _string_property(music, name)


def _symbol_property(music: etree.Element, name: str) -> str | None:
    child = _property_child(music, name)
    if child is None or child.tag != "symbol":
        return None
    return child.text


def _pair_property(music: etree.Element, name: str) -> tuple[int, int] | None:
    child = _property_child(music, name)
    if child is None or child.tag != "pair":
        return None
    values = [int(_flatten_text(number)) for number in child.findall("number")]
    if len(values) != 2:
        return None
    return values[0], values[1]


def _list_property(music: etree.Element, name: str) -> etree.Element | None:
    child = _property_child(music, name)
    return child if child is not None and child.tag == "list" else None


def _duration_length(music: etree.Element) -> Fraction:
    length = _property_child(music, "length")
    if length is None or length.tag != "moment":
        return Fraction(0)
    return Fraction(int(length.attrib["main-numer"]), int(length.attrib["main-denom"]))


def _subtree_advances_time(music: etree.Element) -> bool:
    if _duration_length(music) > 0:
        return True
    return any(_subtree_advances_time(child) for child in _elements_music(music)) or (
        _element_music(music) is not None and _subtree_advances_time(_element_music(music))
    )


def _parse_header(header_elem: etree.Element | None) -> dict[str, str]:
    if header_elem is None:
        return {}
    header: dict[str, str] = {}
    for variable in header_elem.findall("variable"):
        name = variable.attrib.get("name")
        value_elem = next(iter(variable), None)
        if not name or value_elem is None:
            continue
        text = _flatten_text(value_elem)
        if text:
            header[name] = text
    return header


def _flatten_text(elem: etree.Element | None) -> str | None:
    if elem is None:
        return None
    if elem.tag in {"string", "number", "symbol", "boolean", "char"}:
        return (elem.text or "").strip() or None
    pieces: list[str] = []
    if elem.text and elem.text.strip():
        pieces.append(elem.text.strip())
    for child in elem:
        child_text = _flatten_text(child)
        if child_text:
            pieces.append(child_text)
        if child.tail and child.tail.strip():
            pieces.append(child.tail.strip())
    text = " ".join(piece for piece in pieces if piece)
    return text or None


def _duration_type_name(duration_elem: etree.Element) -> str:
    log_value = int(duration_elem.attrib.get("log", "2"))
    return NOTE_TYPE_NAMES.get(log_value, "quarter")


def _duration_fraction_from_element(duration_elem: etree.Element) -> Fraction:
    log_value = int(duration_elem.attrib.get("log", "0"))
    dots = int(duration_elem.attrib.get("dots", "0"))
    numer = _fraction_from_text(duration_elem.attrib.get("numer", "1"))
    denom = _fraction_from_text(duration_elem.attrib.get("denom", "1"))

    base = Fraction(2 ** max(log_value, 0), 1)
    if log_value < 0:
        base = Fraction(1, 2 ** abs(log_value))
    whole_length = Fraction(1, base)
    dot_multiplier = Fraction(1, 1)
    for index in range(dots):
        dot_multiplier += Fraction(1, 2 ** (index + 1))
    return whole_length * dot_multiplier * numer / denom


def _fraction_from_text(text: str) -> Fraction:
    return Fraction(text)


def _musicxml_alter_from_lily(text: str) -> Fraction:
    return _fraction_from_text(text) * 2


def _apply_articulation(note: Note, articulation_type: str | None) -> None:
    if articulation_type is None:
        return
    if articulation_type in {"accent", "staccato", "tenuto"}:
        note.articulations.append(articulation_type)
    elif articulation_type in {"upbow", "downbow"}:
        note.technicals.append(articulation_type)
    elif articulation_type == "portato":
        note.articulations.append("portato")
    elif articulation_type == "fermata":
        note.fermata = True


def _merge_note_attachments(note: Note, extra: Note) -> Note:
    note.tie_start = note.tie_start or extra.tie_start
    note.tie_stop = note.tie_stop or extra.tie_stop
    note.slur_starts.extend(extra.slur_starts)
    note.slur_stops.extend(extra.slur_stops)
    note.articulations.extend(extra.articulations)
    note.technicals.extend(extra.technicals)
    note.fermata = note.fermata or extra.fermata
    note.breath_mark = note.breath_mark or extra.breath_mark
    return note


def _placement_from_direction(direction: Fraction | None) -> str | None:
    if direction is None:
        return None
    return "below" if direction < 0 else "above"


def _wedge_direction(event_name: str, span_direction: Fraction | None) -> DirectionItem:
    if span_direction == START_SPAN:
        wedge = "crescendo" if event_name == "CrescendoEvent" else "diminuendo"
        return DirectionItem(wedge=wedge)
    return DirectionItem(wedge="stop")


def _parse_ottava_direction(music: etree.Element, source_lookup: SourceLookup) -> DirectionItem | None:
    line = source_lookup.line_for_music(music) or ""
    match = re.search(r"\\ottava\s+#(-?\d+)", line)
    if match:
        ottava_number = int(match.group(1))
    else:
        property_number = _number_property(music, "ottava-number")
        ottava_number = int(property_number) if property_number is not None else 0

    if ottava_number == 0:
        return DirectionItem(octave_shift=OctaveShift(shift_type="stop", size=8))
    if ottava_number > 0:
        return DirectionItem(octave_shift=OctaveShift(shift_type="up", size=8 * ottava_number))
    return DirectionItem(octave_shift=OctaveShift(shift_type="down", size=8 * abs(ottava_number)))


def _parse_clef_from_origin(line: str | None) -> tuple[str, int, int | None] | None:
    if not line:
        return None
    match = re.search(r"\\clef\s+([A-Za-z]+)", line)
    if not match:
        return None
    return CLEF_MAP.get(match.group(1).lower())


def _clef_sign_from_glyph(glyph: str | None) -> str | None:
    mapping = {
        "clefs.G": "G",
        "clefs.F": "F",
        "clefs.C": "C",
    }
    return mapping.get(glyph)


def _clef_line_from_position(sign: str, position: int | None) -> int:
    default_lines = {"G": 2, "F": 4, "C": 3}
    if position is None:
        return default_lines[sign]
    return 3 + (position // 2)


def _clef_octave_change_from_transposition(transposition: int | None) -> int | None:
    if transposition in (None, 0):
        return None
    return -(transposition // 7)


def _parse_key_mode_from_origin(line: str | None) -> str | None:
    if not line:
        return None
    match = re.search(r"\\key\s+[^\s]+\s+\\([A-Za-z]+)", line)
    if not match:
        return None
    return match.group(1).lower()


def _key_fifths_from_pitch_alist(pitch_alist: etree.Element | None) -> int | None:
    if pitch_alist is None:
        return None
    accidentals: list[Fraction] = []
    for pair in pitch_alist.findall("pair"):
        numbers = pair.findall("number")
        if len(numbers) != 2 or numbers[1].text is None:
            continue
        accidentals.append(_fraction_from_text(numbers[1].text))
    sharps = sum(1 for accidental in accidentals if accidental > 0)
    flats = sum(1 for accidental in accidentals if accidental < 0)
    if sharps and flats:
        return None
    if sharps:
        return sharps
    if flats:
        return -flats
    return 0


def _barline_style(bar_type: str | None) -> str | None:
    mapping = {
        "|.": "light-heavy",
        "||": "light-light",
        ".|": "heavy-light",
        "|": "regular",
    }
    return mapping.get(bar_type)