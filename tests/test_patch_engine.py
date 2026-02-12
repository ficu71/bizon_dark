from __future__ import annotations

import shutil
from pathlib import Path

from core.codec.estate import EstateSaveCodec
from core.codec.game import GameSaveCodec
from core.codec.loading_screen import LoadingScreenSaveCodec
from core.codec.options import OptionsSaveCodec
from core.codec.raid import RaidSaveCodec
from core.codec.roster import RosterSaveCodec
from core.codec.upgrades import UpgradesSaveCodec
import pytest

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


def test_apply_wallet_patch_dry_run_does_not_modify_file(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    estate_path = profile / "persist.estate.json"
    before = estate_path.read_bytes()

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_wallet_patch(
        profile,
        updates={"gold": 123},
        expected={"gold": 0},
        dry_run=True,
        skip_backup=True,
    )

    after = estate_path.read_bytes()
    assert before == after
    assert result.applied is False
    assert any(op.key == "wallet.gold" for op in result.operations)


def test_apply_hero_patch_commits_change(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    roster_codec = RosterSaveCodec()
    before = roster_codec.parse(profile / "persist.roster.json")
    old_value = int(before.fields["roster.heroes.1.resolve_xp"].value)

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_hero_patch(
        profile,
        hero_index=1,
        updates={"resolve_xp": old_value + 9},
        expected={"resolve_xp": old_value},
        dry_run=False,
        skip_backup=True,
    )

    after = roster_codec.parse(profile / "persist.roster.json")
    assert int(after.fields["roster.heroes.1.resolve_xp"].value) == old_value + 9
    assert result.applied is True


def test_apply_wallet_patch_commits_change(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    estate_codec = EstateSaveCodec()
    before = estate_codec.parse(profile / "persist.estate.json")
    old_gold = int(before.fields["wallet.gold.amount"].value)

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_wallet_patch(
        profile,
        updates={"gold": old_gold + 1000},
        expected={"gold": old_gold},
        dry_run=False,
        skip_backup=True,
    )

    after = estate_codec.parse(profile / "persist.estate.json")
    assert int(after.fields["wallet.gold.amount"].value) == old_gold + 1000
    assert result.applied is True


def test_apply_wallet_patch_creates_backup_when_enabled(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    backup_root = tmp_path / "backups"

    estate_codec = EstateSaveCodec()
    before = estate_codec.parse(profile / "persist.estate.json")
    old_gold = int(before.fields["wallet.gold.amount"].value)

    engine = PatchEngine(backup_root=backup_root)
    result = engine.apply_wallet_patch(
        profile,
        updates={"gold": old_gold + 1},
        expected={"gold": old_gold},
        dry_run=False,
        skip_backup=False,
    )

    assert result.applied is True
    backups = sorted(backup_root.glob("profile_1.*"))
    assert backups


def test_apply_upgrades_patch_commits_change(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    upgrades_codec = UpgradesSaveCodec()
    before = upgrades_codec.parse(profile / "persist.upgrades.json")
    field_key = "upgrades.purchases.items.crusader.smite.is_purchased"
    old_state = int(before.fields[field_key].value)
    new_state = 0 if old_state == 1 else 1

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_upgrades_patch(
        profile,
        updates={"crusader.smite": new_state},
        expected={"crusader.smite": old_state},
        dry_run=False,
        skip_backup=True,
    )

    after = upgrades_codec.parse(profile / "persist.upgrades.json")
    assert int(after.fields[field_key].value) == new_state
    assert result.applied is True


def test_apply_game_patch_commits_change(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    game_codec = GameSaveCodec()
    before = game_codec.parse(profile / "persist.game.json")
    old_state = int(before.fields["game.inraid"].value)
    new_state = 0 if old_state == 1 else 1

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_game_patch(
        profile,
        updates={"inraid": new_state},
        expected={"inraid": old_state},
        dry_run=False,
        skip_backup=True,
    )

    after = game_codec.parse(profile / "persist.game.json")
    assert int(after.fields["game.inraid"].value) == new_state
    assert result.applied is True


def test_apply_loading_patch_commits_change(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    loading_codec = LoadingScreenSaveCodec()
    before = loading_codec.parse(profile / "persist.loading_screen.json")
    old_tip_id = int(before.fields["loading.tip_id"].value)
    new_tip_id = old_tip_id + 100

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_loading_patch(
        profile,
        updates={"tip_id": new_tip_id},
        expected={"tip_id": old_tip_id},
        dry_run=False,
        skip_backup=True,
    )

    after = loading_codec.parse(profile / "persist.loading_screen.json")
    assert int(after.fields["loading.tip_id"].value) == new_tip_id
    assert result.applied is True


def test_apply_raid_patch_commits_change_with_override(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    raid_codec = RaidSaveCodec()
    before = raid_codec.parse(profile / "persist.raid.json")
    old_state = int(before.fields["raid.teleported"].value)
    new_state = 0 if old_state == 1 else 1

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_raid_patch(
        profile,
        updates={"teleported": new_state},
        expected={"teleported": old_state},
        dry_run=False,
        skip_backup=True,
        allow_inbattle=True,
    )

    after = raid_codec.parse(profile / "persist.raid.json")
    assert int(after.fields["raid.teleported"].value) == new_state
    assert result.applied is True


def test_apply_raid_patch_blocks_when_inbattle_without_override(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    raid_codec = RaidSaveCodec()
    before = raid_codec.parse(profile / "persist.raid.json")
    before.fields["raid.inbattle"].value = 1
    raid_codec.write(before, profile / "persist.raid.json")

    current = raid_codec.parse(profile / "persist.raid.json")
    assert int(current.fields["raid.inbattle"].value) == 1

    old_state = int(before.fields["raid.teleported"].value)
    new_state = 0 if old_state == 1 else 1

    engine = PatchEngine(backup_root=tmp_path / "backups")
    with pytest.raises(PatchEngineError):
        engine.apply_raid_patch(
            profile,
            updates={"teleported": new_state},
            expected={"teleported": old_state},
            dry_run=False,
            skip_backup=True,
            allow_inbattle=False,
        )


def test_restore_backup_restores_previous_state(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    engine = PatchEngine(backup_root=tmp_path / "backups")

    estate_codec = EstateSaveCodec()
    before = estate_codec.parse(profile / "persist.estate.json")
    original_gold = int(before.fields["wallet.gold.amount"].value)

    backup_path = engine.create_backup(profile)
    engine.apply_wallet_patch(
        profile,
        updates={"gold": original_gold + 111},
        expected={"gold": original_gold},
        dry_run=False,
        skip_backup=True,
    )

    changed = estate_codec.parse(profile / "persist.estate.json")
    assert int(changed.fields["wallet.gold.amount"].value) == original_gold + 111

    safety = engine.restore_backup(profile, backup_path, create_safety_backup=False)
    assert safety is None

    restored = estate_codec.parse(profile / "persist.estate.json")
    assert int(restored.fields["wallet.gold.amount"].value) == original_gold


def test_restore_backup_creates_safety_backup_when_enabled(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    engine = PatchEngine(backup_root=tmp_path / "backups")

    source_backup = engine.create_backup(profile)
    safety = engine.restore_backup(profile, source_backup, create_safety_backup=True)

    assert safety is not None
    assert isinstance(safety, Path)
    assert safety.exists()


def test_list_backups_returns_matching_profile_entries(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    engine = PatchEngine(backup_root=tmp_path / "backups")

    created = engine.create_backup(profile)
    backups = engine.list_backups("profile_1")

    assert backups
    assert created in backups


def test_apply_hero_patch_strict_validation_blocks_warning(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    roster_codec = RosterSaveCodec()
    before = roster_codec.parse(profile / "persist.roster.json")
    old_value = int(before.fields["roster.heroes.1.resolve_xp"].value)

    engine = PatchEngine(backup_root=tmp_path / "backups")
    with pytest.raises(PatchEngineError):
        engine.apply_hero_patch(
            profile,
            hero_index=1,
            updates={"resolve_xp": old_value + 1},
            expected={"resolve_xp": old_value},
            dry_run=False,
            skip_backup=True,
            strict_validation=True,
        )


def test_apply_options_patch_requires_existing_file(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)
    engine = PatchEngine(backup_root=tmp_path / "backups")

    # Options file doesn't exist in fixture profile
    with pytest.raises(PatchEngineError, match="Options file not found"):
        engine.apply_options_patch(
            profile,
            updates={"language": "english"},
            expected={},
            dry_run=False,
            skip_backup=True,
        )


def test_apply_options_patch_commits_change(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    # Create options file
    options_path = profile / "persist.options.json"
    options_path.write_text(
        '{"version": 1, "data": {"values": {"language": "german", "fullscreen": [1], '
        '"tutorial": [1], "allow_analytics_and_multiplayer": [0], '
        '"resolution": [1920, 1080]}}}\n'
    )

    options_codec = OptionsSaveCodec()
    before = options_codec.parse(options_path)
    old_language = before.fields["options.language"].value

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_options_patch(
        profile,
        updates={"language": "english"},
        expected={"language": old_language},
        dry_run=False,
        skip_backup=True,
    )

    after = options_codec.parse(options_path)
    assert after.fields["options.language"].value == "english"
    assert result.applied is True
    assert any(op.key == "options.language" for op in result.operations)


def test_apply_options_patch_dry_run_does_not_modify(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    # Create options file
    options_path = profile / "persist.options.json"
    options_path.write_text(
        '{"version": 1, "data": {"values": {"language": "french", "fullscreen": [0], '
        '"tutorial": [1], "allow_analytics_and_multiplayer": [0], '
        '"resolution": [1280, 720]}}}\n'
    )

    before_bytes = options_path.read_bytes()

    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_options_patch(
        profile,
        updates={"language": "italian", "fullscreen": 1},
        expected={},
        dry_run=True,
        skip_backup=True,
    )

    after_bytes = options_path.read_bytes()
    assert before_bytes == after_bytes
    assert result.applied is False
    assert len(result.operations) == 2


def test_apply_options_patch_with_external_options_path(tmp_path: Path) -> None:
    profile = _make_profile_copy(tmp_path)

    external_options = tmp_path / "persist.options.json"
    external_options.write_text(
        '{"version": 1, "data": {"values": {"language": "german", "subtitles": "off", '
        '"fullscreen": [1], "tutorial": [1], "allow_analytics_and_multiplayer": [0], '
        '"resolution": [1920, 1080]}}}\n'
    )

    options_codec = OptionsSaveCodec()
    engine = PatchEngine(backup_root=tmp_path / "backups")
    result = engine.apply_options_patch(
        profile,
        updates={"language": "english"},
        expected={"language": "german"},
        options_path=external_options,
        dry_run=False,
        skip_backup=True,
    )

    after = options_codec.parse(external_options)
    assert after.fields["options.language"].value == "english"
    assert result.applied is True
    language_ops = [op for op in result.operations if op.key == "options.language"]
    assert language_ops
    assert language_ops[0].new_value == "english"
