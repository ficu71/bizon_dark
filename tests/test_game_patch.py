from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.game import GameSaveCodec
from core.patch.game import GamePatchError, apply_game_updates


def _game_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.game.json"


def test_apply_game_updates_changes_selected_key() -> None:
    codec = GameSaveCodec()
    parsed = codec.parse(_game_fixture_path())

    field = parsed.fields["game.inraid"]
    old = int(field.value)
    new = 0 if old == 1 else 1

    changes = apply_game_updates(parsed, updates={"inraid": new}, expected={"inraid": old})

    assert len(changes) == 1
    assert changes[0].key == "inraid"
    assert int(parsed.fields["game.inraid"].value) == new


def test_apply_game_updates_rejects_bad_expect() -> None:
    codec = GameSaveCodec()
    parsed = codec.parse(_game_fixture_path())

    with pytest.raises(GamePatchError):
        apply_game_updates(parsed, updates={"inraid": 1}, expected={"inraid": 9})


def test_apply_game_updates_rejects_unsupported_key() -> None:
    codec = GameSaveCodec()
    parsed = codec.parse(_game_fixture_path())

    with pytest.raises(GamePatchError):
        apply_game_updates(parsed, updates={"mode": 1})
