# Bizon Dark Editor - Tutorial dla Laika 🎮

## Co to w ogóle jest?

**Bizon Dark Editor** to program do edycji zapisanych stanów gry (save'ów) z Darkest Dungeon. 

### Co to są "save'y"?

Gdy grasz w Darkest Dungeon, gra co jakiś czas zapisuje Twój postęp w specjalnych plikach. Te pliki nazywamy "save'ami" (zapisami). Znajdują się one w folderze gry i zawierają wszystkie informacje o Twoim posiadłości, bohaterach, złocie, itp.

### Po co ten program?

Czasami chcesz:
- **Dodać trochę złota** - bo ciężko Ci się gra i brakuje Ci pieniędzy
- **Uleczyć bohatera** - bo wszyscy Twoi heroisi są stresowani i chore
- **Zmienić poziom doświadczenia** - bo chcesz szybciej zobaczyć end-game
- **Naprawić zepsuty save** - bo gra się crashuje
- **Eksperymentować** - bo chcesz wypróbować różne buildy bez grindu

## Instalacja Krok po Kroku

### Krok 1: Znajdź folder z grą

Najpierw musisz wiedzieć, gdzie Darkest Dungeon trzyma swoje pliki.

**Na Macu:**
```
~/Library/Application Support/Darkest/profile_1
```

**Na Windows:**
```
C:\Users\TWOJA_NAZWA\AppData\Roaming\Darkest\profile_1
```

**Na Linux:**
```
~/.local/share/Darkest/profile_1
```

> 💡 **Wskazówka:** `~` oznacza Twój folder domowy. Na Macu to `/Users/twoja_nazwa`, na Windows `C:\Users\twoja_nazwa`.

### Krok 2: Pobierz program

1. Pobierz folder `bizon_dark` (cały projekt)
2. Rozpakuj go gdziekolwiek chcesz (np. na Pulpit)
3. Otwórz program **Terminal** (Mac/Linux) lub **Wiersz poleceń** (Windows)
4. Przejdź do folderu z programem:

```bash
cd ~/Desktop/bizon_dark  # lub gdziekolwiek go wypakowałeś
```

### Krok 3: Zainstaluj wymagane programy

Wpisz w terminalu (kopiuj-wklej):

```bash
python3 -m venv .venv
```

To stworzy wirtualne środowisko - tak jakby osobną "przestrzeń" dla tego programu.

Potem wpisz:

```bash
.venv/bin/pip install pytest fastapi uvicorn python-multipart jinja2
```

Na Windows:
```bash
.venv\Scripts\pip install pytest fastapi uvicorn python-multipart jinja2
```

To zainstaluje wszystkie potrzebne biblioteki.

### Krok 4: Sprawdź czy działa

Wpisz:

```bash
.venv/bin/python cli/main.py doctor
```

Jeśli widzisz zielone `[ok]` przy wszystkich linijkach - gratulacje! Wszystko działa! 🎉

Jeśli widzisz `[error]` lub `[warning]` - sprawdź czy:
- Masz zainstalowaną grę Darkest Dungeon
- Gra była przynajmniej raz uruchomiona (żeby utworzyła save'y)
- Ścieżka do profilu jest poprawna

## Jak tego używać?

### Sposób 1: Prosty GUI (polecane dla początkujących)

Najprostszy sposób to użycie przeglądarki internetowej:

```bash
.venv/bin/python gui-web/main.py
```

Potem otwórz w przeglądarce:
```
http://localhost:8000
```

Zobaczysz stronę z zakładkami:
- **Dashboard** - podsumowanie Twojego save'a
- **Wallet** - Twoje złoto i przedmioty
- **Heroes** - lista bohaterów
- **Upgrades** - ulepszenia posiadłości
- **Game** - ustawienia gry
- **Raid** - status wyprawy
- **Backup** - backupy i presety

**Jak edytować wartość:**
1. Wejdź w zakładkę (np. Wallet)
2. Zobaczysz aktualne wartości
3. Wypełnij formularz na dole
4. **ZAZNACZ** checkbox "Dry Run" (na początek)
5. Kliknij "Apply Changes"
6. Jeśli wszystko OK - odznacz "Dry Run" i kliknij jeszcze raz

> ⚠️ **WAŻNE:** Zawsze najpierw użyj "Dry Run" (próbny przebieg). To pokazuje co się zmieni, ale NIE zapisuje zmian. Dopiero kiedy widzisz, że wszystko jest OK - wyłącz Dry Run i zatwierdź na prawdę.

### Sposób 2: CLI (dla zaawansowanych)

CLI (Command Line Interface) to program działający w terminalu. Jest szybszy, ale wymaga wpisywania komend.

#### Podstawowe komendy:

**Sprawdź ile masz złota:**
```bash
.venv/bin/python cli/main.py list-wallet
```

Wynik:
```
gold=1500
bust=25
portrait=10
deed=5
crest=100
```

**Zmień ilość złota (najpierw dry-run!):**
```bash
.venv/bin/python cli/main.py patch-wallet --set gold=99999 --dry-run
```

Jeśli widzisz `[dry-run]` i wartości się zgadzają - wykonaj bez `--dry-run`:
```bash
.venv/bin/python cli/main.py patch-wallet --set gold=99999
```

**Zobacz listę bohaterów:**
```bash
.venv/bin/python cli/main.py list-heroes
```

Wynik:
```
1: Reynauld (crusader) resolve_xp=0
2: Dismas (highwayman) resolve_xp=12
3: Audrey (plague_doctor) resolve_xp=45
```

**Zmień doświadczenie bohatera:**
```bash
.venv/bin/python cli/main.py patch-hero --hero 1 --set resolve_xp=100 --dry-run
```

**Ustaw wszystkich bohaterów na max:**
```bash
.venv/bin/python cli/main.py patch-hero --hero 1 --set resolve_xp=999 --dry-run
.venv/bin/python cli/main.py patch-hero --hero 2 --set resolve_xp=999 --dry-run
.venv/bin/python cli/main.py patch-hero --hero 3 --set resolve_xp=999 --dry-run
# itd...
```

## Co możesz edytować?

### Wallet (Portfel) - `patch-wallet`
- `gold` - złoto 💰
- `bust` - popiersia 🗿
- `portrait` - portrety 🖼️
- `deed` - akty własności 📜
- `crest` - herby 🛡️

### Bohater - `patch-hero`
- `resolve_xp` - doświadczenie (poziom stresu/zaradności)
- `weapon_rank` - poziom broni (0-5)
- `armour_rank` - poziom pancerza (0-5)

### Gra - `patch-game`
- `inraid` - czy jesteś na wyprawie (0 = miasto, 1 = dungeon)
- `dd_options_altered` - czy opcje były zmieniane

### Raid (Wyprawa) - `patch-raid`
- `inbattle` - czy trwa walka ⚠️
- `teleported` - czy byłeś teleportowany
- `torchlight` - poziom pochodni
- I inne...

### Opcje - `patch-options`
- `language` - język (np. `english`, `polish`)
- `fullscreen` - pełny ekran (0 lub 1)
- `resolution_width` - szerokość ekranu
- `resolution_height` - wysokość ekranu
- `tutorial` - włączony tutorial (0 lub 1)

## Bezpieczeństwo - Jak nie zepsuć save'a?

### Zasada 1: Zawsze rób backup!

Przed KAŻDĄ zmianą:
```bash
.venv/bin/python cli/main.py backup
```

To stworzy kopię zapasową w folderze `backups/`.

### Zasada 2: Zawsze używaj --dry-run

Najpierw:
```bash
--dry-run
```

Sprawdź czy wynik wygląda OK, dopiero potem uruchom bez `--dry-run`.

### Zasada 3: Używaj --expect dla bezpieczeństwa

Jeśli chcesz zmienić złoto z 1500 na 99999, ale tylko jeśli masz DOKŁADNIE 1500:

```bash
.venv/bin/python cli/main.py patch-wallet --set gold=99999 --expect gold=1500 --dry-run
```

Jeśli masz inną ilość złota niż 1500, program się wysypie i NIC nie zmieni. To chroni przed przypadkowym nadpisaniem.

### Zasada 4: Nie edytuj podczas walki!

Jeśli `inbattle=1` (trwa walka), nie edytuj raidu! To może zepsuć save'a.

Jeśli MUSISZ edytować podczas walki (np. naprawić zepsuty save), użyj:
```bash
--allow-inbattle
```

Ale robisz to na własne ryzyko!

## Presety - Gotowe ustawienia

Masz do dyspozycji gotowe "presety" - zestawy zmian:

```bash
.venv/bin/python cli/main.py list-presets
```

Dostępne presety:

1. **economy-rich** - Maksymalne złoto i przedmioty
   ```bash
   .venv/bin/python cli/main.py apply-preset --name economy-rich --dry-run
   ```

2. **starter-boost** - Mały boost na start kampanii
   ```bash
   .venv/bin/python cli/main.py apply-preset --name starter-boost --dry-run
   ```

3. **hero-resolve-boost** - Zwiększ doświadczenie konkretnego bohatera
   ```bash
   .venv/bin/python cli/main.py apply-preset --name hero-resolve-boost --hero 1 --resolve-xp 200 --dry-run
   ```

4. **game-town-state** - Wróć do miasta (wyjdź z dungeonu)
   ```bash
   .venv/bin/python cli/main.py apply-preset --name game-town-state --dry-run
   ```

## Przywracanie backupu

Jeśli coś poszło nie tak:

```bash
# Zobacz listę backupów
.venv/bin/python cli/main.py list-backups

# Przywróć najnowszy
.venv/bin/python cli/main.py restore --latest

# Albo przywróć konkretny
.venv/bin/python cli/main.py restore --from-backup "nazwa_backupu"
```

## Częste Problemy

### "File not found"
Sprawdź czy:
- Masz zainstalowaną grę
- Gra była uruchomiona przynajmniej raz
- Ścieżka do profilu jest poprawna

### "Active raid detected"
Jesteś na wyprawie (w dungeonie). Wróć do miasta i zapisz grę, albo użyj `--allow-inbattle` (ryzykowne!)

### "Current mismatch"
Wartość w `--expect` nie zgadza się z rzeczywistą wartością w save'ie. Sprawdź aktualne wartości przez `list-*`.

### "Validation failed"
Zmiany spowodowałyby nieprawidłowości w save'ie. Użyj `--strict` aby traktować ostrzeżenia jako błędy.

## Słowniczek

- **Save** - zapisany stan gry
- **Backup** - kopia zapasowa save'a
- **Dry run** - próbny przebieg (bez zapisywania zmian)
- **CLI** - wiersz poleceń (terminal)
- **GUI** - graficzny interfejs użytkownika (strona www)
- **Profile** - folder z save'ami (np. `profile_1`)
- **Patch** - zmiana/wizja w pliku save'a
- **Preset** - gotowy zestaw zmian

## Podsumowanie

1. **Zainstaluj** - `pip install ...`
2. **Sprawdź** - `python cli/main.py doctor`
3. **Zrób backup** - `python cli/main.py backup`
4. **Sprawdź wartości** - `python cli/main.py list-wallet`
5. **Dry run** - `python cli/main.py patch-wallet --set gold=999 --dry-run`
6. **Zatwierdź** - (bez `--dry-run`)
7. **Ciesz się grą!** 🎮

## Potrzebujesz więcej pomocy?

- Pełna dokumentacja: `docs/DOKUMENTACJA_AKTUALNA.md`
- Raport techniczny: `RAPORT_KONCOWY_AGENTA.md`
- Lista zmian: `RELEASE_CHECKLIST.md`

**Pamiętaj: Zawsze rób backup przed edycją!** 💾
