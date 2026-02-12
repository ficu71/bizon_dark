# `darkest_tool.py` - wlasne narzedzie do edycji sejwow Darkest Dungeon

Plik: `darkest_tool.py`
Katalog: `/Users/f1cu_71/Desktop/bizon_dark`
Domyslny profil: `/Users/f1cu_71/Library/Application Support/Darkest/profile_1`

## Co robi (bez DDSaveEditor.jar)

To jest **wlasny patcher** binarny dla `persist.estate.json`.
Nie potrzebuje Javy ani zewnetrznych editorow.

Obsluguje:
- backup calego `profile_1`
- odczyt walletu (`gold`, `bust`, `portrait`, `deed`, `crest`)
- patch walletu bezposrednio w binarnym save
- bezpieczne warunki `--expect` (nie patchuje, jesli wartosc sie nie zgadza)
- tryb 1-komendowy (`quick-wallet`)

## Podstawowe komendy

```bash
cd "/Users/f1cu_71/Desktop/bizon_dark"

# 1) diagnostyka
python3 darkest_tool.py doctor

# 2) podglad aktualnych wartosci wallet
python3 darkest_tool.py list-wallet

# 3) backup profilu
python3 darkest_tool.py backup

# 4) test patcha bez zapisu
python3 darkest_tool.py patch-wallet --set gold=999999 --expect gold=0 --dry-run

# 5) patch z zapisem
python3 darkest_tool.py patch-wallet --set gold=999999 --expect gold=0
```

## Tryb 1-komendowy (backup + patch)

```bash
python3 darkest_tool.py quick-wallet \
  --set gold=999999 \
  --set crest=999 \
  --expect gold=0 \
  --expect crest=20
```

Tryb bez zapisu:

```bash
python3 darkest_tool.py quick-wallet \
  --set gold=999999 \
  --expect gold=0 \
  --dry-run
```

## Bezpieczenstwo

- zawsze zamknij gre przed edycja
- `backup` tworzy timestampowany snapshot calego profilu
- `--expect` chroni przed edycja zlego rekordu
- wartosci musza byc w zakresie `0..4294967295`

## Uwaga

Aktualna wersja patchuje **wallet** w `persist.estate.json`.
Jesli chcesz, nastepny krok to rozszerzenie o inne sekcje (np. roster/bohaterowie).
