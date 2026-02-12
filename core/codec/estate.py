from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport, UnknownSegment


class EstateCodecError(Exception):
    pass


@dataclass(slots=True)
class WalletToken:
    name: str
    value: int
    value_offset: int
    amount_offset: int
    type_offset: int


class EstateSaveCodec(SaveCodec):
    """Codec for `persist.estate.json` (binary format used by Darkest Dungeon)."""

    file_name = "persist.estate.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        data = file_path.read_bytes()
        wallet = self._parse_wallet_entries(data)

        fields: Dict[str, ParsedField] = {}
        for token in wallet.values():
            field_path = f"wallet.{token.name}.amount"
            fields[field_path] = ParsedField(
                path=field_path,
                value=token.value,
                location=BinaryRange(start=token.value_offset, end=token.value_offset + 4),
                type_name="u32",
            )

        start, end = self._find_wallet_bounds(data)
        unknown = [
            UnknownSegment(
                name="prefix",
                location=BinaryRange(start=0, end=start),
                raw=data[:start],
            ),
            UnknownSegment(
                name="suffix",
                location=BinaryRange(start=end, end=len(data)),
                raw=data[end:],
            ),
        ]

        parsed = ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-estate-v1",
            fields=fields,
            unknown_segments=unknown,
        )
        parsed.metadata = {
            "source_path": str(file_path),
            "raw_bytes": data,
            "wallet_bounds": (start, end),
        }
        return parsed

    def write(self, parsed: ParsedSaveFile, output_path: Path) -> None:
        if not any(path.startswith("wallet.") and path.endswith(".amount") for path in parsed.fields):
            raise EstateCodecError("Parsed payload does not look like estate wallet data")

        raw = parsed.metadata.get("raw_bytes") if hasattr(parsed, "metadata") else None
        if not isinstance(raw, (bytes, bytearray)):
            raise EstateCodecError("Missing source raw bytes in parsed metadata")

        blob = bytearray(raw)

        for field in parsed.fields.values():
            if field.type_name != "u32":
                continue

            if not isinstance(field.value, int):
                raise EstateCodecError(f"Field '{field.path}' must be int for u32")

            if field.value < 0 or field.value > 0xFFFFFFFF:
                raise EstateCodecError(
                    f"Field '{field.path}' value out of u32 range: {field.value}"
                )

            start = field.location.start
            end = field.location.end
            if end - start != 4:
                raise EstateCodecError(
                    f"Field '{field.path}' location size invalid: {start}:{end}"
                )

            blob[start:end] = int(field.value).to_bytes(4, "little", signed=False)

        output_path.write_bytes(blob)

    def round_trip(self, file_path: Path, out_path: Path) -> RoundTripReport:
        parsed = self.parse(file_path)
        self.write(parsed, out_path)

        in_bytes = file_path.read_bytes()
        out_bytes = out_path.read_bytes()
        logical_equal = self.parse(file_path).fields == self.parse(out_path).fields
        binary_equal = in_bytes == out_bytes

        changed_ranges = []
        if not binary_equal:
            min_len = min(len(in_bytes), len(out_bytes))
            run_start = None
            for i in range(min_len):
                if in_bytes[i] != out_bytes[i] and run_start is None:
                    run_start = i
                if in_bytes[i] == out_bytes[i] and run_start is not None:
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

    def _find_wallet_bounds(self, data: bytes) -> Tuple[int, int]:
        start = data.find(b"wallet\x00")
        if start < 0:
            raise EstateCodecError("wallet section not found")

        end_candidates = []
        for marker in (b"trinkets\x00", b"estate_items\x00", b"items\x00"):
            idx = data.find(marker, start + 1)
            if idx > start:
                end_candidates.append(idx)

        if not end_candidates:
            raise EstateCodecError("wallet end marker not found")

        return start, min(end_candidates)

    def _parse_wallet_entries(self, data: bytes) -> Dict[str, WalletToken]:
        start, end = self._find_wallet_bounds(data)
        pos = start + len(b"wallet\x00")
        entries: Dict[str, WalletToken] = {}

        while pos < end:
            amount_pos = data.find(b"amount\x00", pos, end)
            if amount_pos < 0:
                break

            type_pos = data.find(b"type\x00", amount_pos, end)
            if type_pos < 0:
                break

            if type_pos < 4:
                raise EstateCodecError("type marker before value bytes")

            name_len_pos = type_pos + 8
            name_start = type_pos + 12
            if name_len_pos + 4 > len(data) or name_start > len(data):
                break

            name_len = int.from_bytes(data[name_len_pos:name_len_pos + 4], "little", signed=False)
            if name_len <= 0 or name_len > 256:
                pos = type_pos + len(b"type\x00")
                continue

            name_end = name_start + name_len
            if name_end > len(data):
                break

            raw_name = data[name_start:name_end]
            name = raw_name.rstrip(b"\x00").decode("utf-8", errors="ignore").strip().lower()
            if not name:
                pos = name_end
                continue

            value_offset = type_pos - 4
            value = int.from_bytes(data[value_offset:value_offset + 4], "little", signed=False)

            entries[name] = WalletToken(
                name=name,
                value=value,
                value_offset=value_offset,
                amount_offset=amount_pos,
                type_offset=type_pos,
            )
            pos = name_end

        if not entries:
            raise EstateCodecError("No wallet entries parsed")

        return entries
