from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport


class MapCodecError(Exception):
    pass


class MapSaveCodec(SaveCodec):
    """Read-first codec for binary `persist.map.json` with derived structural counters."""

    file_name = "persist.map.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        raw = file_path.read_bytes()

        area_matches = list(re.finditer(rb"([A-Za-z0-9_]{3,16})\x00id\x00", raw))
        area_ids = sorted({m.group(1).decode("ascii", errors="ignore") for m in area_matches})

        tile_matches = list(re.finditer(rb"tile([0-9]+)\x00", raw))
        tile_ids = sorted({int(m.group(1)) for m in tile_matches})

        door_matches = list(re.finditer(rb"door([0-9]+)\x00", raw))
        door_ids = sorted({int(m.group(1)) for m in door_matches})

        marker_tokens = {
            "areas_markers": b"areas\x00",
            "base_root_markers": b"base_root\x00",
            "obstacle_count": b"obstacle\x00",
            "curio_count": b"curio_prop\x00",
            "trap_count": b"trap\x00",
            "crit_scout_count": b"crit_scout\x00",
            "knowledge_count": b"knowledge\x00",
        }
        marker_counts = {name: raw.count(token) for name, token in marker_tokens.items()}

        fields: Dict[str, ParsedField] = {}

        first_area_pos = area_matches[0].start() if area_matches else max(0, raw.find(b"areas\x00"))
        first_tile_pos = tile_matches[0].start() if tile_matches else max(0, raw.find(b"tiles\x00"))
        first_door_pos = door_matches[0].start() if door_matches else max(0, raw.find(b"door0\x00"))

        fields["map.areas.count"] = ParsedField(
            path="map.areas.count",
            value=len(area_ids),
            location=BinaryRange(start=max(0, first_area_pos), end=max(0, first_area_pos)),
            type_name="derived_u32",
        )
        fields["map.tiles.count"] = ParsedField(
            path="map.tiles.count",
            value=len(tile_ids),
            location=BinaryRange(start=max(0, first_tile_pos), end=max(0, first_tile_pos)),
            type_name="derived_u32",
        )
        fields["map.doors.count"] = ParsedField(
            path="map.doors.count",
            value=len(door_ids),
            location=BinaryRange(start=max(0, first_door_pos), end=max(0, first_door_pos)),
            type_name="derived_u32",
        )

        for name, count in marker_counts.items():
            pos = raw.find(marker_tokens[name])
            fields[f"map.markers.{name}"] = ParsedField(
                path=f"map.markers.{name}",
                value=count,
                location=BinaryRange(start=max(0, pos), end=max(0, pos)),
                type_name="derived_u32",
            )

        for area_id in area_ids:
            token = f"{area_id}\x00id\x00".encode("utf-8", errors="ignore")
            pos = raw.find(token)
            fields[f"map.areas.ids.{area_id}"] = ParsedField(
                path=f"map.areas.ids.{area_id}",
                value=1,
                location=BinaryRange(start=max(0, pos), end=max(0, pos)),
                type_name="present",
            )

        return ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-map-v1",
            fields=fields,
            unknown_segments=[],
            metadata={
                "source_path": str(file_path),
                "raw_bytes": raw,
                "area_ids": area_ids,
                "tile_ids": tile_ids,
                "door_ids": door_ids,
                "marker_counts": marker_counts,
            },
        )

    def write(self, parsed: ParsedSaveFile, output_path: Path) -> None:
        raw = parsed.metadata.get("raw_bytes") if isinstance(parsed.metadata, dict) else None
        if not isinstance(raw, (bytes, bytearray)):
            raise MapCodecError("Missing source raw bytes in parsed metadata")
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


def extract_map_summary(parsed: ParsedSaveFile) -> dict[str, object]:
    area_ids = parsed.metadata.get("area_ids", []) if isinstance(parsed.metadata, dict) else []
    tile_ids = parsed.metadata.get("tile_ids", []) if isinstance(parsed.metadata, dict) else []
    door_ids = parsed.metadata.get("door_ids", []) if isinstance(parsed.metadata, dict) else []
    marker_counts = parsed.metadata.get("marker_counts", {}) if isinstance(parsed.metadata, dict) else {}

    return {
        "areas_count": int(parsed.fields.get("map.areas.count").value if "map.areas.count" in parsed.fields else 0),
        "tiles_count": int(parsed.fields.get("map.tiles.count").value if "map.tiles.count" in parsed.fields else 0),
        "doors_count": int(parsed.fields.get("map.doors.count").value if "map.doors.count" in parsed.fields else 0),
        "area_ids": area_ids,
        "tile_ids": tile_ids,
        "door_ids": door_ids,
        "marker_counts": marker_counts,
    }
