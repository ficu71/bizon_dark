from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.game import GameSaveCodec, extract_game_summary


def _game_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.game.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.game.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.game.json fixture found")


def test_parse_game_summary_has_core_fields() -> None:
    codec = GameSaveCodec()
    parsed = codec.parse(_game_fixture_path())

    summary = extract_game_summary(parsed)
    assert isinstance(summary.get("version"), int)
    assert isinstance(summary.get("inraid"), int)
    assert summary.get("inraid") in (0, 1)

    estate_name = summary.get("estate_name")
    assert isinstance(estate_name, str)
    assert estate_name


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _game_fixture_path()
    out = tmp_path / "persist.game.roundtrip.json"

    codec = GameSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []
