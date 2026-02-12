from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


class PresetError(Exception):
    pass


@dataclass(slots=True)
class PresetDefinition:
    name: str
    description: str
    supports_hero_index: bool = False
    supports_resolve_xp: bool = False


_PRESETS: Dict[str, PresetDefinition] = {
    "economy-rich": PresetDefinition(
        name="economy-rich",
        description="Set core estate resources to rich values",
    ),
    "starter-boost": PresetDefinition(
        name="starter-boost",
        description="Small early-campaign boost (wallet + out-of-raid flag)",
    ),
    "hero-resolve-boost": PresetDefinition(
        name="hero-resolve-boost",
        description="Set selected hero resolve XP to target value",
        supports_hero_index=True,
        supports_resolve_xp=True,
    ),
    "game-town-state": PresetDefinition(
        name="game-town-state",
        description="Force game.inraid=0 and clear dd_options_altered flag",
    ),
}


def list_presets() -> List[PresetDefinition]:
    return sorted(_PRESETS.values(), key=lambda p: p.name)


def get_preset(name: str) -> PresetDefinition:
    preset = _PRESETS.get(name)
    if preset is None:
        raise PresetError(f"Unknown preset: {name}")
    return preset


def build_manifest_for_preset(
    *,
    name: str,
    hero_index: int = 1,
    resolve_xp: int = 120,
) -> Dict[str, Any]:
    if name == "economy-rich":
        return {
            "wallet_updates": {
                "gold": 999_999,
                "bust": 999,
                "portrait": 999,
                "deed": 999,
                "crest": 999,
            },
            "wallet_expected": {},
            "hero_updates": [],
            "upgrades_updates": {},
            "upgrades_expected": {},
            "game_updates": {},
            "game_expected": {},
            "loading_updates": {},
            "loading_expected": {},
            "raid_updates": {},
            "raid_expected": {},
        }

    if name == "starter-boost":
        return {
            "wallet_updates": {
                "gold": 20_000,
                "bust": 25,
                "portrait": 25,
                "deed": 25,
                "crest": 50,
            },
            "wallet_expected": {},
            "hero_updates": [],
            "upgrades_updates": {},
            "upgrades_expected": {},
            "game_updates": {
                "inraid": 0,
            },
            "game_expected": {},
            "loading_updates": {},
            "loading_expected": {},
            "raid_updates": {},
            "raid_expected": {},
        }

    if name == "hero-resolve-boost":
        if hero_index <= 0:
            raise PresetError("hero_index must be >= 1 for hero-resolve-boost")
        if resolve_xp < 0 or resolve_xp > 0xFFFFFFFF:
            raise PresetError(f"resolve_xp out of u32 range: {resolve_xp}")
        return {
            "wallet_updates": {},
            "wallet_expected": {},
            "hero_updates": [
                {
                    "hero_index": hero_index,
                    "updates": {
                        "resolve_xp": int(resolve_xp),
                    },
                    "expected": {},
                }
            ],
            "upgrades_updates": {},
            "upgrades_expected": {},
            "game_updates": {},
            "game_expected": {},
            "loading_updates": {},
            "loading_expected": {},
            "raid_updates": {},
            "raid_expected": {},
        }

    if name == "game-town-state":
        return {
            "wallet_updates": {},
            "wallet_expected": {},
            "hero_updates": [],
            "upgrades_updates": {},
            "upgrades_expected": {},
            "game_updates": {
                "inraid": 0,
                "dd_options_altered": 0,
            },
            "game_expected": {},
            "loading_updates": {},
            "loading_expected": {},
            "raid_updates": {},
            "raid_expected": {},
        }

    raise PresetError(f"Unknown preset: {name}")
