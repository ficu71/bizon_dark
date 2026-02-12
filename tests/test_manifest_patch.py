from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from core.codec.estate import EstateSaveCodec
from core.codec.game import GameSaveCodec
from core.codec.loading_screen import LoadingScreenSaveCodec
from core.codec.options import OptionsSaveCodec
from core.codec.raid import RaidSaveCodec
from core.codec.roster import RosterSaveCodec
from core.patch.engine import PatchEngine, PatchEngineError


def _fixture_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "fixtures" / "raw" / "smoke_profile_1"


def _make_profile_copy(tmp_path: Path) -> Path:
    profile = tmp_path / "profile_1"
    profile.mkdir(parents=True)
    src = _fixture_dir()
    for name in [
        "persist.estate.json",
        "persist.roster.json",
        "persist.upgrades.json",
        "persist.map.json",
        "persist.game.json",
        "persist.raid.json",
        "persist.tutorial.json",
        "persist.narration.json",
        "persist.loading_screen.json",
    ]:
        shutil.copy2(src / name, profile / name)
    return profile


def test_manifest_patch_dry_run_does_not_modify_files(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    estate_path = profile / "persist.estate.json"
    game_path = profile / "persist.game.json"
    before_estate = estate_path.read_bytes()
    before_game = game_path.read_bytes()

    estate_codec = EstateSaveCodec()
    game_codec = GameSaveCodec()
    old_gold = int(estate_codec.parse(estate_path).fields["wallet.gold.amount"].value)
    old_inraid = int(game_codec.parse(game_path).fields["game.inraid"].value)

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_manifest_patch(
        profile,
        {
            "wallet_updates": {"gold": old_gold + 10},
            "wallet_expected": {"gold": old_gold},
            "game_updates": {"inraid": 0 if old_inraid == 1 else 1},
            "game_expected": {"inraid": old_inraid},
        },
        dry_run=True,
        skip_backup=True,
    )

    assert result.applied is False
    assert estate_path.read_bytes() == before_estate
    assert game_path.read_bytes() == before_game
    assert any(op.key == "wallet.gold" for op in result.operations)
    assert any(op.key == "game.inraid" for op in result.operations)


def test_manifest_patch_commits_multiple_sections(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    estate_codec = EstateSaveCodec()
    roster_codec = RosterSaveCodec()
    game_codec = GameSaveCodec()
    loading_codec = LoadingScreenSaveCodec()

    old_gold = int(estate_codec.parse(profile / "persist.estate.json").fields["wallet.gold.amount"].value)
    old_resolve = int(roster_codec.parse(profile / "persist.roster.json").fields["roster.heroes.1.resolve_xp"].value)
    old_inraid = int(game_codec.parse(profile / "persist.game.json").fields["game.inraid"].value)
    old_tip_id = int(loading_codec.parse(profile / "persist.loading_screen.json").fields["loading.tip_id"].value)

    new_gold = old_gold + 123
    new_resolve = old_resolve + 7
    new_inraid = 0 if old_inraid == 1 else 1
    new_tip_id = old_tip_id + 10

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_manifest_patch(
        profile,
        {
            "wallet_updates": {"gold": new_gold},
            "wallet_expected": {"gold": old_gold},
            "hero_updates": [
                {
                    "hero_index": 1,
                    "updates": {"resolve_xp": new_resolve},
                    "expected": {"resolve_xp": old_resolve},
                }
            ],
            "game_updates": {"inraid": new_inraid},
            "game_expected": {"inraid": old_inraid},
            "loading_updates": {"tip_id": new_tip_id},
            "loading_expected": {"tip_id": old_tip_id},
        },
        dry_run=False,
        skip_backup=True,
    )

    assert result.applied is True
    assert int(estate_codec.parse(profile / "persist.estate.json").fields["wallet.gold.amount"].value) == new_gold
    assert (
        int(roster_codec.parse(profile / "persist.roster.json").fields["roster.heroes.1.resolve_xp"].value)
        == new_resolve
    )
    assert int(game_codec.parse(profile / "persist.game.json").fields["game.inraid"].value) == new_inraid
    assert int(loading_codec.parse(profile / "persist.loading_screen.json").fields["loading.tip_id"].value) == new_tip_id


def test_manifest_patch_blocks_raid_when_inbattle_without_override(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    raid_codec = RaidSaveCodec()

    raid = raid_codec.parse(profile / "persist.raid.json")
    raid.fields["raid.inbattle"].value = 1
    raid_codec.write(raid, profile / "persist.raid.json")

    old_teleported = int(raid.fields["raid.teleported"].value)
    new_teleported = 0 if old_teleported == 1 else 1

    engine = PatchEngine(backup_root=tmp_path / "backups")
    with pytest.raises(PatchEngineError):
        engine.apply_manifest_patch(
            profile,
            {
                "raid_updates": {"teleported": new_teleported},
                "raid_expected": {"teleported": old_teleported},
            },
            dry_run=False,
            skip_backup=True,
            allow_inbattle=False,
        )


def test_manifest_patch_applies_options_with_external_path(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    estate_codec = EstateSaveCodec()
    options_codec = OptionsSaveCodec()

    external_options = tmp_path / "persist.options.json"
    external_options.write_text(
        '{"version": 1, "data": {"values": {"language": "german", "subtitles": "off", '
        '"fullscreen": [1], "tutorial": [1], "allow_analytics_and_multiplayer": [0], '
        '"resolution": [1920, 1080]}}}\n'
    )

    old_gold = int(estate_codec.parse(profile / "persist.estate.json").fields["wallet.gold.amount"].value)
    new_gold = old_gold + 55

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_manifest_patch(
        profile,
        {
            "wallet_updates": {"gold": new_gold},
            "wallet_expected": {"gold": old_gold},
            "options_updates": {"language": "english", "fullscreen": 0},
            "options_expected": {"language": "german", "fullscreen": 1},
        },
        options_path=external_options,
        dry_run=False,
        skip_backup=True,
    )

    assert result.applied is True
    assert int(estate_codec.parse(profile / "persist.estate.json").fields["wallet.gold.amount"].value) == new_gold
    assert options_codec.parse(external_options).fields["options.language"].value == "english"
