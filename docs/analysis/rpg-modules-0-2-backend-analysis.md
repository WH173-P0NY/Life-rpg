# Analiza backendu dla RPG Modules 0-2

Data analizy: 2026-06-10
Zakres: `docs/rpg-modules-0-2-backend-core-spec.md` vs aktualny backend w `/home/wh173-p0ny/ProjectLevel`.
Tryb: analiza statyczna plikow. Testow nie uruchamialem, zeby nie generowac artefaktow poza tym raportem.

## 1. Werdykt gotowosci modulow 0-2

**Werdykt ogolny: moduly 0-2 nie sa gotowe do akceptacji.** Aktualny backend ma solidny fundament MVP: Django 6.0.6, PostgreSQL-only config, aplikacje `skills`, `activities`, `statuses`, `dashboard`, ledger `skills.XpEvent` i transakcyjne naliczanie XP dla aktywnosci. Nie ma jednak aplikacji `rpg`, modeli questow/habitow, endpointow RPG, admina RPG, seedow RPG ani testow `rpg`.

| Modul | Status | Uzasadnienie |
|---|---|---|
| Modul 0: fundament `rpg` | **Nie gotowy** | Brak katalogu `rpg/`; `config/settings.py` rejestruje tylko `skills`, `activities`, `statuses`, `dashboard` (`config/settings.py:60-71`); `config/urls.py` nie podpina `path("api/", include("rpg.urls"))` (`config/urls.py:21-24`). |
| Modul 1: questy | **Nie gotowy** | Brak `Quest`, `QuestReward`, `QuestCompletion`, `complete_quest`, `update_quest_progress`, endpointow `/api/quests/...`, admina i seedow questow. Obecne `daily_quests` w dashboardzie sa wyliczane heurystycznie z aktywnosci (`dashboard/services.py:379-397`). |
| Modul 2: habity/streaki/milestone | **Nie gotowy** | Brak `Habit`, `HabitCheckIn`, `HabitMilestone*`, `toggle_habit`, `calculate_habit_streak`, endpointu `/api/habits/.../toggle/`, admina i seedow habitow. Obecne `habits` i `habits_summary.streak_days` sa pochodne aktywnosci/statusow, nie rekordow habitow (`dashboard/services.py:398-407`, `dashboard/services.py:471-475`). |

Gotowe zaleznosci bazowe:

- `requirements.txt` zawiera `Django==6.0.6` i `psycopg`, bez DRF/Celery.
- PostgreSQL jest wymagany przez settings bez SQLite fallbacku (`config/settings.py:103-135`).
- `skills.Skill` liczy XP z `XpEvent`, a nie z pola na skillu (`skills/models.py:84-92`).
- `Skill.add_xp()` tworzy `XpEvent` i pozwala na przyszle `source_type` typu `quest` lub `habit_milestone` (`skills/models.py:94-114`).
- `activities.create_activity_entry()` pokazuje docelowy wzorzec: `transaction.atomic()` i jeden `XpEvent` per reward (`activities/services.py:10-40`).

## 2. Mapa wymagan spec -> stan kodu

