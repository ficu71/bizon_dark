# Corpus i Fixture'y

## Cel

Zbudowac reprezentatywny zestaw save'ow do testow round-trip i regresji.

## Profil fixture

Kazdy fixture powinien miec metadane:

- `fixture_id`
- `game_build`
- `dlc_enabled`
- `campaign_stage`
- `active_raid`
- `notable_states` (np. 0 gold, max stress, hero dead)

## Kategorie fixture'ow

1. Fresh campaign
2. Mid campaign
3. Late campaign
4. Active raid
5. High-stress/edge values
6. Corrupted/minimally broken samples

## Struktura katalogu

- `tests/fixtures/raw/<fixture_id>/profile_1/persist.*`
- `tests/fixtures/manifest.json`
- `tests/fixtures/snapshots/<fixture_id>/`

## Zasady

- Surowe fixture'y trzymac lokalnie (bez wrzucania prywatnych danych do zdalnego repo).
- W repo trzymac metadane i minimalne sample zanonimizowane.
