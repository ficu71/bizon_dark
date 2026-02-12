from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.raid import RaidSaveCodec
from core.patch.raid import RaidPatchError, apply_raid_updates


def _raid_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.raid.json"


def test_apply_raid_updates_changes_selected_key() -> None:
    codec = RaidSaveCodec()
    parsed = codec.parse(_raid_fixture_path())

    field = parsed.fields["raid.teleported"]
    old = int(field.value)
    new = 0 if old == 1 else 1

    changes = apply_raid_updates(parsed, updates={"teleported": new}, expected={"teleported": old})

    assert len(changes) == 1
    assert changes[0].key == "teleported"
    assert int(parsed.fields["raid.teleported"].value) == new


def test_apply_raid_updates_rejects_bad_expect() -> None:
    codec = RaidSaveCodec()
    parsed = codec.parse(_raid_fixture_path())

    with pytest.raises(RaidPatchError):
        apply_raid_updates(parsed, updates={"teleported": 1}, expected={"teleported": 9})


def test_apply_raid_updates_rejects_unsupported_key() -> None:
    codec = RaidSaveCodec()
    parsed = codec.parse(_raid_fixture_path())

    with pytest.raises(RaidPatchError):
        apply_raid_updates(parsed, updates={"torchlight": 1})
