# Life RPG Tracker - specyfikacja etapu 1

## 1. Cel etapu

Etap 1 ma dostarczyc lokalne MVP bez ActivityWatch i bez AI.

Po zakonczeniu etapu aplikacja ma pozwalac jednemu lokalnemu uzytkownikowi:

- zarzadzac skillami, obszarami zycia, aktywnosciami i statusami przez Django Admin,
- recznie dodawac aktywnosci z dashboardu,
- naliczac XP z jednej aktywnosci do wielu skilli,
- liczyc poziomy skilli z `XpEvent`,
- widziec dashboard dla dzisiaj, obecnego tygodnia, obecnego miesiaca i zakresu wlasnego,
- widziec aktualne statusy zyciowe,
- korzystac z danych startowych przez komende seed.

Etap 1 nie obejmuje ActivityWatch, questow AI ani modulu finansow.

## 2. Zakres

### W zakresie

- rejestracja aplikacji Django,
- konfiguracja PostgreSQL dla lokalnego MVP,
- modele domenowe,
- migracje,
- Django Admin,
- serwis tworzenia aktywnosci i XP,
- seed danych startowych,
- podstawowy dashboard,
- formularz recznej aktywnosci,
- przełącznik 5 motywów dashboardu,
- agregacje XP, czasu i statusow,
- podstawowe wykresy Chart.js,
- testy domenowe i widokowe.

### Poza zakresem

- ActivityWatch,
- generowanie questow przez AI,
- OpenAI API i Claude API,
- achievements,
- streaks,
- modul finansow,
- konta wielu uzytkownikow,
- DRF,
- Celery.

## 3. Stack etapu 1

Backend:

- Django 6.0.6.

Baza danych:

- PostgreSQL.

Frontend:

- React,
- TypeScript,
- Vite,
- Tailwind CSS,
- Chart.js.

Backend API dla frontendu:

- standardowe widoki Django zwracajace JSON,
- bez DRF w etapie 1,
- Django Templates tylko jako opcjonalny shell do zamontowania Reacta albo dla Django Admin.

Zasady PostgreSQL:

- nie uzywac SQLite jako bazy etapu 1,
- wygenerowana konfiguracja SQLite w `config/settings.py` musi zostac zastapiona konfiguracja PostgreSQL,
- konfiguracja polaczenia powinna pochodzic z `.env` albo zmiennych srodowiskowych,
- `.env.example` powinien dokumentowac wymagane zmienne PostgreSQL,
- lokalna rola PostgreSQL uzywana przez Django musi miec `CREATEDB`, jezeli ma uruchamiac `manage.py test`,
- aplikacja powinna miec czytelny blad konfiguracji, jezeli PostgreSQL nie jest ustawiony,
- migracje i testy powinny byc uruchamiane przeciwko PostgreSQL.

## 4. Aplikacje Django

Etap 1 powinien uzywac aplikacji:

- `skills` - `LifeArea`, `Skill`, `XpEvent`,
- `activities` - `ActivityDefinition`, `ActivityReward`, `ActivityRule`, `ActivityEntry`,
- `statuses` - `StatusDefinition`, `StatusEntry`,
- `dashboard` - widoki JSON, formularze backendowe/API, agregacje i shell Reacta.

Wymaganie:

- `skills`, `activities`, `statuses` i `dashboard` musza byc dodane do `INSTALLED_APPS`.

## 5. Modele

### 5.1. LifeArea

Model: `skills.LifeArea`

Pola:

- `name` - `CharField`, unikalne, wymagane,
- `description` - `TextField`, opcjonalne,
- `created_at` - `DateTimeField(auto_now_add=True)`.

Zasady:

- `LifeArea` jest edytowalna przez admin,
- nie uzywac enumow ani `choices`,
- seed tworzy domyslne obszary.

### 5.2. Skill

Model: `skills.Skill`

Pola:

- `name` - `CharField`, unikalne, wymagane,
- `life_area` - opcjonalny `ForeignKey` do `LifeArea`,
- `created_at` - `DateTimeField(auto_now_add=True)`.

Metody:

- `get_total_xp() -> int`,
- `get_level() -> int`,
- `get_progress_to_next_level() -> dict`,
- `add_xp(amount: int, source_type: str, note: str = "", activity_entry: ActivityEntry | None = None) -> XpEvent`.

Zasady:

- `Skill` nie ma pola `xp` jako glownego zrodla prawdy,
- XP skilla jest suma `XpEvent.amount`,
- skille sa edytowalne i rozszerzalne przez uzytkownika,
- `Entertainment` nie jest skillem.

Formula levelowania:

