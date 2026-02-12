from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.roster import RosterSaveCodec
from core.patch.roster import RosterPatchError, apply_hero_updates


def _roster_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.roster.json"


def test_apply_hero_updates_changes_selected_field() -> None:
    codec = RosterSaveCodec()
    parsed = codec.parse(_roster_fixture_path())

    field = parsed.fields["roster.heroes.1.resolve_xp"]
    old = int(field.value)
    new = old + 5

    changes = apply_hero_updates(parsed, hero_index=1, updates={"resolve_xp": new}, expected={"resolve_xp": old})

    assert len(changes) == 1
    assert changes[0].key == "resolve_xp"
    assert int(parsed.fields["roster.heroes.1.resolve_xp"].value) == new


def test_apply_hero_updates_rejects_bad_expect() -> None:
    codec = RosterSaveCodec()
    parsed = codec.parse(_roster_fixture_path())

    with pytest.raises(RosterPatchError):
        apply_hero_updates(parsed, hero_index=1, updates={"resolve_xp": 1}, expected={"resolve_xp": 999999})


def test_apply_hero_updates_rejects_unsupported_key() -> None:
    codec = RosterSaveCodec()
    parsed = codec.parse(_roster_fixture_path())

    with pytest.raises(RosterPatchError):
        apply_hero_updates(parsed, hero_index=1, updates={"hp": 10})
