from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from core.codec.contracts import ParsedSaveFile


class GamePatchError(Exception):
    pass


@dataclass(slots=True)
class GameChange:
    key: str
    old_value: int
    new_value: int


_ALLOWED_KEYS = {
    "inraid": "game.inraid",
    "dd_options_altered": "game.dd_options_altered",
}


def apply_game_updates(
    parsed: ParsedSaveFile,
    updates: Dict[str, int],
    expected: Dict[str, int] | None = None,
) -> List[GameChange]:
    if not updates:
        raise GamePatchError("No game updates provided")

    expected = expected or {}
    out: List[GameChange] = []

    for key in updates:
        if key not in _ALLOWED_KEYS:
            raise GamePatchError(f"Unsupported game key: {key}")

    for key, new_value in updates.items():
        if new_value not in (0, 1):
            raise GamePatchError(f"Value must be 0 or 1 for '{key}'")

        field_path = _ALLOWED_KEYS[key]
        field = parsed.fields.get(field_path)
        if field is None:
            raise GamePatchError(f"Game field not found: {field_path}")

        if not isinstance(field.value, int):
            raise GamePatchError(f"Game field '{field_path}' has non-int value")

        if key in expected and field.value != expected[key]:
            raise GamePatchError(
                f"Current mismatch for '{key}': expected {expected[key]}, found {field.value}"
            )

        old_value = field.value
        field.value = new_value
        out.append(GameChange(key=key, old_value=old_value, new_value=new_value))

    out.sort(key=lambda c: c.key)
    return out
