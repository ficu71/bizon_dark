from __future__ import annotations

import struct
from pathlib import Path
from typing import Dict, List, Tuple

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport


class RaidCodecError(Exception):
    pass


class RaidSaveCodec(SaveCodec):
    """Codec for binary `persist.raid.json` with safe writes for selected fields."""

    file_name = "persist.raid.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        raw = file_path.read_bytes()
        fields: Dict[str, ParsedField] = {}

        version = self._read_u32_with_optional_padding(raw, b"version\x00", max_value=1_000_000)
        if version:
            value, start, end = version
            fields["raid.version"] = ParsedField(
                path="raid.version",
                value=value,
                location=BinaryRange(start=start, end=end),
                type_name="u32",
            )

        torchlight = self._read_f32_with_optional_padding(
            raw,
            b"torchlight\x00",
            min_value=0.0,
            max_value=1_000_000.0,
        )
        if torchlight:
            value, start, end = torchlight
            fields["raid.torchlight"] = ParsedField(
                path="raid.torchlight",
                value=value,
                location=BinaryRange(start=start, end=end),
                type_name="f32",
            )

        bool_markers = [
            (b"is_plot_quest\x00", "raid.is_plot_quest"),
            (b"counted_in_generation\x00", "raid.counted_in_generation"),
            (b"use_default_progression_goals\x00", "raid.use_default_progression_goals"),
            (b"is_from_town_event\x00", "raid.is_from_town_event"),
            (b"teleported\x00", "raid.teleported"),
            (b"inbattle\x00", "raid.inbattle"),
            (b"has_mash_data\x00", "raid.has_mash_data"),
            (b"implied\x00", "raid.implied"),
        ]
        for marker, field_path in bool_markers:
            parsed = self._read_bool_with_optional_padding(raw, marker)
            if parsed:
                value, start, end = parsed
                fields[field_path] = ParsedField(
                    path=field_path,
                    value=value,
                    location=BinaryRange(start=start, end=end),
                    type_name="bool_u8",
                )

        if "raid.inbattle" not in fields:
            raise RaidCodecError("Missing critical field in raid file: raid.inbattle")

        return ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-raid-v1",
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
            raise RaidCodecError("Missing source raw bytes in parsed metadata")

        blob = bytearray(raw)
        for field in parsed.fields.values():
            start = field.location.start
            end = field.location.end
            if start < 0 or end > len(blob) or start >= end:
                raise RaidCodecError(f"Invalid field location for {field.path}: {start}:{end}")

            if field.type_name == "u32":
                if not isinstance(field.value, int):
                    raise RaidCodecError(f"Field '{field.path}' must be int")
                if field.value < 0 or field.value > 0xFFFFFFFF:
                    raise RaidCodecError(f"Field '{field.path}' out of u32 range: {field.value}")
                if end - start != 4:
                    raise RaidCodecError(f"Field '{field.path}' has invalid u32 size")
                blob[start:end] = int(field.value).to_bytes(4, "little", signed=False)

            elif field.type_name == "f32":
                if not isinstance(field.value, (int, float)):
                    raise RaidCodecError(f"Field '{field.path}' must be float-compatible")
                if end - start != 4:
                    raise RaidCodecError(f"Field '{field.path}' has invalid f32 size")
                blob[start:end] = struct.pack("<f", float(field.value))

            elif field.type_name == "bool_u8":
                if not isinstance(field.value, int) or field.value not in (0, 1):
                    raise RaidCodecError(f"Field '{field.path}' must be 0/1")
                if end - start != 1:
                    raise RaidCodecError(f"Field '{field.path}' has invalid bool size")
                blob[start] = int(field.value)

        output_path.write_bytes(bytes(blob))

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
    ) -> Tuple[int, int, int] | None:
        pos = raw.find(marker)
        if pos < 0:
            return None

        base = pos + len(marker)
        for off in range(0, 5):
            start = base + off
            end = start + 4
            if end > len(raw):
                break
            value = int.from_bytes(raw[start:end], "little", signed=False)
            if value > max_value:
                continue
            if _next_markerish(raw, end):
                return value, start, end

        return None

    def _read_f32_with_optional_padding(
        self,
        raw: bytes,
        marker: bytes,
        *,
        min_value: float,
        max_value: float,
    ) -> Tuple[float, int, int] | None:
        pos = raw.find(marker)
        if pos < 0:
            return None

        base = pos + len(marker)
        for off in range(0, 5):
            start = base + off
            end = start + 4
            if end > len(raw):
                break
            value = struct.unpack("<f", raw[start:end])[0]
            if not (min_value <= value <= max_value):
                continue
            if _next_markerish(raw, end):
                return float(value), start, end

        return None

    def _read_bool_with_optional_padding(self, raw: bytes, marker: bytes) -> Tuple[int, int, int] | None:
        pos = raw.find(marker)
        if pos < 0:
            return None

        base = pos + len(marker)
        for off in range(0, 2):
            idx = base + off
            if idx >= len(raw):
                break
            value = raw[idx]
            if value not in (0, 1):
                continue
            if _next_markerish(raw, idx + 1):
                return int(value), idx, idx + 1

        return None


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


def extract_raid_summary(parsed: ParsedSaveFile) -> dict[str, object]:
    def _get(path: str, default=None):
        field = parsed.fields.get(path)
        return field.value if field is not None else default

    return {
        "version": _get("raid.version", 0),
        "torchlight": _get("raid.torchlight", 0.0),
        "inbattle": _get("raid.inbattle", 0),
        "teleported": _get("raid.teleported", 0),
        "has_mash_data": _get("raid.has_mash_data", 0),
        "implied": _get("raid.implied", 0),
        "is_plot_quest": _get("raid.is_plot_quest", 0),
        "counted_in_generation": _get("raid.counted_in_generation", 0),
        "use_default_progression_goals": _get("raid.use_default_progression_goals", 0),
        "is_from_town_event": _get("raid.is_from_town_event", 0),
    }
