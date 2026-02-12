from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Set

from core.codec.contracts import ParsedSaveFile


@dataclass(slots=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    file_name: str | None = None
    field_path: str | None = None


def validate_ranges(pairs: Iterable[tuple[str, int]], low: int, high: int) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for name, value in pairs:
        if value < low or value > high:
            issues.append(
                ValidationIssue(
                    code="OUT_OF_RANGE",
                    severity="error",
                    message=f"{name}={value} outside [{low}, {high}]",
                    field_path=name,
                )
            )
    return issues


def validate_estate_wallet(parsed_estate: ParsedSaveFile) -> List[ValidationIssue]:
    required = ["gold", "bust", "portrait", "deed", "crest"]
    issues: List[ValidationIssue] = []

    for key in required:
        path = f"wallet.{key}.amount"
        field = parsed_estate.fields.get(path)
        if field is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD",
                    severity="error",
                    message=f"Missing required wallet field: {path}",
                    file_name=parsed_estate.file_name,
                    field_path=path,
                )
            )
            continue

        if not isinstance(field.value, int):
            issues.append(
                ValidationIssue(
                    code="TYPE_MISMATCH",
                    severity="error",
                    message=f"Wallet field must be int: {path}",
                    file_name=parsed_estate.file_name,
                    field_path=path,
                )
            )
            continue

        if field.value < 0 or field.value > 0xFFFFFFFF:
            issues.append(
                ValidationIssue(
                    code="OUT_OF_RANGE",
                    severity="error",
                    message=f"Wallet field outside u32 range: {path}={field.value}",
                    file_name=parsed_estate.file_name,
                    field_path=path,
                )
            )

    return issues


def validate_upgrades_structure(parsed_upgrades: ParsedSaveFile) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    version = parsed_upgrades.fields.get("upgrades.version")
    if version is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="error",
                message="Missing upgrades.version",
                file_name=parsed_upgrades.file_name,
                field_path="upgrades.version",
            )
        )
    elif not isinstance(version.value, int):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="upgrades.version must be int",
                file_name=parsed_upgrades.file_name,
                field_path="upgrades.version",
            )
        )

    purchases = parsed_upgrades.fields.get("upgrades.purchases.count")
    if purchases is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="error",
                message="Missing upgrades.purchases.count",
                file_name=parsed_upgrades.file_name,
                field_path="upgrades.purchases.count",
            )
        )
    elif not isinstance(purchases.value, int) or purchases.value < 0:
        issues.append(
            ValidationIssue(
                code="OUT_OF_RANGE",
                severity="error",
                message=f"Invalid upgrades.purchases.count={purchases.value}",
                file_name=parsed_upgrades.file_name,
                field_path="upgrades.purchases.count",
            )
        )

    return issues


def validate_map_structure(parsed_map: ParsedSaveFile) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    def get_int(path: str) -> int | None:
        field = parsed_map.fields.get(path)
        if field is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD",
                    severity="error",
                    message=f"Missing {path}",
                    file_name=parsed_map.file_name,
                    field_path=path,
                )
            )
            return None
        if not isinstance(field.value, int):
            issues.append(
                ValidationIssue(
                    code="TYPE_MISMATCH",
                    severity="error",
                    message=f"{path} must be int",
                    file_name=parsed_map.file_name,
                    field_path=path,
                )
            )
            return None
        return field.value

    areas = get_int("map.areas.count")
    tiles = get_int("map.tiles.count")
    doors = get_int("map.doors.count")

    if areas is not None and areas <= 0:
        issues.append(
            ValidationIssue(
                code="EMPTY_MAP_AREAS",
                severity="error",
                message="map.areas.count must be > 0",
                file_name=parsed_map.file_name,
                field_path="map.areas.count",
            )
        )

    if tiles is not None and tiles <= 0:
        issues.append(
            ValidationIssue(
                code="EMPTY_MAP_TILES",
                severity="error",
                message="map.tiles.count must be > 0",
                file_name=parsed_map.file_name,
                field_path="map.tiles.count",
            )
        )

    if doors is not None and doors <= 0:
        issues.append(
            ValidationIssue(
                code="MAP_NO_DOORS",
                severity="warning",
                message="map.doors.count is 0",
                file_name=parsed_map.file_name,
                field_path="map.doors.count",
            )
        )

    return issues


def validate_game_structure(parsed_game: ParsedSaveFile) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    required_int_fields = [
        ("game.version", 0, 1_000_000),
        ("game.inraid", 0, 1),
        ("game.dd_options_altered", 0, 1),
    ]
    for path, low, high in required_int_fields:
        field = parsed_game.fields.get(path)
        if field is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD",
                    severity="error",
                    message=f"Missing {path}",
                    file_name=parsed_game.file_name,
                    field_path=path,
                )
            )
            continue
        if not isinstance(field.value, int):
            issues.append(
                ValidationIssue(
                    code="TYPE_MISMATCH",
                    severity="error",
                    message=f"{path} must be int",
                    file_name=parsed_game.file_name,
                    field_path=path,
                )
            )
            continue
        if field.value < low or field.value > high:
            issues.append(
                ValidationIssue(
                    code="OUT_OF_RANGE",
                    severity="error",
                    message=f"{path}={field.value} outside [{low}, {high}]",
                    file_name=parsed_game.file_name,
                    field_path=path,
                )
            )

    total_elapsed = parsed_game.fields.get("game.total_elapsed")
    if total_elapsed is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="error",
                message="Missing game.total_elapsed",
                file_name=parsed_game.file_name,
                field_path="game.total_elapsed",
            )
        )
    elif not isinstance(total_elapsed.value, (int, float)):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="game.total_elapsed must be float-compatible",
                file_name=parsed_game.file_name,
                field_path="game.total_elapsed",
            )
        )
    elif float(total_elapsed.value) < -1.0:
        issues.append(
            ValidationIssue(
                code="OUT_OF_RANGE",
                severity="error",
                message=f"game.total_elapsed={total_elapsed.value} below -1.0",
                file_name=parsed_game.file_name,
                field_path="game.total_elapsed",
            )
        )

    for path in ["game.estate_name", "game.mode", "game.date_time"]:
        field = parsed_game.fields.get(path)
        if field is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD",
                    severity="warning",
                    message=f"Missing optional {path}",
                    file_name=parsed_game.file_name,
                    field_path=path,
                )
            )
            continue

        if not isinstance(field.value, str):
            issues.append(
                ValidationIssue(
                    code="TYPE_MISMATCH",
                    severity="warning",
                    message=f"{path} should be string",
                    file_name=parsed_game.file_name,
                    field_path=path,
                )
            )
            continue

        if path == "game.date_time" and field.value:
            date_pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
            if not re.match(date_pattern, field.value):
                issues.append(
                    ValidationIssue(
                        code="DATE_FORMAT_SUSPECT",
                        severity="warning",
                        message=f"game.date_time has unexpected format: {field.value}",
                        file_name=parsed_game.file_name,
                        field_path=path,
                    )
                )

    return issues


def validate_raid_structure(parsed_raid: ParsedSaveFile) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    bool_paths = [
        "raid.inbattle",
        "raid.teleported",
        "raid.has_mash_data",
        "raid.implied",
    ]
    for path in bool_paths:
        field = parsed_raid.fields.get(path)
        if field is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD",
                    severity="error",
                    message=f"Missing {path}",
                    file_name=parsed_raid.file_name,
                    field_path=path,
                )
            )
            continue
        if not isinstance(field.value, int):
            issues.append(
                ValidationIssue(
                    code="TYPE_MISMATCH",
                    severity="error",
                    message=f"{path} must be int",
                    file_name=parsed_raid.file_name,
                    field_path=path,
                )
            )
            continue
        if field.value not in (0, 1):
            issues.append(
                ValidationIssue(
                    code="OUT_OF_RANGE",
                    severity="error",
                    message=f"{path} must be 0/1, found {field.value}",
                    file_name=parsed_raid.file_name,
                    field_path=path,
                )
            )

    torchlight = parsed_raid.fields.get("raid.torchlight")
    if torchlight is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="warning",
                message="Missing raid.torchlight",
                file_name=parsed_raid.file_name,
                field_path="raid.torchlight",
            )
        )
    elif not isinstance(torchlight.value, (int, float)):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="raid.torchlight must be float-compatible",
                file_name=parsed_raid.file_name,
                field_path="raid.torchlight",
            )
        )
    else:
        val = float(torchlight.value)
        if val < 0.0 or val > 200.0:
            issues.append(
                ValidationIssue(
                    code="OUT_OF_RANGE",
                    severity="warning",
                    message=f"raid.torchlight outside typical range [0, 200]: {val}",
                    file_name=parsed_raid.file_name,
                    field_path="raid.torchlight",
                )
            )

    return issues