| Wymaganie ze spec | Stan w kodzie | Ocena |
|---|---|---|
| Jedna aplikacja Django `rpg` dla modulow 0-2 | Katalog `rpg/` nie istnieje; brak `rpg/apps.py`, `rpg/models.py`, `rpg/services.py`, `rpg/views.py`, `rpg/urls.py`, `rpg/admin.py`, `rpg/tests.py`. | Brak |
| Dodanie `"rpg"` do `INSTALLED_APPS` | `INSTALLED_APPS` zawiera `skills`, `activities`, `statuses`, `dashboard`, ale nie `rpg` (`config/settings.py:60-71`). | Brak |
| Podpiecie `rpg.urls` pod `/api/` | `config/urls.py` podpina tylko `dashboard.urls` i admin (`config/urls.py:21-24`). Istniejace API dashboardu jest w `dashboard/urls.py:7-17`. | Brak |
| Brak DRF/Celery | `requirements.txt` zawiera tylko Django i psycopg. `rg` nie pokazuje uzycia `rest_framework` ani `celery` poza dokumentacja. | Gotowe |
| PostgreSQL jako baza | `DATABASES` budowane z `DATABASE_URL` albo zmiennych `POSTGRES_*`, brak SQLite fallbacku (`config/settings.py:103-143`). | Gotowe |
| `XpEvent` jako jedyne zrodlo XP | `Skill.get_total_xp()` sumuje `xp_events.amount` (`skills/models.py:84-86`), a dashboard agreguje `XpEvent` (`dashboard/services.py:302-329`). | Gotowe jako fundament |
| Dozwolone `source_type`: `activity`, `quest`, `habit_milestone`, `manual` | `source_type` jest wolnym `CharField`, bez choices/constraint (`skills/models.py:123-124`). `activity` jest uzywany w `activities/services.py:35`; `manual` w testach `skills/tests.py:24-25`; brak `quest` i `habit_milestone`. | Czesc gotowa, brak kontroli slownika |
| Brak sygnalow do XP | Nie widac sygnalow; XP z aktywnosci jest jawnie tworzone w serwisie (`activities/services.py:10-40`). | Gotowe dla istniejacego MVP |
| TextChoices `QuestType`, `QuestStatus`, `QuestDifficulty`, `CreationSource`, `TargetUnit`, `HabitFrequency` | Brak aplikacji `rpg`, wiec brak tych choices. | Brak |
| Modele `Quest`, `QuestReward`, `QuestCompletion` z walidacja i constraintami | Brak modeli RPG. Obecne modele dotycza tylko `skills`, `activities`, `statuses`. | Brak |
| Serwisy `complete_quest` i `update_quest_progress` w `rpg/services.py` | Brak `rpg/services.py`. | Brak |
| Idempotentne XP questow, `transaction.atomic()`, `select_for_update()` | Brak implementacji questow. Wzor transakcyjny istnieje tylko dla aktywnosci (`activities/services.py:10-40`). | Brak |
| Endpointy `POST /api/quests/<id>/complete/` i `/progress/` | Brak `rpg.urls` i widokow questow. | Brak |
| Admin questow z inline rewards | Brak `rpg/admin.py`. Istniejace adminy sa tylko dla MVP (`skills/admin.py`, `activities/admin.py`, `statuses/admin.py`). | Brak |
| Seed 5 questow dziennych | `seed_life_rpg` seeduje obszary, skille, aktywnosci, rewardy, reguly, statusy i sample activity (`activities/management/commands/seed_life_rpg.py:17-25`), ale nie questy. | Brak |
| Helper `build_daily_quest_rows(day)` | Brak. Dashboard ma lokalna liste `_quest_row(...)` w `build_dashboard_context()` (`dashboard/services.py:391-397`). | Brak |
| Modele `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock` | Brak modeli RPG. | Brak |
| Serwisy `toggle_habit`, `calculate_habit_streak`, `unlock_due_habit_milestones` | Brak `rpg/services.py`. | Brak |
| Endpoint `POST /api/habits/<id>/toggle/` | Brak `rpg.urls` i widokow habitow. | Brak |
| Admin habitow/milestone | Brak `rpg/admin.py`. | Brak |
| Seed 7 habitow i milestone 7/14/30 | `seed_life_rpg` nie seeduje habitow ani milestone (`activities/management/commands/seed_life_rpg.py:17-25`). | Brak |
| Helper `build_habit_rows(day)` | Brak. Dashboard wylicza habity z aktywnosci/statusow (`dashboard/services.py:398-407`). | Brak |
| Dashboard API zwraca `daily_quests`, `habits`, `habits_summary` | Endpoint istnieje (`dashboard/urls.py:10-11`, `dashboard/views.py:66-70`) i serializuje te pola (`dashboard/views.py:147-150`), ale dane nie pochodza z modeli RPG. | Czesc gotowa |
| JSON parsing dla nowych endpointow RPG: snake_case, 400 dla zlego JSON, daty ISO | Brak nowych endpointow. Istniejacy `manual_activity_api` ma parser dla aktywnosci i akceptuje tez camelCase (`dashboard/views.py:103-124`), co jest dopuszczalne dla starego endpointu, ale nie jest jeszcze wspolnym kontraktem RPG. | Brak dla RPG |
| CSRF dla POST | Middleware CSRF jest aktywny (`config/settings.py:73-80`), istnieje `GET /api/csrf/` (`dashboard/urls.py:10`, `dashboard/views.py:73-76`), brak `csrf_exempt` w kodzie. Nowe endpointy jeszcze nie istnieja. | Fundament gotowy |
| Testy `python manage.py test rpg` | Brak aplikacji i testow `rpg`. Istnieja testy MVP dla skills/activities/statuses/dashboard. | Brak |

## 3. Blokery i ryzyka

### Blokery akceptacji

1. **Brak aplikacji `rpg`** - modul 0 nie moze przejsc bez struktury appki, wpisu w `INSTALLED_APPS`, `rpg.urls` i smoke testow.
2. **Brak migracji RPG** - bez modeli `Quest*` i `Habit*` nie da sie uruchomic admina, seedow ani API modulow 1-2.
3. **Brak serwisow domenowych** - nie ma miejsca, ktore tworzy `XpEvent` z questow lub milestone w `transaction.atomic()`.
4. **Brak endpointow POST** - React/backend nie maja trwałego API dla wykonania questa ani toggle habitu.
5. **Dashboard nadal jest heurystyczny** - `daily_quests`, `habits` i streak nie sa realnym stanem PostgreSQL; to blokuje cel specyfikacji, czyli usuniecie mock/localStorage z najwazniejszych interakcji.
6. **Brak seedow RPG** - obecny seed nie utworzy danych potrzebnych do testowania questow/habitow.
7. **Brak testow `rpg`** - zadne kryterium `python manage.py test rpg` nie jest teraz spelnialne.

### Ryzyka techniczne

- **Wyścigi przy podwojnym kliknieciu**: spec wymaga `select_for_update()` dla completion questow. Bez tego latwo zdublowac XP mimo constraintu dziennego, szczegolnie przy rownoleglych requestach.
- **Ledger XP bez jawnego FK do questow/milestone**: spec akceptuje `source_type`, `note` i `xp_awarded_at`, ale audyt oraz przyszle cofanie XP beda trudniejsze. `XpEvent` ma jawny FK tylko do `ActivityEntry` (`skills/models.py:125-131`).
- **`source_type` jest niekontrolowany**: literowka w serwisie moze stworzyc np. `habit-milestone` zamiast `habit_milestone`. Warto rozwazyc lokalne stale albo `TextChoices` w `skills`/`rpg`, nawet jesli DB zostanie luzna.
- **Metryki dashboardu zmienia znaczenie po questach**: `range_xp` liczy wszystkie `XpEvent`, ale `range_minutes` i `activity_count` licza tylko `ActivityEntry` (`dashboard/services.py:302-325`). Po dodaniu questow/habit milestone XP wykres XP wzrosnie, ale czas/aktywnosci nie, co jest poprawne technicznie, lecz wymaga swiadomego UX.
- **`weekly_progress.quests` nie sa questami**: obecnie to `len(week_entries)` z aktywnosci (`dashboard/services.py:231-263`). Po dodaniu realnych questow nazwa stanie sie mylaca.
- **Testy wymagaja PostgreSQL env**: `settings.py` rzuci `ImproperlyConfigured`, jezeli nie ma `DATABASE_URL` albo `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_HOST` (`config/settings.py:124-134`).

## 4. Niespojnosci w specyfikacji

1. **MVP source of truth vs spec RPG**: `docs/life-rpg-tracker-mvp-spec.md` mowi, ze zaawansowane mechaniki RPG, questy, achievementy i streaki sa poza MVP, a spec 0-2 wprowadza questy/habity/streaki jako backend core. To jest logiczne jako kolejny etap, ale dokumentacja powinna jasno wskazac, ze `docs/rpg-modules-0-2-backend-core-spec.md` rozszerza MVP, a nie zmienia MVP wstecz.
2. **Nazwa przyszlej aplikacji**: MVP spec wspomina, ze przyszla aplikacja `quests` moze tworzyc XP przez `XpEvent`, natomiast spec 0-2 wymusza jedna aplikacje `rpg`. Trzeba uznac `rpg` za aktualna decyzje i ewentualnie skorygowac starszy opis MVP.
3. **Modul 0: puste serwisy/widoki**: zakres modulu 0 wymienia `rpg/services.py` i `rpg/views.py`, ale kolejnosc implementacji mowi, zeby dodac puste serwisy i widoki dopiero z modulami 1-2. To drobna niespojnosc: najlepiej stworzyc pliki skeleton w module 0 bez logiki albo doprecyzowac, ze modul 0 ma tylko pliki importowalne.
4. **Cel "usunac mocki/localStorage" vs zakres backendowy**: dokument mowi, ze moduly 0-2 maja usunac mocki/localStorage z najwazniejszych interakcji dashboardu, ale koniec spec zaleca przepiecie `GET /api/dashboard/` na realne questy/habity dopiero po tych modulach. Trzeba doprecyzowac, czy akceptacja 0-2 obejmuje tylko backend API i helpery, czy takze faktyczne podpiecie dashboardu.
5. **Jednostka czasu w API**: spec pokazuje `target_unit="minutes"` i payload `unit: "minutes"`, a obecny dashboard uzywa `unit: "min"` dla quest-row (`dashboard/services.py:391-395`). Przy integracji React mappera trzeba wybrac jeden kontrakt.
6. **`created_by=ai` przy braku AI w zakresie**: spec sugeruje wymuszanie `status=draft` dla `created_by=ai`, ale AI jest poza zakresem modulow 0-2. Trzeba zdecydowac, czy walidacja ma juz byc w `Quest.clean()`, czy dopiero w przyszlym serwisie AI.
7. **Globalne milestone i unikalnosc**: spec podaje `UniqueConstraint(fields=["habit", "streak_days"])` i jednoczesnie przyznaje, ze `habit=null` pozwala na duplikaty w SQL. Walidacja w `clean()` pomaga w adminie, ale nie jest odporna na race condition; jesli globalne milestone sa istotne, warto zaplanowac dodatkowy constraint warunkowy dla PostgreSQL.
8. **Seed `Plan tomorrow` jest niejednoznaczny**: spec dopuszcza `Learning +10 XP` albo brak reward do czasu dodania `Discipline`. To powinno byc jednoznaczne dla testow seedow.

