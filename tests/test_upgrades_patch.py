from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.upgrades import UpgradesSaveCodec
from core.patch.upgrades import UpgradesPatchError, apply_purchase_updates


def _upgrades_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.upgrades.json"


def test_apply_purchase_updates_changes_selected_key() -> None:
    codec = UpgradesSaveCodec()
    parsed = codec.parse(_upgrades_fixture_path())

    field = parsed.fields["upgrades.purchases.items.crusader.smite.is_purchased"]
    old = int(field.value)
    new = 0 if old == 1 else 1

    changes = apply_purchase_updates(
        parsed,
        updates={"crusader.smite": new},
        expected={"crusader.smite": old},
    )

    assert len(changes) == 1
    assert changes[0].key == "crusader.smite"
    assert int(parsed.fields["upgrades.purchases.items.crusader.smite.is_purchased"].value) == new


def test_apply_purchase_updates_rejects_bad_expect() -> None:
    codec = UpgradesSaveCodec()
    parsed = codec.parse(_upgrades_fixture_path())

    with pytest.raises(UpgradesPatchError):
        apply_purchase_updates(
            parsed,
            updates={"crusader.smite": 1},
            expected={"crusader.smite": 0},
        )


def test_apply_purchase_updates_rejects_unknown_key() -> None:
    codec = UpgradesSaveCodec()
    parsed = codec.parse(_upgrades_fixture_path())

    with pytest.raises(UpgradesPatchError):
        apply_purchase_updates(parsed, updates={"unknown.skill": 1})
