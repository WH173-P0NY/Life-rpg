# Life RPG Tracker - specyfikacja MVP

## 1. Cel projektu

Life RPG Tracker to lokalna aplikacja webowa, ktora zamienia codzienne aktywnosci uzytkownika w system rozwoju postaci w stylu RPG.

Aplikacja ma w pierwszej wersji:

- sledzic aktywnosci uzytkownika,
- przyznawac XP za czas spedzony na aktywnosciach,
- przygotowac architekture pod przyznawanie XP za questy,
- rozwijac umiejetnosci,
- liczyc poziomy dla poszczegolnych skilli,
- sledzic statusy zyciowe, takie jak wyspanie, najedzenie, nawodnienie i rozrywka,
- prezentowac statystyki i progres na dashboardzie,
- dzialac lokalnie dla jednego uzytkownika.

Zakres finansowy jest poza MVP tej specyfikacji. Osobna notatka dla przyszlego modulu finansow znajduje sie w `docs/finance-module-notes.md`.

## 2. Zakres MVP

### W zakresie

- modele danych dla skilli, regul mapowania i wpisow aktywnosci,
- wspolny ledger XP dla roznych zrodel levelowania,
- podstawowe modele statusow zyciowych,
- panel Django Admin dla zarzadzania danymi,
- dashboard z podstawowymi statystykami,
- formularz recznego dodawania aktywnosci na dashboardzie,
- lista skilli z poziomem, XP i paskiem postepu,
- aktualne statusy zyciowe,
- wykresy Chart.js dla XP i czasu,
- mechanizm tworzenia przykladowych danych developerskich,
- lokalna baza PostgreSQL.

### Poza zakresem MVP

- integracja z ActivityWatch,
- logowanie wielu uzytkownikow,
- modul finansow,
- publiczne API zewnetrzne,
- DRF,
- Celery,
- produkcyjne wdrozenie,
- zaawansowane mechaniki RPG, takie jak questy, achievementy i streaki.

## 3. Stack technologiczny

Backend:

- Django 6.0.6 jako docelowa wersja projektu.

Baza danych:

- PostgreSQL dla MVP.

Zasady bazy danych:

- nie uzywac SQLite jako bazy MVP,
- konfiguracja powinna byc czytana ze zmiennych srodowiskowych,
- lokalny development moze uzywac lokalnego serwera PostgreSQL albo kontenera,
- testy powinny dzialac na testowej bazie PostgreSQL.

Frontend:

- React,
- TypeScript,
- Vite,
- Tailwind CSS,
- Chart.js.

Backend API dla frontendu:

- standardowe widoki Django zwracajace JSON,
- bez DRF w MVP,
- Django Templates tylko jako opcjonalny shell do zamontowania Reacta albo dla Django Admin.

Integracje:

- ActivityWatch API w etapie 2.
- OpenAI API i Claude API w pozniejszym etapie generowania questow.

Decyzja techniczna: projekt korzysta z Django 6.0.6.

## 4. Struktura aplikacji Django

Projekt powinien korzystac z istniejacych aplikacji:

- `skills` - zarzadzanie umiejetnosciami i logika poziomow,
- `activities` - reguly mapowania oraz wpisy aktywnosci,
- `statuses` - statusy zyciowe, ktore nie sa levelowanymi skillami,
- `dashboard` - widoki, agregacje i prezentacja postepu.

Rekomendowany podzial odpowiedzialnosci:

- modele `Skill` w aplikacji `skills`,
- model `LifeArea` w aplikacji `skills` jako edytowalna kategoria dla skilli i aktywnosci,
- modele `ActivityDefinition`, `ActivityReward`, `ActivityRule` i `ActivityEntry` w aplikacji `activities`,
- modele `StatusDefinition` i `StatusEntry` w aplikacji `statuses`,
- model `XpEvent` w aplikacji `skills` jako wspolne zrodlo prawdy dla XP,
- dashboard API i agregacje statystyczne w aplikacji `dashboard`,
- React frontend w katalogu `frontend/`,
- wspolna logika naliczania XP w serwisach aplikacji `activities`, jezeli zacznie przekraczac proste metody modelu,
- przyszla aplikacja `rpg` obsluzy questy, habity, challenge, achievementy i journal oraz bedzie tworzyc XP przez `XpEvent`, bez mieszania questow z aktywnosciami.

