from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from core.codec.contracts import ParsedSaveFile


class RaidPatchError(Exception):
    pass


@dataclass(slots=True)
class RaidChange:
    key: str
    old_value: int
    new_value: int


_ALLOWED_KEYS = {
    "inbattle": "raid.inbattle",
    "teleported": "raid.teleported",
    "has_mash_data": "raid.has_mash_data",
    "implied": "raid.implied",
    "is_plot_quest": "raid.is_plot_quest",
    "counted_in_generation": "raid.counted_in_generation",
    "use_default_progression_goals": "raid.use_default_progression_goals",
    "is_from_town_event": "raid.is_from_town_event",
}


def apply_raid_updates(
    parsed: ParsedSaveFile,
    updates: Dict[str, int],
    expected: Dict[str, int] | None = None,
) -> List[RaidChange]:
    if not updates:
        raise RaidPatchError("No raid updates provided")

    expected = expected or {}
    out: List[RaidChange] = []

    for key in updates:
        if key not in _ALLOWED_KEYS:
            raise RaidPatchError(f"Unsupported raid key: {key}")

    for key, new_value in updates.items():
        if new_value not in (0, 1):
            raise RaidPatchError(f"Value must be 0 or 1 for '{key}'")

        field_path = _ALLOWED_KEYS[key]
        field = parsed.fields.get(field_path)
        if field is None:
            raise RaidPatchError(f"Raid field not found: {field_path}")

        if not isinstance(field.value, int):
            raise RaidPatchError(f"Raid field '{field_path}' has non-int value")

        if key in expected and field.value != expected[key]:
            raise RaidPatchError(
                f"Current mismatch for '{key}': expected {expected[key]}, found {field.value}"
            )

        old_value = field.value
        field.value = new_value
        out.append(RaidChange(key=key, old_value=old_value, new_value=new_value))

    out.sort(key=lambda c: c.key)
    return out
