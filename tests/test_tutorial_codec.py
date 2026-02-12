from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.tutorial import TutorialSaveCodec, extract_tutorial_summary


def _tutorial_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.tutorial.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.tutorial.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.tutorial.json fixture found")


def test_parse_tutorial_summary_has_core_fields() -> None:
    codec = TutorialSaveCodec()
    parsed = codec.parse(_tutorial_fixture_path())

    summary = extract_tutorial_summary(parsed)
    assert isinstance(summary.get("version"), int)
    assert isinstance(summary.get("dispatched_events_count"), int)
    assert int(summary.get("dispatched_events_count")) >= 0


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _tutorial_fixture_path()
    out = tmp_path / "persist.tutorial.roundtrip.json"

    codec = TutorialSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []
