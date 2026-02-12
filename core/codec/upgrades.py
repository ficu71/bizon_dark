from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

from core.codec.base import SaveCodec
from core.codec.contracts import BinaryRange, ParsedField, ParsedSaveFile, RoundTripReport


class UpgradesCodecError(Exception):
    pass


class UpgradesSaveCodec(SaveCodec):
    """Codec for JSON `persist.upgrades.json` (read-first, lossless write by default)."""

    file_name = "persist.upgrades.json"

    def supports(self, file_name: str) -> bool:
        return file_name == self.file_name

    def parse(self, file_path: Path) -> ParsedSaveFile:
        raw = file_path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UpgradesCodecError(f"Invalid UTF-8 in {file_path.name}") from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise UpgradesCodecError(f"Invalid JSON in {file_path.name}: {exc}") from exc

        if not isinstance(data, dict):
            raise UpgradesCodecError("Top-level upgrades JSON must be an object")

        fields: Dict[str, ParsedField] = {}

        version = int(data.get("version", 0))
        v_start, v_end = self._locate_key_value_span(raw, "version", str(version).encode("ascii"))
        fields["upgrades.version"] = ParsedField(
            path="upgrades.version",
            value=version,
            location=BinaryRange(start=v_start, end=v_end),
            type_name="u32",
        )

        root_data = data.get("data") if isinstance(data.get("data"), dict) else {}
        purchases = root_data.get("purchases") if isinstance(root_data.get("purchases"), dict) else {}
        discounts = root_data.get("discounts") if isinstance(root_data.get("discounts"), dict) else {}

        p_start = raw.find(b'"purchases"')
        d_start = raw.find(b'"discounts"')
        fields["upgrades.purchases.count"] = ParsedField(
            path="upgrades.purchases.count",
            value=len(purchases),
            location=BinaryRange(start=max(0, p_start), end=max(0, p_start)),
            type_name="derived_u32",
        )
        fields["upgrades.discounts.count"] = ParsedField(
            path="upgrades.discounts.count",
            value=len(discounts),
            location=BinaryRange(start=max(0, d_start), end=max(0, d_start)),
            type_name="derived_u32",
        )

        classes: Dict[str, int] = {}
        purchased_count = 0
        for key, value in purchases.items():
            if not isinstance(key, str):
                continue
            if not isinstance(value, dict):
                continue

            hero_class = key.split(".", 1)[0] if "." in key else "unknown"
            classes[hero_class] = classes.get(hero_class, 0) + 1

            is_purchased = bool(value.get("is_purchased", False))
            if is_purchased:
                purchased_count += 1

            key_marker = f'"{key}"'.encode("utf-8")
            k_pos = raw.find(key_marker)
            fields[f"upgrades.purchases.items.{key}.is_purchased"] = ParsedField(
                path=f"upgrades.purchases.items.{key}.is_purchased",
                value=1 if is_purchased else 0,
                location=BinaryRange(start=max(0, k_pos), end=max(0, k_pos)),
                type_name="bool_as_u8",
            )

        for hero_class, count in sorted(classes.items()):
            token = f'"{hero_class}.'.encode("utf-8")
            pos = raw.find(token)
            fields[f"upgrades.purchases.classes.{hero_class}.count"] = ParsedField(
                path=f"upgrades.purchases.classes.{hero_class}.count",
                value=count,
                location=BinaryRange(start=max(0, pos), end=max(0, pos)),
                type_name="derived_u32",
            )

        fields["upgrades.purchases.purchased_count"] = ParsedField(
            path="upgrades.purchases.purchased_count",
            value=purchased_count,
            location=BinaryRange(start=max(0, p_start), end=max(0, p_start)),
            type_name="derived_u32",
        )

        return ParsedSaveFile(
            file_name=file_path.name,
            format_version="dd-upgrades-json-v1",
            fields=fields,
            unknown_segments=[],
            metadata={
                "source_path": str(file_path),
                "raw_bytes": raw,
                "json": data,
            },
        )

    def write(self, parsed: ParsedSaveFile, output_path: Path) -> None:
        if not isinstance(parsed.metadata, dict):
            raise UpgradesCodecError("Missing metadata for write")

        obj = parsed.metadata.get("json")
        if obj is None:
            raise UpgradesCodecError("Missing metadata for write")

        dirty_json = bool(parsed.metadata.get("dirty_json", False))
        raw = parsed.metadata.get("raw_bytes")

        if not dirty_json and isinstance(raw, (bytes, bytearray)):
            output_path.write_bytes(bytes(raw))
            return

        output_path.write_text(json.dumps(obj, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

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

    def _locate_key_value_span(self, raw: bytes, key: str, value_repr: bytes) -> tuple[int, int]:
        pattern = rb'"' + re.escape(key.encode("utf-8")) + rb'"\s*:\s*' + re.escape(value_repr)
        m = re.search(pattern, raw)
        if not m:
            pos = raw.find(key.encode("utf-8"))
            return (max(0, pos), max(0, pos))
        value_start = m.end() - len(value_repr)
        return value_start, value_start + len(value_repr)


def extract_upgrades_summary(parsed: ParsedSaveFile) -> dict[str, object]:
    purchases_field = parsed.fields.get("upgrades.purchases.count")
    discounts_field = parsed.fields.get("upgrades.discounts.count")
    purchases = int(purchases_field.value) if purchases_field and isinstance(purchases_field.value, int) else 0
    discounts = int(discounts_field.value) if discounts_field and isinstance(discounts_field.value, int) else 0
    classes: Dict[str, int] = {}
    purchased_count_field = parsed.fields.get("upgrades.purchases.purchased_count")
    purchased_count = (
        int(purchased_count_field.value)
        if purchased_count_field and isinstance(purchased_count_field.value, int)
        else 0
    )
    for path, field in parsed.fields.items():
        if not path.startswith("upgrades.purchases.classes.") or not path.endswith(".count"):
            continue
        cls = path.split(".")[3]
        if isinstance(field.value, int):
            classes[cls] = field.value

    return {
        "purchases_count": purchases,
        "discounts_count": discounts,
        "purchased_count": purchased_count,
        "classes": dict(sorted(classes.items())),
    }
