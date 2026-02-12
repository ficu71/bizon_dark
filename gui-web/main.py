"""Bizon Dark Editor - GUI Web MVP (FastAPI)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.codec import (
    EstateSaveCodec,
    GameSaveCodec,
    LoadingScreenSaveCodec,
    OptionsSaveCodec,
    RaidSaveCodec,
    RosterSaveCodec,
    UpgradesSaveCodec,
    extract_game_summary,
    extract_hero_summary,
    extract_loading_screen_summary,
    extract_options_summary,
    extract_raid_summary,
    extract_upgrades_summary,
)
from core.patch import PatchEngine
from core.presets import build_manifest_for_preset, list_presets

app = FastAPI(title="Bizon Dark Editor", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="gui-web/static"), name="static")

# Templates
templates = Jinja2Templates(directory="gui-web/templates")

# Default profile path (macOS)
DEFAULT_PROFILE = Path.home() / "Library" / "Application Support" / "Darkest" / "profile_1"
BACKUP_DIR = Path("backups")


def get_profile_path(profile: str | None = None) -> Path:
    """Get profile path."""
    if profile:
        return Path(profile).expanduser().resolve()
    return DEFAULT_PROFILE


def get_profile_files(profile_path: Path) -> dict[str, Path]:
    """Get paths to all profile files."""
    return {
        "estate": profile_path / "persist.estate.json",
        "roster": profile_path / "persist.roster.json",
        "upgrades": profile_path / "persist.upgrades.json",
        "game": profile_path / "persist.game.json",
        "raid": profile_path / "persist.raid.json",
        "loading": profile_path / "persist.loading_screen.json",
        "options": profile_path.parent / "persist.options.json",
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/profile/status")
async def profile_status(profile: str | None = None):
    """Get profile status and summary."""
    profile_path = get_profile_path(profile)
    
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    
    files = get_profile_files(profile_path)
    result = {
        "profile": str(profile_path),
        "exists": True,
        "files": {},
        "wallet": {},
        "heroes": [],
        "game": {},
        "raid": {},
    }
    
    # Check files
    for name, path in files.items():
        result["files"][name] = {"exists": path.exists(), "path": str(path)}
    
    # Parse wallet
    if files["estate"].exists():
        try:
            estate = EstateSaveCodec().parse(files["estate"])
            for field in estate.fields.values():
                if field.path.startswith("wallet.") and field.path.endswith(".amount"):
                    key = field.path.split(".")[1]
                    result["wallet"][key] = int(field.value)
        except Exception as e:
            result["wallet_error"] = str(e)
    
    # Parse heroes
    if files["roster"].exists():
        try:
            roster = RosterSaveCodec().parse(files["roster"])
            result["heroes"] = extract_hero_summary(roster)
        except Exception as e:
            result["heroes_error"] = str(e)
    
    # Parse game
    if files["game"].exists():
        try:
            game = GameSaveCodec().parse(files["game"])
            result["game"] = extract_game_summary(game)
        except Exception as e:
            result["game_error"] = str(e)
    
    # Parse raid
    if files["raid"].exists():
        try:
            raid = RaidSaveCodec().parse(files["raid"])
            result["raid"] = extract_raid_summary(raid)
        except Exception as e:
            result["raid_error"] = str(e)
    
    return result


@app.get("/api/wallet")
async def get_wallet(profile: str | None = None):
    """Get wallet data."""
    profile_path = get_profile_path(profile)
    estate_path = profile_path / "persist.estate.json"
    
    if not estate_path.exists():
        raise HTTPException(status_code=404, detail="Estate file not found")
    
    try:
        estate = EstateSaveCodec().parse(estate_path)
        wallet = {}
        for field in estate.fields.values():
            if field.path.startswith("wallet.") and field.path.endswith(".amount"):
                key = field.path.split(".")[1]
                wallet[key] = int(field.value)
        return wallet
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wallet")
async def update_wallet(
    profile: str | None = None,
    gold: int | None = Form(None),
    bust: int | None = Form(None),
    portrait: int | None = Form(None),
    deed: int | None = Form(None),
    crest: int | None = Form(None),
    dry_run: bool = Form(False),
):
    """Update wallet values."""
    profile_path = get_profile_path(profile)
    
    updates = {}
    if gold is not None:
        updates["gold"] = gold
    if bust is not None:
        updates["bust"] = bust
    if portrait is not None:
        updates["portrait"] = portrait
    if deed is not None:
        updates["deed"] = deed
    if crest is not None:
        updates["crest"] = crest
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    try:
        engine = PatchEngine(backup_root=BACKUP_DIR)
        result = engine.apply_wallet_patch(
            profile_path,
            updates=updates,
            expected={},
            dry_run=dry_run,
            skip_backup=False,
        )
        return {
            "applied": result.applied,
            "dry_run": dry_run,
            "operations": [{"key": op.key, "new_value": op.new_value} for op in result.operations],
            "notes": result.notes,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/heroes")
async def get_heroes(profile: str | None = None):
    """Get heroes list."""
    profile_path = get_profile_path(profile)
    roster_path = profile_path / "persist.roster.json"
    
    if not roster_path.exists():
        raise HTTPException(status_code=404, detail="Roster file not found")
    
    try:
        roster = RosterSaveCodec().parse(roster_path)
        return {"heroes": extract_hero_summary(roster)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/heroes/{hero_index}")
async def update_hero(
    hero_index: int,
    profile: str | None = None,
    resolve_xp: int | None = Form(None),
    weapon_rank: int | None = Form(None),
    armour_rank: int | None = Form(None),
    dry_run: bool = Form(False),
):
    """Update hero stats."""
    profile_path = get_profile_path(profile)
    
    updates = {}
    if resolve_xp is not None:
        updates["resolve_xp"] = resolve_xp
    if weapon_rank is not None:
        updates["weapon_rank"] = weapon_rank
    if armour_rank is not None:
        updates["armour_rank"] = armour_rank
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    try:
        engine = PatchEngine(backup_root=BACKUP_DIR)
        result = engine.apply_hero_patch(
            profile_path,
            hero_index=hero_index,
            updates=updates,
            expected={},
            dry_run=dry_run,
            skip_backup=False,
        )
        return {
            "applied": result.applied,
            "dry_run": dry_run,
            "operations": [{"key": op.key, "new_value": op.new_value} for op in result.operations],
            "notes": result.notes,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/upgrades")
async def get_upgrades(profile: str | None = None):
    """Get upgrades data."""
    profile_path = get_profile_path(profile)
    upgrades_path = profile_path / "persist.upgrades.json"
    
    if not upgrades_path.exists():
        raise HTTPException(status_code=404, detail="Upgrades file not found")
    
    try:
        upgrades = UpgradesSaveCodec().parse(upgrades_path)
        return extract_upgrades_summary(upgrades)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/game")
async def get_game(profile: str | None = None):
    """Get game state."""
    profile_path = get_profile_path(profile)
    game_path = profile_path / "persist.game.json"
    
    if not game_path.exists():
        raise HTTPException(status_code=404, detail="Game file not found")
    
    try:
        game = GameSaveCodec().parse(game_path)
        return extract_game_summary(game)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game")
async def update_game(
    profile: str | None = None,
    inraid: int | None = Form(None),
    dd_options_altered: int | None = Form(None),
    dry_run: bool = Form(False),
):
    """Update game flags."""
    profile_path = get_profile_path(profile)
    
    updates = {}
    if inraid is not None:
        updates["inraid"] = inraid
    if dd_options_altered is not None:
        updates["dd_options_altered"] = dd_options_altered
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    try:
        engine = PatchEngine(backup_root=BACKUP_DIR)
        result = engine.apply_game_patch(
            profile_path,
            updates=updates,
            expected={},
            dry_run=dry_run,
            skip_backup=False,
        )
        return {
            "applied": result.applied,
            "dry_run": dry_run,
            "operations": [{"key": op.key, "new_value": op.new_value} for op in result.operations],
            "notes": result.notes,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/raid")
async def get_raid(profile: str | None = None):
    """Get raid state."""
    profile_path = get_profile_path(profile)
    raid_path = profile_path / "persist.raid.json"
    
    if not raid_path.exists():
        raise HTTPException(status_code=404, detail="Raid file not found")
    
    try:
        raid = RaidSaveCodec().parse(raid_path)
        return extract_raid_summary(raid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/raid")
async def update_raid(
    profile: str | None = None,
    teleported: int | None = Form(None),
    dry_run: bool = Form(False),
    allow_inbattle: bool = Form(False),
):
    """Update raid flags."""
    profile_path = get_profile_path(profile)
    
    updates = {}
    if teleported is not None:
        updates["teleported"] = teleported
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    try:
        engine = PatchEngine(backup_root=BACKUP_DIR)
        result = engine.apply_raid_patch(
            profile_path,
            updates=updates,
            expected={},
            dry_run=dry_run,
            skip_backup=False,
            allow_inbattle=allow_inbattle,
        )
        return {
            "applied": result.applied,
            "dry_run": dry_run,
            "operations": [{"key": op.key, "new_value": op.new_value} for op in result.operations],
            "notes": result.notes,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backups")
async def list_backups(profile: str | None = None):
    """List available backups."""
    profile_path = get_profile_path(profile)
    engine = PatchEngine(backup_root=BACKUP_DIR)
    backups = engine.list_backups(profile_path.name)
    return {
        "profile": profile_path.name,
        "backups": [str(b) for b in backups],
        "count": len(backups),
    }


@app.post("/api/backups")
async def create_backup(profile: str | None = None):
    """Create new backup."""
    profile_path = get_profile_path(profile)
    
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        engine = PatchEngine(backup_root=BACKUP_DIR)
        backup_path = engine.create_backup(profile_path)
        return {"created": str(backup_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/restore")
async def restore_backup(
    profile: str | None = None,
    backup_path: str = Form(...),
):
    """Restore from backup."""
    profile_path = get_profile_path(profile)
    backup = Path(backup_path)
    
    if not backup.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    
    try:
        engine = PatchEngine(backup_root=BACKUP_DIR)
        safety = engine.restore_backup(profile_path, backup, create_safety_backup=True)
        return {
            "restored": True,
            "safety_backup": str(safety) if safety else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/presets")
async def get_presets():
    """List available presets."""
    return {
        "presets": [
            {
                "name": p.name,
                "description": p.description,
                "supports_hero_index": p.supports_hero_index,
                "supports_resolve_xp": p.supports_resolve_xp,
            }
            for p in list_presets()
        ]
    }


@app.post("/api/presets/apply")
async def apply_preset(
    name: str = Form(...),
    profile: str | None = None,
    hero: int = Form(1),
    resolve_xp: int = Form(120),
    dry_run: bool = Form(False),
):
    """Apply a preset."""
    profile_path = get_profile_path(profile)
    
    try:
        manifest = build_manifest_for_preset(
            name=name,
            hero_index=hero,
            resolve_xp=resolve_xp,
        )
        engine = PatchEngine(backup_root=BACKUP_DIR)
        result = engine.apply_manifest_patch(
            profile_path,
            manifest,
            dry_run=dry_run,
            skip_backup=False,
        )
        return {
            "applied": result.applied,
            "dry_run": dry_run,
            "preset": name,
            "operations": [{"key": op.key, "new_value": op.new_value} for op in result.operations],
            "notes": result.notes,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