Decyzja po analizie modulow RPG: nie tworzymy osobnej aplikacji `quests`. Wczesniejsze wzmianki o przyszlej appce `quests` sa zastapione jedna aplikacja `rpg`.

## 5. Model domenowy

### 5.1. LifeArea

LifeArea reprezentuje obszar zycia, do ktorego mozna przypisac skille i definicje aktywnosci.

Predefiniowane obszary:

- Mind & Learning,
- Craft & Work,
- Body & Health,
- Creative Output,
- Home & Organization,
- Social & Relationships,
- Recovery & Wellbeing,
- Finance & Admin.

Pola:

- `id` - klucz glowny,
- `name` - nazwa obszaru, unikalna,
- `description` - opcjonalny opis,
- `created_at` - data utworzenia.

Wymagania:

- `name` nie moze byc puste,
- obszary maja byc zwyklymi rekordami w bazie, tworzonymi przez seed,
- uzytkownik moze dodawac i edytowac obszary przez admin,
- `Finance & Admin` jest obszarem zarezerwowanym pod przyszly modul finansow, ale sam modul finansow nie jest czescia MVP.

### 5.2. Skill

Skill reprezentuje umiejetnosc rozwijana przez uzytkownika.

System powinien dostarczac predefiniowana liste skilli startowych, ale lista nie moze byc zamknieta. Uzytkownik musi moc tworzyc, edytowac i usuwac skille zgodnie z potrzebami.

Przyklady:

- Programming,
- Reading,
- Fitness,
- Research,
- Learning,
- Writing.

Pola:

- `id` - klucz glowny,
- `name` - nazwa skilla, unikalna,
- `life_area` - opcjonalna relacja do `LifeArea`,
- `created_at` - data utworzenia.

Wymagania:

- `name` nie moze byc puste,
- XP skilla powinien byc liczony z powiazanych rekordow `XpEvent`,
- `Skill` nie powinien byc jedynym zrodlem prawdy dla XP,
- predefiniowane skille maja byc zwyklymi rekordami w bazie, tworzonymi przez seed,
- skille nie moga byc zaimplementowane jako enum, stale w kodzie ani Django `choices`,
- admin musi pozwalac na tworzenie i edycje dowolnych skilli,
- sortowanie domyslne: nazwa albo najwyzszy XP; decyzja UI moze byc podjeta podczas implementacji dashboardu.

Metody:

- `get_level() -> int` - zwraca poziom skilla,
- `get_progress_to_next_level() -> dict` - zwraca dane potrzebne do paska postepu,
- `get_total_xp() -> int` - zwraca sume XP z `XpEvent`,
- `add_xp(amount: int, source_type: str, note: str = "") -> XpEvent` - tworzy wpis XP i pilnuje, zeby wartosc nie byla ujemna.

Formula poziomu dla MVP:

```text
level = floor(sqrt(xp / 100)) + 1
```

Poziom minimalny:

```text
level = max(1, calculated_level)
```

### 5.3. ActivityDefinition

ActivityDefinition reprezentuje typ aktywnosci, ktory uzytkownik wykonuje. Jedna definicja aktywnosci moze rozwijac wiele skilli naraz.

Przyklady:

- Coding,
- Technical research,
- Reading technical book,
- Writing notes,
- Workout,
- Watching tutorial.

Pola:

- `id` - klucz glowny,
- `name` - nazwa aktywnosci, unikalna,
- `life_area` - opcjonalna relacja do `LifeArea`,
- `description` - opcjonalny opis,
- `created_at` - data utworzenia.

