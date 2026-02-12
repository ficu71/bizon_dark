"""Transactional patch engine."""

from core.patch.engine import PatchEngine, PatchEngineError, PatchOperation, PatchResult
from core.patch.game import GameChange, GamePatchError, apply_game_updates
from core.patch.loading import LoadingChange, LoadingPatchError, apply_loading_updates
from core.patch.options import OptionsChange, OptionsPatchError, apply_options_updates
from core.patch.raid import RaidChange, RaidPatchError, apply_raid_updates
from core.patch.roster import RosterHeroChange, RosterPatchError, apply_hero_updates
from core.patch.upgrades import UpgradesChange, UpgradesPatchError, apply_purchase_updates
from core.patch.wallet import WalletChange, WalletPatchError, apply_wallet_updates

__all__ = [
    "PatchEngine",
    "PatchEngineError",
    "PatchOperation",
    "PatchResult",
    "GameChange",
    "GamePatchError",
    "apply_game_updates",
    "LoadingChange",
    "LoadingPatchError",
    "apply_loading_updates",
    "OptionsChange",
    "OptionsPatchError",
    "apply_options_updates",
    "RaidChange",
    "RaidPatchError",
    "apply_raid_updates",
    "RosterHeroChange",
    "RosterPatchError",
    "apply_hero_updates",
    "UpgradesChange",
    "UpgradesPatchError",
    "apply_purchase_updates",
    "WalletChange",
    "WalletPatchError",
    "apply_wallet_updates",
]