```text
level = floor(sqrt(total_xp / 100)) + 1
```

Progi:

```text
xp_required_for_level(level) = 100 * (level - 1)^2
xp_required_for_next_level(current_level) = 100 * current_level^2
```

### 5.3. XpEvent

Model: `skills.XpEvent`

Pola:

- `skill` - wymagany `ForeignKey` do `Skill`,
- `amount` - dodatni `PositiveIntegerField`,
- `source_type` - `CharField`, np. `activity`, `quest`, `manual`,
- `activity_entry` - opcjonalny `ForeignKey` do `activities.ActivityEntry`,
- `note` - `CharField` albo `TextField`, opcjonalne,
- `earned_at` - `DateTimeField`,
- `created_at` - `DateTimeField(auto_now_add=True)`.

Zasady:

- `amount` musi byc wieksze od `0`,
- etap 1 tworzy `XpEvent` glownie z aktywnosci,
- `quest` i `manual` moga istniec jako wartosci przyszlosciowe, ale nie trzeba budowac ich UI w etapie 1,
- dashboard i levelowanie zawsze licza XP z `XpEvent`.

### 5.4. ActivityDefinition

Model: `activities.ActivityDefinition`

Pola:

- `name` - `CharField`, unikalne, wymagane,
- `life_area` - opcjonalny `ForeignKey` do `LifeArea`,
- `description` - `TextField`, opcjonalne,
- `created_at` - `DateTimeField(auto_now_add=True)`.

Zasady:

- definicja aktywnosci jest wybierana recznie w formularzu dashboardu,
- jedna definicja aktywnosci moze miec wiele `ActivityReward`,
- kod nie moze zakladac relacji 1 aktywnosc = 1 skill.

### 5.5. ActivityReward

Model: `activities.ActivityReward`

Pola:

- `activity_definition` - wymagany `ForeignKey` do `ActivityDefinition`,
- `skill` - wymagany `ForeignKey` do `Skill`,
- `xp_per_minute` - dodatni `PositiveIntegerField`.

Zasady:

- para `activity_definition` + `skill` musi byc unikalna,
- jedna definicja aktywnosci moze nagradzac kilka skilli,
- XP dla pojedynczego skilla liczymy jako `minutes * xp_per_minute`.

### 5.6. ActivityRule

Model: `activities.ActivityRule`

Pola:

- `pattern` - `CharField`, wymagane,
- `activity_definition` - wymagany `ForeignKey` do `ActivityDefinition`.

Zasady:

- w etapie 1 reguly sluza glownie do konfiguracji pod etap 2,
- reczny formularz dashboardu nie musi uzywac `ActivityRule`,
- `ActivityRule` nie wskazuje bezposrednio na `Skill`.

### 5.7. ActivityEntry

Model: `activities.ActivityEntry`

Pola:

- `activity_definition` - wymagany `ForeignKey` do `ActivityDefinition`,
- `source` - `CharField`, opcjonalne albo z domyslna wartoscia dla recznego wpisu,
- `minutes` - dodatni `PositiveIntegerField`,
- `started_at` - `DateTimeField`,
- `created_at` - `DateTimeField(auto_now_add=True)`.

Metody albo wlasciwosci:

- `total_xp() -> int` - suma powiazanych `XpEvent.amount`.

Zasady:

- tworzenie aktywnosci przez serwis musi utworzyc `XpEvent` dla kazdego `ActivityReward`,
- usuniecie aktywnosci powinno usuwac powiazane `XpEvent` przez relacje albo jawna logike,
- nie uzywac ukrytych sygnalow do naliczania XP.

### 5.8. StatusDefinition

Model: `statuses.StatusDefinition`

Pola:

- `name` - `CharField`, unikalne, wymagane,
- `description` - `TextField`, opcjonalne,
- `created_at` - `DateTimeField(auto_now_add=True)`.

Zasady:

- status nie jest skillem,
- status nie ma levelu,
- status nie daje XP w etapie 1,
- `Entertainment` jest statusem.

### 5.9. StatusEntry

Model: `statuses.StatusEntry`

Pola:

- `status_definition` - wymagany `ForeignKey` do `StatusDefinition`,
- `value` - liczba calkowita w zakresie `0..100`,
- `note` - opcjonalna notatka,
- `recorded_at` - `DateTimeField`,
- `created_at` - `DateTimeField(auto_now_add=True)`.

Zasady:

- dashboard pokazuje najnowszy wpis dla kazdego statusu,
- brak wpisu dla statusu jest poprawnym stanem.

## 6. Serwisy

### 6.1. Tworzenie aktywnosci

Dodac jawny serwis, np. `activities/services.py`.

Funkcja:

```python
def create_activity_entry(
    *,
    activity_definition: ActivityDefinition,
    minutes: int,
    started_at: datetime,
    source: str = "manual",
) -> ActivityEntry:
    ...
```

Zasady:

1. Zweryfikuj, ze `minutes > 0`.
2. Utworz `ActivityEntry`.
3. Pobierz wszystkie `ActivityReward` dla `activity_definition`.
4. Dla kazdej nagrody utworz `XpEvent`.
5. Ustaw `XpEvent.amount = minutes * reward.xp_per_minute`.
6. Ustaw `XpEvent.source_type = "activity"`.
7. Ustaw `XpEvent.activity_entry` na utworzony wpis.
8. Uzyj transakcji bazodanowej.

## 7. Django Admin

Zarejestrowac:

- `LifeArea`,
- `Skill`,
- `XpEvent`,
- `ActivityDefinition`,
- `ActivityReward`,
- `ActivityRule`,
- `ActivityEntry`,
- `StatusDefinition`,
- `StatusEntry`.

Admin powinien umozliwiac:

- szybkie wyszukiwanie po nazwach i zrodlach,
- filtrowanie aktywnosci po definicji i dacie,
- filtrowanie XP po skillu, typie zrodla i dacie,
- filtrowanie statusow po typie statusu i dacie,
- edycje predefiniowanych danych seed.

## 8. Seed

Dodac komende:

```bash
python manage.py seed_life_rpg
```

Komenda musi byc idempotentna.

Seed tworzy:

- obszary zycia,
- skille,
- definicje aktywnosci,
- nagrody aktywnosci,
- reguly rozpoznawania zrodel,
- definicje statusow,
- przykladowe aktywnosci,
- przykladowe wpisy statusow.

Minimalne dane:

- obszary: `Mind & Learning`, `Craft & Work`, `Body & Health`, `Creative Output`, `Home & Organization`, `Social & Relationships`, `Recovery & Wellbeing`, `Finance & Admin`,
- skille: `Programming`, `Reading`, `Fitness`, `Research`, `Learning`, `Writing`,
- statusy: `Rested`, `Fed`, `Hydrated`, `Energy`, `Mood`, `Focus`, `Calm`, `Entertainment`,
- aktywnosci: `Coding`, `Technical research`, `Reading`, `Writing notes`, `Fitness training`, `Watching tutorial`.

## 9. Dashboard

Dashboard jest implementowany jako frontend React korzystajacy z backendowych endpointow JSON.

### 9.1. Zakresy czasu

Dashboard musi obslugiwac:

- dzisiaj jako zakres domyslny,
- obecny tydzien,
- obecny miesiac,
- wlasny zakres dat.

### 9.2. Statystyki

Dashboard pokazuje:

- XP w zakresie,
- calkowity XP,
- globalny level,
- liczbe aktywnosci w zakresie,
- czas aktywnosci w zakresie,
- liste skilli z XP i poziomem,
- aktualne statusy zyciowe.

### 9.3. Formularz recznej aktywnosci

Formularz na dashboardzie zawiera:

- wybor `ActivityDefinition`,
- `minutes`,
- `started_at`,
- opcjonalne `source`.

Po zapisie:

- tworzy sie `ActivityEntry`,
- tworza sie powiazane `XpEvent`,
- backend zwraca JSON z wynikiem operacji albo odswiezonym stanem dashboardu,
- dashboard pokazuje zaktualizowane statystyki.

### 9.4. Wykresy

Chart.js w etapie 1 powinien pokazac minimum:

- XP dziennie,
- czas dziennie.

Wykres rozwoju skilli moze byc prosty i oparty o dane z `XpEvent`.

### 9.5. Motywy dashboardu

Dashboard powinien pozwalac przelaczac motyw wizualny bez zmiany backendu.

Wymagane motywy:

- Minimal Dark RPG,
- Cyberpunk Life RPG,
- Living World,
- Adventurer's Journal,
- Premium Hybrid.

Zasady:

- wybor motywu powinien zapisywac sie lokalnie w przegladarce,
- motyw powinien zmieniac kolory, tlo, karty, pola formularzy, paski postepu i wykresy,
- dane dashboardu i formularze pozostaja te same niezaleznie od motywu.

## 10. Testy

Minimalny zestaw testow:

- `Skill.get_level()` dla kilku progow XP,
- `Skill.get_total_xp()` liczy sume `XpEvent`,
- jedna aktywnosc z kilkoma `ActivityReward` tworzy kilka `XpEvent`,
- `ActivityEntry.total_xp()` zwraca sume XP z powiazanych eventow,
- `Entertainment` istnieje jako `StatusDefinition`, a nie `Skill`,
- `StatusEntry.value` waliduje zakres `0..100`,
- seed mozna uruchomic dwa razy bez duplikatow,
- dashboard dziala na pustej bazie,
- dashboard pokazuje dane po seed,
- formularz dashboardu tworzy aktywnosc i XP.
- dashboard renderuje przelacznik 5 motywow.
- dashboard API zwraca dane JSON potrzebne Reactowi.

## 11. Kryteria akceptacji

Etap 1 jest gotowy, gdy:

1. Projekt jest skonfigurowany pod PostgreSQL, bez SQLite jako bazy MVP.
2. `python manage.py makemigrations` tworzy migracje dla modeli etapu 1.
3. `python manage.py migrate` przechodzi bez bledu na PostgreSQL.
4. Lokalna rola PostgreSQL ma uprawnienie `CREATEDB`, zeby Django moglo utworzyc baze testowa.
5. `python manage.py test` przechodzi na PostgreSQL.
6. `python manage.py seed_life_rpg` tworzy komplet danych i jest idempotentne.
7. Admin pozwala zarzadzac wszystkimi modelami etapu 1.
8. Dashboard dziala na pustej bazie.
9. Dashboard dziala po seed.
10. Reczny formularz aktywnosci tworzy wpis i XP dla wielu skilli.
11. Statusy zyciowe sa widoczne na dashboardzie.
12. `Entertainment` nie jest skillem i nie dostaje XP.
13. React frontend pobiera dane dashboardu z backendu.

## 12. Kolejnosc implementacji

1. Utworz aplikacje `statuses`.
2. Dodaj aplikacje do `INSTALLED_APPS`.
3. Skonfiguruj PostgreSQL przez zmienne srodowiskowe.
4. Zaimplementuj modele `LifeArea`, `Skill`, `XpEvent`.
5. Zaimplementuj modele aktywnosci.
6. Zaimplementuj modele statusow.
7. Dodaj migracje.
8. Dodaj admin.
9. Dodaj serwis `create_activity_entry`.
10. Dodaj testy domenowe.
11. Dodaj seed.
12. Dodaj dashboard API zwracajace JSON.
13. Scaffoldowac React + TypeScript + Vite + Tailwind CSS.
14. Dodaj formularz recznej aktywnosci w React.
15. Dodaj statusy na dashboardzie React.
16. Dodaj podstawowe wykresy Chart.js w React.
17. Uruchom testy backendu i check/build frontendu.

## 13. Implementation Status

| Phase | Status | Date | Notes |
|---|---|---|---|
| Phase 1 - Local MVP foundation | Implemented for local development | 2026-06-10 | Models, PostgreSQL `.env` settings, migrations, admin, seed command, dashboard aggregation services, JSON API endpoints, manual activity endpoint, CSRF endpoint, and tests are in place. Backend tests passed against PostgreSQL. |
| Phase 1 - React dashboard | Implemented for Vite development mode | 2026-06-10 | React + TypeScript + Vite + Tailwind CSS frontend is scaffolded. Dashboard UI consumes the backend API, supports time ranges, manual activity submission, local mock fallback, and frontend typecheck/build passed. |
| Phase 1 - Dashboard themes | Implemented in React | 2026-06-10 | The 5 dashboard themes are implemented in React with local browser persistence. Theme switching updates the dashboard UI without backend changes. |

### Phase 1 - Detailed Progress

- [x] Create `statuses` app.
- [x] Register `skills`, `activities`, `statuses`, and `dashboard`.
- [x] Configure PostgreSQL from `.env` or environment variables without SQLite fallback.
- [x] Implement domain models and migrations.
- [x] Register Django Admin for all phase 1 models.
- [x] Implement explicit activity creation and XP service.
- [x] Add idempotent `seed_life_rpg` command.
- [x] Add dashboard aggregation services, manual activity handling, ranges, statuses, and Chart.js payloads.
- [x] Add a Django-template dashboard prototype with 5 themes and a persistent theme switcher.
- [x] Add domain and view tests.
- [x] Apply migrations and run tests against PostgreSQL.
- [x] Add dashboard JSON API endpoints for React.
- [x] Add CSRF JSON endpoint for React requests.
- [x] Add manual activity JSON endpoint compatible with the React payload.
- [x] Scaffold React + TypeScript + Vite + Tailwind CSS frontend.
- [x] Move dashboard UI and theme switching into React.
- [x] Verify frontend typecheck and production build.
- [x] Verify backend checks and tests.
- [ ] Serve the production React build through Django.
- [ ] Persist quest and habit click state in the database as part of the next RPG mechanics stages.
