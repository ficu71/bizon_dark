from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from core.codec.contracts import ParsedSaveFile


class WalletPatchError(Exception):
    pass


@dataclass(slots=True)
class WalletChange:
    key: str
    old_value: int
    new_value: int


def apply_wallet_updates(
    parsed: ParsedSaveFile,
    updates: Dict[str, int],
    expected: Dict[str, int] | None = None,
) -> List[WalletChange]:
    if not updates:
        raise WalletPatchError("No wallet updates provided")

    expected = expected or {}
    out: List[WalletChange] = []

    for key, new_value in updates.items():
        field_key = f"wallet.{key}.amount"
        field = parsed.fields.get(field_key)
        if field is None:
            raise WalletPatchError(f"Wallet field not found: {key}")

        if not isinstance(field.value, int):
            raise WalletPatchError(f"Wallet field '{key}' has non-int value")

        if key in expected and field.value != expected[key]:
            raise WalletPatchError(
                f"Current mismatch for '{key}': expected {expected[key]}, found {field.value}"
            )

        if new_value < 0 or new_value > 0xFFFFFFFF:
            raise WalletPatchError(f"Value out of u32 range for '{key}': {new_value}")

        old_value = field.value
        field.value = new_value
        out.append(WalletChange(key=key, old_value=old_value, new_value=new_value))

    out.sort(key=lambda c: c.key)
    return out
