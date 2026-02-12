from __future__ import annotations

from pathlib import Path

from core.codec.estate import EstateSaveCodec
from core.codec.game import GameSaveCodec
from core.codec.loading_screen import LoadingScreenSaveCodec
from core.codec.map import MapSaveCodec
from core.codec.narration import NarrationSaveCodec
from core.codec.options import OptionsSaveCodec
from core.codec.raid import RaidSaveCodec
from core.codec.roster import RosterSaveCodec
from core.codec.tutorial import TutorialSaveCodec
from core.codec.upgrades import UpgradesSaveCodec
from core.validate import (
    validate_estate_roster_consistency,
    validate_estate_wallet,
    validate_game_structure,
    validate_loading_screen_structure,
    validate_map_structure,
    validate_narration_structure,
    validate_options_structure,
    validate_raid_structure,
    validate_roster_map_consistency,
    validate_roster_upgrades_consistency,
    validate_tutorial_structure,
    validate_upgrades_structure,
)


def _fixture_path(name: str) -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "fixtures" / "raw" / "smoke_profile_1" / name


def test_validate_estate_wallet_has_no_errors_for_smoke_fixture() -> None:
    estate_codec = EstateSaveCodec()
    parsed = estate_codec.parse(_fixture_path("persist.estate.json"))

    issues = validate_estate_wallet(parsed)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_estate_roster_consistency_has_no_errors_for_smoke_fixture() -> None:
    estate_codec = EstateSaveCodec()
    roster_codec = RosterSaveCodec()

    estate = estate_codec.parse(_fixture_path("persist.estate.json"))
    roster = roster_codec.parse(_fixture_path("persist.roster.json"))

    issues = validate_estate_roster_consistency(estate, roster)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_upgrades_structure_has_no_errors_for_smoke_fixture() -> None:
    upgrades_codec = UpgradesSaveCodec()
    upgrades = upgrades_codec.parse(_fixture_path("persist.upgrades.json"))

    issues = validate_upgrades_structure(upgrades)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_map_structure_has_no_errors_for_smoke_fixture() -> None:
    map_codec = MapSaveCodec()
    parsed_map = map_codec.parse(_fixture_path("persist.map.json"))

    issues = validate_map_structure(parsed_map)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_game_structure_has_no_errors_for_smoke_fixture() -> None:
    game_codec = GameSaveCodec()
    parsed_game = game_codec.parse(_fixture_path("persist.game.json"))

    issues = validate_game_structure(parsed_game)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_raid_structure_has_no_errors_for_smoke_fixture() -> None:
    raid_codec = RaidSaveCodec()
    parsed_raid = raid_codec.parse(_fixture_path("persist.raid.json"))

    issues = validate_raid_structure(parsed_raid)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_tutorial_structure_has_no_errors_for_smoke_fixture() -> None:
    tutorial_codec = TutorialSaveCodec()
    parsed_tutorial = tutorial_codec.parse(_fixture_path("persist.tutorial.json"))

    issues = validate_tutorial_structure(parsed_tutorial)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_narration_structure_has_no_errors_for_smoke_fixture() -> None:
    narration_codec = NarrationSaveCodec()
    parsed_narration = narration_codec.parse(_fixture_path("persist.narration.json"))

    issues = validate_narration_structure(parsed_narration)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_loading_screen_structure_has_no_errors_for_smoke_fixture() -> None:
    loading_codec = LoadingScreenSaveCodec()
    parsed_loading = loading_codec.parse(_fixture_path("persist.loading_screen.json"))

    issues = validate_loading_screen_structure(parsed_loading)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_options_structure_has_no_errors_for_local_options_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    options_path = root / "persist.options.json"
    if not options_path.exists():
        return

    options_codec = OptionsSaveCodec()
    parsed_options = options_codec.parse(options_path)

    issues = validate_options_structure(parsed_options)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_roster_upgrades_consistency_has_no_errors_for_smoke_fixture() -> None:
    roster_codec = RosterSaveCodec()
    upgrades_codec = UpgradesSaveCodec()

    roster = roster_codec.parse(_fixture_path("persist.roster.json"))
    upgrades = upgrades_codec.parse(_fixture_path("persist.upgrades.json"))

    issues = validate_roster_upgrades_consistency(roster, upgrades)
    assert all(issue.severity != "error" for issue in issues)


def test_validate_roster_map_consistency_has_no_errors_for_smoke_fixture() -> None:
    roster_codec = RosterSaveCodec()
    map_codec = MapSaveCodec()

    roster = roster_codec.parse(_fixture_path("persist.roster.json"))
    parsed_map = map_codec.parse(_fixture_path("persist.map.json"))

    issues = validate_roster_map_consistency(roster, parsed_map)
    assert all(issue.severity != "error" for issue in issues)
