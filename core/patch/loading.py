from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

from core.codec.contracts import ParsedSaveFile


class LoadingPatchError(Exception):
    pass


@dataclass(slots=True)
class LoadingChange:
    key: str
    old_value: int
    new_value: int


_ALLOWED_KEYS = {
    "version": "loading.version",
    "title_id": "loading.title_id",
    "tip_id": "loading.tip_id",
    "narration_entry_id": "loading.narration_entry_id",
}


def apply_loading_updates(
    parsed: ParsedSaveFile,
    updates: Dict[str, int],
    expected: Dict[str, int] | None = None,
) -> List[LoadingChange]:
    if not updates:
        raise LoadingPatchError("No loading updates provided")

    expected = expected or {}
    out: List[LoadingChange] = []

    for key in updates:
        if key not in _ALLOWED_KEYS:
            raise LoadingPatchError(f"Unsupported loading key: {key}")

    metadata = parsed.metadata
    if not isinstance(metadata, dict):
        raise LoadingPatchError("Parsed loading metadata is missing")

    payload = metadata.get("json")
    if not isinstance(payload, dict):
        raise LoadingPatchError("Parsed loading JSON missing in metadata")

    root = payload.get("data")
    if root is None:
        root = {}
        payload["data"] = root
    if not isinstance(root, dict):
        raise LoadingPatchError("loading.data must be an object")

    for key, new_value in updates.items():
        if not isinstance(new_value, int):
            raise LoadingPatchError(f"Value for '{key}' must be int")
        if new_value < 0 or new_value > 0xFFFFFFFF:
            raise LoadingPatchError(f"Value out of u32 range for '{key}': {new_value}")

        field_path = _ALLOWED_KEYS[key]
        field = parsed.fields.get(field_path)
        if field is None:
            raise LoadingPatchError(f"Loading field not found: {field_path}")
        if not isinstance(field.value, int):
            raise LoadingPatchError(f"Loading field '{field_path}' has non-int value")

        if key in expected and field.value != expected[key]:
            raise LoadingPatchError(
                f"Current mismatch for '{key}': expected {expected[key]}, found {field.value}"
            )

        old_value = int(field.value)
        field.value = new_value
        out.append(LoadingChange(key=key, old_value=old_value, new_value=new_value))

        if key == "version":
            payload["version"] = new_value
        else:
            root[key] = new_value

    metadata["raw_bytes"] = (json.dumps(payload, ensure_ascii=False, indent=4) + "\n").encode("utf-8")
    out.sort(key=lambda c: c.key)
    return out
