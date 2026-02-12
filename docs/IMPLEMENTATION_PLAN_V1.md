# Plan Implementacji V1

To jest wykonawczy plan budowy kompletnego save/game editora bez DDSaveEditor.jar.

## Etapy

1. Specyfikacja i kontrakty danych
2. Corpus + fixture'y
3. Codec read-only
4. Codec writer lossless
5. Walidator spojnosc
6. Patch engine transakcyjny
7. Moduly edycyjne
8. Produkcyjne CLI
9. Lokalny GUI
10. QA i regresja
11. Hardening UX
12. Release v1

## Priorytety

1. Economy + backup/restore + validate
2. Heroes
3. Buildings/upgrades + progression
4. Raw editor + preset manager

## Progress (2026-02-12)

- [x] Etap 1: kontrakty i szkielety modułów
- [x] Etap 2: plan corpus + fixture bootstrap
- [~] Etap 3: codec `persist.estate`, `persist.roster`, `persist.upgrades`, `persist.map`, `persist.game`, `persist.raid`, `persist.loading_screen` (R/W na polach bezpiecznych) + read-only `persist.tutorial`, `persist.narration`, `persist.options`
- [~] Etap 5: walidator cross-file (`estate` <-> `roster` <-> `upgrades` <-> `map`) + strukturalny `game`, `raid`, `tutorial`, `narration`, `loading_screen`, `options` + tryb `strict`
- [~] Etap 6: patch engine transakcyjny (wallet + hero + upgrades + game + loading + raid z guardem `allow_inbattle`) + restore backup + manifest import (multi-patch transaction)
- [~] Etap 8: CLI rozszerzone o komendy diagnostyczne i patch (`list-*`, `validate`, `patch-*`, `inspect`, `list-backups`, `diff`, `restore`, `export`, `import`, `list-presets`, `apply-preset`)
- [~] Etap 7: moduly edycyjne - gotowe presety v1 (`list-presets`, `apply-preset`)
- [ ] Etapy 9-12
