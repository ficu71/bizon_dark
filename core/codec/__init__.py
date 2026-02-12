"""Binary codec layer (parse/write, lossless strategy)."""

from core.codec.estate import EstateCodecError, EstateSaveCodec
from core.codec.game import GameCodecError, GameSaveCodec, extract_game_summary
from core.codec.loading_screen import (
    LoadingScreenCodecError,
    LoadingScreenSaveCodec,
    extract_loading_screen_summary,
)
from core.codec.map import MapCodecError, MapSaveCodec, extract_map_summary
from core.codec.narration import NarrationCodecError, NarrationSaveCodec, extract_narration_summary
from core.codec.options import OptionsCodecError, OptionsSaveCodec, extract_options_summary
from core.codec.raid import RaidCodecError, RaidSaveCodec, extract_raid_summary
from core.codec.roster import RosterCodecError, RosterSaveCodec, extract_hero_summary
from core.codec.tutorial import TutorialCodecError, TutorialSaveCodec, extract_tutorial_summary
from core.codec.upgrades import UpgradesCodecError, UpgradesSaveCodec, extract_upgrades_summary

__all__ = [
    "EstateSaveCodec",
    "EstateCodecError",
    "UpgradesSaveCodec",
    "UpgradesCodecError",
    "GameSaveCodec",
    "GameCodecError",
    "TutorialSaveCodec",
    "TutorialCodecError",
    "NarrationSaveCodec",
    "NarrationCodecError",
    "LoadingScreenSaveCodec",
    "LoadingScreenCodecError",
    "OptionsSaveCodec",
    "OptionsCodecError",
    "RaidSaveCodec",
    "RaidCodecError",
    "MapSaveCodec",
    "MapCodecError",
    "RosterSaveCodec",
    "RosterCodecError",
    "extract_game_summary",
    "extract_tutorial_summary",
    "extract_narration_summary",
    "extract_loading_screen_summary",
    "extract_options_summary",
    "extract_raid_summary",
    "extract_hero_summary",
    "extract_upgrades_summary",
    "extract_map_summary",
]
