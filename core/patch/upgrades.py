from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from core.codec.contracts import ParsedSaveFile


class UpgradesPatchError(Exception):
    pass


@dataclass(slots=True)
class UpgradesChange:
    key: str
    old_value: int
    new_value: int


def apply_purchase_updates(
    parsed: ParsedSaveFile,
    updates: Dict[str, int],
    expected: Dict[str, int] | None = None,
) -> List[UpgradesChange]:
    if not updates:
        raise UpgradesPatchError("No upgrades updates provided")

    if not isinstance(parsed.metadata, dict):
        raise UpgradesPatchError("Parsed upgrades metadata missing")

    obj = parsed.metadata.get("json")
    if not isinstance(obj, dict):
        raise UpgradesPatchError("Parsed upgrades JSON missing in metadata")

    root_data = obj.get("data")
    if not isinstance(root_data, dict):
        raise UpgradesPatchError("Invalid upgrades JSON: data must be object")

    purchases = root_data.get("purchases")
    if not isinstance(purchases, dict):
        raise UpgradesPatchError("Invalid upgrades JSON: data.purchases must be object")

    expected = expected or {}
    out: List[UpgradesChange] = []

    for key, new_value in updates.items():
        if key not in purchases or not isinstance(purchases[key], dict):
            raise UpgradesPatchError(f"Purchase key not found: {key}")

        if new_value not in (0, 1):
            raise UpgradesPatchError(f"is_purchased must be 0 or 1 for key '{key}'")

        current_bool = bool(purchases[key].get("is_purchased", False))
        current = 1 if current_bool else 0

        if key in expected and expected[key] != current:
            raise UpgradesPatchError(
                f"Current mismatch for '{key}': expected {expected[key]}, found {current}"
            )

        purchases[key]["is_purchased"] = bool(new_value)

        field_path = f"upgrades.purchases.items.{key}.is_purchased"
        field = parsed.fields.get(field_path)
        if field is not None:
            field.value = int(new_value)

        out.append(UpgradesChange(key=key, old_value=current, new_value=int(new_value)))

    # Recompute derived purchased_count field.
    purchased_count = 0
    for value in purchases.values():
        if isinstance(value, dict) and bool(value.get("is_purchased", False)):
            purchased_count += 1
    count_field = parsed.fields.get("upgrades.purchases.purchased_count")
    if count_field is not None:
        count_field.value = purchased_count

    parsed.metadata["json"] = obj
    parsed.metadata["dirty_json"] = True

    out.sort(key=lambda x: x.key)
    return out
