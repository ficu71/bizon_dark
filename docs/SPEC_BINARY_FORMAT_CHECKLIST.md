# Checklista Specyfikacji Binarnej

## 1. Metadane pliku

- [ ] Zidentyfikowany naglowek
- [ ] Zidentyfikowana wersja formatu
- [ ] Zidentyfikowana tabela/offsety sekcji
- [ ] Potwierdzona endianness

## 2. Tokenizacja i struktura

- [ ] Separator stringow i dlugosci nazw
- [ ] Reprezentacja int32/u32/i64/f32/bool
- [ ] Reprezentacja list/map/obiektow
- [ ] Reprezentacja null/empty

## 3. Pole -> offset

- [ ] `persist.estate.json`: wallet, trinkets, estate_items
- [ ] `persist.roster.json`: heroes, stats, skills, quirks, diseases
- [ ] `persist.game.json`: mode, date_time, flags
- [ ] `persist.upgrades.json`: unlocks i ranki budynkow
- [ ] `persist.map.json`: region state i progression
- [ ] `persist.raid.json`: aktywny raid i guardy
- [ ] `persist.narration/tutorial/loading_screen`: flagi pomocnicze

## 4. Lossless strategy

- [ ] Segmentacja: known vs unknown
- [ ] Odtworzenie nieznanych segmentow 1:1
- [ ] Round-trip na pliku bez zmian logicznych

## 5. Bezpieczenstwo zapisu

- [ ] Backup snapshot przed zapisem
- [ ] Walidacja pre-write
- [ ] Walidacja post-write
- [ ] Atomic replace
- [ ] Auto-rollback po bledzie

## 6. Testy

- [ ] Round-trip unit test per `persist.*`
- [ ] Integracja multi-file
- [ ] Regresja na corpusie fixture'ow
- [ ] Przynajmniej 20 scenariuszy e2e
