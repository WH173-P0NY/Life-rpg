# Life RPG Tracker - przyszly modul finansow

## Status

Modul finansow jest odlozony poza MVP aplikacji RPG.

Ten plik sluzy jako miejsce na przyszle decyzje produktowe i techniczne. Nie powinien blokowac implementacji etapu 1.

## Cel przyszlego modulu

Modul finansow ma pomoc uzytkownikowi zarzadzac pieniedzmi w sposob kompatybilny z systemem rozwoju osobistego.

Mozliwe cele:

- sledzenie przychodow i wydatkow,
- budzety miesieczne,
- cele oszczednosciowe,
- analiza kategorii wydatkow,
- powiazanie zachowan finansowych z questami albo achievementami,
- widok finansowego progresu bez mieszania go z XP skilli.

## Poza zakresem MVP

- integracje bankowe,
- automatyczny import transakcji,
- platnosci,
- podatki,
- fakturowanie,
- synchronizacja z zewnetrznymi systemami,
- wielouzytkownikowosc.

## Wstepne modele do przemyslenia

- `Account` - konto gotowkowe, bankowe albo inwestycyjne,
- `Transaction` - przychod albo wydatek,
- `BudgetCategory` - kategoria budzetowa,
- `Budget` - limit dla kategorii i zakresu czasu,
- `SavingsGoal` - cel oszczednosciowy,
- `FinancialSnapshot` - okresowy stan finansow.

## Integracja z RPG

Finanse nie powinny bezposrednio zwiekszac XP w MVP.

W przyszlosci mozliwe integracje:

- questy finansowe, np. "zaplanuj budzet na tydzien",
- achievementy za regularne oszczedzanie,
- status finansowy jako osobny wskaznik dobrostanu,
- cele finansowe jako dlugoterminowe questy.

## Otwarte decyzje na przyszlosc

- Czy transakcje beda dodawane recznie, importowane z pliku, czy synchronizowane przez API?
- Czy kategorie budzetowe maja byc osobne od `LifeArea`?
- Czy modul finansow ma miec wlasny dashboard, czy sekcje na glownym dashboardzie?
- Czy finansowe questy powinny dawac XP do skilli, czy tylko achievementy?
- Jak przechowywac dane wrazliwe lokalnie?
