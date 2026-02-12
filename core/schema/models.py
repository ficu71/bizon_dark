from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(slots=True)
class WalletState:
    resources: Dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class HeroState:
    hero_id: str
    name: str
    class_id: str
    level: int
    resolve_xp: int
    stress: int
    hp: int
    quirks: List[str] = field(default_factory=list)
    diseases: List[str] = field(default_factory=list)


@dataclass(slots=True)
class CampaignState:
    estate_name: str
    game_mode: str
    week: int
    in_raid: bool
