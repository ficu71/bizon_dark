# Data Contract V1

## Cele kontraktu

- Jednoznaczne mapowanie: binary <-> model domenowy <-> API CLI/GUI.
- Zachowanie nieznanych segmentow bajtowych (lossless).
- Stabilna polityka bledow i walidacji.

## Kontrakty glowne

- `ParsedSaveFile`
- `ParsedField`
- `UnknownSegment`
- `RoundTripReport`
- `ValidationIssue`

## Reguly

- Wartosci liczbowe domyslnie jako unsigned little-endian, chyba ze sekcja wymaga inaczej.
- Kazde pole ma:
  - `field_path` (kanoniczna sciezka)
  - `file_name`
  - `offset/range`
  - `type_name`
- Nieznane fragmenty musza byc odtworzone 1:1 przy zapisie.

## Polityka bledow

- `error`: zapis/podmiana zablokowane.
- `warning`: zapis dopuszczony tylko w trybie `--force` (v1.1).
- `info`: diagnostyka.

## Versioning

- `format_version` per plik `persist.*`.
- Zmiany niekompatybilne: podbicie major kontraktu.
