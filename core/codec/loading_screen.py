from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport


class LoadingScreenCodecError(Exception):
    pass


class LoadingScreenSaveCodec(SaveCodec):
    """Codec for JSON `persist.loading_screen.json` (read-first)."""

    file_name = "persist.loading_screen.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        raw = file_path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LoadingScreenCodecError(f"Invalid UTF-8 in {file_path.name}") from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LoadingScreenCodecError(f"Invalid JSON in {file_path.name}: {exc}") from exc

        if not isinstance(data, dict):
            raise LoadingScreenCodecError("Top-level loading screen JSON must be an object")

        root = data.get("data") if isinstance(data.get("data"), dict) else {}

        fields: Dict[str, ParsedField] = {}
        version = int(data.get("version", 0))
        version_pos = raw.find(b'"version"')
        fields["loading.version"] = ParsedField(
            path="loading.version",
            value=version,
            location=BinaryRange(start=max(0, version_pos), end=max(0, version_pos)),
            type_name="u32",
        )

        texture = str(root.get("background_texture_path", ""))
        texture_pos = raw.find(b'"background_texture_path"')
        fields["loading.background_texture_path"] = ParsedField(
            path="loading.background_texture_path",
            value=texture,
            location=BinaryRange(start=max(0, texture_pos), end=max(0, texture_pos)),
            type_name="string",
        )

        for key in ["title_id", "tip_id", "narration_entry_id"]:
            value = int(root.get(key, 0))
            pos = raw.find(f'"{key}"'.encode("utf-8"))
            fields[f"loading.{key}"] = ParsedField(
                path=f"loading.{key}",
                value=value,
                location=BinaryRange(start=max(0, pos), end=max(0, pos)),
                type_name="u32",
            )

        queue = root.get("narration_audio_event_queue_tags", [])
        queue_count = len(queue) if isinstance(queue, list) else 0
        queue_pos = raw.find(b'"narration_audio_event_queue_tags"')
        fields["loading.narration_audio_event_queue_tags.count"] = ParsedField(
            path="loading.narration_audio_event_queue_tags.count",
            value=queue_count,
            location=BinaryRange(start=max(0, queue_pos), end=max(0, queue_pos)),
            type_name="derived_u32",
        )

        return ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-loading-json-v1",
            fields=fields,
            unknown_segments=[],
            metadata={
                "source_path": str(file_path),
                "raw_bytes": raw,
                "json": data,
            },
        )

    def write(self, parsed: ParsedSaveFile, output_path: Path) -> None:
        raw = parsed.metadata.get("raw_bytes") if isinstance(parsed.metadata, dict) else None
        if not isinstance(raw, (bytes, bytearray)):
            raise LoadingScreenCodecError("Missing source raw bytes in parsed metadata")
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


def extract_loading_screen_summary(parsed: ParsedSaveFile) -> dict[str, object]:
    def _get(path: str, default=None):
        field = parsed.fields.get(path)
        return field.value if field is not None else default

    return {
        "version": _get("loading.version", 0),
        "background_texture_path": _get("loading.background_texture_path", ""),
        "title_id": _get("loading.title_id", 0),
        "tip_id": _get("loading.tip_id", 0),
        "narration_entry_id": _get("loading.narration_entry_id", 0),
        "narration_audio_event_queue_tags_count": _get("loading.narration_audio_event_queue_tags.count", 0),
    }
