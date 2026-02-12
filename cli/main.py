from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.codec import (
    EstateCodecError,
    EstateSaveCodec,
    GameCodecError,
    GameSaveCodec,
    LoadingScreenCodecError,
    LoadingScreenSaveCodec,
    MapCodecError,
    MapSaveCodec,
    NarrationCodecError,
    NarrationSaveCodec,
    OptionsCodecError,
    OptionsSaveCodec,
    RaidCodecError,
    RaidSaveCodec,
    RosterCodecError,
    RosterSaveCodec,
    TutorialCodecError,
    TutorialSaveCodec,
    UpgradesCodecError,
    UpgradesSaveCodec,
    extract_game_summary,
    extract_hero_summary,
    extract_loading_screen_summary,
    extract_map_summary,
    extract_narration_summary,
    extract_options_summary,
    extract_raid_summary,
    extract_tutorial_summary,
    extract_upgrades_summary,
)
from core.patch import PatchEngine, PatchEngineError
from core.patch.options import OptionsPatchError
from core.presets import PresetError, build_manifest_for_preset, list_presets
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bizon Dark Editor CLI")
    parser.add_argument(
        "--profile",
        default=str(Path.home() / "Library" / "Application Support" / "Darkest" / "profile_1"),
        help="Path to profile directory (default: DD profile_1)",
    )
    parser.add_argument(
        "--options-file",
        default=None,
        help="Path to persist.options.json (default: sibling to profile dir)",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check profile and codec parsing")
    sub.add_parser("list-wallet", help="Print wallet resources")
    sub.add_parser("list-heroes", help="Print roster hero summary")
    sub.add_parser("list-upgrades", help="Print upgrades summary")
    sub.add_parser("list-map", help="Print map summary")
    sub.add_parser("list-game", help="Print game summary")
    sub.add_parser("list-raid", help="Print raid summary")
    sub.add_parser("list-tutorial", help="Print tutorial summary")
    sub.add_parser("list-narration", help="Print narration summary")
    sub.add_parser("list-loading-screen", help="Print loading screen summary")
    sub.add_parser("list-options", help="Print options summary")
    p_validate = sub.add_parser("validate", help="Run cross-file consistency validation")
    p_validate.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as blocking (exit code 2)",
    )
    sub.add_parser("inspect", help="Print full profile snapshot as JSON")
    sub.add_parser("list-presets", help="List available built-in presets")

    p_export = sub.add_parser("export", help="Export profile snapshot JSON to file")
    p_export.add_argument("--output", required=True, help="Output JSON path")

    p_import = sub.add_parser("import", help="Apply patch manifest JSON transactionally")
    p_import.add_argument("--file", required=True, help="Input manifest JSON path")
    p_import.add_argument("--dry-run", action="store_true")
    p_import.add_argument("--backup-dir", default="backups")
    p_import.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_import.add_argument(
        "--allow-inbattle",
        action="store_true",
        help="Allow raid updates when raid.inbattle=1",
    )
    p_import.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    p_apply_preset = sub.add_parser("apply-preset", help="Apply built-in preset transactionally")
    p_apply_preset.add_argument("--name", required=True, help="Preset name (see list-presets)")
    p_apply_preset.add_argument("--hero", type=int, default=1, help="Hero index for hero presets")
    p_apply_preset.add_argument(
        "--resolve-xp",
        type=int,
        default=120,
        help="Resolve XP value for hero-resolve-boost preset",
    )
    p_apply_preset.add_argument("--dry-run", action="store_true")
    p_apply_preset.add_argument("--backup-dir", default="backups")
    p_apply_preset.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_apply_preset.add_argument(
        "--allow-inbattle",
        action="store_true",
        help="Allow raid updates when raid.inbattle=1",
    )
    p_apply_preset.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    p_backup = sub.add_parser("backup", help="Create backup snapshot of profile")
    p_backup.add_argument("--backup-dir", default="backups")

    p_list_backups = sub.add_parser("list-backups", help="List available backups for selected profile")
    p_list_backups.add_argument("--backup-dir", default="backups")
    p_list_backups.add_argument("--limit", type=int, default=20)

    p_restore = sub.add_parser("restore", help="Restore profile from backup snapshot")
    p_restore.add_argument("--backup-dir", default="backups")
    p_restore.add_argument(
        "--from-backup",
        default=None,
        help="Absolute path or backup directory name",
    )
    p_restore.add_argument("--latest", action="store_true", help="Use latest backup for this profile")
    p_restore.add_argument(
        "--no-safety-backup",
        action="store_true",
        help="Do not create safety backup before restore",
    )

    p_diff = sub.add_parser("diff", help="Diff current profile against backup snapshot")
    p_diff.add_argument("--backup-dir", default="backups")
    p_diff.add_argument(
        "--from-backup",
        default=None,
        help="Absolute path or backup directory name",
    )
    p_diff.add_argument("--latest", action="store_true", help="Use latest backup for this profile")

    p_patch = sub.add_parser("patch-wallet", help="Patch wallet resources")
    p_patch.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    p_patch.add_argument("--expect", action="append", default=[], metavar="KEY=VALUE")
    p_patch.add_argument("--dry-run", action="store_true")
    p_patch.add_argument("--backup-dir", default="backups")
    p_patch.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_patch.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    p_hero = sub.add_parser("patch-hero", help="Patch selected hero stats in roster")
    p_hero.add_argument("--hero", type=int, required=True, help="Hero index from list-heroes")
    p_hero.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Allowed keys: resolve_xp, weapon_rank, armour_rank",
    )
    p_hero.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional current-value guard for same keys",
    )
    p_hero.add_argument("--dry-run", action="store_true")
    p_hero.add_argument("--backup-dir", default="backups")
    p_hero.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_hero.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    p_upg = sub.add_parser("patch-upgrades", help="Patch upgrades purchase flags")
    p_upg.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Example: --set crusader.smite=1",
    )
    p_upg.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional current-value guard (0/1 or true/false)",
    )
    p_upg.add_argument("--dry-run", action="store_true")
    p_upg.add_argument("--backup-dir", default="backups")
    p_upg.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_upg.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    p_game = sub.add_parser("patch-game", help="Patch selected game flags")
    p_game.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Allowed keys: inraid, dd_options_altered",
    )
    p_game.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional current-value guard for same keys",
    )
    p_game.add_argument("--dry-run", action="store_true")
    p_game.add_argument("--backup-dir", default="backups")
    p_game.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_game.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    p_loading = sub.add_parser("patch-loading", help="Patch selected loading screen fields")
    p_loading.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Allowed keys: version, title_id, tip_id, narration_entry_id",
    )
    p_loading.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional current-value guard for same keys",
    )
    p_loading.add_argument("--dry-run", action="store_true")
    p_loading.add_argument("--backup-dir", default="backups")
    p_loading.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_loading.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    p_raid = sub.add_parser("patch-raid", help="Patch selected raid flags")
    p_raid.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Allowed keys: inbattle, teleported, has_mash_data, implied, "
            "is_plot_quest, counted_in_generation, use_default_progression_goals, is_from_town_event"
        ),
    )
    p_raid.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional current-value guard for same keys",
    )
    p_raid.add_argument("--dry-run", action="store_true")
    p_raid.add_argument("--backup-dir", default="backups")
    p_raid.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_raid.add_argument(
        "--allow-inbattle",
        action="store_true",
        help="Allow patch when raid.inbattle=1",
    )
    p_raid.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    p_options = sub.add_parser("patch-options", help="Patch selected options fields (safe preferences only)")
    p_options.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Allowed keys: language, subtitles, fullscreen, tutorial, allow_analytics_and_multiplayer, resolution_width, resolution_height",
    )
    p_options.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional current-value guard for same keys",
    )
    p_options.add_argument("--dry-run", action="store_true")
    p_options.add_argument("--backup-dir", default="backups")
    p_options.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation before write",
    )
    p_options.add_argument(
        "--strict",
        action="store_true",
        help="Treat validation warnings as blocking during commit",
    )

    return parser


