from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport, UnknownSegment


class RosterCodecError(Exception):
    pass


HERO_BLOCK_MARKER = b"hero_file_data\x00raw_data\x00"


@dataclass(slots=True)
class HeroSpan:
    hero_index: int
    start: int
    end: int


class RosterSaveCodec(SaveCodec):
    """Read-first codec for `persist.roster.json` with offset mapping for hero fields."""

    file_name = "persist.roster.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        data = file_path.read_bytes()
        spans = self._locate_hero_spans(data)
        if not spans:
            raise RosterCodecError("No hero blocks found in persist.roster.json")

        fields: Dict[str, ParsedField] = {}

        for span in spans:
            prefix = f"roster.heroes.{span.hero_index}"

            fields[f"{prefix}.offset.start"] = ParsedField(
                path=f"{prefix}.offset.start",
                value=span.start,
                location=BinaryRange(start=span.start, end=span.start),
                type_name="offset",
            )
            fields[f"{prefix}.offset.end"] = ParsedField(
                path=f"{prefix}.offset.end",
                value=span.end,
                location=BinaryRange(start=span.end, end=span.end),
                type_name="offset",
            )

            name = self._read_len_prefixed_string(data, span.start, span.end, b"actor\x00name\x00")
            if name:
                value, value_start, value_end = name
                fields[f"{prefix}.name"] = ParsedField(
                    path=f"{prefix}.name",
                    value=value,
                    location=BinaryRange(start=value_start, end=value_end),
                    type_name="string",
                )

            hero_class = self._read_len_prefixed_string(data, span.start, span.end, b"heroClass\x00")
            if hero_class:
                value, value_start, value_end = hero_class
                fields[f"{prefix}.class"] = ParsedField(
                    path=f"{prefix}.class",
                    value=value,
                    location=BinaryRange(start=value_start, end=value_end),
                    type_name="string",
                )

            for key, field_suffix in [
                ("resolveXp", "resolve_xp"),
                ("enemies_killed", "enemies_killed"),
                ("weapon_rank", "weapon_rank"),
                ("armour_rank", "armour_rank"),
            ]:
                parsed = self._read_u32_after_key(data, span.start, span.end, key)
                if parsed is None:
                    continue
                value, value_offset = parsed
                fields[f"{prefix}.{field_suffix}"] = ParsedField(
                    path=f"{prefix}.{field_suffix}",
                    value=value,
                    location=BinaryRange(start=value_offset, end=value_offset + 4),
                    type_name="u32",
                )

        first_start = spans[0].start
        last_end = spans[-1].end
        unknown = [
            UnknownSegment(
                name="prefix",
                location=BinaryRange(start=0, end=first_start),
                raw=data[:first_start],
            ),
            UnknownSegment(
                name="suffix",
                location=BinaryRange(start=last_end, end=len(data)),
                raw=data[last_end:],
            ),
        ]

        return ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-roster-v1",
            fields=fields,
            unknown_segments=unknown,
            metadata={
                "source_path": str(file_path),
                "raw_bytes": data,
                "hero_spans": [(s.hero_index, s.start, s.end) for s in spans],
            },
        )

    def write(self, parsed: ParsedSaveFile, output_path: Path) -> None:
        raw = parsed.metadata.get("raw_bytes") if isinstance(parsed.metadata, dict) else None
        if not isinstance(raw, (bytes, bytearray)):
            raise RosterCodecError("Missing source raw bytes in parsed metadata")

        blob = bytearray(raw)
        for field in parsed.fields.values():
            if field.type_name != "u32":
                continue

            if not isinstance(field.value, int):
                raise RosterCodecError(f"Field '{field.path}' must be int for u32")
            if field.value < 0 or field.value > 0xFFFFFFFF:
                raise RosterCodecError(f"Field '{field.path}' out of u32 range: {field.value}")

            start = field.location.start
            end = field.location.end
            if end - start != 4:
                raise RosterCodecError(f"Field '{field.path}' has invalid location size")

            blob[start:end] = int(field.value).to_bytes(4, "little", signed=False)

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

    def _locate_hero_spans(self, data: bytes) -> List[HeroSpan]:
        starts: List[int] = []
        pos = 0
        while True:
            idx = data.find(HERO_BLOCK_MARKER, pos)
            if idx < 0:
                break
            starts.append(idx)
            pos = idx + 1

        spans: List[HeroSpan] = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(data)
            spans.append(HeroSpan(hero_index=i + 1, start=start, end=end))
        return spans

    def _read_len_prefixed_string(
        self,
        data: bytes,
        start: int,
        end: int,
        marker: bytes,
    ) -> Tuple[str, int, int] | None:
        pos = data.find(marker, start, end)
        if pos < 0:
            return None

        cursor = pos + len(marker)
        # Most strings in this format have one or more null bytes before 4-byte length.
        skip = 0
        while cursor < end and data[cursor] == 0 and skip < 4:
            cursor += 1
            skip += 1

        if cursor + 4 > end:
            return None

        size = int.from_bytes(data[cursor:cursor + 4], "little", signed=False)
        if size <= 0 or size > 128:
            return None

        value_start = cursor + 4
        value_end = value_start + size
        if value_end > end:
            return None

        raw = data[value_start:value_end]
        text = raw.rstrip(b"\x00").decode("utf-8", errors="ignore").strip()
        if not text:
            return None

        return text, value_start, value_end

    def _read_u32_after_key(
        self,
        data: bytes,
        start: int,
        end: int,
        key: str,
    ) -> Tuple[int, int] | None:
        marker = key.encode("utf-8") + b"\x00"
        pos = data.find(marker, start, end)
        if pos < 0:
            return None

        value_offset = pos + len(marker)
        if value_offset + 4 > end:
            return None

        value = int.from_bytes(data[value_offset:value_offset + 4], "little", signed=False)
        return value, value_offset


def extract_hero_summary(parsed: ParsedSaveFile) -> List[dict[str, object]]:
    hero_indexes = sorted(
        {
            int(match.group(1))
            for path in parsed.fields
            for match in [re.match(r"^roster\.heroes\.(\d+)\.", path)]
            if match
        }
    )

    summary: List[dict[str, object]] = []
    for idx in hero_indexes:
        prefix = f"roster.heroes.{idx}"
        name = parsed.fields.get(f"{prefix}.name")
        hero_class = parsed.fields.get(f"{prefix}.class")
        resolve = parsed.fields.get(f"{prefix}.resolve_xp")
        summary.append(
            {
                "hero_index": idx,
                "name": name.value if name else None,
                "class": hero_class.value if hero_class else None,
                "resolve_xp": resolve.value if resolve else None,
            }
        )

    return summary