def validate_tutorial_structure(parsed_tutorial: ParsedSaveFile) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    version = parsed_tutorial.fields.get("tutorial.version")
    if version is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="error",
                message="Missing tutorial.version",
                file_name=parsed_tutorial.file_name,
                field_path="tutorial.version",
            )
        )
    elif not isinstance(version.value, int):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="tutorial.version must be int",
                file_name=parsed_tutorial.file_name,
                field_path="tutorial.version",
            )
        )

    dispatched = parsed_tutorial.fields.get("tutorial.dispatched_events.count")
    if dispatched is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="warning",
                message="Missing tutorial.dispatched_events.count",
                file_name=parsed_tutorial.file_name,
                field_path="tutorial.dispatched_events.count",
            )
        )
    elif not isinstance(dispatched.value, int):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="tutorial.dispatched_events.count must be int",
                file_name=parsed_tutorial.file_name,
                field_path="tutorial.dispatched_events.count",
            )
        )
    elif dispatched.value < 0:
        issues.append(
            ValidationIssue(
                code="OUT_OF_RANGE",
                severity="error",
                message=f"tutorial.dispatched_events.count invalid: {dispatched.value}",
                file_name=parsed_tutorial.file_name,
                field_path="tutorial.dispatched_events.count",
            )
        )

    return issues


def validate_narration_structure(parsed_narration: ParsedSaveFile) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    version = parsed_narration.fields.get("narration.version")
    if version is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="error",
                message="Missing narration.version",
                file_name=parsed_narration.file_name,
                field_path="narration.version",
            )
        )
    elif not isinstance(version.value, int):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="narration.version must be int",
                file_name=parsed_narration.file_name,
                field_path="narration.version",
            )
        )

    for path in [
        "narration.entry_type.count",
        "narration.audio_event_type.count",
        "narration.vo_path.count",
    ]:
        field = parsed_narration.fields.get(path)
        if field is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD",
                    severity="warning",
                    message=f"Missing {path}",
                    file_name=parsed_narration.file_name,
                    field_path=path,
                )
            )
            continue
        if not isinstance(field.value, int):
            issues.append(
                ValidationIssue(
                    code="TYPE_MISMATCH",
                    severity="error",
                    message=f"{path} must be int",
                    file_name=parsed_narration.file_name,
                    field_path=path,
                )
            )
            continue
        if field.value < 0:
            issues.append(
                ValidationIssue(
                    code="OUT_OF_RANGE",
                    severity="error",
                    message=f"{path} invalid: {field.value}",
                    file_name=parsed_narration.file_name,
                    field_path=path,
                )
            )

    return issues


def validate_loading_screen_structure(parsed_loading: ParsedSaveFile) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    required_ints = [
        "loading.version",
        "loading.title_id",
        "loading.tip_id",
        "loading.narration_entry_id",
        "loading.narration_audio_event_queue_tags.count",
    ]
    for path in required_ints:
        field = parsed_loading.fields.get(path)
        if field is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD",
                    severity="error",
                    message=f"Missing {path}",
                    file_name=parsed_loading.file_name,
                    field_path=path,
                )
            )
            continue
        if not isinstance(field.value, int):
            issues.append(
                ValidationIssue(
                    code="TYPE_MISMATCH",
                    severity="error",
                    message=f"{path} must be int",
                    file_name=parsed_loading.file_name,
                    field_path=path,
                )
            )

    texture = parsed_loading.fields.get("loading.background_texture_path")
    if texture is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="warning",
                message="Missing loading.background_texture_path",
                file_name=parsed_loading.file_name,
                field_path="loading.background_texture_path",
            )
        )
    elif not isinstance(texture.value, str):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="loading.background_texture_path must be string",
                file_name=parsed_loading.file_name,
                field_path="loading.background_texture_path",
            )
        )

    return issues


def validate_options_structure(parsed_options: ParsedSaveFile) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    version = parsed_options.fields.get("options.version")
    if version is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="error",
                message="Missing options.version",
                file_name=parsed_options.file_name,
                field_path="options.version",
            )
        )
    elif not isinstance(version.value, int):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="options.version must be int",
                file_name=parsed_options.file_name,
                field_path="options.version",
            )
        )

    language = parsed_options.fields.get("options.language")
    if language is None:
        issues.append(
            ValidationIssue(
                code="MISSING_FIELD",
                severity="warning",
                message="Missing options.language",
                file_name=parsed_options.file_name,
                field_path="options.language",
            )
        )
    elif not isinstance(language.value, str):
        issues.append(
            ValidationIssue(
                code="TYPE_MISMATCH",
                severity="error",
                message="options.language must be string",
                file_name=parsed_options.file_name,
                field_path="options.language",
            )
        )

    for path in ["options.resolution.width", "options.resolution.height"]:
        field = parsed_options.fields.get(path)
        if field is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD",
                    severity="warning",
                    message=f"Missing {path}",
                    file_name=parsed_options.file_name,
                    field_path=path,
                )
            )
            continue
        if not isinstance(field.value, int):
            issues.append(
                ValidationIssue(
                    code="TYPE_MISMATCH",
                    severity="error",
                    message=f"{path} must be int",
                    file_name=parsed_options.file_name,
                    field_path=path,
                )
            )
            continue
        if field.value <= 0:
            issues.append(
                ValidationIssue(
                    code="OUT_OF_RANGE",
                    severity="warning",
                    message=f"{path} is non-positive: {field.value}",
                    file_name=parsed_options.file_name,
                    field_path=path,
                )
            )

    return issues


