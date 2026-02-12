from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.narration import NarrationSaveCodec, extract_narration_summary


def _narration_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.narration.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.narration.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.narration.json fixture found")


def test_parse_narration_summary_has_core_fields() -> None:
    codec = NarrationSaveCodec()
    parsed = codec.parse(_narration_fixture_path())

    summary = extract_narration_summary(parsed)
    assert isinstance(summary.get("version"), int)
    assert isinstance(summary.get("entry_type_count"), int)
    assert isinstance(summary.get("audio_event_type_count"), int)
    assert int(summary.get("entry_type_count")) >= 0
    assert int(summary.get("audio_event_type_count")) >= 0


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _narration_fixture_path()
    out = tmp_path / "persist.narration.roundtrip.json"

    codec = NarrationSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []
