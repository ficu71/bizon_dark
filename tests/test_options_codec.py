from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.options import OptionsSaveCodec, extract_options_summary


def _options_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "persist.options.json"
    if candidate.exists():
        return candidate

    pytest.skip("No persist.options.json fixture found")


def test_parse_options_summary_has_core_fields() -> None:
    codec = OptionsSaveCodec()
    parsed = codec.parse(_options_fixture_path())

    summary = extract_options_summary(parsed)
    assert isinstance(summary.get("version"), int)
    assert isinstance(summary.get("language"), str)
    assert isinstance(summary.get("resolution_width"), int)
    assert isinstance(summary.get("resolution_height"), int)


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _options_fixture_path()
    out = tmp_path / "persist.options.roundtrip.json"

    codec = OptionsSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []
