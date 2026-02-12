from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.loading_screen import LoadingScreenSaveCodec, extract_loading_screen_summary


def _loading_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.loading_screen.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.loading_screen.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.loading_screen.json fixture found")


def test_parse_loading_summary_has_core_fields() -> None:
    codec = LoadingScreenSaveCodec()
    parsed = codec.parse(_loading_fixture_path())

    summary = extract_loading_screen_summary(parsed)
    assert isinstance(summary.get("version"), int)
    assert isinstance(summary.get("background_texture_path"), str)
    assert isinstance(summary.get("tip_id"), int)


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _loading_fixture_path()
    out = tmp_path / "persist.loading_screen.roundtrip.json"

    codec = LoadingScreenSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []
