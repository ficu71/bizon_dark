## 2025-05-15 - Poprawa interakcji w listach dynamicznych
**Learning:** W interfejsach zarządzających listami elementów (np. lista bohaterów), zastępowanie całej listy wynikiem pojedynczej operacji niszczy kontekst użytkownika i zmusza go do ponownego nawigowania. Wyniki operacji powinny być wyświetlane lokalnie wewnątrz elementu lub jako nieinwazyjne powiadomienia.
**Action:** Zawsze projektuj kontenery na komunikaty zwrotne (success/error) wewnątrz kart elementów listy, jeśli operacja dotyczy konkretnego elementu.
