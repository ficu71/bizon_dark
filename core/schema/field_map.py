from __future__ import annotations

# Canonical field paths used by CLI/API and patch engine.
# TODO: Fill from binary reverse-engineering checklist.

FIELD_MAP = {
    "estate.wallet.gold": {
        "file": "persist.estate.json",
        "path": "wallet.gold.amount",
        "type": "u32",
    },
    "estate.wallet.bust": {
        "file": "persist.estate.json",
        "path": "wallet.bust.amount",
        "type": "u32",
    },
    "estate.wallet.portrait": {
        "file": "persist.estate.json",
        "path": "wallet.portrait.amount",
        "type": "u32",
    },
    "estate.wallet.deed": {
        "file": "persist.estate.json",
        "path": "wallet.deed.amount",
        "type": "u32",
    },
    "estate.wallet.crest": {
        "file": "persist.estate.json",
        "path": "wallet.crest.amount",
        "type": "u32",
    },
    "roster.heroes.*.name": {
        "file": "persist.roster.json",
        "path": "roster.heroes.{index}.name",
        "type": "string",
    },
    "roster.heroes.*.class": {
        "file": "persist.roster.json",
        "path": "roster.heroes.{index}.class",
        "type": "string",
    },
    "roster.heroes.*.resolve_xp": {
        "file": "persist.roster.json",
        "path": "roster.heroes.{index}.resolve_xp",
        "type": "u32",
    },
    "upgrades.version": {
        "file": "persist.upgrades.json",
        "path": "upgrades.version",
        "type": "u32",
    },
    "upgrades.purchases.count": {
        "file": "persist.upgrades.json",
        "path": "upgrades.purchases.count",
        "type": "derived_u32",
    },
    "map.areas.count": {
        "file": "persist.map.json",
        "path": "map.areas.count",
        "type": "derived_u32",
    },
    "map.tiles.count": {
        "file": "persist.map.json",
        "path": "map.tiles.count",
        "type": "derived_u32",
    },
    "map.doors.count": {
        "file": "persist.map.json",
        "path": "map.doors.count",
        "type": "derived_u32",
    },
}
