from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class BinaryRange:
    start: int
    end: int


@dataclass(slots=True)
class UnknownSegment:
    """Raw bytes that must survive round-trip unchanged."""

    name: str
    location: BinaryRange
    raw: bytes


@dataclass(slots=True)
class ParsedField:
    path: str
    value: Any
    location: BinaryRange
    type_name: str


@dataclass(slots=True)
class ParsedSaveFile:
    file_name: str
    format_version: str
    fields: Dict[str, ParsedField] = field(default_factory=dict)
    unknown_segments: List[UnknownSegment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RoundTripReport:
    file_name: str
    logical_equal: bool
    binary_equal: bool
    changed_ranges: List[BinaryRange] = field(default_factory=list)