## 5. Rekomendowana kolejnosc implementacji

1. **Modul 0 skeleton**: utworzyc `rpg/`, `apps.py`, `models.py`, `services.py`, `views.py`, `urls.py`, `admin.py`, `tests.py`, `migrations/__init__.py`; dodac `"rpg"` do `INSTALLED_APPS`; podpiac `path("api/", include("rpg.urls"))` bez ruszania `/api/dashboard/` i `/api/activities/manual/`.
2. **Choices i smoke testy**: dodac `QuestType`, `QuestStatus`, `QuestDifficulty`, `CreationSource`, `TargetUnit`, `HabitFrequency`; testy importu app config i `rpg.urls`.
3. **Quest models + migracje + admin**: dodac `Quest`, `QuestReward`, `QuestCompletion`, `clean()`, constrainty i admin z `QuestRewardInline`.
4. **Quest services**: zaimplementowac `complete_quest()` i `update_quest_progress()` w `transaction.atomic()`, z `select_for_update()`, idempotencja XP i domenowymi wyjatkami.
5. **Quest API + serializacja**: dodac `parse_json_body`, parsowanie dat, endpointy `complete/progress`, odpowiedzi 200/400/404/409 i testy CSRF/API.
6. **Quest seed + helper dashboardu**: dopisac `_seed_daily_quests()` i `build_daily_quest_rows(day)`, ale z przepieciem `GET /api/dashboard/` poczekac, jesli modul 3-4 ma przejac frontend/live dashboard.
7. **Habit models + migracje + admin**: dodac `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock`, constrainty, `clean()` i adminy.
8. **Habit services**: zaimplementowac `calculate_habit_streak()`, `unlock_due_habit_milestones()` i `toggle_habit()`; upewnic sie, ze check-in nie daje XP, a milestone daje XP tylko raz.
9. **Habit API + seed + helper**: dodac `/api/habits/<id>/toggle/`, `_seed_habits()`, `_seed_habit_milestones()` i `build_habit_rows(day)`.
10. **Regresja dashboard/frontend**: po backendzie sprawdzic, czy aktualny `GET /api/dashboard/` nadal dziala; dopiero potem podmieniac heurystyki `daily_quests`/`habits` na realne helpery, jesli zakres kolejnego modulu tego wymaga.

## 6. Testy i komendy do uruchomienia

Nie uruchamialem tych komend w trakcie analizy, bo zadanie ogranicza zmiany do raportu, a Django test/check moze tworzyc `__pycache__` i wymaga poprawnej lokalnej konfiguracji PostgreSQL.

Minimalny baseline przed implementacja:

```bash
PYTHONDONTWRITEBYTECODE=1 python manage.py check
PYTHONDONTWRITEBYTECODE=1 python manage.py test skills activities statuses dashboard
```

Po module 0:

```bash
PYTHONDONTWRITEBYTECODE=1 python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 python manage.py check
PYTHONDONTWRITEBYTECODE=1 python manage.py test rpg
```

Po modulach 1-2:

```bash
python manage.py makemigrations rpg
python manage.py migrate
python manage.py seed_life_rpg
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test rpg
python manage.py test
cd frontend && npm run typecheck
cd frontend && npm run build
```

Endpoint smoke po uruchomieniu serwera:

```bash
curl -s http://127.0.0.1:8000/api/dashboard/
curl -s http://127.0.0.1:8000/api/csrf/
```

Dla nowych POST endpointow trzeba testowac z CSRF tokenem:

```bash
curl -i -X POST http://127.0.0.1:8000/api/quests/1/complete/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -b "csrftoken=<token>" \
  --data '{"completed_on":"2026-06-10","note":"smoke"}'

curl -i -X POST http://127.0.0.1:8000/api/habits/1/toggle/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -b "csrftoken=<token>" \
  --data '{"checked_on":"2026-06-10","value":1,"note":"smoke"}'
```
