from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

from core.codec.contracts import ParsedSaveFile


class OptionsPatchError(Exception):
    pass


@dataclass(slots=True)
class OptionsChange:
    key: str
    old_value: int | str
    new_value: int | str


# Safe fields for editing in persist.options.json
# Only primitive fields that don't affect game logic critically
_ALLOWED_KEYS = {
    "language": ("options.language", str),
    "subtitles": ("options.subtitles", str),
    "fullscreen": ("options.fullscreen", int),
    "tutorial": ("options.tutorial", int),
    "allow_analytics_and_multiplayer": ("options.allow_analytics_and_multiplayer", int),
    "resolution_width": ("options.resolution.width", int),
    "resolution_height": ("options.resolution.height", int),
}


def apply_options_updates(
    parsed: ParsedSaveFile,
    updates: Dict[str, int | str],
    expected: Dict[str, int | str] | None = None,
) -> List[OptionsChange]:
    """Apply safe updates to options JSON.
    
    Only allows editing display/preferences fields.
    Critical gameplay fields (cloud saves, etc.) are blocked.
    """
    if not updates:
        raise OptionsPatchError("No options updates provided")

    expected = expected or {}
    out: List[OptionsChange] = []

    for key in updates:
        if key not in _ALLOWED_KEYS:
            raise OptionsPatchError(f"Unsupported or unsafe options key: {key}")

    metadata = parsed.metadata
    if not isinstance(metadata, dict):
        raise OptionsPatchError("Parsed options metadata is missing")

    payload = metadata.get("json")
    if not isinstance(payload, dict):
        raise OptionsPatchError("Parsed options JSON missing in metadata")

    root = payload.get("data")
    if not isinstance(root, dict):
        raise OptionsPatchError("options.data must be an object")

    values = root.get("values")
    if not isinstance(values, dict):
        raise OptionsPatchError("options.data.values must be an object")

    for key, new_value in updates.items():
        field_path, expected_type = _ALLOWED_KEYS[key]
        
        if not isinstance(new_value, expected_type):
            raise OptionsPatchError(
                f"Value for '{key}' must be {expected_type.__name__}, got {type(new_value).__name__}"
            )
        
        # Validate int range for numeric fields
        if expected_type == int:
            if isinstance(new_value, int) and (new_value < 0 or new_value > 0xFFFFFFFF):
                raise OptionsPatchError(f"Value out of u32 range for '{key}': {new_value}")

        field = parsed.fields.get(field_path)
        if field is None:
            raise OptionsPatchError(f"Options field not found: {field_path}")

        current_value = field.value
        if not isinstance(current_value, (int, str)):
            raise OptionsPatchError(f"Options field '{field_path}' has unsupported type")

        if key in expected:
            exp_val = expected[key]
            if current_value != exp_val:
                raise OptionsPatchError(
                    f"Current mismatch for '{key}': expected {exp_val!r}, found {current_value!r}"
                )

        old_value = current_value
        field.value = new_value
        out.append(OptionsChange(key=key, old_value=old_value, new_value=new_value))

        # Update the JSON payload for serialization
        if key == "resolution_width":
            resolution = values.get("resolution")
            if isinstance(resolution, list) and len(resolution) >= 2:
                resolution[0] = new_value
            else:
                values["resolution"] = [new_value, 0]
        elif key == "resolution_height":
            resolution = values.get("resolution")
            if isinstance(resolution, list) and len(resolution) >= 2:
                resolution[1] = new_value
            else:
                values["resolution"] = [0, new_value]
        elif key in ("fullscreen", "tutorial", "allow_analytics_and_multiplayer"):
            # These are stored as single-element arrays in the JSON
            values[key] = [new_value]
        else:
            values[key] = new_value

    metadata["raw_bytes"] = (json.dumps(payload, ensure_ascii=False, indent=4) + "\n").encode("utf-8")
    out.sort(key=lambda c: c.key)
    return out
