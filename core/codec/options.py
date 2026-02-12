from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport


class OptionsCodecError(Exception):
    pass


class OptionsSaveCodec(SaveCodec):
    """Codec for JSON `persist.options.json` (read-only in v1)."""

    file_name = "persist.options.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        raw = file_path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OptionsCodecError(f"Invalid UTF-8 in {file_path.name}") from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OptionsCodecError(f"Invalid JSON in {file_path.name}: {exc}") from exc

        if not isinstance(data, dict):
            raise OptionsCodecError("Top-level options JSON must be an object")

        root = data.get("data") if isinstance(data.get("data"), dict) else {}
        values = root.get("values") if isinstance(root.get("values"), dict) else {}

        fields: Dict[str, ParsedField] = {}
        version = int(data.get("version", 0))
        version_pos = raw.find(b'"version"')
        fields["options.version"] = ParsedField(
            path="options.version",
            value=version,
            location=BinaryRange(start=max(0, version_pos), end=max(0, version_pos)),
            type_name="u32",
        )

        language = str(values.get("language", ""))
        language_pos = raw.find(b'"language"')
        fields["options.language"] = ParsedField(
            path="options.language",
            value=language,
            location=BinaryRange(start=max(0, language_pos), end=max(0, language_pos)),
            type_name="string",
        )

        subtitles = str(values.get("subtitles", ""))
        subtitles_pos = raw.find(b'"subtitles"')
        fields["options.subtitles"] = ParsedField(
            path="options.subtitles",
            value=subtitles,
            location=BinaryRange(start=max(0, subtitles_pos), end=max(0, subtitles_pos)),
            type_name="string",
        )

        for key in ["fullscreen", "tutorial", "allow_analytics_and_multiplayer"]:
            val = _read_first_int(values.get(key), default=0)
            pos = raw.find(f'"{key}"'.encode("utf-8"))
            fields[f"options.{key}"] = ParsedField(
                path=f"options.{key}",
                value=val,
                location=BinaryRange(start=max(0, pos), end=max(0, pos)),
                type_name="u32",
            )

        resolution = values.get("resolution")
        width = 0
        height = 0
        if isinstance(resolution, list) and len(resolution) >= 2:
            width = int(resolution[0]) if isinstance(resolution[0], (int, float)) else 0
            height = int(resolution[1]) if isinstance(resolution[1], (int, float)) else 0
        resolution_pos = raw.find(b'"resolution"')
        fields["options.resolution.width"] = ParsedField(
            path="options.resolution.width",
            value=width,
            location=BinaryRange(start=max(0, resolution_pos), end=max(0, resolution_pos)),
            type_name="u32",
        )
        fields["options.resolution.height"] = ParsedField(
            path="options.resolution.height",
            value=height,
            location=BinaryRange(start=max(0, resolution_pos), end=max(0, resolution_pos)),
            type_name="u32",
        )

        return ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-options-json-v1",
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
            raise OptionsCodecError("Missing source raw bytes in parsed metadata")
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


def _read_first_int(value, default: int) -> int:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, (int, float)):
            return int(first)
    if isinstance(value, (int, float)):
        return int(value)
    return default


def extract_options_summary(parsed: ParsedSaveFile) -> dict[str, object]:
    def _get(path: str, default=None):
        field = parsed.fields.get(path)
        return field.value if field is not None else default

    return {
        "version": _get("options.version", 0),
        "language": _get("options.language", ""),
        "subtitles": _get("options.subtitles", ""),
        "fullscreen": _get("options.fullscreen", 0),
        "tutorial": _get("options.tutorial", 0),
        "allow_analytics_and_multiplayer": _get("options.allow_analytics_and_multiplayer", 0),
        "resolution_width": _get("options.resolution.width", 0),
        "resolution_height": _get("options.resolution.height", 0),
    }