Wymagania:

- `name` nie moze byc puste,
- definicje aktywnosci maja byc edytowalne przez admin,
- definicja aktywnosci powinna miec co najmniej jedna nagrode `ActivityReward`, jezeli ma przyznawac XP,
- kod aplikacji nie moze zakladac, ze jedna aktywnosc rozwija tylko jeden skill.

### 5.4. ActivityReward

ActivityReward opisuje, ile XP dana definicja aktywnosci daje do konkretnego skilla.

Przyklady:

- Coding -> Programming, `5 XP/min`,
- Coding -> Learning, `1 XP/min`,
- Technical research -> Research, `3 XP/min`,
- Technical research -> Learning, `2 XP/min`,
- Writing notes -> Writing, `4 XP/min`,
- Writing notes -> Learning, `1 XP/min`.

Pola:

- `id` - klucz glowny,
- `activity_definition` - relacja do `ActivityDefinition`,
- `skill` - relacja do `Skill`,
- `xp_per_minute` - liczba XP za minute aktywnosci.

Wymagania:

- `activity_definition` jest wymagane,
- `skill` jest wymagany,
- `xp_per_minute` musi byc wieksze od `0`,
- para `activity_definition` + `skill` powinna byc unikalna,
- jedna definicja aktywnosci moze miec wiele rekordow `ActivityReward`.

### 5.5. ActivityRule

ActivityRule mapuje zrodlo aktywnosci na definicje aktywnosci. Definicja aktywnosci decyduje potem, ktore skille dostaja XP.

Przyklady:

- `VS Code` -> Coding,
- `PyCharm` -> Coding,
- `Chrome` -> Technical research,
- `Kindle` -> Reading technical book,
- `Obsidian` -> Writing notes.

Pola:

- `id` - klucz glowny,
- `pattern` - tekstowy wzorzec dopasowania zrodla,
- `activity_definition` - relacja do `ActivityDefinition`.

Wymagania:

- `pattern` nie moze byc pusty,
- `activity_definition` jest wymagane,
- w MVP dopasowanie moze byc case-insensitive substring match.

Przyklad dopasowania:

```text
source = "Visual Studio Code"
pattern = "code"
wynik = ActivityDefinition("Coding")
```

### 5.6. ActivityEntry

ActivityEntry reprezentuje pojedyncza zarejestrowana aktywnosc.

Pola:

- `id` - klucz glowny,
- `activity_definition` - relacja do `ActivityDefinition`,
- `source` - zrodlo aktywnosci, np. nazwa aplikacji lub okna,
- `minutes` - czas trwania w minutach,
- `started_at` - data i czas rozpoczecia aktywnosci,
- `created_at` - data utworzenia wpisu.

Wymagania:

- `activity_definition` jest wymagane,
- `minutes` musi byc wieksze od `0`,
- `started_at` jest wymagane,
- przy utworzeniu wpisu system powinien utworzyc po jednym `XpEvent` dla kazdego `ActivityReward` przypisanego do definicji aktywnosci,
- usuniecie aktywnosci powinno usunac albo uniewaznic powiazane `XpEvent`, zeby XP skilli pozostalo spojne.

Rekomendacja:

- w etapie 1 najprosciej naliczac XP podczas tworzenia wpisu przez metode serwisowa, a nie przez ukryte sygnaly Django,
- sygnaly moga utrudnic debugowanie i nie sa potrzebne w MVP.

### 5.7. XpEvent

XpEvent reprezentuje pojedyncze przyznanie XP do skilla. To jest wspolne zrodlo prawdy dla levelowania.

XP moze pochodzic z:

- aktywnosci,
- ukonczonego questa,
- recznej korekty w przyszlosci.

Pola:

- `id` - klucz glowny,
- `skill` - relacja do `Skill`,
- `amount` - liczba przyznanych XP,
- `source_type` - zrodlo XP, np. `activity`, `quest`, `manual`,
- `activity_entry` - opcjonalna relacja do `ActivityEntry`,
- `note` - opcjonalny opis, np. tytul questa albo nazwa aktywnosci,
- `earned_at` - data i czas zdobycia XP,
- `created_at` - data utworzenia wpisu.

Wymagania:

- `amount` musi byc wieksze od `0` w MVP,
- `skill` jest wymagany,
- `source_type` jest wymagany,
- aktywnosc powinna tworzyc po jednym `XpEvent` na kazdy powiazany `ActivityReward`,
- przyszle ukonczenie questa powinno tworzyc `XpEvent` z `source_type = "quest"`,
- dashboard i poziomy powinny liczyc XP z `XpEvent`, a nie tylko z `ActivityEntry`.

### 5.8. StatusDefinition

StatusDefinition reprezentuje status zyciowy postaci. Status nie jest skillem, nie ma levelu i nie daje XP w MVP.

Predefiniowane statusy:

- Rested,
- Fed,
- Hydrated,
- Energy,
- Mood,
- Focus,
- Calm,
- Entertainment.

Pola:

- `id` - klucz glowny,
- `name` - nazwa statusu, unikalna,
- `description` - opcjonalny opis,
- `created_at` - data utworzenia.

Wymagania:

- `name` nie moze byc puste,
- statusy sa zwyklymi rekordami w bazie, tworzonymi przez seed,
- uzytkownik moze dodawac i edytowac statusy przez admin,
- status nie moze byc uzywany jako skill ani zrodlo XP w MVP.

### 5.9. StatusEntry

StatusEntry reprezentuje pojedynczy pomiar statusu.

Pola:

- `id` - klucz glowny,
- `status_definition` - relacja do `StatusDefinition`,
- `value` - wartosc statusu od `0` do `100`,
- `note` - opcjonalna notatka,
- `recorded_at` - data i czas pomiaru,
- `created_at` - data utworzenia wpisu.

Wymagania:

- `status_definition` jest wymagane,
- `value` musi byc w zakresie `0..100`,
- `recorded_at` jest wymagane,
- dashboard pokazuje najnowszy wpis dla kazdego statusu,
- brak wpisu statusu nie powinien powodowac bledu dashboardu.

## 6. Logika XP i poziomow

### 6.1. Zrodla XP

System powinien obslugiwac dwie drogi levelowania:

1. **Aktywnosc podczas wykonywania czynnosci** - XP wynika z czasu i nagrod `ActivityReward` przypisanych do `ActivityDefinition`.
2. **Questy generowane przez AI** - XP wynika z ukonczonego questa zaakceptowanego przez uzytkownika.

W MVP implementowana jest pierwsza droga. Druga droga powinna byc uwzgledniona w architekturze przez `XpEvent`, ale pelna generacja questow przez AI nalezy do pozniejszego etapu.

AI nie powinno bezposrednio zwiekszac poziomu ani XP. AI moze generowac propozycje questow, ale XP powinno byc przyznane dopiero po tym, jak quest istnieje w systemie i zostanie oznaczony jako wykonany.

### 6.2. Naliczenie XP z aktywnosci

Dla kazdej nagrody aktywnosci:

```text
xp_for_skill = minutes * activity_reward.xp_per_minute
```

Przykladowo:

```text
30 minut Coding:
- Programming: 30 * 5 XP/min = 150 XP
- Learning: 30 * 1 XP/min = 30 XP
```

Po utworzeniu aktywnosci system tworzy:

- `ActivityEntry` z informacja o czasie i zrodle,
- po jednym `XpEvent` dla kazdego skilla nagradzanego przez definicje aktywnosci.

### 6.3. Naliczenie XP z questa

Dla kazdej nagrody questa:

```text
xp_for_skill = quest_reward.amount
```

Przykladowo:

