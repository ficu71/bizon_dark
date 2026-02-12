from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from core.codec.contracts import ParsedSaveFile


class RosterPatchError(Exception):
    pass


@dataclass(slots=True)
class RosterHeroChange:
    hero_index: int
    key: str
    old_value: int
    new_value: int


_ALLOWED_KEYS = {"resolve_xp", "weapon_rank", "armour_rank"}


def apply_hero_updates(
    parsed: ParsedSaveFile,
    hero_index: int,
    updates: Dict[str, int],
    expected: Dict[str, int] | None = None,
) -> List[RosterHeroChange]:
    if hero_index <= 0:
        raise RosterPatchError("hero_index must be >= 1")

    if not updates:
        raise RosterPatchError("No hero updates provided")

    expected = expected or {}
    out: List[RosterHeroChange] = []

    for key in updates:
        if key not in _ALLOWED_KEYS:
            raise RosterPatchError(f"Unsupported hero key: {key}")

    for key, new_value in updates.items():
        field_path = f"roster.heroes.{hero_index}.{key}"
        field = parsed.fields.get(field_path)
        if field is None:
            raise RosterPatchError(f"Field not found for hero {hero_index}: {key}")

        if not isinstance(field.value, int):
            raise RosterPatchError(f"Field '{field_path}' has non-int value")

        if key in expected and field.value != expected[key]:
            raise RosterPatchError(
                f"Current mismatch for hero {hero_index} '{key}': "
                f"expected {expected[key]}, found {field.value}"
            )

        if new_value < 0 or new_value > 0xFFFFFFFF:
            raise RosterPatchError(f"Value out of u32 range for '{key}': {new_value}")

        old_value = field.value
        field.value = new_value
        out.append(
            RosterHeroChange(
                hero_index=hero_index,
                key=key,
                old_value=old_value,
                new_value=new_value,
            )
        )

    out.sort(key=lambda x: x.key)
    return out
