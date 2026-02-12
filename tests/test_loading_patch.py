from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.loading_screen import LoadingScreenSaveCodec
from core.patch.loading import LoadingPatchError, apply_loading_updates


def _loading_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.loading_screen.json"


def test_apply_loading_updates_changes_selected_key() -> None:
    codec = LoadingScreenSaveCodec()
    parsed = codec.parse(_loading_fixture_path())

    field = parsed.fields["loading.tip_id"]
    old = int(field.value)
    new = old + 11

    changes = apply_loading_updates(parsed, updates={"tip_id": new}, expected={"tip_id": old})

    assert len(changes) == 1
    assert changes[0].key == "tip_id"
    assert int(parsed.fields["loading.tip_id"].value) == new


def test_apply_loading_updates_rejects_bad_expect() -> None:
    codec = LoadingScreenSaveCodec()
    parsed = codec.parse(_loading_fixture_path())

    with pytest.raises(LoadingPatchError):
        apply_loading_updates(parsed, updates={"tip_id": 1}, expected={"tip_id": 999999})


def test_apply_loading_updates_rejects_unsupported_key() -> None:
    codec = LoadingScreenSaveCodec()
    parsed = codec.parse(_loading_fixture_path())

    with pytest.raises(LoadingPatchError):
        apply_loading_updates(parsed, updates={"background_texture_path": 1})