```text
Quest "Przerob 45 minut kursu Django":
- Learning: 120 XP
- Programming: 60 XP
```

Po ukonczeniu questa system tworzy:

- rekord ukonczenia questa,
- po jednym `XpEvent` z `source_type = "quest"` dla kazdego nagradzanego skilla.

### 6.4. Poziom skilla

Formula MVP:

```text
level = floor(sqrt(xp / 100)) + 1
```

Przykladowe wartosci:

- `0 XP` -> level `1`,
- `100 XP` -> level `2`,
- `400 XP` -> level `3`,
- `900 XP` -> level `4`,
- `2500 XP` -> level `6`,
- `10000 XP` -> level `11`.

Progi leveli:

```text
xp_required_for_level(level) = 100 * (level - 1)^2
xp_required_for_next_level(current_level) = 100 * current_level^2
```

Jezeli tempo levelowania okaze sie zbyt szybkie, formule mozna pozniej zmienic bez zmiany struktury danych.

### 6.5. Poziom globalny

W MVP poziom globalny moze byc liczony na podstawie sumy XP ze wszystkich `XpEvent`:

```text
global_xp = sum(xp_event.amount)
global_level = floor(sqrt(global_xp / 100)) + 1
```

Poziom globalny nie wymaga osobnej tabeli w etapie 1.

## 7. Dashboard

Dashboard jest glowna strona aplikacji.

### 7.1. Ogolne statystyki

Dashboard powinien pokazywac:

- calkowity XP,
- globalny poziom uzytkownika,
- liczbe aktywnosci dzisiaj,
- laczny czas dzisiaj,
- XP zdobyty dzisiaj,
- aktualne statusy zyciowe.

### 7.2. Lista skilli

Dla kazdego skilla dashboard powinien pokazac:

- nazwe,
- poziom,
- laczny XP,
- pasek postepu do kolejnego poziomu,
- czas i XP dla aktualnie wybranego zakresu.

Sortowanie dla MVP:

- domyslnie od najwyzszego XP do najnizszego.

### 7.3. Wykresy

Chart.js powinien obslugiwac:

- XP dziennie,
- czas dziennie,
- rozwoj skilli.

Zakres danych dla MVP:

- domyslnie dzisiaj,
- obecny tydzien,
- obecny miesiac,
- dowolnie definiowany zakres dat.

### 7.4. Formularz recznej aktywnosci

Dashboard powinien zawierac formularz dodawania aktywnosci.

Pola:

- `activity_definition` - wybor definicji aktywnosci,
- `minutes` - liczba minut,
- `started_at` - czas rozpoczecia,
- `source` - opcjonalne zrodlo albo opis.

Wymagania:

- uzytkownik wybiera `ActivityDefinition` recznie,
- reczny wpis nie wymaga dopasowania przez `ActivityRule`,
- po zapisie system tworzy `ActivityEntry` i `XpEvent` dla kazdego `ActivityReward`,
- formularz w React wysyla dane do standardowego widoku Django zwracajacego JSON.

### 7.5. Widok pustego stanu

Jezeli nie ma danych:

- dashboard pokazuje komunikat, ze brak aktywnosci,
- lista skilli nadal moze pokazywac istniejace skille,
- wykresy nie powinny powodowac bledu JavaScript.

## 8. Frontend React

React w MVP powinien obslugiwac:

- dashboard,
- filtrowanie zakresu wykresow,
- formularz recznej aktywnosci,
- przełączanie motywow,
- interakcje questow, habitow i journala w pozniejszych etapach.

Backend powinien wystawiac dane dla Reacta przez standardowe widoki Django zwracajace JSON. DRF nie jest wymagany w MVP.

## 9. Django Admin

Admin powinien umozliwiac:

- zarzadzanie obszarami zycia `LifeArea`,
- dodawanie, edycje i usuwanie skilli,
- zarzadzanie definicjami aktywnosci `ActivityDefinition`,
- zarzadzanie nagrodami aktywnosci `ActivityReward`,
- zarzadzanie regulami `ActivityRule`,
- przegladanie aktywnosci `ActivityEntry`,
- przegladanie zdarzen XP `XpEvent`,
- zarzadzanie definicjami statusow `StatusDefinition`,
- przegladanie i dodawanie wpisow statusow `StatusEntry`,
- filtrowanie aktywnosci po definicji aktywnosci i dacie,
- wyszukiwanie po `source`,
- sortowanie po `started_at`, `created_at` i `minutes`.

Rekomendowane ustawienia admina:

LifeArea:

- `list_display`: `name`, `created_at`,
- `search_fields`: `name`, `description`.

Skill:

- `list_display`: `name`, `life_area`, `total_xp`, `level`, `created_at`,
- `list_filter`: `life_area`,
- `search_fields`: `name`.

ActivityDefinition:

- `list_display`: `name`, `life_area`, `created_at`,
- `list_filter`: `life_area`,
- `search_fields`: `name`, `description`.

ActivityReward:

- `list_display`: `activity_definition`, `skill`, `xp_per_minute`,
- `list_filter`: `activity_definition`, `skill`,
- `search_fields`: `activity_definition__name`, `skill__name`.

ActivityRule:

- `list_display`: `pattern`, `activity_definition`,
- `list_filter`: `activity_definition`,
- `search_fields`: `pattern`.

ActivityEntry:

- `list_display`: `source`, `activity_definition`, `minutes`, `total_xp`, `started_at`, `created_at`,
- `list_filter`: `activity_definition`, `started_at`,
- `search_fields`: `source`.

XpEvent:

- `list_display`: `skill`, `amount`, `source_type`, `earned_at`, `created_at`,
- `list_filter`: `skill`, `source_type`, `earned_at`,
- `search_fields`: `note`.

StatusDefinition:

- `list_display`: `name`, `created_at`,
- `search_fields`: `name`, `description`.

StatusEntry:

- `list_display`: `status_definition`, `value`, `recorded_at`, `created_at`,
- `list_filter`: `status_definition`, `recorded_at`,
- `search_fields`: `note`.

## 10. Przykladowe dane

Etap 1 powinien zawierac sposob utworzenia danych developerskich.

Rekomendacja:

- komenda management command, np. `python manage.py seed_life_rpg`,
- bez automatycznego seedowania przy migracji.

Predefiniowane obszary zycia:

- Mind & Learning,
- Craft & Work,
- Body & Health,
- Creative Output,
- Home & Organization,
- Social & Relationships,
- Recovery & Wellbeing,
- Finance & Admin.

Predefiniowane skille startowe:

- Programming,
- Reading,
- Fitness,
- Research,
- Learning,
- Writing.

Wymagania:

- seed tworzy obszary zycia, skille, definicje aktywnosci, nagrody aktywnosci, reguly i statusy jako zwykle rekordy w bazie,
- ponowne uruchomienie seed nie powinno tworzyc duplikatow,
- uzytkownik moze pozniej zmienic nazwe, dodac nowy skill albo usunac skill przez admin,
- kod aplikacji nie moze zakladac, ze istnieje tylko powyzsza lista skilli.

Predefiniowane definicje aktywnosci:

- Coding,
- Technical research,
- Reading,
- Writing notes,
- Fitness training,
- Watching tutorial.

Przykladowe nagrody aktywnosci:

- Coding -> Programming, `5 XP/min`,
- Coding -> Learning, `1 XP/min`,
- Technical research -> Research, `3 XP/min`,
- Technical research -> Learning, `2 XP/min`,
- Reading -> Reading, `4 XP/min`,
- Reading -> Learning, `1 XP/min`,
- Writing notes -> Writing, `4 XP/min`,
- Writing notes -> Learning, `1 XP/min`,
- Fitness training -> Fitness, `5 XP/min`,
- Watching tutorial -> Learning, `2 XP/min`,
- Watching tutorial -> Research, `1 XP/min`.

