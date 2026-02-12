## 2025-05-15 - Poprawa interakcji w listach dynamicznych
**Learning:** W interfejsach zarządzających listami elementów (np. lista bohaterów), zastępowanie całej listy wynikiem pojedynczej operacji niszczy kontekst użytkownika i zmusza go do ponownego nawigowania. Wyniki operacji powinny być wyświetlane lokalnie wewnątrz elementu lub jako nieinwazyjne powiadomienia.
**Action:** Zawsze projektuj kontenery na komunikaty zwrotne (success/error) wewnątrz kart elementów listy, jeśli operacja dotyczy konkretnego elementu.

## 2026-02-12 - Spójność tematyczna i stany ładowania w edytorach gier
**Learning:** W narzędziach fanowskich do gier (jak Darkest Dungeon), immersion (zanurzenie) w klimacie gry znacząco poprawia UX. Zastosowanie specyficznej terminologii (np. „Trzos” zamiast „Portfel”) i stylistyki (czcionki szeryfowe, kolory „krwi i żelaza”) sprawia, że narzędzie staje się przedłużeniem gry. Dodatkowo, operacje patchowania plików są asynchroniczne, więc brak blokady przycisków i wizualnego potwierdzenia „Przetwarzanie...” prowadzi do niepewności użytkownika.
**Action:** Implementuj jawne stany `.btn-loading` z disableniem przycisków i spójną mapę tłumaczeń kluczy technicznych na nazwy znane graczom.
