from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.raid import RaidSaveCodec, extract_raid_summary


def _raid_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.raid.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.raid.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.raid.json fixture found")


def test_parse_raid_summary_has_core_fields() -> None:
    codec = RaidSaveCodec()
    parsed = codec.parse(_raid_fixture_path())

    summary = extract_raid_summary(parsed)
    assert isinstance(summary.get("inbattle"), int)
    assert summary.get("inbattle") in (0, 1)
    assert isinstance(summary.get("teleported"), int)
    assert summary.get("teleported") in (0, 1)

    torchlight = summary.get("torchlight")
    assert isinstance(torchlight, (int, float))
    assert float(torchlight) >= 0.0


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _raid_fixture_path()
    out = tmp_path / "persist.raid.roundtrip.json"

    codec = RaidSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []
