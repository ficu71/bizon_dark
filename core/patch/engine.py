from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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
)
from core.patch.game import GamePatchError, apply_game_updates
from core.patch.loading import LoadingPatchError, apply_loading_updates
from core.patch.options import OptionsPatchError, apply_options_updates
from core.patch.raid import RaidPatchError, apply_raid_updates
from core.patch.roster import RosterPatchError, apply_hero_updates
from core.patch.upgrades import UpgradesPatchError, apply_purchase_updates
from core.patch.wallet import WalletPatchError, apply_wallet_updates
from core.validate import (
    ValidationIssue,
    validate_estate_roster_consistency,
    validate_estate_wallet,
    validate_game_structure,
    validate_loading_screen_structure,
    validate_map_structure,
    validate_narration_structure,
    validate_options_structure,
    validate_tutorial_structure,
    validate_raid_structure,
    validate_roster_map_consistency,
    validate_roster_upgrades_consistency,
    validate_upgrades_structure,
)


class PatchEngineError(Exception):
    pass


@dataclass(slots=True)
class PatchOperation:
    key: str
    expected: int | str | None
    new_value: int | str


@dataclass(slots=True)
class PatchResult:
    applied: bool
    operations: List[PatchOperation] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class PatchEngine:
    """Backup -> stage -> validate -> atomic replace."""

    def __init__(self, backup_root: Path) -> None:
        self.backup_root = backup_root
        self.estate_codec = EstateSaveCodec()
        self.roster_codec = RosterSaveCodec()
        self.upgrades_codec = UpgradesSaveCodec()
        self.map_codec = MapSaveCodec()
        self.game_codec = GameSaveCodec()
        self.raid_codec = RaidSaveCodec()
        self.tutorial_codec = TutorialSaveCodec()
        self.narration_codec = NarrationSaveCodec()
        self.loading_codec = LoadingScreenSaveCodec()
        self.options_codec = OptionsSaveCodec()

    def _blocking_issues(
        self,
        issues: List[ValidationIssue],
        *,
        strict_validation: bool,
    ) -> List[ValidationIssue]:
        if strict_validation:
            return [issue for issue in issues if issue.severity in {"error", "warning"}]
        return [issue for issue in issues if issue.severity == "error"]

    def create_backup(self, profile_dir: Path) -> Path:
        if not profile_dir.exists() or not profile_dir.is_dir():
            raise PatchEngineError(f"Profile directory not found: {profile_dir}")

        self.backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = self.backup_root / f"{profile_dir.name}.{stamp}"
        shutil.copytree(profile_dir, backup_path)
        return backup_path

    def list_backups(self, profile_name: str | None = None) -> List[Path]:
        if not self.backup_root.exists():
            return []

        entries = [p for p in self.backup_root.iterdir() if p.is_dir()]
        if profile_name:
            prefix = f"{profile_name}."
            entries = [p for p in entries if p.name.startswith(prefix)]

        entries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return entries

    def restore_backup(
        self,
        target_profile: Path,
        backup_path: Path,
        *,
        create_safety_backup: bool = True,
    ) -> Path | None:
        if not target_profile.exists() or not target_profile.is_dir():
            raise PatchEngineError(f"Target profile not found: {target_profile}")
        if not backup_path.exists() or not backup_path.is_dir():
            raise PatchEngineError(f"Backup profile not found: {backup_path}")

        safety_backup = None
        if create_safety_backup:
            safety_backup = self.create_backup(target_profile)

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-restore-"))
        staged_profile = stage_root / target_profile.name
        try:
            shutil.copytree(backup_path, staged_profile)
            self.atomic_replace(staged_profile, target_profile)
            return safety_backup
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)

    def atomic_replace(self, staged_profile: Path, target_profile: Path) -> None:
        if not staged_profile.exists() or not staged_profile.is_dir():
            raise PatchEngineError(f"Staged profile not found: {staged_profile}")

        if not target_profile.exists() or not target_profile.is_dir():
            raise PatchEngineError(f"Target profile not found: {target_profile}")

        old_path = target_profile.with_name(target_profile.name + ".old")
        if old_path.exists():
            shutil.rmtree(old_path)

        shutil.move(str(target_profile), str(old_path))
        try:
            shutil.move(str(staged_profile), str(target_profile))
        except Exception as exc:  # noqa: BLE001
            # Best-effort rollback of original profile.
            if old_path.exists() and not target_profile.exists():
                shutil.move(str(old_path), str(target_profile))
            raise PatchEngineError(f"Atomic replace failed: {exc}") from exc

        if old_path.exists():
            shutil.rmtree(old_path)

    def validate_profile(self, profile_dir: Path) -> List[ValidationIssue]:
        estate_path = profile_dir / "persist.estate.json"
        roster_path = profile_dir / "persist.roster.json"
        upgrades_path = profile_dir / "persist.upgrades.json"
        map_path = profile_dir / "persist.map.json"
        game_path = profile_dir / "persist.game.json"
        raid_path = profile_dir / "persist.raid.json"
        tutorial_path = profile_dir / "persist.tutorial.json"
        narration_path = profile_dir / "persist.narration.json"
        loading_path = profile_dir / "persist.loading_screen.json"

        try:
            parsed_estate = self.estate_codec.parse(estate_path)
            parsed_roster = self.roster_codec.parse(roster_path)
            parsed_upgrades = self.upgrades_codec.parse(upgrades_path)
            parsed_map = self.map_codec.parse(map_path)
            parsed_game = self.game_codec.parse(game_path)
            parsed_raid = self.raid_codec.parse(raid_path)
            parsed_tutorial = self.tutorial_codec.parse(tutorial_path)
            parsed_narration = self.narration_codec.parse(narration_path)
            parsed_loading = self.loading_codec.parse(loading_path)
        except (
            EstateCodecError,
            RosterCodecError,
            UpgradesCodecError,
            MapCodecError,
            GameCodecError,
            RaidCodecError,
            TutorialCodecError,
            NarrationCodecError,
            LoadingScreenCodecError,
        ) as exc:
            raise PatchEngineError(str(exc)) from exc

        issues: List[ValidationIssue] = []
        issues.extend(validate_estate_wallet(parsed_estate))
        issues.extend(validate_upgrades_structure(parsed_upgrades))
        issues.extend(validate_map_structure(parsed_map))
        issues.extend(validate_game_structure(parsed_game))
        issues.extend(validate_raid_structure(parsed_raid))
        issues.extend(validate_tutorial_structure(parsed_tutorial))
        issues.extend(validate_narration_structure(parsed_narration))
        issues.extend(validate_loading_screen_structure(parsed_loading))
        issues.extend(validate_estate_roster_consistency(parsed_estate, parsed_roster))
        issues.extend(validate_roster_upgrades_consistency(parsed_roster, parsed_upgrades))
        issues.extend(validate_roster_map_consistency(parsed_roster, parsed_map))
        return issues

    def _validate_options_file(self, options_path: Path) -> List[ValidationIssue]:
        try:
            parsed_options = self.options_codec.parse(options_path)
        except OptionsCodecError as exc:
            raise PatchEngineError(str(exc)) from exc
        return validate_options_structure(parsed_options)

    def _atomic_replace_file(self, target_path: Path, content: bytes) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target_path.name}.", dir=target_path.parent)
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
            os.replace(tmp_path, target_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def apply_wallet_patch(
        self,
        profile_dir: Path,
        updates: Dict[str, int],
        expected: Dict[str, int] | None = None,
        *,
        dry_run: bool = False,
        skip_backup: bool = False,
        strict_validation: bool = False,
    ) -> PatchResult:
        expected = expected or {}

        estate_path = profile_dir / "persist.estate.json"
        try:
            parsed_estate = self.estate_codec.parse(estate_path)
            changes = apply_wallet_updates(parsed_estate, updates=updates, expected=expected)
        except (EstateCodecError, WalletPatchError) as exc:
            raise PatchEngineError(str(exc)) from exc

        ops = [
            PatchOperation(
                key=f"wallet.{change.key}",
                expected=expected.get(change.key),
                new_value=change.new_value,
            )
            for change in changes
        ]
        notes = [f"profile={profile_dir}", f"ops={len(ops)}", f"dry_run={dry_run}"]

        if dry_run:
            return PatchResult(applied=False, operations=ops, notes=notes)

        backup_path = None
        if not skip_backup:
            backup_path = self.create_backup(profile_dir)
            notes.append(f"backup={backup_path}")

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-stage-"))
        staged_profile = stage_root / profile_dir.name

        try:
            shutil.copytree(profile_dir, staged_profile)
            self.estate_codec.write(parsed_estate, staged_profile / "persist.estate.json")

            issues = self.validate_profile(staged_profile)
            blocking = self._blocking_issues(issues, strict_validation=strict_validation)
            if blocking:
                first = blocking[0]
                raise PatchEngineError(f"Validation failed: {first.code}: {first.message}")

            self.atomic_replace(staged_profile, profile_dir)
            notes.append("commit=ok")
            return PatchResult(applied=True, operations=ops, notes=notes)
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)

    def apply_options_patch(
        self,
        profile_dir: Path,
        updates: Dict[str, int | str],
        expected: Dict[str, int | str] | None = None,
        *,
        options_path: Path | None = None,
        dry_run: bool = False,
        skip_backup: bool = False,
        strict_validation: bool = False,
    ) -> PatchResult:
        expected = expected or {}
        target_options_path = options_path.resolve() if options_path is not None else (profile_dir / "persist.options.json")
        in_profile_options_path = profile_dir / "persist.options.json"
        options_in_profile = target_options_path.resolve() == in_profile_options_path.resolve()

        if not target_options_path.exists():
            raise PatchEngineError(f"Options file not found: {target_options_path}")

        try:
            parsed_options = self.options_codec.parse(target_options_path)
            changes = apply_options_updates(parsed_options, updates=updates, expected=expected)
        except (OptionsCodecError, OptionsPatchError) as exc:
            raise PatchEngineError(str(exc)) from exc

        ops = [
            PatchOperation(
                key=f"options.{change.key}",
                expected=expected.get(change.key) if isinstance(expected.get(change.key), (int, str)) else None,
                new_value=change.new_value,
            )
            for change in changes
        ]
        notes = [
            f"profile={profile_dir}",
            f"options={target_options_path}",
            f"ops={len(ops)}",
            f"dry_run={dry_run}",
        ]

        if dry_run:
            return PatchResult(applied=False, operations=ops, notes=notes)

        if not skip_backup:
            backup_path = self.create_backup(profile_dir)
            notes.append(f"backup={backup_path}")

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-stage-"))
        staged_profile = stage_root / profile_dir.name

        try:
            shutil.copytree(profile_dir, staged_profile)

            if options_in_profile:
                staged_options_path = staged_profile / "persist.options.json"
            else:
                staged_options_path = stage_root / "persist.options.json"

            self.options_codec.write(parsed_options, staged_options_path)

            issues = self.validate_profile(staged_profile)
            issues.extend(self._validate_options_file(staged_options_path))
            blocking = self._blocking_issues(issues, strict_validation=strict_validation)
            if blocking:
                first = blocking[0]
                raise PatchEngineError(f"Validation failed: {first.code}: {first.message}")

            if options_in_profile:
                self.atomic_replace(staged_profile, profile_dir)
            else:
                self._atomic_replace_file(target_options_path, staged_options_path.read_bytes())
            notes.append("commit=ok")
            return PatchResult(applied=True, operations=ops, notes=notes)
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)

    def apply_hero_patch(
        self,
        profile_dir: Path,
        hero_index: int,
        updates: Dict[str, int],
        expected: Dict[str, int] | None = None,
        *,
        dry_run: bool = False,
        skip_backup: bool = False,
        strict_validation: bool = False,
    ) -> PatchResult:
        expected = expected or {}

        roster_path = profile_dir / "persist.roster.json"
        try:
            parsed_roster = self.roster_codec.parse(roster_path)
            changes = apply_hero_updates(
                parsed_roster,
                hero_index=hero_index,
                updates=updates,
                expected=expected,
            )
        except (RosterCodecError, RosterPatchError) as exc:
            raise PatchEngineError(str(exc)) from exc

        ops = [
            PatchOperation(
                key=f"hero.{hero_index}.{change.key}",
                expected=expected.get(change.key),
                new_value=change.new_value,
            )
            for change in changes
        ]
        notes = [f"profile={profile_dir}", f"hero={hero_index}", f"ops={len(ops)}", f"dry_run={dry_run}"]

        if dry_run:
            return PatchResult(applied=False, operations=ops, notes=notes)

        backup_path = None
        if not skip_backup:
            backup_path = self.create_backup(profile_dir)
            notes.append(f"backup={backup_path}")

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-stage-"))
        staged_profile = stage_root / profile_dir.name

        try:
            shutil.copytree(profile_dir, staged_profile)
            self.roster_codec.write(parsed_roster, staged_profile / "persist.roster.json")

            issues = self.validate_profile(staged_profile)
            blocking = self._blocking_issues(issues, strict_validation=strict_validation)
            if blocking:
                first = blocking[0]
                raise PatchEngineError(f"Validation failed: {first.code}: {first.message}")

            self.atomic_replace(staged_profile, profile_dir)
            notes.append("commit=ok")
            return PatchResult(applied=True, operations=ops, notes=notes)
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)

    def apply_upgrades_patch(
        self,
        profile_dir: Path,
        updates: Dict[str, int],
        expected: Dict[str, int] | None = None,
        *,
        dry_run: bool = False,
        skip_backup: bool = False,
        strict_validation: bool = False,
    ) -> PatchResult:
        expected = expected or {}

        upgrades_path = profile_dir / "persist.upgrades.json"
        try:
            parsed_upgrades = self.upgrades_codec.parse(upgrades_path)
            changes = apply_purchase_updates(parsed_upgrades, updates=updates, expected=expected)
        except (UpgradesCodecError, UpgradesPatchError) as exc:
            raise PatchEngineError(str(exc)) from exc

        ops = [
            PatchOperation(
                key=f"upgrades.{change.key}.is_purchased",
                expected=expected.get(change.key),
                new_value=change.new_value,
            )
            for change in changes
        ]
        notes = [f"profile={profile_dir}", f"ops={len(ops)}", f"dry_run={dry_run}"]

        if dry_run:
            return PatchResult(applied=False, operations=ops, notes=notes)

        if not skip_backup:
            backup_path = self.create_backup(profile_dir)
            notes.append(f"backup={backup_path}")

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-stage-"))
        staged_profile = stage_root / profile_dir.name

        try:
            shutil.copytree(profile_dir, staged_profile)
            self.upgrades_codec.write(parsed_upgrades, staged_profile / "persist.upgrades.json")

            issues = self.validate_profile(staged_profile)
            blocking = self._blocking_issues(issues, strict_validation=strict_validation)
            if blocking:
                first = blocking[0]
                raise PatchEngineError(f"Validation failed: {first.code}: {first.message}")

            self.atomic_replace(staged_profile, profile_dir)
            notes.append("commit=ok")
            return PatchResult(applied=True, operations=ops, notes=notes)
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)

    def apply_game_patch(
        self,
        profile_dir: Path,
        updates: Dict[str, int],
        expected: Dict[str, int] | None = None,
        *,
        dry_run: bool = False,
        skip_backup: bool = False,
        strict_validation: bool = False,
    ) -> PatchResult:
        expected = expected or {}

        game_path = profile_dir / "persist.game.json"
        try:
            parsed_game = self.game_codec.parse(game_path)
            changes = apply_game_updates(parsed_game, updates=updates, expected=expected)
        except (GameCodecError, GamePatchError) as exc:
            raise PatchEngineError(str(exc)) from exc

        ops = [
            PatchOperation(
                key=f"game.{change.key}",
                expected=expected.get(change.key),
                new_value=change.new_value,
            )
            for change in changes
        ]
        notes = [f"profile={profile_dir}", f"ops={len(ops)}", f"dry_run={dry_run}"]

        if dry_run:
            return PatchResult(applied=False, operations=ops, notes=notes)

        if not skip_backup:
            backup_path = self.create_backup(profile_dir)
            notes.append(f"backup={backup_path}")

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-stage-"))
        staged_profile = stage_root / profile_dir.name

        try:
            shutil.copytree(profile_dir, staged_profile)
            self.game_codec.write(parsed_game, staged_profile / "persist.game.json")

            issues = self.validate_profile(staged_profile)
            blocking = self._blocking_issues(issues, strict_validation=strict_validation)
            if blocking:
                first = blocking[0]
                raise PatchEngineError(f"Validation failed: {first.code}: {first.message}")

            self.atomic_replace(staged_profile, profile_dir)
            notes.append("commit=ok")
            return PatchResult(applied=True, operations=ops, notes=notes)
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)

    def apply_raid_patch(
        self,
        profile_dir: Path,
        updates: Dict[str, int],
        expected: Dict[str, int] | None = None,
        *,
        dry_run: bool = False,
        skip_backup: bool = False,
        allow_inbattle: bool = False,
        strict_validation: bool = False,
    ) -> PatchResult:
        expected = expected or {}

        raid_path = profile_dir / "persist.raid.json"
        try:
            parsed_raid = self.raid_codec.parse(raid_path)
            current_inbattle = parsed_raid.fields.get("raid.inbattle")
            if (
                not allow_inbattle
                and current_inbattle is not None
                and isinstance(current_inbattle.value, int)
                and current_inbattle.value == 1
            ):
                raise PatchEngineError(
                    "Active raid detected (raid.inbattle=1). "
                    "Use allow_inbattle=True / --allow-inbattle to override."
                )
            changes = apply_raid_updates(parsed_raid, updates=updates, expected=expected)
        except (RaidCodecError, RaidPatchError) as exc:
            raise PatchEngineError(str(exc)) from exc

        ops = [
            PatchOperation(
                key=f"raid.{change.key}",
                expected=expected.get(change.key),
                new_value=change.new_value,
            )
            for change in changes
        ]
        notes = [
            f"profile={profile_dir}",
            f"ops={len(ops)}",
            f"dry_run={dry_run}",
            f"allow_inbattle={allow_inbattle}",
        ]

        if dry_run:
            return PatchResult(applied=False, operations=ops, notes=notes)

        if not skip_backup:
            backup_path = self.create_backup(profile_dir)
            notes.append(f"backup={backup_path}")

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-stage-"))
        staged_profile = stage_root / profile_dir.name

        try:
            shutil.copytree(profile_dir, staged_profile)
            self.raid_codec.write(parsed_raid, staged_profile / "persist.raid.json")

            issues = self.validate_profile(staged_profile)
            blocking = self._blocking_issues(issues, strict_validation=strict_validation)
            if blocking:
                first = blocking[0]
                raise PatchEngineError(f"Validation failed: {first.code}: {first.message}")

            self.atomic_replace(staged_profile, profile_dir)
            notes.append("commit=ok")
            return PatchResult(applied=True, operations=ops, notes=notes)
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)

    def apply_loading_patch(
        self,
        profile_dir: Path,
        updates: Dict[str, int],
        expected: Dict[str, int] | None = None,
        *,
        dry_run: bool = False,
        skip_backup: bool = False,
        strict_validation: bool = False,
    ) -> PatchResult:
        expected = expected or {}

        loading_path = profile_dir / "persist.loading_screen.json"
        try:
            parsed_loading = self.loading_codec.parse(loading_path)
            changes = apply_loading_updates(parsed_loading, updates=updates, expected=expected)
        except (LoadingScreenCodecError, LoadingPatchError) as exc:
            raise PatchEngineError(str(exc)) from exc

        ops = [
            PatchOperation(
                key=f"loading.{change.key}",
                expected=expected.get(change.key),
                new_value=change.new_value,
            )
            for change in changes
        ]
        notes = [f"profile={profile_dir}", f"ops={len(ops)}", f"dry_run={dry_run}"]

        if dry_run:
            return PatchResult(applied=False, operations=ops, notes=notes)

        if not skip_backup:
            backup_path = self.create_backup(profile_dir)
            notes.append(f"backup={backup_path}")

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-stage-"))
        staged_profile = stage_root / profile_dir.name

        try:
            shutil.copytree(profile_dir, staged_profile)
            self.loading_codec.write(parsed_loading, staged_profile / "persist.loading_screen.json")

            issues = self.validate_profile(staged_profile)
            blocking = self._blocking_issues(issues, strict_validation=strict_validation)
            if blocking:
                first = blocking[0]
                raise PatchEngineError(f"Validation failed: {first.code}: {first.message}")

            self.atomic_replace(staged_profile, profile_dir)
            notes.append("commit=ok")
            return PatchResult(applied=True, operations=ops, notes=notes)
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)

    def apply_manifest_patch(
        self,
        profile_dir: Path,
        manifest: Dict[str, Any],
        *,
        options_path: Path | None = None,
        dry_run: bool = False,
        skip_backup: bool = False,
        allow_inbattle: bool = False,
        strict_validation: bool = False,
    ) -> PatchResult:
        if not isinstance(manifest, dict):
            raise PatchEngineError("Manifest payload must be a JSON object")

        wallet_updates = manifest.get("wallet_updates") or {}
        wallet_expected = manifest.get("wallet_expected") or {}
        hero_updates = manifest.get("hero_updates") or []
        upgrades_updates = manifest.get("upgrades_updates") or {}
        upgrades_expected = manifest.get("upgrades_expected") or {}
        game_updates = manifest.get("game_updates") or {}
        game_expected = manifest.get("game_expected") or {}
        loading_updates = manifest.get("loading_updates") or {}
        loading_expected = manifest.get("loading_expected") or {}
        options_updates = manifest.get("options_updates") or {}
        options_expected = manifest.get("options_expected") or {}
        raid_updates = manifest.get("raid_updates") or {}
        raid_expected = manifest.get("raid_expected") or {}

        if not isinstance(wallet_updates, dict) or not isinstance(wallet_expected, dict):
            raise PatchEngineError("Manifest wallet section must contain objects")
        if not isinstance(hero_updates, list):
            raise PatchEngineError("Manifest hero_updates must be a list")
        if not isinstance(upgrades_updates, dict) or not isinstance(upgrades_expected, dict):
            raise PatchEngineError("Manifest upgrades section must contain objects")
        if not isinstance(game_updates, dict) or not isinstance(game_expected, dict):
            raise PatchEngineError("Manifest game section must contain objects")
        if not isinstance(loading_updates, dict) or not isinstance(loading_expected, dict):
            raise PatchEngineError("Manifest loading section must contain objects")
        if not isinstance(options_updates, dict) or not isinstance(options_expected, dict):
            raise PatchEngineError("Manifest options section must contain objects")
        if not isinstance(raid_updates, dict) or not isinstance(raid_expected, dict):
            raise PatchEngineError("Manifest raid section must contain objects")

        parsed_estate = None
        parsed_roster = None
        parsed_upgrades = None
        parsed_game = None
        parsed_loading = None
        parsed_options = None
        parsed_raid = None
        touched_files: set[str] = set()
        ops: List[PatchOperation] = []

        if wallet_updates:
            estate_path = profile_dir / "persist.estate.json"
            try:
                parsed_estate = self.estate_codec.parse(estate_path)
                wallet_changes = apply_wallet_updates(
                    parsed_estate,
                    updates=wallet_updates,
                    expected=wallet_expected,
                )
            except (EstateCodecError, WalletPatchError) as exc:
                raise PatchEngineError(str(exc)) from exc

            touched_files.add("persist.estate.json")
            ops.extend(
                PatchOperation(
                    key=f"wallet.{change.key}",
                    expected=wallet_expected.get(change.key),
                    new_value=change.new_value,
                )
                for change in wallet_changes
            )

        if hero_updates:
            roster_path = profile_dir / "persist.roster.json"
            try:
                parsed_roster = self.roster_codec.parse(roster_path)
            except RosterCodecError as exc:
                raise PatchEngineError(str(exc)) from exc

            for item in hero_updates:
                if not isinstance(item, dict):
                    raise PatchEngineError("Each hero update entry must be an object")
                hero_index = item.get("hero_index")
                updates = item.get("updates") or {}
                expected = item.get("expected") or {}
                if not isinstance(hero_index, int) or hero_index <= 0:
                    raise PatchEngineError(f"Invalid hero_index in manifest: {hero_index}")
                if not isinstance(updates, dict) or not isinstance(expected, dict):
                    raise PatchEngineError("Hero updates/expected must be objects")

                try:
                    hero_changes = apply_hero_updates(
                        parsed_roster,
                        hero_index=hero_index,
                        updates=updates,
                        expected=expected,
                    )
                except RosterPatchError as exc:
                    raise PatchEngineError(str(exc)) from exc

                touched_files.add("persist.roster.json")
                ops.extend(
                    PatchOperation(
                        key=f"hero.{hero_index}.{change.key}",
                        expected=expected.get(change.key),
                        new_value=change.new_value,
                    )
                    for change in hero_changes
                )

        if upgrades_updates:
            upgrades_path = profile_dir / "persist.upgrades.json"
            try:
                parsed_upgrades = self.upgrades_codec.parse(upgrades_path)
                upgrades_changes = apply_purchase_updates(
                    parsed_upgrades,
                    updates=upgrades_updates,
                    expected=upgrades_expected,
                )
            except (UpgradesCodecError, UpgradesPatchError) as exc:
                raise PatchEngineError(str(exc)) from exc

            touched_files.add("persist.upgrades.json")
            ops.extend(
                PatchOperation(
                    key=f"upgrades.{change.key}.is_purchased",
                    expected=upgrades_expected.get(change.key),
                    new_value=change.new_value,
                )
                for change in upgrades_changes
            )

        if game_updates:
            game_path = profile_dir / "persist.game.json"
            try:
                parsed_game = self.game_codec.parse(game_path)
                game_changes = apply_game_updates(
                    parsed_game,
                    updates=game_updates,
                    expected=game_expected,
                )
            except (GameCodecError, GamePatchError) as exc:
                raise PatchEngineError(str(exc)) from exc

            touched_files.add("persist.game.json")
            ops.extend(
                PatchOperation(
                    key=f"game.{change.key}",
                    expected=game_expected.get(change.key),
                    new_value=change.new_value,
                )
                for change in game_changes
            )

        if loading_updates:
            loading_path = profile_dir / "persist.loading_screen.json"
            try:
                parsed_loading = self.loading_codec.parse(loading_path)
                loading_changes = apply_loading_updates(
                    parsed_loading,
                    updates=loading_updates,
                    expected=loading_expected,
                )
            except (LoadingScreenCodecError, LoadingPatchError) as exc:
                raise PatchEngineError(str(exc)) from exc

            touched_files.add("persist.loading_screen.json")
            ops.extend(
                PatchOperation(
                    key=f"loading.{change.key}",
                    expected=loading_expected.get(change.key),
                    new_value=change.new_value,
                )
                for change in loading_changes
            )

        target_options_path = options_path.resolve() if options_path is not None else (profile_dir / "persist.options.json")
        in_profile_options_path = profile_dir / "persist.options.json"
        options_in_profile = target_options_path.resolve() == in_profile_options_path.resolve()

        if options_updates:
            if not target_options_path.exists():
                raise PatchEngineError(f"Options file not found: {target_options_path}")
            try:
                parsed_options = self.options_codec.parse(target_options_path)
                options_changes = apply_options_updates(
                    parsed_options,
                    updates=options_updates,
                    expected=options_expected,
                )
            except (OptionsCodecError, OptionsPatchError) as exc:
                raise PatchEngineError(str(exc)) from exc

            touched_files.add(
                "persist.options.json" if options_in_profile else f"options:{target_options_path}"
            )
            ops.extend(
                PatchOperation(
                    key=f"options.{change.key}",
                    expected=options_expected.get(change.key)
                    if isinstance(options_expected.get(change.key), (int, str))
                    else None,
                    new_value=change.new_value,
                )
                for change in options_changes
            )

        if raid_updates:
            raid_path = profile_dir / "persist.raid.json"
            try:
                parsed_raid = self.raid_codec.parse(raid_path)
                current_inbattle = parsed_raid.fields.get("raid.inbattle")
                if (
                    not allow_inbattle
                    and current_inbattle is not None
                    and isinstance(current_inbattle.value, int)
                    and current_inbattle.value == 1
                ):
                    raise PatchEngineError(
                        "Active raid detected (raid.inbattle=1). "
                        "Use allow_inbattle=True / --allow-inbattle to override."
                    )
                raid_changes = apply_raid_updates(
                    parsed_raid,
                    updates=raid_updates,
                    expected=raid_expected,
                )
            except (RaidCodecError, RaidPatchError) as exc:
                raise PatchEngineError(str(exc)) from exc

            touched_files.add("persist.raid.json")
            ops.extend(
                PatchOperation(
                    key=f"raid.{change.key}",
                    expected=raid_expected.get(change.key),
                    new_value=change.new_value,
                )
                for change in raid_changes
            )

        if not ops:
            raise PatchEngineError("Manifest contains no updates")

        notes = [
            f"profile={profile_dir}",
            f"ops={len(ops)}",
            f"dry_run={dry_run}",
            "mode=manifest",
            f"allow_inbattle={allow_inbattle}",
            f"touched={','.join(sorted(touched_files))}",
        ]

        if dry_run:
            return PatchResult(applied=False, operations=ops, notes=notes)

        if not skip_backup:
            backup_path = self.create_backup(profile_dir)
            notes.append(f"backup={backup_path}")

        stage_root = Path(tempfile.mkdtemp(prefix="bizon-dark-stage-"))
        staged_profile = stage_root / profile_dir.name
        try:
            shutil.copytree(profile_dir, staged_profile)
            if parsed_estate is not None:
                self.estate_codec.write(parsed_estate, staged_profile / "persist.estate.json")
            if parsed_roster is not None:
                self.roster_codec.write(parsed_roster, staged_profile / "persist.roster.json")
            if parsed_upgrades is not None:
                self.upgrades_codec.write(parsed_upgrades, staged_profile / "persist.upgrades.json")
            if parsed_game is not None:
                self.game_codec.write(parsed_game, staged_profile / "persist.game.json")
            if parsed_loading is not None:
                self.loading_codec.write(parsed_loading, staged_profile / "persist.loading_screen.json")
            staged_options_path: Path | None = None
            if parsed_options is not None:
                if options_in_profile:
                    staged_options_path = staged_profile / "persist.options.json"
                else:
                    staged_options_path = stage_root / "persist.options.json"
                self.options_codec.write(parsed_options, staged_options_path)
            if parsed_raid is not None:
                self.raid_codec.write(parsed_raid, staged_profile / "persist.raid.json")

            issues = self.validate_profile(staged_profile)
            if staged_options_path is not None:
                issues.extend(self._validate_options_file(staged_options_path))
            blocking = self._blocking_issues(issues, strict_validation=strict_validation)
            if blocking:
                first = blocking[0]
                raise PatchEngineError(f"Validation failed: {first.code}: {first.message}")

            profile_mutated = any(
                item is not None
                for item in [parsed_estate, parsed_roster, parsed_upgrades, parsed_game, parsed_loading, parsed_raid]
            ) or (parsed_options is not None and options_in_profile)

            old_external_options_bytes: bytes | None = None
            if parsed_options is not None and not options_in_profile and staged_options_path is not None:
                old_external_options_bytes = target_options_path.read_bytes()
                self._atomic_replace_file(target_options_path, staged_options_path.read_bytes())

            if profile_mutated:
                try:
                    self.atomic_replace(staged_profile, profile_dir)
                except Exception:
                    if old_external_options_bytes is not None:
                        self._atomic_replace_file(target_options_path, old_external_options_bytes)
                    raise

            notes.append("commit=ok")
            return PatchResult(applied=True, operations=ops, notes=notes)
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root, ignore_errors=True)
