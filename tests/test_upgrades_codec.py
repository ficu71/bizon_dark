from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.upgrades import UpgradesSaveCodec, extract_upgrades_summary


def _upgrades_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.upgrades.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.upgrades.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.upgrades.json fixture found")


def test_parse_upgrades_summary() -> None:
    codec = UpgradesSaveCodec()
    parsed = codec.parse(_upgrades_fixture_path())

    summary = extract_upgrades_summary(parsed)
    assert int(summary["purchases_count"]) >= 0
    assert int(summary["discounts_count"]) >= 0

    classes = summary.get("classes", {})
    assert isinstance(classes, dict)
    assert classes


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _upgrades_fixture_path()
    out = tmp_path / "persist.upgrades.roundtrip.json"

    codec = UpgradesSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []
