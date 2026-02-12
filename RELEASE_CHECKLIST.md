# Bizon Dark Editor v1.0 - Release Checklist

## Weryfikacja Przed Release

### ✅ Testy
- [x] Wszystkie testy przechodzą: `83 passed`
- [x] `python3 -m py_compile` dla wszystkich plików .py
- [x] CLI komendy działają
- [x] GUI startuje bez błędów

### ✅ Funkcjonalność
- [x] CLI: Wszystkie komendy list-* działają
- [x] CLI: Wszystkie komendy patch-* działają
- [x] CLI: Backup/restore działa
- [x] CLI: Import/export manifestu działa
- [x] CLI: Presety działają
- [x] GUI: Dashboard wyświetla dane
- [x] GUI: Formularze edycji działają
- [x] GUI: Dry-run działa
- [x] GUI: Backup/restore działa

### ✅ Dokumentacja
- [x] README.md zaktualizowane
- [x] DOKUMENTACJA_AKTUALNA.md zaktualizowane
- [x] RAPORT_KONCOWY_AGENTA.md utworzony
- [x] RELEASE_CHECKLIST.md utworzony

### ✅ Bezpieczeństwo
- [x] Dry-run dla wszystkich operacji modyfikujących
- [x] Automatyczny backup przed zmianami
- [x] Guard `expect` działa
- [x] Tryb `--strict` działa
- [x] Blokada `inbattle` działa
- [x] Czytelne komunikaty błędów

### ✅ Kod
- [x] Wszystkie pliki kompilują się
- [x] Brak błędów importów
- [x] Brak błędów składniowych
- [x] Struktura katalogów poprawna

## Pliki Dołączone Do Release

### Główne
- `cli/main.py` - CLI operatorskie
- `gui-web/main.py` - GUI backend
- `gui-web/static/style.css` - GUI styles
- `gui-web/static/app.js` - GUI frontend
- `gui-web/templates/dashboard.html` - GUI template

### Core
- `core/codec/*.py` - Kodeki dla wszystkich plików
- `core/patch/*.py` - Silnik patchy
- `core/validate/*.py` - Walidacja
- `core/presets/*.py` - Presety

### Testy
- `tests/test_*.py` - 83 testy

### Dokumentacja
- `README.md`
- `docs/DOKUMENTACJA_AKTUALNA.md`
- `docs/IMPLEMENTATION_PLAN_V1.md`
- `RAPORT_KONCOWY_AGENTA.md`
- `RELEASE_CHECKLIST.md`

## Instrukcja Instalacji

```bash
# 1. Klonowanie repozytorium
git clone <repo-url>
cd bizon_dark

# 2. Tworzenie venv
python3 -m venv .venv

# 3. Instalacja zależności
.venv/bin/pip install pytest fastapi uvicorn python-multipart jinja2

# 4. Weryfikacja
.venv/bin/python cli/main.py doctor
.venv/bin/python -m pytest -q

# 5. Uruchomienie GUI
.venv/bin/python gui-web/main.py
# Otwórz http://localhost:8000
```

## Znane Ograniczenia

1. Map, Tutorial, Narration są read-only
2. Brak edytora raw/binarnego
3. Testowane głównie na macOS
4. Wymaga Python 3.11+

## Następne Wersje

### v1.1 (Potencjalne)
- [ ] Więcej pól w patch-options
- [ ] Wsparcie dla map/tutorial/narration (jeśli bezpieczne)
- [ ] Lepsze walidacje zakresów wartości
- [ ] Więcej presetów

### v2.0 (Daleka przyszłość)
- [ ] Edytor raw/binarny
- [ ] GUI desktopowe (PyQt/Electron)
- [ ] Wsparcie dla modów
- [ ] Cloud sync backupów

---

**Status:** ✅ READY FOR RELEASE

**Data:** 2026-02-12

**Wersja:** 1.0.0
