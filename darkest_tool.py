#!/usr/bin/env python3
"""Darkest Dungeon save helper without external save editor dependencies."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from core.codec import EstateCodecError, EstateSaveCodec
from core.patch import WalletPatchError, apply_wallet_updates


DEFAULT_PROFILE = Path.home() / "Library" / "Application Support" / "Darkest" / "profile_1"
DEFAULT_BACKUP_DIR = Path("backups")
ESTATE_FILENAME = "persist.estate.json"


class ToolError(Exception):
    pass


@dataclass
class WalletEntry:
    name: str
    value: int
    value_offset: int
    amount_offset: int = -1
    type_offset: int = -1


def parse_key_value_pairs(values: Iterable[str]) -> Dict[str, int]:
    parsed: Dict[str, int] = {}
    for raw in values:
        if "=" not in raw:
            raise ToolError(f"Invalid key=value pair: {raw}")

        key, val = raw.split("=", 1)
        key = key.strip().lower()
        if not key:
            raise ToolError(f"Invalid empty key in pair: {raw}")

        try:
            num = int(val)
        except ValueError as exc:
            raise ToolError(f"Invalid integer value in pair: {raw}") from exc

        if num < 0 or num > 0xFFFFFFFF:
            raise ToolError(f"Value out of uint32 range in pair: {raw}")

        parsed[key] = num

    return parsed


def to_abs(base: Path, raw: str) -> Path:
    p = Path(raw).expanduser()
    if p.is_absolute():
        return p
    return (base / p).resolve()


def estate_path_from_profile(profile_dir: Path) -> Path:
    return profile_dir / ESTATE_FILENAME


def backup_profile(profile_dir: Path, backup_dir: Path) -> Path:
    if not profile_dir.exists() or not profile_dir.is_dir():
        raise ToolError(f"Profile directory not found: {profile_dir}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{profile_dir.name}.{stamp}"
    shutil.copytree(profile_dir, backup_path)
    return backup_path


def load_estate_binary(profile_dir: Path) -> Tuple[Path, bytearray]:
    estate_path = estate_path_from_profile(profile_dir)
    if not estate_path.exists() or not estate_path.is_file():
        raise ToolError(f"Estate file not found: {estate_path}")
    return estate_path, bytearray(estate_path.read_bytes())


def list_wallet(profile_dir: Path) -> List[WalletEntry]:
    estate_path = estate_path_from_profile(profile_dir)
    codec = EstateSaveCodec()
    try:
        parsed = codec.parse(estate_path)
    except EstateCodecError as exc:
        raise ToolError(str(exc)) from exc

    out: List[WalletEntry] = []
    for field in parsed.fields.values():
        if not (field.path.startswith("wallet.") and field.path.endswith(".amount")):
            continue
        name = field.path.split(".")[1]
        value = int(field.value)
        out.append(WalletEntry(name=name, value=value, value_offset=field.location.start))

    if not out:
        raise ToolError("No wallet entries parsed from persist.estate.json")

    return sorted(out, key=lambda e: e.name)


def patch_wallet(
    profile_dir: Path,
    updates: Dict[str, int],
    expected: Dict[str, int],
    dry_run: bool,
) -> Tuple[List[Tuple[str, int, int]], Path]:
    if not updates:
        raise ToolError("No updates provided. Use --set TYPE=VALUE")

    estate_path = estate_path_from_profile(profile_dir)
    codec = EstateSaveCodec()

    try:
        parsed = codec.parse(estate_path)
        wallet_changes = apply_wallet_updates(parsed, updates=updates, expected=expected)
    except (EstateCodecError, WalletPatchError) as exc:
        raise ToolError(str(exc)) from exc

    if not dry_run:
        codec.write(parsed, estate_path)

    changes = [(c.key, c.old_value, c.new_value) for c in wallet_changes]
    return changes, estate_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Darkest Dungeon save helper (direct binary wallet patching, no DDSaveEditor.jar)."
    )
    parser.add_argument("--cwd", default=".", help="Base directory for relative paths")
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE),
        help="Profile directory (default: ~/Library/Application Support/Darkest/profile_1)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Validate profile and parse wallet section.")

    p_backup = sub.add_parser("backup", help="Create timestamped backup of profile directory.")
    p_backup.add_argument(
        "--backup-dir",
        default=str(DEFAULT_BACKUP_DIR),
        help="Backup directory (default: backups)",
    )

    sub.add_parser("list-wallet", help="List wallet resources and values from binary estate file.")

    p_patch = sub.add_parser("patch-wallet", help="Patch wallet values directly in binary save.")
    p_patch.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="TYPE=VALUE",
        help="Resource update, repeatable (example: --set gold=999999)",
    )
    p_patch.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="TYPE=VALUE",
        help="Safety check current value, repeatable (example: --expect gold=12345)",
    )
    p_patch.add_argument("--dry-run", action="store_true", help="Validate and preview changes only")

    p_quick = sub.add_parser("quick-wallet", help="Backup profile and patch wallet in one command.")
    p_quick.add_argument(
        "--backup-dir",
        default=str(DEFAULT_BACKUP_DIR),
        help="Backup directory (default: backups)",
    )
    p_quick.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="TYPE=VALUE",
        help="Resource update, repeatable",
    )
    p_quick.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="TYPE=VALUE",
        help="Safety check current value, repeatable",
    )
    p_quick.add_argument("--dry-run", action="store_true", help="Do not write file after validation")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    base = Path(args.cwd).expanduser().resolve()
    profile = to_abs(base, args.profile)

    try:
        if args.command == "doctor":
            if not profile.exists() or not profile.is_dir():
                raise ToolError(f"Profile directory not found: {profile}")

            estate = estate_path_from_profile(profile)
            if not estate.exists():
                raise ToolError(f"Estate file not found: {estate}")

            entries = list_wallet(profile)
            print(f"[ok] profile: {profile}")
            print(f"[ok] estate: {estate}")
            print(f"[ok] wallet entries parsed: {len(entries)}")
            return 0

        if args.command == "backup":
            backup_dir = to_abs(base, args.backup_dir)
            backup_path = backup_profile(profile, backup_dir)
            print(f"[ok] backup created: {backup_path}")
            return 0

        if args.command == "list-wallet":
            entries = list_wallet(profile)
            for e in entries:
                print(f"{e.name}={e.value}")
            return 0

        if args.command == "patch-wallet":
            updates = parse_key_value_pairs(args.set)
            expected = parse_key_value_pairs(args.expect)
            changes, estate_path = patch_wallet(profile, updates, expected, dry_run=args.dry_run)
            for key, old_val, new_val in changes:
                tag = "[dry-run]" if args.dry_run else "[ok]"
                print(f"{tag} {key}: {old_val} -> {new_val}")
            if not args.dry_run:
                print(f"[ok] patched file: {estate_path}")
            return 0

        if args.command == "quick-wallet":
            backup_dir = to_abs(base, args.backup_dir)
            updates = parse_key_value_pairs(args.set)
            expected = parse_key_value_pairs(args.expect)

            backup_path = backup_profile(profile, backup_dir)
            print(f"[ok] backup created: {backup_path}")

            changes, estate_path = patch_wallet(profile, updates, expected, dry_run=args.dry_run)
            for key, old_val, new_val in changes:
                tag = "[dry-run]" if args.dry_run else "[ok]"
                print(f"{tag} {key}: {old_val} -> {new_val}")
            if not args.dry_run:
                print(f"[ok] patched file: {estate_path}")
            return 0

        raise ToolError(f"Unknown command: {args.command}")
    except ToolError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