Predefiniowane statusy:

- Rested,
- Fed,
- Hydrated,
- Energy,
- Mood,
- Focus,
- Calm,
- Entertainment.

Przykladowe reguly rozpoznawania zrodel:

- `code` -> Coding,
- `pycharm` -> Coding,
- `chrome` -> Technical research,
- `youtube` -> Watching tutorial,
- `kindle` -> Reading,
- `obsidian` -> Writing notes.

Przykladowe aktywnosci:

- 60 minut VS Code jako Coding,
- 30 minut Chrome jako Technical research,
- 45 minut Kindle jako Reading,
- 20 minut Fitness training,
- 15 minut YouTube jako Watching tutorial.

## 11. Etapy realizacji

### Etap 1 - lokalne MVP bez ActivityWatch

Szczegolowa specyfikacja wykonawcza etapu 1 znajduje sie w `docs/phase-1-local-mvp-spec.md`.

Zaimplementowac:

- rejestracje aplikacji `skills`, `activities`, `statuses`, `dashboard` w `INSTALLED_APPS`,
- modele `LifeArea`, `Skill`, `XpEvent`, `ActivityDefinition`, `ActivityReward`, `ActivityRule`, `ActivityEntry`, `StatusDefinition`, `StatusEntry`,
- migracje,
- admin dla wszystkich modeli,
- podstawowy dashboard,
- formularz recznego dodawania aktywnosci na dashboardzie,
- agregacje statystyk,
- wyswietlanie aktualnych statusow,
- wykresy Chart.js,
- przykladowe dane,
- podstawowe testy modelu i logiki XP.

Kryteria akceptacji:

- `python manage.py migrate` dziala,
- `python manage.py createsuperuser` pozwala wejsc do admina,
- admin pozwala dodac obszar zycia, skill, definicje aktywnosci, nagrode aktywnosci, regule, aktywnosc i status,
- dashboard pozwala recznie dodac aktywnosc przez wybor `ActivityDefinition`,
- dodanie aktywnosci tworzy `ActivityEntry` i powiazane `XpEvent` dla wszystkich nagradzanych skilli,
- XP skilla jest liczone z `XpEvent`,
- dashboard pokazuje laczny XP, liste skilli i aktualne statusy,
- dashboard nie wywala sie przy pustej bazie,
- seed tworzy komplet danych przykladowych.

### Etap 2 - integracja z ActivityWatch

Dodac importer, ktory:

- pobiera aktywnosci z ActivityWatch API,
- dopasowuje aktywnosci do `ActivityRule`,
- tworzy `ActivityEntry`,
- tworzy powiazane `XpEvent` na podstawie `ActivityReward`,
- unika duplikatow przy ponownym imporcie.

Prawdopodobne dodatkowe pola:

- `external_id` na `ActivityEntry`,
- `external_source` na `ActivityEntry`,
- `imported_at` na `ActivityEntry`.

Kryteria akceptacji:

- importer moze zostac uruchomiony komenda management command,
- ponowne uruchomienie importera nie dubluje tych samych wpisow,
- aktywnosci bez pasujacej reguly sa zapisywane jako nierozpoznane do pozniejszego recznego przypisania `ActivityDefinition`.

### Etap 3 - mechaniki RPG

Dodac:

- streaki,
- achievementy,
- dzienne questy,
- tygodniowe questy,
- codzienne generowanie propozycji questow przez AI,
- bardziej rozbudowany poziom globalny,
- opcjonalne kategorie skilli.

Kryteria akceptacji:

