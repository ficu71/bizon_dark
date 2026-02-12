from __future__ import annotations

from core.presets import build_manifest_for_preset, get_preset, list_presets


def test_list_presets_contains_expected_names() -> None:
    names = [preset.name for preset in list_presets()]
    assert "economy-rich" in names
    assert "starter-boost" in names
    assert "hero-resolve-boost" in names
    assert "game-town-state" in names


def test_get_preset_returns_metadata() -> None:
    preset = get_preset("hero-resolve-boost")
    assert preset.supports_hero_index is True
    assert preset.supports_resolve_xp is True


def test_build_manifest_for_economy_rich() -> None:
    manifest = build_manifest_for_preset(name="economy-rich")
    wallet = manifest.get("wallet_updates", {})
    assert isinstance(wallet, dict)
    assert int(wallet.get("gold", 0)) == 999_999


def test_build_manifest_for_hero_resolve_boost_uses_parameters() -> None:
    manifest = build_manifest_for_preset(
        name="hero-resolve-boost",
        hero_index=2,
        resolve_xp=222,
    )
    heroes = manifest.get("hero_updates", [])
    assert isinstance(heroes, list)
    assert heroes
    first = heroes[0]
    assert first.get("hero_index") == 2
    updates = first.get("updates", {})
    assert isinstance(updates, dict)
    assert int(updates.get("resolve_xp", 0)) == 222
