# Bizon Dark Editor v1.0

Własny edytor save'ów Darkest Dungeon bez DDSaveEditor.jar.

**Status:** v1.0 - Pełna funkcjonalność CLI + GUI Web MVP

---

## Szybki Start

```bash
# Instalacja
python3 -m venv .venv
.venv/bin/pip install pytest fastapi uvicorn python-multipart jinja2

# Weryfikacja
.venv/bin/python cli/main.py doctor

# GUI Web
.venv/bin/python gui-web/main.py
# Otwórz http://localhost:8000
```

---

## Funkcje

### CLI - Komendy

**Diagnostyka:**
```bash
.venv/bin/python cli/main.py doctor                    # Sprawdź profil
.venv/bin/python cli/main.py validate                  # Walidacja
.venv/bin/python cli/main.py validate --strict         # Strict mode
.venv/bin/python cli/main.py inspect                   # Pełny snapshot
```

**Listowanie danych:**
```bash
.venv/bin/python cli/main.py list-wallet
.venv/bin/python cli/main.py list-heroes
.venv/bin/python cli/main.py list-upgrades
.venv/bin/python cli/main.py list-game
.venv/bin/python cli/main.py list-raid
.venv/bin/python cli/main.py list-options
```

**Edycja (zawsze używaj --dry-run najpierw!):**
```bash
# Wallet
.venv/bin/python cli/main.py patch-wallet --set gold=99999 --dry-run
.venv/bin/python cli/main.py patch-wallet --set gold=99999 --expect gold=1000

# Bohater
.venv/bin/python cli/main.py patch-hero --hero 1 --set resolve_xp=120 --dry-run

# Game / Raid
.venv/bin/python cli/main.py patch-game --set inraid=0 --dry-run
.venv/bin/python cli/main.py patch-raid --set teleported=1 --dry-run

# Opcje
.venv/bin/python cli/main.py patch-options --set language=polish --dry-run
.venv/bin/python cli/main.py patch-options --set fullscreen=1 --set resolution_width=1920 --dry-run
```

**Presety:**
```bash
.venv/bin/python cli/main.py list-presets
.venv/bin/python cli/main.py apply-preset --name economy-rich --dry-run
.venv/bin/python cli/main.py apply-preset --name hero-resolve-boost --hero 1 --dry-run
```

**Backup/Restore:**
```bash
.venv/bin/python cli/main.py backup
.venv/bin/python cli/main.py list-backups
.venv/bin/python cli/main.py restore --latest
.venv/bin/python cli/main.py diff --latest
```

**Import/Export:**
```bash
.venv/bin/python cli/main.py export --output mysave.json
.venv/bin/python cli/main.py import --file manifest.json --dry-run
```

### GUI Web

```bash
.venv/bin/python gui-web/main.py
```

Dostępne pod `http://localhost:8000`:
- **Dashboard** - podsumowanie profilu
- **Wallet** - edycja zasobów
- **Heroes** - lista i edycja bohaterów
- **Upgrades** - podsumowanie upgrade'ów
- **Game** - flagi gry
- **Raid** - flagi raid
- **Backup** - backup/restore/presety

---

## Struktura Projektu

```
bizon_dark/
├── cli/                    # CLI operatorskie
│   └── main.py            # Główny plik CLI
├── core/                   # Rdzeń edytora
│   ├── codec/             # Parsery plików JSON/binarnych
│   ├── patch/             # Silnik patchy transakcyjnych
│   ├── validate/          # Walidacja spójności
│   ├── presets/           # Presety gotowych modyfikacji
│   └── schema/            # Modele danych
├── gui-web/               # GUI Web (FastAPI)
│   ├── main.py           # Backend
│   ├── static/           # CSS/JS
│   └── templates/        # HTML
├── docs/                  # Dokumentacja
├── tests/                 # Testy (86 testow)
└── profile_1/            # Przykładowy profil
```

---

## Bezpieczeństwo

⚠️ **WAŻNE:**

1. **Zawsze używaj `--dry-run` przed właściwą zmianą**
2. **Automatyczny backup** jest tworzony przed każdą modyfikacją
3. **Guard `expect`** pozwala weryfikować aktualne wartości
4. **Tryb `--strict`** traktuje warningi jako błędy
5. **Blokada `inbattle`** - nie można modyfikować raidu podczas walki (chyba że `--allow-inbattle`)

### Backup Policy

- Każda operacja `patch-*`, `import`, `apply-preset`, `restore` tworzy backup
- Backupy są w katalogu `backups/`
- `restore` tworzy dodatkowy "safety backup" przed przywróceniem
- Backup zawiera cały profil (wszystkie pliki persist.*)

---

## Obsługiwane Pliki

| Plik | Odczyt | Zapis | Patch CLI |
|------|--------|-------|-----------|
| `persist.estate.json` | ✅ | ✅ | `patch-wallet` |
| `persist.roster.json` | ✅ | ✅ | `patch-hero` |
| `persist.upgrades.json` | ✅ | ✅ | `patch-upgrades` |
| `persist.game.json` | ✅ | ✅ | `patch-game` |
| `persist.raid.json` | ✅ | ✅ | `patch-raid` |
| `persist.loading_screen.json` | ✅ | ✅ | `patch-loading` |
| `persist.options.json` | ✅ | ✅ | `patch-options` |
| `persist.map.json` | ✅ | ❌ | - |
| `persist.tutorial.json` | ✅ | ❌ | - |
| `persist.narration.json` | ✅ | ❌ | - |

---

## Testy

```bash
# Wszystkie testy
.venv/bin/python -m pytest -q

# 86 passed
```

---

## Wymagania

- Python 3.11+
- macOS (testowane) / Linux / Windows
- Darkest Dungeon (pliki save w formacie JSON)

---

## Ograniczenia v1.0

- Map, Tutorial, Narration są read-only (wymagają bezpiecznego writera lossless)
- Brak edytora raw/binarnego
- Testowane głównie na macOS

---

## Dokumentacja

**📖 Zacznij od tutoriala dla początkujących:**  
👉 `docs/TUTORIAL_LAIKA.md` - Łopatologiczne wyjaśnienie co to jest, jak zainstalować i używać

Pełna dokumentacja techniczna: `docs/DOKUMENTACJA_AKTUALNA.md`

Plan implementacji: `docs/IMPLEMENTATION_PLAN_V1.md`

Checklista release: `RELEASE_CHECKLIST.md`

---

## Licencja

Projekt edukacyjny - używaj na własne ryzyko. Zawsze rób backup save'ów!