def _normalize_wallet_key(key: str) -> str:
    raw = key.strip().lower()
    if raw.startswith("estate.wallet."):
        return raw.split("estate.wallet.", 1)[1]
    if raw.startswith("wallet."):
        tail = raw.split("wallet.", 1)[1]
        if tail.endswith(".amount"):
            return tail[: -len(".amount")]
        return tail
    return raw


def _parse_key_values(values: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid KEY=VALUE: {item}")

        key, raw = item.split("=", 1)
        wallet_key = _normalize_wallet_key(key)
        value = int(raw)
        if value < 0 or value > 0xFFFFFFFF:
            raise ValueError(f"Value out of u32 range for '{wallet_key}': {value}")
        out[wallet_key] = value
    return out


def _parse_hero_key_values(values: list[str]) -> dict[str, int]:
    aliases = {
        "resolve_xp": "resolve_xp",
        "resolvexp": "resolve_xp",
        "weapon_rank": "weapon_rank",
        "weaponrank": "weapon_rank",
        "weapon": "weapon_rank",
        "armour_rank": "armour_rank",
        "armorrank": "armour_rank",
        "armor_rank": "armour_rank",
        "armour": "armour_rank",
        "armor": "armour_rank",
    }
    out: dict[str, int] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid KEY=VALUE: {item}")
        key, raw = item.split("=", 1)
        k = key.strip().lower()
        canonical = aliases.get(k)
        if not canonical:
            raise ValueError(f"Unsupported hero key: {key}")

        value = int(raw)
        if value < 0 or value > 0xFFFFFFFF:
            raise ValueError(f"Value out of u32 range for '{canonical}': {value}")
        out[canonical] = value
    return out


def _parse_boolish(raw: str) -> int:
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return 1
    if value in {"0", "false", "no", "off"}:
        return 0
    raise ValueError(f"Invalid bool/int value: {raw}")


def _parse_upgrades_key_values(values: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid KEY=VALUE: {item}")
        key, raw = item.split("=", 1)
        k = key.strip()
        if not k:
            raise ValueError(f"Invalid upgrades key in pair: {item}")
        out[k] = _parse_boolish(raw)
    return out


def _parse_game_key_values(values: list[str]) -> dict[str, int]:
    aliases = {
        "inraid": "inraid",
        "game.inraid": "inraid",
        "dd_options_altered": "dd_options_altered",
        "ddoptionsaltered": "dd_options_altered",
        "options_altered": "dd_options_altered",
        "game.dd_options_altered": "dd_options_altered",
    }
    out: dict[str, int] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid KEY=VALUE: {item}")
        key, raw = item.split("=", 1)
        normalized = aliases.get(key.strip().lower())
        if not normalized:
            raise ValueError(f"Unsupported game key: {key}")
        out[normalized] = _parse_boolish(raw)
    return out


def _parse_loading_key_values(values: list[str]) -> dict[str, int]:
    aliases = {
        "version": "version",
        "loading.version": "version",
        "title_id": "title_id",
        "titleid": "title_id",
        "loading.title_id": "title_id",
        "tip_id": "tip_id",
        "tipid": "tip_id",
        "loading.tip_id": "tip_id",
        "narration_entry_id": "narration_entry_id",
        "narrationentryid": "narration_entry_id",
        "loading.narration_entry_id": "narration_entry_id",
    }
    out: dict[str, int] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid KEY=VALUE: {item}")
        key, raw = item.split("=", 1)
        normalized = aliases.get(key.strip().lower())
        if not normalized:
            raise ValueError(f"Unsupported loading key: {key}")

        value = int(raw)
        if value < 0 or value > 0xFFFFFFFF:
            raise ValueError(f"Value out of u32 range for '{normalized}': {value}")
        out[normalized] = value
    return out


def _parse_raid_key_values(values: list[str]) -> dict[str, int]:
    aliases = {
        "inbattle": "inbattle",
        "raid.inbattle": "inbattle",
        "teleported": "teleported",
        "raid.teleported": "teleported",
        "has_mash_data": "has_mash_data",
        "hasmashdata": "has_mash_data",
        "raid.has_mash_data": "has_mash_data",
        "implied": "implied",
        "raid.implied": "implied",
        "is_plot_quest": "is_plot_quest",
        "isplotquest": "is_plot_quest",
        "raid.is_plot_quest": "is_plot_quest",
        "counted_in_generation": "counted_in_generation",
        "countedingeneration": "counted_in_generation",
        "raid.counted_in_generation": "counted_in_generation",
        "use_default_progression_goals": "use_default_progression_goals",
        "usedefaultprogressiongoals": "use_default_progression_goals",
        "raid.use_default_progression_goals": "use_default_progression_goals",
        "is_from_town_event": "is_from_town_event",
        "isfromtownevent": "is_from_town_event",
        "raid.is_from_town_event": "is_from_town_event",
    }
    out: dict[str, int] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid KEY=VALUE: {item}")
        key, raw = item.split("=", 1)
        normalized = aliases.get(key.strip().lower())
        if not normalized:
            raise ValueError(f"Unsupported raid key: {key}")
        out[normalized] = _parse_boolish(raw)
    return out


def _parse_options_key_values(values: list[str]) -> dict[str, int | str]:
    """Parse options key-values. Returns int for numeric fields, str for string fields."""
    string_keys = {"language", "subtitles"}
    int_keys = {
        "fullscreen",
        "tutorial",
        "allow_analytics_and_multiplayer",
        "resolution_width",
        "resolution_height",
    }
    all_keys = string_keys | int_keys

    out: dict[str, int | str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid KEY=VALUE: {item}")
        key, raw = item.split("=", 1)
        k = key.strip().lower()

        if k not in all_keys:
            raise ValueError(f"Unsupported options key: {key}. Allowed: {', '.join(sorted(all_keys))}")

        if k in string_keys:
            out[k] = raw.strip()
        else:
            # Int field
            value = int(raw)
            if value < 0 or value > 0xFFFFFFFF:
                raise ValueError(f"Value out of u32 range for '{k}': {value}")
            out[k] = value
    return out


def _estate_path(profile: Path) -> Path:
    return profile / "persist.estate.json"


def _roster_path(profile: Path) -> Path:
    return profile / "persist.roster.json"


def _upgrades_path(profile: Path) -> Path:
    return profile / "persist.upgrades.json"


def _map_path(profile: Path) -> Path:
    return profile / "persist.map.json"


def _game_path(profile: Path) -> Path:
    return profile / "persist.game.json"


def _raid_path(profile: Path) -> Path:
    return profile / "persist.raid.json"


def _tutorial_path(profile: Path) -> Path:
    return profile / "persist.tutorial.json"


def _narration_path(profile: Path) -> Path:
    return profile / "persist.narration.json"


def _loading_path(profile: Path) -> Path:
    return profile / "persist.loading_screen.json"


def _options_path(profile: Path, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    return (profile.parent / "persist.options.json").resolve()


def _list_wallet(codec: EstateSaveCodec, estate_path: Path) -> list[tuple[str, int]]:
    parsed = codec.parse(estate_path)
    out: list[tuple[str, int]] = []
    for field in parsed.fields.values():
        if field.path.startswith("wallet.") and field.path.endswith(".amount"):
            key = field.path.split(".")[1]
            out.append((key, int(field.value)))
    return sorted(out)


def _print_validation_issues(issues, *, strict: bool = False) -> int:
    if not issues:
        print("[ok] validation passed")
        return 0

    has_error = False
    has_warning = False
    for issue in issues:
        if issue.severity == "error":
            has_error = True
        if issue.severity == "warning":
            has_warning = True
        location = f" {issue.file_name}:{issue.field_path}" if issue.file_name or issue.field_path else ""
        print(f"[{issue.severity}] {issue.code}{location} - {issue.message}")

    if strict and has_warning and not has_error:
        print("[strict] warnings treated as blocking")
        return 2

    return 2 if has_error else 0


def _resolve_backup_path(
    *,
    backup_root: Path,
    profile_name: str,
    from_backup: str | None,
    latest: bool,
) -> Path:
    engine = PatchEngine(backup_root=backup_root)

    if latest:
        backups = engine.list_backups(profile_name=profile_name)
        if not backups:
            raise FileNotFoundError(f"No backups found in {backup_root} for profile '{profile_name}'")
        return backups[0]

    if not from_backup:
        raise ValueError("Either --from-backup or --latest is required")

    candidate = Path(from_backup).expanduser()
    if candidate.is_absolute():
        path = candidate.resolve()
    else:
        direct = (Path.cwd() / candidate).resolve()
        if direct.exists():
            path = direct
        else:
            path = (backup_root / candidate).resolve()

    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Backup path not found: {path}")
    return path


def _profile_files_for_diff() -> list[str]:
    return [
        "persist.estate.json",
        "persist.roster.json",
        "persist.upgrades.json",
        "persist.map.json",
        "persist.game.json",
        "persist.raid.json",
        "persist.tutorial.json",
        "persist.narration.json",
        "persist.loading_screen.json",
    ]


def _byte_diff_stats(left: bytes, right: bytes) -> tuple[int, int | None]:
    min_len = min(len(left), len(right))
    first_diff: int | None = None
    changed = 0

    for i in range(min_len):
        if left[i] != right[i]:
            changed += 1
            if first_diff is None:
                first_diff = i

    if len(left) != len(right):
        changed += abs(len(left) - len(right))
        if first_diff is None:
            first_diff = min_len

    return changed, first_diff


def _pairs_from_mapping(mapping: dict) -> list[str]:
    pairs: list[str] = []
    for key, value in mapping.items():
        if isinstance(value, bool):
            value_raw = "1" if value else "0"
        else:
            value_raw = str(value)
        pairs.append(f"{key}={value_raw}")
    return pairs


def _parse_manifest_payload(manifest_path: Path) -> dict[str, object]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON manifest: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Manifest must be a JSON object")

    def parse_section(
        name: str,
        parser_fn,
    ) -> tuple[dict[str, int | str], dict[str, int | str]]:
        section = data.get(name)
        if section is None:
            return {}, {}
        if not isinstance(section, dict):
            raise ValueError(f"Manifest section '{name}' must be an object")

        set_obj = section.get("set", {})
        expect_obj = section.get("expect", {})
        if not isinstance(set_obj, dict) or not isinstance(expect_obj, dict):
            raise ValueError(f"Manifest section '{name}' requires object keys 'set' and 'expect'")

        updates = parser_fn(_pairs_from_mapping(set_obj))
        expected = parser_fn(_pairs_from_mapping(expect_obj))
        return updates, expected

    wallet_updates, wallet_expected = parse_section("wallet", _parse_key_values)
    upgrades_updates, upgrades_expected = parse_section("upgrades", _parse_upgrades_key_values)
    game_updates, game_expected = parse_section("game", _parse_game_key_values)
    loading_updates, loading_expected = parse_section("loading", _parse_loading_key_values)
    options_updates, options_expected = parse_section("options", _parse_options_key_values)
    raid_updates, raid_expected = parse_section("raid", _parse_raid_key_values)

    heroes_raw = data.get("heroes", [])
    if not isinstance(heroes_raw, list):
        raise ValueError("Manifest section 'heroes' must be a list")

    hero_updates: list[dict[str, object]] = []
    for index, item in enumerate(heroes_raw):
        if not isinstance(item, dict):
            raise ValueError(f"Manifest heroes[{index}] must be an object")
        hero_index = item.get("hero", item.get("hero_index"))
        if not isinstance(hero_index, int) or hero_index <= 0:
            raise ValueError(f"Manifest heroes[{index}] has invalid hero index: {hero_index}")

        set_obj = item.get("set", {})
        expect_obj = item.get("expect", {})
        if not isinstance(set_obj, dict) or not isinstance(expect_obj, dict):
            raise ValueError(f"Manifest heroes[{index}] requires object keys 'set' and 'expect'")

        updates = _parse_hero_key_values(_pairs_from_mapping(set_obj))
        expected = _parse_hero_key_values(_pairs_from_mapping(expect_obj))
        if not updates:
            continue

        hero_updates.append(
            {
                "hero_index": hero_index,
                "updates": updates,
                "expected": expected,
            }
        )

    return {
        "wallet_updates": wallet_updates,
        "wallet_expected": wallet_expected,
        "hero_updates": hero_updates,
        "upgrades_updates": upgrades_updates,
        "upgrades_expected": upgrades_expected,
        "game_updates": game_updates,
        "game_expected": game_expected,
        "loading_updates": loading_updates,
        "loading_expected": loading_expected,
        "options_updates": options_updates,
        "options_expected": options_expected,
        "raid_updates": raid_updates,
        "raid_expected": raid_expected,
    }


def _collect_validation_issues(
    *,
    parsed_estate,
    parsed_roster,
    parsed_upgrades,
    parsed_map,
    parsed_game,
    parsed_raid,
    parsed_tutorial,
    parsed_narration,
    parsed_loading,
    parsed_options=None,
) -> list:
    issues = []
    issues.extend(validate_estate_wallet(parsed_estate))
    issues.extend(validate_upgrades_structure(parsed_upgrades))
    issues.extend(validate_map_structure(parsed_map))
    issues.extend(validate_game_structure(parsed_game))
    issues.extend(validate_raid_structure(parsed_raid))
    issues.extend(validate_tutorial_structure(parsed_tutorial))
    issues.extend(validate_narration_structure(parsed_narration))
    issues.extend(validate_loading_screen_structure(parsed_loading))
    if parsed_options is not None:
        issues.extend(validate_options_structure(parsed_options))
    issues.extend(validate_estate_roster_consistency(parsed_estate, parsed_roster))
    issues.extend(validate_roster_upgrades_consistency(parsed_roster, parsed_upgrades))
    issues.extend(validate_roster_map_consistency(parsed_roster, parsed_map))
    return issues


def _build_snapshot(
    *,
    profile: Path,
    estate_path: Path,
    roster_path: Path,
    upgrades_path: Path,
    map_path: Path,
    game_path: Path,
    raid_path: Path,
    tutorial_path: Path,
    narration_path: Path,
    loading_path: Path,
    options_path: Path,
    estate_codec: EstateSaveCodec,
    roster_codec: RosterSaveCodec,
    upgrades_codec: UpgradesSaveCodec,
    map_codec: MapSaveCodec,
    game_codec: GameSaveCodec,
    raid_codec: RaidSaveCodec,
    tutorial_codec: TutorialSaveCodec,
    narration_codec: NarrationSaveCodec,
    loading_codec: LoadingScreenSaveCodec,
    options_codec: OptionsSaveCodec,
) -> dict[str, object]:
    parsed_estate = estate_codec.parse(estate_path)
    parsed_roster = roster_codec.parse(roster_path)
    parsed_upgrades = upgrades_codec.parse(upgrades_path)
    parsed_map = map_codec.parse(map_path)
    parsed_game = game_codec.parse(game_path)
    parsed_raid = raid_codec.parse(raid_path)
    parsed_tutorial = tutorial_codec.parse(tutorial_path)
    parsed_narration = narration_codec.parse(narration_path)
    parsed_loading = loading_codec.parse(loading_path)
    parsed_options = options_codec.parse(options_path) if options_path.exists() else None

    issues = _collect_validation_issues(
        parsed_estate=parsed_estate,
        parsed_roster=parsed_roster,
        parsed_upgrades=parsed_upgrades,
        parsed_map=parsed_map,
        parsed_game=parsed_game,
        parsed_raid=parsed_raid,
        parsed_tutorial=parsed_tutorial,
        parsed_narration=parsed_narration,
        parsed_loading=parsed_loading,
        parsed_options=parsed_options,
    )

    return {
        "profile": str(profile),
        "files": {
            "estate": str(estate_path),
            "roster": str(roster_path),
            "upgrades": str(upgrades_path),
            "map": str(map_path),
            "game": str(game_path),
            "raid": str(raid_path),
            "tutorial": str(tutorial_path),
            "narration": str(narration_path),
            "loading_screen": str(loading_path),
            "options": str(options_path) if options_path.exists() else None,
        },
        "wallet": dict(_list_wallet(estate_codec, estate_path)),
        "heroes": extract_hero_summary(parsed_roster),
        "upgrades": extract_upgrades_summary(parsed_upgrades),
        "map": extract_map_summary(parsed_map),
        "game": extract_game_summary(parsed_game),
        "raid": extract_raid_summary(parsed_raid),
        "tutorial": extract_tutorial_summary(parsed_tutorial),
        "narration": extract_narration_summary(parsed_narration),
        "loading_screen": extract_loading_screen_summary(parsed_loading),
        "options": extract_options_summary(parsed_options) if parsed_options is not None else None,
        "validation": [
            {
                "code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "file_name": issue.file_name,
                "field_path": issue.field_path,
            }
            for issue in issues
        ],
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    profile = Path(args.profile).expanduser().resolve()
    estate_path = _estate_path(profile)
    roster_path = _roster_path(profile)
    upgrades_path = _upgrades_path(profile)
    map_path = _map_path(profile)
    game_path = _game_path(profile)
    raid_path = _raid_path(profile)
    tutorial_path = _tutorial_path(profile)
    narration_path = _narration_path(profile)
    loading_path = _loading_path(profile)
    options_path = _options_path(profile, args.options_file)

    estate_codec = EstateSaveCodec()
    roster_codec = RosterSaveCodec()
    upgrades_codec = UpgradesSaveCodec()
    map_codec = MapSaveCodec()
    game_codec = GameSaveCodec()
    raid_codec = RaidSaveCodec()
    tutorial_codec = TutorialSaveCodec()
    narration_codec = NarrationSaveCodec()
    loading_codec = LoadingScreenSaveCodec()
    options_codec = OptionsSaveCodec()

    try:
        if args.command == "doctor":
            if not profile.exists() or not profile.is_dir():
                raise FileNotFoundError(f"Profile not found: {profile}")

            required_files = [
                estate_path,
                roster_path,
                upgrades_path,
                map_path,
                game_path,
                raid_path,
                tutorial_path,
                narration_path,
                loading_path,
            ]
            for path in required_files:
                if not path.exists():
                    raise FileNotFoundError(f"Missing required file: {path}")

            wallet = _list_wallet(estate_codec, estate_path)
            heroes = extract_hero_summary(roster_codec.parse(roster_path))
            upgrades = extract_upgrades_summary(upgrades_codec.parse(upgrades_path))
            map_summary = extract_map_summary(map_codec.parse(map_path))
            game_summary = extract_game_summary(game_codec.parse(game_path))
            raid_summary = extract_raid_summary(raid_codec.parse(raid_path))
            tutorial_summary = extract_tutorial_summary(tutorial_codec.parse(tutorial_path))
            narration_summary = extract_narration_summary(narration_codec.parse(narration_path))
            loading_summary = extract_loading_screen_summary(loading_codec.parse(loading_path))
            options_summary = None
            if options_path.exists():
                options_summary = extract_options_summary(options_codec.parse(options_path))

            print(f"[ok] profile={profile}")
            print(f"[ok] estate={estate_path}")
            print(f"[ok] roster={roster_path}")
            print(f"[ok] upgrades={upgrades_path}")
            print(f"[ok] map={map_path}")
            print(f"[ok] game={game_path}")
            print(f"[ok] raid={raid_path}")
            print(f"[ok] tutorial={tutorial_path}")
            print(f"[ok] narration={narration_path}")
            print(f"[ok] loading={loading_path}")
            print(f"[ok] wallet_entries={len(wallet)}")
            print(f"[ok] heroes={len(heroes)}")
            print(f"[ok] upgrades_purchases={upgrades.get('purchases_count')}")
            print(f"[ok] map_areas={map_summary.get('areas_count')}")
            print(f"[ok] game_inraid={game_summary.get('inraid')}")
            print(f"[ok] raid_inbattle={raid_summary.get('inbattle')}")
            print(f"[ok] tutorial_dispatched_events={tutorial_summary.get('dispatched_events_count')}")
            print(f"[ok] narration_entries={narration_summary.get('entry_type_count')}")
            print(f"[ok] loading_tip_id={loading_summary.get('tip_id')}")
            if options_summary is not None:
                print(f"[ok] options={options_path}")
                print(f"[ok] options_language={options_summary.get('language')}")
            else:
                print(f"[warning] options file not found: {options_path}")
            return 0

        if args.command == "list-wallet":
            wallet = _list_wallet(estate_codec, estate_path)
            for key, value in wallet:
                print(f"{key}={value}")
            return 0

        if args.command == "list-heroes":
            summary = extract_hero_summary(roster_codec.parse(roster_path))
            for item in summary:
                idx = item.get("hero_index")
                name = item.get("name") or "unknown"
                hero_class = item.get("class") or "unknown"
                resolve = item.get("resolve_xp")
                print(f"{idx}: {name} ({hero_class}) resolve_xp={resolve}")
            return 0

        if args.command == "list-upgrades":
            summary = extract_upgrades_summary(upgrades_codec.parse(upgrades_path))
            print(f"purchases_count={summary.get('purchases_count')}")
            print(f"discounts_count={summary.get('discounts_count')}")
            print(f"purchased_count={summary.get('purchased_count')}")
            classes = summary.get("classes", {})
            if isinstance(classes, dict):
                for cls, count in classes.items():
                    print(f"class.{cls}.purchases={count}")
            return 0

        if args.command == "list-map":
            summary = extract_map_summary(map_codec.parse(map_path))
            print(f"areas_count={summary.get('areas_count')}")
            print(f"tiles_count={summary.get('tiles_count')}")
            print(f"doors_count={summary.get('doors_count')}")
            area_ids = summary.get("area_ids", [])
            if isinstance(area_ids, list):
                print("area_ids=" + ",".join(str(x) for x in area_ids))
            return 0

        if args.command == "list-game":
            summary = extract_game_summary(game_codec.parse(game_path))
            print(f"version={summary.get('version')}")
            print(f"total_elapsed={summary.get('total_elapsed')}")
            print(f"inraid={summary.get('inraid')}")
            print(f"dd_options_altered={summary.get('dd_options_altered')}")
            print(f"estate_name={summary.get('estate_name')}")
            print(f"mode={summary.get('mode')}")
            print(f"date_time={summary.get('date_time')}")
            return 0

        if args.command == "list-raid":
            summary = extract_raid_summary(raid_codec.parse(raid_path))
            print(f"version={summary.get('version')}")
            print(f"torchlight={summary.get('torchlight')}")
            print(f"inbattle={summary.get('inbattle')}")
            print(f"teleported={summary.get('teleported')}")
            print(f"has_mash_data={summary.get('has_mash_data')}")
            print(f"implied={summary.get('implied')}")
            print(f"is_plot_quest={summary.get('is_plot_quest')}")
            print(f"counted_in_generation={summary.get('counted_in_generation')}")
            print(f"use_default_progression_goals={summary.get('use_default_progression_goals')}")
            print(f"is_from_town_event={summary.get('is_from_town_event')}")
            return 0

        if args.command == "list-tutorial":
            summary = extract_tutorial_summary(tutorial_codec.parse(tutorial_path))
            print(f"version={summary.get('version')}")
            print(f"dispatched_events_count={summary.get('dispatched_events_count')}")
            return 0

        if args.command == "list-narration":
            summary = extract_narration_summary(narration_codec.parse(narration_path))
            print(f"version={summary.get('version')}")
            print(f"entry_type_count={summary.get('entry_type_count')}")
            print(f"audio_event_type_count={summary.get('audio_event_type_count')}")
            print(f"vo_path_count={summary.get('vo_path_count')}")
            print(f"raid_entry_log_present={summary.get('raid_entry_log_present')}")
            print(f"town_visit_entry_log_present={summary.get('town_visit_entry_log_present')}")
            print(f"campaign_entry_log_present={summary.get('campaign_entry_log_present')}")
            return 0

        if args.command == "list-loading-screen":
            summary = extract_loading_screen_summary(loading_codec.parse(loading_path))
            print(f"version={summary.get('version')}")
            print(f"background_texture_path={summary.get('background_texture_path')}")
            print(f"title_id={summary.get('title_id')}")
            print(f"tip_id={summary.get('tip_id')}")
            print(f"narration_entry_id={summary.get('narration_entry_id')}")
            print(
                "narration_audio_event_queue_tags_count="
                f"{summary.get('narration_audio_event_queue_tags_count')}"
            )
            return 0

        if args.command == "list-options":
            if not options_path.exists():
                raise FileNotFoundError(f"Options file not found: {options_path}")
            summary = extract_options_summary(options_codec.parse(options_path))
            print(f"version={summary.get('version')}")
            print(f"language={summary.get('language')}")
            print(f"subtitles={summary.get('subtitles')}")
            print(f"fullscreen={summary.get('fullscreen')}")
            print(f"tutorial={summary.get('tutorial')}")
            print(f"allow_analytics_and_multiplayer={summary.get('allow_analytics_and_multiplayer')}")
            print(f"resolution_width={summary.get('resolution_width')}")
            print(f"resolution_height={summary.get('resolution_height')}")
            return 0

        if args.command == "validate":
            parsed_estate = estate_codec.parse(estate_path)
            parsed_roster = roster_codec.parse(roster_path)
            parsed_upgrades = upgrades_codec.parse(upgrades_path)
            parsed_map = map_codec.parse(map_path)
            parsed_game = game_codec.parse(game_path)
            parsed_raid = raid_codec.parse(raid_path)
            parsed_tutorial = tutorial_codec.parse(tutorial_path)
            parsed_narration = narration_codec.parse(narration_path)
            parsed_loading = loading_codec.parse(loading_path)
            parsed_options = options_codec.parse(options_path) if options_path.exists() else None

            issues = _collect_validation_issues(
                parsed_estate=parsed_estate,
                parsed_roster=parsed_roster,
                parsed_upgrades=parsed_upgrades,
                parsed_map=parsed_map,
                parsed_game=parsed_game,
                parsed_raid=parsed_raid,
                parsed_tutorial=parsed_tutorial,
                parsed_narration=parsed_narration,
                parsed_loading=parsed_loading,
                parsed_options=parsed_options,
            )

            return _print_validation_issues(issues, strict=args.strict)

        if args.command == "inspect":
            snapshot = _build_snapshot(
                profile=profile,
                estate_path=estate_path,
                roster_path=roster_path,
                upgrades_path=upgrades_path,
                map_path=map_path,
                game_path=game_path,
                raid_path=raid_path,
                tutorial_path=tutorial_path,
                narration_path=narration_path,
                loading_path=loading_path,
                options_path=options_path,
                estate_codec=estate_codec,
                roster_codec=roster_codec,
                upgrades_codec=upgrades_codec,
                map_codec=map_codec,
                game_codec=game_codec,
                raid_codec=raid_codec,
                tutorial_codec=tutorial_codec,
                narration_codec=narration_codec,
                loading_codec=loading_codec,
                options_codec=options_codec,
            )
            print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
            return 0

        if args.command == "list-presets":
            for preset in list_presets():
                flags = []
                if preset.supports_hero_index:
                    flags.append("hero")
                if preset.supports_resolve_xp:
                    flags.append("resolve_xp")
                suffix = f" [{','.join(flags)}]" if flags else ""
                print(f"{preset.name}{suffix} - {preset.description}")
            return 0

        if args.command == "export":
            snapshot = _build_snapshot(
                profile=profile,
                estate_path=estate_path,
                roster_path=roster_path,
                upgrades_path=upgrades_path,
                map_path=map_path,
                game_path=game_path,
                raid_path=raid_path,
                tutorial_path=tutorial_path,
                narration_path=narration_path,
                loading_path=loading_path,
                options_path=options_path,
                estate_codec=estate_codec,
                roster_codec=roster_codec,
                upgrades_codec=upgrades_codec,
                map_codec=map_codec,
                game_codec=game_codec,
                raid_codec=raid_codec,
                tutorial_codec=tutorial_codec,
                narration_codec=narration_codec,
                loading_codec=loading_codec,
                options_codec=options_codec,
            )
            output_path = Path(args.output).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(f"[ok] export={output_path}")
            return 0

        if args.command == "import":
            manifest_path = Path(args.file).expanduser().resolve()
            manifest_payload = _parse_manifest_payload(manifest_path)
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_manifest_patch(
                profile,
                manifest_payload,
                options_path=options_path,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                allow_inbattle=args.allow_inbattle,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        if args.command == "apply-preset":
            manifest_payload = build_manifest_for_preset(
                name=args.name,
                hero_index=args.hero,
                resolve_xp=args.resolve_xp,
            )
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_manifest_patch(
                profile,
                manifest_payload,
                options_path=options_path,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                allow_inbattle=args.allow_inbattle,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            print(f"{tag} preset={args.name}")
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        if args.command == "backup":
            backup_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            backup_path = backup_engine.create_backup(profile)
            print(f"[ok] backup={backup_path}")
            return 0

        if args.command == "list-backups":
            backup_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            backups = backup_engine.list_backups(profile.name)
            limit = max(0, int(args.limit))
            selected = backups[:limit] if limit > 0 else backups
            print(f"[ok] backups={len(backups)} profile={profile.name} root={backup_engine.backup_root}")
            for item in selected:
                print(item)
            return 0

        if args.command == "restore":
            backup_root = Path(args.backup_dir).expanduser().resolve()
            backup_path = _resolve_backup_path(
                backup_root=backup_root,
                profile_name=profile.name,
                from_backup=args.from_backup,
                latest=args.latest,
            )
            patch_engine = PatchEngine(backup_root=backup_root)
            safety = patch_engine.restore_backup(
                profile,
                backup_path,
                create_safety_backup=not args.no_safety_backup,
            )
            print(f"[ok] restored_from={backup_path}")
            if safety is not None:
                print(f"[note] safety_backup={safety}")
            return 0

        if args.command == "diff":
            backup_root = Path(args.backup_dir).expanduser().resolve()
            backup_path = _resolve_backup_path(
                backup_root=backup_root,
                profile_name=profile.name,
                from_backup=args.from_backup,
                latest=args.latest,
            )
            changed_files = 0
            compared = 0
            for name in _profile_files_for_diff():
                current_file = profile / name
                backup_file = backup_path / name

                if not current_file.exists() and not backup_file.exists():
                    print(f"[skip] {name} missing_in_both")
                    continue
                if not current_file.exists():
                    changed_files += 1
                    print(f"[diff] {name} missing_in_current")
                    continue
                if not backup_file.exists():
                    changed_files += 1
                    print(f"[diff] {name} missing_in_backup")
                    continue

                compared += 1
                left = backup_file.read_bytes()
                right = current_file.read_bytes()
                changed_bytes, first_diff = _byte_diff_stats(left, right)
                if changed_bytes == 0:
                    print(f"[same] {name}")
                    continue

                changed_files += 1
                print(
                    f"[diff] {name} changed_bytes={changed_bytes} "
                    f"backup_size={len(left)} current_size={len(right)} first_diff={first_diff}"
                )

            print(f"[ok] compared={compared} changed_files={changed_files} backup={backup_path}")
            return 0

        if args.command == "patch-wallet":
            updates = _parse_key_values(args.set)
            expected = _parse_key_values(args.expect)
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_wallet_patch(
                profile,
                updates=updates,
                expected=expected,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        if args.command == "patch-hero":
            updates = _parse_hero_key_values(args.set)
            expected = _parse_hero_key_values(args.expect)
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_hero_patch(
                profile,
                hero_index=args.hero,
                updates=updates,
                expected=expected,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        if args.command == "patch-upgrades":
            updates = _parse_upgrades_key_values(args.set)
            expected = _parse_upgrades_key_values(args.expect)
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_upgrades_patch(
                profile,
                updates=updates,
                expected=expected,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        if args.command == "patch-game":
            updates = _parse_game_key_values(args.set)
            expected = _parse_game_key_values(args.expect)
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_game_patch(
                profile,
                updates=updates,
                expected=expected,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        if args.command == "patch-loading":
            updates = _parse_loading_key_values(args.set)
            expected = _parse_loading_key_values(args.expect)
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_loading_patch(
                profile,
                updates=updates,
                expected=expected,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        if args.command == "patch-raid":
            updates = _parse_raid_key_values(args.set)
            expected = _parse_raid_key_values(args.expect)
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_raid_patch(
                profile,
                updates=updates,
                expected=expected,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                allow_inbattle=args.allow_inbattle,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        if args.command == "patch-options":
            updates = _parse_options_key_values(args.set)
            expected = _parse_options_key_values(args.expect)
            patch_engine = PatchEngine(backup_root=Path(args.backup_dir).expanduser().resolve())
            result = patch_engine.apply_options_patch(
                profile,
                updates=updates,
                expected=expected,
                options_path=options_path,
                dry_run=args.dry_run,
                skip_backup=args.skip_backup,
                strict_validation=args.strict,
            )
            tag = "[dry-run]" if args.dry_run else "[ok]"
            for op in result.operations:
                print(f"{tag} {op.key}: -> {op.new_value}")
            for note in result.notes:
                print(f"[note] {note}")
            return 0

        return 2
    except FileNotFoundError as exc:
        print(f"[error] File not found: {exc}")
        print("[hint] Check if the profile path is correct and the save files exist")
        print("[hint] Default profile: ~/Library/Application Support/Darkest/profile_1")
        return 2
    except PatchEngineError as exc:
        error_msg = str(exc).lower()
        print(f"[error] {exc}")
        
        if "inbattle" in error_msg:
            print("[warning] Active raid detected! Modifying raid while in battle can corrupt your save.")
            print("[hint] Use --allow-inbattle flag if you really want to proceed")
            print("[hint] Or exit to main menu first to ensure raid.inbattle=0")
        elif "validation failed" in error_msg:
            print("[warning] Changes would make the save inconsistent")
            print("[hint] Use --strict to treat warnings as errors")
            print("[hint] Or use --dry-run to preview changes without applying")
        elif "current mismatch" in error_msg:
            print("[warning] The current value doesn't match your --expect guard")
            print("[hint] Run list-* command to see current values")
            print("[hint] Or remove --expect to skip the guard check")
        elif "manifest" in error_msg:
            print("[hint] Check manifest JSON structure")
            print("[hint] Required sections: wallet, heroes, upgrades, game, loading, raid (optional)")
        return 2
    except (
        ValueError,
        EstateCodecError,
        RosterCodecError,
        UpgradesCodecError,
        MapCodecError,
        GameCodecError,
        RaidCodecError,
        TutorialCodecError,
        NarrationCodecError,
        LoadingScreenCodecError,
        OptionsCodecError,
        OptionsPatchError,
        PresetError,
    ) as exc:
        print(f"[error] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
