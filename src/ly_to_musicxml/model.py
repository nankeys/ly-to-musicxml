from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction


@dataclass(slots=True)
class Pitch:
    step: str
    octave: int
    alter: Fraction = Fraction(0)


@dataclass(slots=True)
class MetronomeMark:
    beat_unit: str
    beat_unit_dots: int
    per_minute: str
    sound_tempo: float | None = None


@dataclass(slots=True)
class OctaveShift:
    shift_type: str
    size: int


@dataclass(slots=True)
class MeasureItem:
    pass


@dataclass(slots=True)
class AttributesItem(MeasureItem):
    divisions: int | None = None
    key_fifths: int | None = None
    key_mode: str | None = None
    beats: int | None = None
    beat_type: int | None = None
    clef_sign: str | None = None
    clef_line: int | None = None
    clef_octave_change: int | None = None


@dataclass(slots=True)
class DirectionItem(MeasureItem):
    words: str | None = None
    dynamics: list[str] = field(default_factory=list)
    wedge: str | None = None
    metronome: MetronomeMark | None = None
    octave_shift: OctaveShift | None = None
    placement: str | None = None


@dataclass(slots=True)
class Note:
    pitch: Pitch | None
    is_rest: bool
    duration: Fraction
    type_name: str | None
    dots: int
    voice: int = 1
    tie_start: bool = False
    tie_stop: bool = False
    slur_starts: list[int] = field(default_factory=list)
    slur_stops: list[int] = field(default_factory=list)
    articulations: list[str] = field(default_factory=list)
    technicals: list[str] = field(default_factory=list)
    fermata: bool = False
    breath_mark: bool = False
    tuplet_actual: int | None = None
    tuplet_normal: int | None = None


@dataclass(slots=True)
class NoteGroupItem(MeasureItem):
    notes: list[Note]
    duration: Fraction


@dataclass(slots=True)
class BarlineItem(MeasureItem):
    style: str


@dataclass(slots=True)
class Measure:
    number: int
    implicit: bool = False
    items: list[MeasureItem] = field(default_factory=list)
    right_barline: str | None = None


@dataclass(slots=True)
class Part:
    identifier: str
    name: str
    measures: list[Measure]


@dataclass(slots=True)
class Score:
    identifier: str
    header: dict[str, str]
    parts: list[Part]
    warnings: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any(
            isinstance(item, NoteGroupItem)
            for part in self.parts
            for measure in part.measures
            for item in measure.items
        )


@dataclass(slots=True)
class Book:
    index: int
    header: dict[str, str]
    scores: list[Score]


@dataclass(slots=True)
class ParsedDocument:
    books: list[Book]
    warnings: list[str] = field(default_factory=list)