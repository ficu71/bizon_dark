from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport


class NarrationCodecError(Exception):
    pass


class NarrationSaveCodec(SaveCodec):
    """Read-first codec for binary `persist.narration.json`."""

    file_name = "persist.narration.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        raw = file_path.read_bytes()
        fields: Dict[str, ParsedField] = {}

        version = self._read_u32_with_optional_padding(
            raw,
            b"version\x00",
            max_value=1_000_000,
            prefer_smallest=True,
        )
        if version:
            value, start, end = version
            fields["narration.version"] = ParsedField(
                path="narration.version",
                value=value,
                location=BinaryRange(start=start, end=end),
                type_name="u32",
            )

        entry_type_count = raw.count(b"entry_type\x00")
        audio_event_type_count = raw.count(b"audio_event_type\x00")
        vo_path_count = raw.count(b"/vo/")

        markers = {
            "raid_entry_log": b"raid_entry_log\x00",
            "town_visit_entry_log": b"town_visit_entry_log\x00",
            "campaign_entry_log": b"campaign_entry_log\x00",
        }
        for key, marker in markers.items():
            pos = raw.find(marker)
            fields[f"narration.{key}.present"] = ParsedField(
                path=f"narration.{key}.present",
                value=1 if pos >= 0 else 0,
                location=BinaryRange(start=max(0, pos), end=max(0, pos)),
                type_name="bool_as_u8",
            )

        entry_pos = raw.find(b"entry_type\x00")
        audio_pos = raw.find(b"audio_event_type\x00")
        vo_pos = raw.find(b"/vo/")

        fields["narration.entry_type.count"] = ParsedField(
            path="narration.entry_type.count",
            value=entry_type_count,
            location=BinaryRange(start=max(0, entry_pos), end=max(0, entry_pos)),
            type_name="derived_u32",
        )
        fields["narration.audio_event_type.count"] = ParsedField(
            path="narration.audio_event_type.count",
            value=audio_event_type_count,
            location=BinaryRange(start=max(0, audio_pos), end=max(0, audio_pos)),
            type_name="derived_u32",
        )
        fields["narration.vo_path.count"] = ParsedField(
            path="narration.vo_path.count",
            value=vo_path_count,
            location=BinaryRange(start=max(0, vo_pos), end=max(0, vo_pos)),
            type_name="derived_u32",
        )

        if not fields:
            raise NarrationCodecError("No known fields parsed from persist.narration.json")

        return ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-narration-v1",
            fields=fields,
            unknown_segments=[],
            metadata={
                "source_path": str(file_path),
                "raw_bytes": raw,
            },
        )

    def write(self, parsed: ParsedSaveFile, output_path: Path) -> None:
        raw = parsed.metadata.get("raw_bytes") if isinstance(parsed.metadata, dict) else None
        if not isinstance(raw, (bytes, bytearray)):
            raise NarrationCodecError("Missing source raw bytes in parsed metadata")
        output_path.write_bytes(bytes(raw))

    def round_trip(self, file_path: Path, out_path: Path) -> RoundTripReport:
        parsed = self.parse(file_path)
        self.write(parsed, out_path)

        in_bytes = file_path.read_bytes()
        out_bytes = out_path.read_bytes()
        logical_equal = self.parse(file_path).fields == self.parse(out_path).fields
        binary_equal = in_bytes == out_bytes

        changed_ranges: List[BinaryRange] = []
        if not binary_equal:
            min_len = min(len(in_bytes), len(out_bytes))
            run_start: int | None = None
            for i in range(min_len):
                if in_bytes[i] != out_bytes[i] and run_start is None:
                    run_start = i
                elif in_bytes[i] == out_bytes[i] and run_start is not None:
                    changed_ranges.append(BinaryRange(start=run_start, end=i))
                    run_start = None
            if run_start is not None:
                changed_ranges.append(BinaryRange(start=run_start, end=min_len))
            if len(in_bytes) != len(out_bytes):
                changed_ranges.append(BinaryRange(start=min_len, end=max(len(in_bytes), len(out_bytes))))

        return RoundTripReport(
            file_name=file_path.name,
            logical_equal=logical_equal,
            binary_equal=binary_equal,
            changed_ranges=changed_ranges,
        )

    def _read_u32_with_optional_padding(
        self,
        raw: bytes,
        marker: bytes,
        *,
        max_value: int,
        require_next_marker: bool = True,
        prefer_smallest: bool = False,
    ) -> Tuple[int, int, int] | None:
        pos = raw.find(marker)
        if pos < 0:
            return None

        base = pos + len(marker)
        candidates: List[Tuple[int, int, int]] = []
        for off in range(0, 5):
            start = base + off
            end = start + 4
            if end > len(raw):
                break
            value = int.from_bytes(raw[start:end], "little", signed=False)
            if value > max_value:
                continue
            if require_next_marker and not _next_markerish(raw, end):
                continue
            candidates.append((value, start, end))

        if not candidates:
            return None
        if prefer_smallest:
            return min(candidates, key=lambda item: (item[0], item[1]))
        return candidates[0]


def _next_markerish(raw: bytes, idx: int) -> bool:
    cursor = idx
    skip = 0
    while cursor < len(raw) and raw[cursor] == 0 and skip < 6:
        cursor += 1
        skip += 1

    if cursor >= len(raw):
        return False

    byte = raw[cursor]
    if ord("a") <= byte <= ord("z"):
        return True
    if ord("A") <= byte <= ord("Z"):
        return True
    return byte in {ord("_"), ord("?"), ord("@"), ord("/")}


def extract_narration_summary(parsed: ParsedSaveFile) -> dict[str, object]:
    def _get(path: str, default=None):
        field = parsed.fields.get(path)
        return field.value if field is not None else default

    return {
        "version": _get("narration.version", 0),
        "entry_type_count": _get("narration.entry_type.count", 0),
        "audio_event_type_count": _get("narration.audio_event_type.count", 0),
        "vo_path_count": _get("narration.vo_path.count", 0),
        "raid_entry_log_present": _get("narration.raid_entry_log.present", 0),
        "town_visit_entry_log_present": _get("narration.town_visit_entry_log.present", 0),
        "campaign_entry_log_present": _get("narration.campaign_entry_log.present", 0),
    }