def validate_estate_roster_consistency(
    parsed_estate: ParsedSaveFile,
    parsed_roster: ParsedSaveFile,
) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    hero_indexes = sorted(
        {
            int(match.group(1))
            for path in parsed_roster.fields
            for match in [re.match(r"^roster\.heroes\.(\d+)\.", path)]
            if match
        }
    )

    if not hero_indexes:
        issues.append(
            ValidationIssue(
                code="NO_HEROES",
                severity="error",
                message="Roster has no parsed heroes",
                file_name=parsed_roster.file_name,
            )
        )

    gold_field = parsed_estate.fields.get("wallet.gold.amount")
    if gold_field and isinstance(gold_field.value, int):
        if gold_field.value == 0:
            issues.append(
                ValidationIssue(
                    code="ZERO_GOLD",
                    severity="warning",
                    message="Gold is 0 (may be intentional, but often indicates early-game or edge state)",
                    file_name=parsed_estate.file_name,
                    field_path="wallet.gold.amount",
                )
            )

    if len(hero_indexes) > 200:
        issues.append(
            ValidationIssue(
                code="HERO_COUNT_SUSPICIOUS",
                severity="warning",
                message=f"Parsed hero count looks suspiciously high: {len(hero_indexes)}",
                file_name=parsed_roster.file_name,
            )
        )

    return issues


def validate_roster_upgrades_consistency(
    parsed_roster: ParsedSaveFile,
    parsed_upgrades: ParsedSaveFile,
) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    roster_classes: Set[str] = {
        str(field.value)
        for path, field in parsed_roster.fields.items()
        if path.endswith(".class") and isinstance(field.value, str)
    }

    upgrade_classes: Set[str] = {
        path.split(".")[3]
        for path in parsed_upgrades.fields
        if path.startswith("upgrades.purchases.classes.") and path.endswith(".count")
    }

    if not upgrade_classes:
        issues.append(
            ValidationIssue(
                code="NO_UPGRADE_CLASSES",
                severity="warning",
                message="No upgrade classes detected",
                file_name=parsed_upgrades.file_name,
            )
        )
        return issues

    for cls in sorted(upgrade_classes - roster_classes):
        issues.append(
            ValidationIssue(
                code="UPGRADE_CLASS_NOT_IN_ROSTER",
                severity="warning",
                message=f"Upgrade class '{cls}' not found in roster classes",
                file_name=parsed_upgrades.file_name,
                field_path=f"upgrades.purchases.classes.{cls}.count",
            )
        )

    for cls in sorted(roster_classes - upgrade_classes):
        issues.append(
            ValidationIssue(
                code="ROSTER_CLASS_WITHOUT_UPGRADES",
                severity="warning",
                message=f"Roster class '{cls}' has no upgrades entries",
                file_name=parsed_roster.file_name,
            )
        )

    return issues


def validate_roster_map_consistency(
    parsed_roster: ParsedSaveFile,
    parsed_map: ParsedSaveFile,
) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    hero_indexes = {
        int(match.group(1))
        for path in parsed_roster.fields
        for match in [re.match(r"^roster\.heroes\.(\d+)\.", path)]
        if match
    }

    areas_field = parsed_map.fields.get("map.areas.count")
    tiles_field = parsed_map.fields.get("map.tiles.count")

    hero_count = len(hero_indexes)
    areas = int(areas_field.value) if areas_field and isinstance(areas_field.value, int) else 0
    tiles = int(tiles_field.value) if tiles_field and isinstance(tiles_field.value, int) else 0

    if hero_count > 0 and areas == 0:
        issues.append(
            ValidationIssue(
                code="ROSTER_WITHOUT_MAP_AREAS",
                severity="error",
                message="Roster has heroes but map has 0 areas",
                file_name=parsed_map.file_name,
                field_path="map.areas.count",
            )
        )

    if areas > 0 and tiles < areas:
        issues.append(
            ValidationIssue(
                code="MAP_TILE_COUNT_LOW",
                severity="warning",
                message=f"map.tiles.count ({tiles}) is lower than map.areas.count ({areas})",
                file_name=parsed_map.file_name,
                field_path="map.tiles.count",
            )
        )

    return issues
