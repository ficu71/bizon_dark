from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.map import MapSaveCodec, extract_map_summary


def _map_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.map.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.map.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.map.json fixture found")


def test_parse_map_summary() -> None:
    codec = MapSaveCodec()
    parsed = codec.parse(_map_fixture_path())

    summary = extract_map_summary(parsed)
    assert int(summary["areas_count"]) > 0
    assert int(summary["tiles_count"]) > 0

    area_ids = summary.get("area_ids", [])
    assert isinstance(area_ids, list)
    assert area_ids


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _map_fixture_path()
    out = tmp_path / "persist.map.roundtrip.json"

    codec = MapSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []
