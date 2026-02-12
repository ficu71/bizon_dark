# Pelna Dokumentacja Stanu Projektu (stan na 2026-02-12)

## 1) Cel projektu

`Bizon Dark Editor` to lokalny edytor save'ow Darkest Dungeon bez `DDSaveEditor.jar`.
Projekt ma wspolny rdzen (`core`) i CLI operatorskie.

## 2) Aktualny status

- Dziala transakcyjny patch engine: backup -> stage -> validate -> atomic replace.
- Dzialaja patche: wallet, hero, upgrades, game, loading, raid, options.
- Dziala import manifestu wielosekcyjnego w jednej transakcji.
- Dziala system presetow (`list-presets`, `apply-preset`).
- Dziala tryb `--strict` (warnings traktowane jako blokujace).
- Dziala backup/restore/diff/inspect/export.
- Dzialaja walidacje strukturalne + cross-file.
- CLI: patch-options dla bezpiecznych pol options (language, subtitles, fullscreen, tutorial, allow_analytics_and_multiplayer, resolution).
- Testy: `83 passed`.

## Postęp v1 (etapy 1-12)

- [x] Etap 1: Kontrakty i szkielety modułów
- [x] Etap 2: Corpus + fixture'y
- [x] Etap 3: Codec R/W dla wszystkich plików
- [x] Etap 4: Writer lossless
- [x] Etap 5: Walidator cross-file + strukturalny
- [x] Etap 6: Patch engine transakcyjny (wallet, hero, upgrades, game, loading, raid, options) + manifest + strict
- [x] Etap 7: Moduły edycyjne - patche dla loading_screen, options (bezpieczne pola JSON)
- [x] Etap 8: CLI operatorskie (list-*, patch-*, validate, import, export, presets, backup/restore)
- [x] Etap 9: GUI lokalne MVP (FastAPI) - Dashboard, Wallet, Heroes, Upgrades, Game, Raid, Backup, Presets
- [x] Etap 10: QA i regresja - 86 testow
- [x] Etap 11: Hardening UX - czytelne błędy, komunikaty ryzyka, hinty dla użytkownika
- [x] Etap 12: Release - dokumentacja zaktualizowana, checklista, tutorial dla laika

**Progres: ~100%**

## GUI Web MVP (FastAPI)

Uruchomienie:
```bash
.venv/bin/python gui-web/main.py
```

Lub:
```bash
.venv/bin/uvicorn gui-web.main:app --reload --port 8000
```

Widoki dostępne pod `http://localhost:8000`:
- **Dashboard** - podsumowanie profilu, status plików
- **Wallet** - edycja gold/bust/portrait/deed/crest
- **Heroes** - lista bohaterów, edycja resolve_xp/weapon_rank/armour_rank
- **Upgrades** - podsumowanie upgrade'ów
- **Game** - flagi inraid, dd_options_altered
- **Raid** - flagi raid (teleported, inbattle)
- **Backup** - lista backupów, restore, presety

Funkcje:
- Dry-run dla wszystkich operacji modyfikujących
- Automatyczny backup przed zmianami
- Obsługa presetów (economy-rich, starter-boost, hero-resolve-boost, game-town-state)

## 3) Struktura repo

- `core/codec` - parse/write binarne i JSON.
- `core/patch` - logika patchowania i transakcji.
- `core/validate` - reguly spojnosci.
- `cli/main.py` - komendy operatorskie.
- `tests/` - testy codec/patch/engine/validation.
- `docs/` - plan i dokumentacja.

## 4) Obslugiwane pliki `persist.*`

| Plik | Odczyt | Zapis | Patch CLI | Walidacja |
|---|---|---|---|---|
| `persist.estate.json` | tak | tak | `patch-wallet` | tak |
| `persist.roster.json` | tak | tak | `patch-hero` | tak |
| `persist.upgrades.json` | tak | tak | `patch-upgrades` | tak |
| `persist.map.json` | tak | read-only | brak | tak |
| `persist.game.json` | tak | tak | `patch-game` | tak |
| `persist.raid.json` | tak | tak | `patch-raid` | tak |
| `persist.tutorial.json` | tak | read-only | brak | tak |
| `persist.narration.json` | tak | read-only | brak | tak |
| `persist.loading_screen.json` | tak | tak | `patch-loading` | tak |
| `persist.options.json` | tak | tak | `patch-options` | tak (jesli plik istnieje) |

## 5) Patchowalne pola (v1)

- `patch-wallet`: `gold`, `bust`, `portrait`, `deed`, `crest`.
- `patch-hero`: `resolve_xp`, `weapon_rank`, `armour_rank`.
- `patch-upgrades`: klucze typu `class.skill` (`0/1`).
- `patch-game`: `inraid`, `dd_options_altered`.
- `patch-loading`: `version`, `title_id`, `tip_id`, `narration_entry_id`.
- `patch-raid`: `inbattle`, `teleported`, `has_mash_data`, `implied`, `is_plot_quest`, `counted_in_generation`, `use_default_progression_goals`, `is_from_town_event`.
- `patch-options`: `language`, `subtitles`, `fullscreen`, `tutorial`, `allow_analytics_and_multiplayer`, `resolution_width`, `resolution_height`.

**Uwaga**: `patch-options` pozwala edytować tylko bezpieczne pola preferencji. Pola krytyczne (cloud saves, DLC, itp.) są zablokowane.

## 6) Komendy CLI

Diagnostyka:

- `doctor`, `validate`, `inspect`
- `list-wallet`, `list-heroes`, `list-upgrades`, `list-map`, `list-game`, `list-raid`, `list-tutorial`, `list-narration`, `list-loading-screen`, `list-options`

Backup/restore/diff:

- `backup`
- `list-backups`
- `diff`
- `restore`

Snapshot/manifest:

- `export --output snapshot.json`
- `import --file manifest.json`

Presety:

- `list-presets`
- `apply-preset --name <preset>`

Patch:

- `patch-wallet`
- `patch-hero`
- `patch-upgrades`
- `patch-game`
- `patch-loading`
- `patch-raid`
- `patch-options`

Globalne opcje:

- `--profile`
- `--options-file`
- `--strict` (dla `validate`, `patch-*`, `import`, `apply-preset`)

## 7) Manifest importu

Format:

```json
{
  "wallet": { "set": {}, "expect": {} },
  "heroes": [
    { "hero": 1, "set": {}, "expect": {} }
  ],
  "upgrades": { "set": {}, "expect": {} },
  "game": { "set": {}, "expect": {} },
  "loading": { "set": {}, "expect": {} },
  "options": { "set": {}, "expect": {} },
  "raid": { "set": {}, "expect": {} }
}
```

Uwagi:

- Sekcje sa opcjonalne.
- Aliasowanie kluczy dziala tak samo jak w `patch-*`.
- Sekcja `options` respektuje `--options-file` i domyslna lokalizacje obok `profile_*`.
- Import jest jedna transakcja (jedna walidacja i jeden commit).

## 8) Bezpieczenstwo

- `dry-run` dla patch/import.
- `expect` jako guard wartosci biezacej.
- Domyslny backup przed zapisem (mozna `--skip-backup`).
- `restore` domyslnie tworzy safety backup.
- `patch-raid` i `import` respektuja guard `inbattle` (chyba ze `--allow-inbattle`).
- Atomic replace + cleanup stage.

## 9) Walidacje

Strukturalne:

- estate, upgrades, map, game, raid, tutorial, narration, loading, options.

Cross-file:

- estate <-> roster
- roster <-> upgrades
- roster <-> map

## 10) Testy

Zakres:

- codec round-trip/parsing dla wszystkich obslugiwanych plikow
- patch module tests
- patch engine tests (commit/dry-run/backup/restore/manifest/inbattle guard)
- validation tests (strukturalne + cross-file)

Uruchomienie:

```bash
python3 -m py_compile core/codec/*.py core/patch/*.py core/validate/*.py cli/main.py tests/test_*.py
python3 -m pytest -q
```

## 11) Ograniczenia v1

- Brak GUI produkcyjnego (FastAPI MVP niezaimplementowane).
- Brak patchy dla `map/tutorial/narration` (read-only - wymagają bezpiecznego writera lossless).
- Brak gotowego raw expert edytora.

## 12) Najblizsze kroki

- [ ] Etap 9: GUI lokalne MVP na FastAPI (Dashboard, Wallet, Heroes, Upgrades, Game/Raid, Backup/Restore, Diff).
- [ ] Etap 11: Hardening UX - czytelne błędy, komunikaty ryzyka, blokady operacji niebezpiecznych.
- [ ] Etap 12: Finalna dokumentacja + checklista release.
- [ ] Rozszerzenie presetów o nowe warianty (economy-richer, hero-max-stats, itp.).
- [ ] Patchowalne pola w `map/tutorial/narration` (jeśli bezpieczne).
