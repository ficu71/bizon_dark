from __future__ import annotations

from pathlib import Path

import pytest

from core.codec.estate import EstateSaveCodec
from core.patch.wallet import WalletPatchError, apply_wallet_updates


def _estate_fixture_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / "persist.estate.json"
    if candidate.exists():
        return candidate

    fallback = root / "profile_1" / "persist.estate.json"
    if fallback.exists():
        return fallback

    pytest.skip("No persist.estate.json fixture found")


def _wallet_values(parsed) -> dict[str, int]:
    out: dict[str, int] = {}
    for field in parsed.fields.values():
        if field.path.startswith("wallet.") and field.path.endswith(".amount"):
            key = field.path.split(".")[1]
            out[key] = int(field.value)
    return out


def test_parse_wallet_fields() -> None:
    codec = EstateSaveCodec()
    parsed = codec.parse(_estate_fixture_path())

    wallet = _wallet_values(parsed)
    assert wallet
    assert {"gold", "bust", "portrait", "deed", "crest"}.issubset(wallet.keys())


def test_round_trip_binary_equal(tmp_path: Path) -> None:
    src = _estate_fixture_path()
    out = tmp_path / "persist.estate.roundtrip.json"

    codec = EstateSaveCodec()
    report = codec.round_trip(src, out)

    assert report.logical_equal is True
    assert report.binary_equal is True
    assert report.changed_ranges == []


def test_patch_wallet_changes_only_target_range(tmp_path: Path) -> None:
    src = _estate_fixture_path()
    work = tmp_path / "persist.estate.work.json"
    work.write_bytes(src.read_bytes())

    codec = EstateSaveCodec()
    parsed = codec.parse(work)

    gold_field = parsed.fields["wallet.gold.amount"]
    old_gold = int(gold_field.value)
    new_gold = old_gold + 777

    apply_wallet_updates(parsed, updates={"gold": new_gold}, expected={"gold": old_gold})
    codec.write(parsed, work)

    reparsed = codec.parse(work)
    assert int(reparsed.fields["wallet.gold.amount"].value) == new_gold

    before = src.read_bytes()
    after = work.read_bytes()
    diff_indices = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert diff_indices
    assert all(gold_field.location.start <= i < gold_field.location.end for i in diff_indices)


def test_expect_guard_blocks_wrong_current_value() -> None:
    codec = EstateSaveCodec()
    parsed = codec.parse(_estate_fixture_path())

    with pytest.raises(WalletPatchError):
        apply_wallet_updates(parsed, updates={"gold": 1}, expected={"gold": 99999999})