- uzytkownik widzi aktualny streak,
- system potrafi przyznac achievement,
- questy maja status wykonania,
- AI generuje propozycje questow na podstawie istniejacych skilli, celow i historii aktywnosci,
- uzytkownik moze zaakceptowac albo odrzucic propozycje questa,
- quest moze nagradzac wiele skilli,
- ukonczenie questa tworzy po jednym `XpEvent` z `source_type = "quest"` dla kazdego nagradzanego skilla,
- AI nie przyznaje XP bez wykonania questa przez uzytkownika,
- mechaniki nie wymagaja recznego wpisywania danych w adminie.

### Etap 4 - providery AI

Dodac neutralna warstwe providerow AI.

Wymagania:

- kod generowania questow nie moze byc przywiazany na sztywno do jednego dostawcy,
- konfiguracja powinna pozwalac wybrac aktywnego providera,
- pierwsze wspierane providery: OpenAI API i Claude API,
- kolejne providery powinny byc dodawalne przez wspolny interfejs,
- brak klucza API powinien wylaczac generowanie AI bez psucia pozostalej aplikacji.

## 12. Wymagania jakosciowe

Kod powinien:

- uzywac type hints tam, gdzie ma to sens,
- trzymac sie PEP8,
- miec czytelny podzial odpowiedzialnosci,
- unikac nadmiernej abstrakcji,
- unikac ukrytej logiki w sygnalach, jezeli zwykla metoda lub serwis wystarczy,
- uzywac React dla glownego frontendu aplikacji,
- nie uzywac DRF w MVP,
- nie uzywac Celery w MVP,
- byc gotowy do dalszej rozbudowy.

Testy minimum:

- test formuly levelowania,
- test dodawania `XpEvent` do skilla,
- test naliczania XP z aktywnosci,
- test tworzenia wielu `XpEvent` po dodaniu aktywnosci z kilkoma nagrodami,
- test formularza recznej aktywnosci na dashboardzie,
- test zakresow dashboardu: dzisiaj, obecny tydzien, obecny miesiac, zakres wlasny,
- test najnowszych statusow na dashboardzie,
- test, ze `Entertainment` jest statusem i nie dostaje XP jako skill,
- test pustego dashboardu,
- test dashboardu z przykladowymi danymi.

## 13. Proponowana struktura plikow

```text
skills/
  admin.py
  apps.py
  models.py
  services.py
  tests.py

activities/
  admin.py
  apps.py
  models.py
  services.py
  tests.py
  management/
    commands/
      seed_life_rpg.py

statuses/
  admin.py
  apps.py
  models.py
  tests.py

dashboard/
  views.py
  urls.py
  tests.py
  services.py

frontend/
  package.json
  src/
    main.tsx
    App.tsx
    components/

templates/
  react_shell.html

static/
  css/
  js/

quests/
  # aplikacja przyszlego etapu dla questow AI

ai_providers/
  # neutralna warstwa providerow AI dla przyszlego etapu
```

## 14. Otwarte decyzje

Brak decyzji blokujacych implementacje MVP.

Pozniejsze decyzje, ktore nie blokuja etapu 1:

- dokladny format promptow dla questow AI,
- limit dziennych propozycji questow,
- sposob przechowywania kluczy API dla providerow AI,
- czy statusy zyciowe maja w przyszlosci wplywac na generowanie questow,
- szczegolowy zakres przyszlego modulu finansow.

## 15. Rekomendacje implementacyjne

Na start najlepiej:

1. Dopisac aplikacje do `INSTALLED_APPS`.
2. Zrobic modele i migracje.
3. Zarejestrowac modele w adminie.
4. Dodac metode naliczania XP przez jawna funkcje/serwis.
5. Dodac seed danych.
6. Wystawic JSON endpointy dla dashboardu i recznego dodawania aktywnosci.
7. Scaffoldowac React + TypeScript + Vite + Tailwind CSS.
8. Zbudowac dashboard w React.
9. Dodac statusy zyciowe na dashboardzie.
10. Dodac wykresy Chart.js w React.

Taki porzadek ogranicza ryzyko, bo najpierw stabilizuje dane i logike domenowa, a dopiero pozniej interakcje frontendowe.
