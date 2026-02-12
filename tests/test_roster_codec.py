from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.roster import RosterSaveCodec, extract_hero_summary


def _roster_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.roster.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.roster.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.roster.json fixture found")


def test_parse_roster_has_heroes() -> None:
    codec = RosterSaveCodec()
    parsed = codec.parse(_roster_fixture_path())

    summary = extract_hero_summary(parsed)
    assert summary
    assert len(summary) >= 1

    names = [str(item.get("name") or "") for item in summary]
    assert any(name for name in names)


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _roster_fixture_path()
    out = tmp_path / "persist.roster.roundtrip.json"

    codec = RosterSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []


def test_fields_have_valid_locations() -> None:
    src = _roster_fixture_path()
    raw_size = src.stat().st_size

    codec = RosterSaveCodec()
    parsed = codec.parse(src)

    for field in parsed.fields.values():
        assert 0 <= field.location.start <= raw_size
        assert 0 <= field.location.end <= raw_size
        assert field.location.start <= field.location.end


def test_summary_contains_name_and_class_when_present() -> None:
    codec = RosterSaveCodec()
    parsed = codec.parse(_roster_fixture_path())

    summary = extract_hero_summary(parsed)
    first = summary[0]

    assert "hero_index" in first
    assert "name" in first
    assert "class" in first
