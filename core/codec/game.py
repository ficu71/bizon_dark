from __future__ import annotations

import struct
from pathlib import Path
from typing import Dict, List, Tuple

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport


class GameCodecError(Exception):
    pass


class GameSaveCodec(SaveCodec):
    """Codec for binary `persist.game.json` with safe offset-based writes."""

    file_name = "persist.game.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        raw = file_path.read_bytes()
        fields: Dict[str, ParsedField] = {}

        version = self._read_u32_with_optional_padding(raw, b"version\x00", max_value=100_000)
        if version:
            value, start, end = version
            fields["game.version"] = ParsedField(
                path="game.version",
                value=value,
                location=BinaryRange(start=start, end=end),
                type_name="u32",
            )

        total_elapsed = self._read_f32_with_optional_padding(raw, b"totalelapsed\x00", min_value=-1.0, max_value=10_000_000.0)
        if total_elapsed:
            value, start, end = total_elapsed
            fields["game.total_elapsed"] = ParsedField(
                path="game.total_elapsed",
                value=value,
                location=BinaryRange(start=start, end=end),
                type_name="f32",
            )

        inraid = self._read_bool_with_optional_padding(raw, b"inraid\x00")
        if inraid:
            value, start, end = inraid
            fields["game.inraid"] = ParsedField(
                path="game.inraid",
                value=value,
                location=BinaryRange(start=start, end=end),
                type_name="bool_u8",
            )

        dd_opts = self._read_bool_with_optional_padding(raw, b"dd_options_altered\x00")
        if dd_opts:
            value, start, end = dd_opts
            fields["game.dd_options_altered"] = ParsedField(
                path="game.dd_options_altered",
                value=value,
                location=BinaryRange(start=start, end=end),
                type_name="bool_u8",
            )

        for marker, field_path in [
            (b"estatename\x00", "game.estate_name"),
            (b"game_mode\x00", "game.mode"),
            (b"date_time\x00", "game.date_time"),
        ]:
            parsed = self._read_len_prefixed_string(raw, marker)
            if parsed:
                value, start, end = parsed
                fields[field_path] = ParsedField(
                    path=field_path,
                    value=value,
                    location=BinaryRange(start=start, end=end),
                    type_name="string",
                )

        if not fields:
            raise GameCodecError("No known fields parsed from persist.game.json")

        return ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-game-v1",
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
            raise GameCodecError("Missing source raw bytes in parsed metadata")

        blob = bytearray(raw)
        for field in parsed.fields.values():
            start = field.location.start
            end = field.location.end
            if start < 0 or end > len(blob) or start >= end:
                raise GameCodecError(f"Invalid field location for {field.path}: {start}:{end}")

            if field.type_name == "u32":
                if not isinstance(field.value, int):
                    raise GameCodecError(f"Field '{field.path}' must be int")
                if field.value < 0 or field.value > 0xFFFFFFFF:
                    raise GameCodecError(f"Field '{field.path}' out of u32 range: {field.value}")
                if end - start != 4:
                    raise GameCodecError(f"Field '{field.path}' has invalid u32 size")
                blob[start:end] = int(field.value).to_bytes(4, "little", signed=False)

            elif field.type_name == "f32":
                if not isinstance(field.value, (int, float)):
                    raise GameCodecError(f"Field '{field.path}' must be float-compatible")
                if end - start != 4:
                    raise GameCodecError(f"Field '{field.path}' has invalid f32 size")
                blob[start:end] = struct.pack("<f", float(field.value))

            elif field.type_name == "bool_u8":
                if not isinstance(field.value, int) or field.value not in (0, 1):
                    raise GameCodecError(f"Field '{field.path}' must be 0/1")
                if end - start != 1:
                    raise GameCodecError(f"Field '{field.path}' has invalid bool size")
                blob[start] = int(field.value)

            elif field.type_name == "string":
                if not isinstance(field.value, str):
                    raise GameCodecError(f"Field '{field.path}' must be string")
                encoded = field.value.encode("utf-8")
                slot_size = end - start
                if len(encoded) > slot_size:
                    raise GameCodecError(
                        f"Field '{field.path}' length too long; max {slot_size}, got {len(encoded)}"
                    )
                blob[start:end] = encoded.ljust(slot_size, b"\x00")

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
            # Heuristic: next byte should likely start another marker/string token.
            if end < len(raw) and raw[end] in _VALID_NEXT_BYTES:
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
            if end < len(raw) and raw[end] in _VALID_NEXT_BYTES:
                return float(value), start, end

        return None

    def _read_bool_with_optional_padding(self, raw: bytes, marker: bytes) -> Tuple[int, int, int] | None:
        pos = raw.find(marker)
        if pos < 0:
            return None

        base = pos + len(marker)
        for off in range(0, 5):
            idx = base + off
            next_idx = idx + 1
            if next_idx >= len(raw):
                break
            value = raw[idx]
            if value not in (0, 1):
                continue
            if raw[next_idx] in _VALID_NEXT_BYTES:
                return int(value), idx, idx + 1

        return None

    def _read_len_prefixed_string(self, raw: bytes, marker: bytes) -> Tuple[str, int, int] | None:
        pos = raw.find(marker)
        if pos < 0:
            return None

        cursor = pos + len(marker)
        skip = 0
        while cursor < len(raw) and raw[cursor] == 0 and skip < 4:
            cursor += 1
            skip += 1

        if cursor + 4 > len(raw):
            return None

        size = int.from_bytes(raw[cursor:cursor + 4], "little", signed=False)
        if size <= 0 or size > 256:
            return None

        value_start = cursor + 4
        value_end = value_start + size
        if value_end > len(raw):
            return None

        text = raw[value_start:value_end].rstrip(b"\x00").decode("utf-8", errors="ignore").strip()
        if not text:
            return None

        return text, value_start, value_end


_VALID_NEXT_BYTES = set(range(ord("a"), ord("z") + 1)) | {ord("_"), 0}


def extract_game_summary(parsed: ParsedSaveFile) -> dict[str, object]:
    def _get(path: str, default=None):
        field = parsed.fields.get(path)
        return field.value if field is not None else default

    return {
        "version": _get("game.version", 0),
        "total_elapsed": _get("game.total_elapsed", 0.0),
        "inraid": _get("game.inraid", 0),
        "dd_options_altered": _get("game.dd_options_altered", 0),
        "estate_name": _get("game.estate_name", ""),
        "mode": _get("game.mode", ""),
        "date_time": _get("game.date_time", ""),
    }
