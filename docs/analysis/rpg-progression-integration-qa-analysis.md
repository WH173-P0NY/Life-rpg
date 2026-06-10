# Analiza QA integracji RPG Progression

Data analizy: 2026-06-10
Zakres: `docs/rpg-progression-integration-qa-spec.md` vs aktualny stan repo `/home/wh173-p0ny/ProjectLevel`.

## Metoda i ograniczenia

Sprawdzone pliki i obszary:

- `docs/rpg-progression-integration-qa-spec.md`;
- `config/settings.py`, `config/urls.py`;
- `rpg/models.py`, `rpg/choices.py`, `rpg/services.py`, `rpg/views.py`, `rpg/urls.py`, `rpg/admin.py`, `rpg/migrations/`;
- `dashboard/services.py`, `dashboard/views.py`, `dashboard/tests.py`;
- `activities/management/commands/seed_life_rpg.py`;
- `rpg/tests.py`, `activities/tests.py`, `skills/tests.py`, `statuses/tests.py`, `planner/tests.py`;
- `frontend/src/api/dashboard.ts`, `frontend/src/types/dashboard.ts`, `frontend/src/components/ChallengePanel.tsx`, `frontend/src/App.tsx`.

Komendy uruchomione w trybie bez zapisu bytecode:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py test rpg dashboard
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run
```

`git status --short` nie dal wiarygodnego wyniku, bo `.git/` jest pustym katalogiem i Git zwrocil `fatal: not a git repository`. W zwiazku z tym nie potwierdzam dirty state przez Git; analiza opiera sie na aktualnych plikach na dysku.

## 1. Werdykt QA/integracji

**Werdykt: spec jest kierunkowo poprawny jako plan wdrozeniowo-QA, ale nie jest aktualnym opisem gotowego modulu. Obecne repo jest gotowym baseline dla questow, habitow, journala i dashboard nullable placeholders, natomiast zakres Goals / Challenges / Achievements nie jest zaimplementowany.**

Stan gotowosci:

| Obszar | Werdykt | Uzasadnienie |
|---|---|---|
| Fundament Django/RPG | Gotowy | Django 6.0.6, PostgreSQL-only config, `rpg` w `INSTALLED_APPS`, `path("api/", include("rpg.urls"))`. |
| Quest/Habit/Journal baseline | Gotowy kierunkowo | Istnieja modele, migracje, admin, serwisy, endpointy i testy dla questow, habitow, milestone i journala. |
| Dashboard integracja wejscia | Gotowy jako placeholder | `daily_quests`, `habits`, `journal_entries` sa realne; `active_challenge` jest `None`, `achievements` jest `[]`. To jest poprawny stan przed modulem progression. |
| Goals | Brak implementacji | Brak `Goal`, `GoalSkill`, choices, migracji, admina, serwisow, endpointow i seedow. |
| Challenges | Brak implementacji | Brak `Challenge`, `ChallengeReward`, `get_active_challenge`, complete/progress API, XP z `source_type="challenge"`. |
| Achievements | Brak implementacji | Brak `Achievement`, `AchievementUnlock`, triggerow, API, dashboard unlock rows, statystyk z bazy. |
| QA deklaracja "85 tests - OK" | Czesc potwierdzona | Test runner znalazl 85 testow dla `rpg dashboard`, ale w tej sesji nie wykonaly sie do konca przez blad polaczenia PostgreSQL. Nie potwierdzam `OK`. |

Rekomendacja QA: **nie traktowac specu jako acceptance reportu.** Mozna go traktowac jako kontrakt implementacyjny po doprecyzowaniu kilku acceptance criteria i po dodaniu migracji `rpg.0005_...` dla goals/challenges/achievements.

## 2. Walidacja deklaracji specu

| Deklaracja ze specu | Stan repo | Ocena |
|---|---|---|
| Django 6.0.6 | `requirements.txt` ma `Django==6.0.6`. | Potwierdzone |
| PostgreSQL | `config/settings.py` buduje DB tylko z `DATABASE_URL` albo `POSTGRES_*`, bez SQLite fallbacku. | Potwierdzone |
| React/Vite/Tailwind | `frontend/package.json` ma React, Vite, Tailwind, TypeScript, Chart.js. | Potwierdzone |
| `rpg` w `INSTALLED_APPS` | `config/settings.py` zawiera `"rpg"`. | Potwierdzone |
| `path("api/", include("rpg.urls"))` | `config/urls.py` podpina `rpg.urls` pod `/api/`. | Potwierdzone |
| Istnieja modele `Quest`, `QuestReward`, `QuestCompletion` | Sa w `rpg/models.py` i migracji `rpg.0001_initial`. | Potwierdzone |
| Istnieja modele `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock` | Sa w `rpg/models.py` i migracji `rpg.0002_...`. | Potwierdzone |
| Istnieja modele `JournalEntry`, `CharacterIdentity` | `JournalEntry` jest w `0003`, `CharacterIdentity` w `0004`. | Potwierdzone |
| Istnieja endpointy quest/habit/journal wymienione w specu | `rpg/urls.py` ma `quests/<id>/complete`, `quests/<id>/progress`, `habits/<id>/toggle`, `journal/`, `journal/<id>/`. | Potwierdzone |
| Istnieja endpointy goals/challenges/achievements | Brak `goals/`, `challenges/`, `achievements/` w `rpg/urls.py`. | Nie dotyczy stanu wejscia; zakres przyszly |
| `dashboard/services.py` zwraca realne questy, habity i journal z `rpg` | Importuje `build_daily_quest_rows`, `build_habit_rows`, `build_journal_entry_rows`. | Potwierdzone |
| `dashboard/services.py` nadal zwraca `active_challenge: None`, `achievements: []` | Wprost w `build_dashboard_context`. Test `dashboard_api_uses_empty_challenge_and_achievements_until_later_modules` to utrwala. | Potwierdzone |
| `JournalEntryType` ma `challenge` i `achievement` | `rpg/choices.py` zawiera oba typy, ale nie ma `goal`. | Potwierdzone czesciowo |
| Unique constraint journala po `(source_type, source_id)` dla automatycznych wpisow | `JournalEntry` ma warunkowy `UniqueConstraint` gdy `source_type != ""` i `source_id is not null`. | Potwierdzone |
| Seed nie tworzy `QuestCompletion` ani `HabitCheckIn` | Testy seedow tego wymagaja i kod seed nie tworzy tych modeli. | Potwierdzone |
| Seed nie tworzy `HabitMilestoneUnlock` | Test `HabitSeedTests` sprawdza count 0. | Potwierdzone |
| Seed nie tworzy historii/unlockow/XP challenge | Brak challenge modelu, wiec brak takiej historii. Uwaga: seed tworzy sample activities i przez nie zwykle tworzy `XpEvent(source_type="activity")`. | Potwierdzone tylko dla challenge |
| `rpg dashboard` ma 85 testow i OK | Runner znalazl `Found 85 test(s)`, ale test DB nie polaczyla sie z PostgreSQL (`OperationalError: connection is bad`). | Liczba potwierdzona, `OK` niepotwierdzone |

Wyniki komend:

- `manage.py check`: `System check identified no issues`.
- `makemigrations --check --dry-run`: `No changes detected`, ale z ostrzezeniem o braku polaczenia do DB przy sprawdzaniu historii migracji.
- `manage.py test rpg dashboard`: `Found 85 test(s)`, potem fail na tworzeniu test DB przez PostgreSQL connection error.

## 3. Mapa seed / migracje / test matrix -> stan kodu

### Seed

Plik: `activities/management/commands/seed_life_rpg.py`.

| Element | Stan kodu | Ocena wzgledem specu QA |
|---|---|---|
| Life areas | `_seed_life_areas()` tworzy 8 kategorii przez `update_or_create`. | Gotowe |
| Skills | `_seed_skills()` tworzy `Programming`, `Reading`, `Fitness`, `Research`, `Learning`, `Writing`. | Gotowe |
| Activities/rewards/rules | Definicje, rewardy i reguly sa idempotentne. | Gotowe |
| Daily quests | `_seed_daily_quests()` tworzy 5 questow i rewardy. | Gotowe dla baseline |
| Habits | `_seed_habits()` tworzy 7 habitow. | Gotowe dla baseline |
| Habit milestones | `_seed_habit_milestones()` tworzy 7/14/30 dni i rewardy. | Gotowe dla baseline |
| Statuses | Tworzy m.in. `Entertainment` jako status, nie skill. | Zgodne z MVP |
| Sample activities | `_seed_sample_activities()` tworzy aktywnosci tylko gdy nie istnieja. | Gotowe, ale tworzy XP z aktywnosci |
| Journal entries | Dwa wpisy seedowe z `source_type="seed"`, idempotentne. | Gotowe |
| Character identity | Jeden aktywny `Builder`. | Gotowe |
| Calendar events | Dwa eventy seedowe. | Gotowe |
| Goals seed | Brak `_seed_goals(...)`. | Brak |
| Challenge seed `30 Days No Sugar` | Brak `_seed_challenges(...)`. | Brak |
| Achievement definitions seed | Brak `_seed_achievements(...)`. | Brak |
| Achievement unlocks | Brak modelu i brak tworzenia. | Poprawne na baseline, ale brak docelowego zakresu |

Wazny edge dla QA: spec mowi, ze seed nie tworzy historii completion/check-in/unlockow i nie tworzy XP z challenge. To jest prawda. Jednoczesnie obecny seed tworzy sample activities przez `create_activity_entry(...)`, a to tworzy `XpEvent(source_type="activity")`. Raport akceptacyjny nie powinien wiec pisac ogolnie "seed nie tworzy XP"; poprawny zakres to "seed nie tworzy XP z challenge ani historii wykonania RPG progression".

### Migracje

| Migracja | Zawartosc | Stan |
|---|---|---|
| `skills.0001_initial` | `LifeArea`, `Skill`, `XpEvent`. | Istnieje |
| `activities.0001/0002` | Activity definitions, rewards, rules, entries. | Istnieje |
| `statuses.0001_initial` | Status definitions/entries. | Istnieje |
| `planner.0001_initial` | Calendar events. | Istnieje |
| `rpg.0001_initial` | `Quest`, `QuestReward`, `QuestCompletion`. | Istnieje |
| `rpg.0002_habit_...` | `Habit`, `HabitCheckIn`, `HabitMilestone*`, constraints. | Istnieje |
| `rpg.0003_journalentry` | `JournalEntry` z `challenge` i `achievement` choices oraz unique source. | Istnieje |
| `rpg.0004_journalentry_reflection_challenge_and_more` | Reflection fields i `CharacterIdentity`. | Istnieje |
| `rpg.0005_...` | Goals/Challenges/Achievements z QA specu. | Brak |

`makemigrations --check --dry-run` pokazuje `No changes detected`, czyli modele na dysku sa zgodne z aktualnymi migracjami. Nie potwierdzono spojnosc historii migracji na DB, bo polaczenie PostgreSQL zwraca blad.

### Test matrix

Aktualne testy `rpg dashboard` to 85 odkrytych testow. Pokrywaja:

- foundation/routing/timezone choices dla `rpg`;
- modele i serwisy questow;
- endpointy quest complete/progress;
- modele, serwisy i endpoint toggle habit;
- milestone unlock i XP z habit milestone;
- model, serwisy i API journala;
- `CharacterIdentity`;
- seed questow/habitow/journala;
- dashboard API: empty state, questy, habity, journal, range filters, manual activity API, CSRF;
- React shell fallback/build serve.

Braki wzgledem matrix ze specu:

| Grupa matrix ze specu | Stan w testach | Luka |
|---|---|---|
| Goal model tests | Brak modeli i testow. | Pelna luka |
| Goal service tests | Brak serwisow i testow. | Pelna luka |
| Challenge model tests | Brak modeli i testow. | Pelna luka |
| Challenge service tests | Brak `get_active_challenge`, progress, complete, XP idempotence. | Pelna luka |
| Achievement service tests | Brak modelu, unlock, triggerow i testow. | Pelna luka |
| API tests goals/challenges/achievements | Brak URL-i i testow. | Pelna luka |
| Dashboard tests active challenge z DB | Test utrwala tylko `active_challenge is None`. | Do zmiany po implementacji |
| Dashboard tests achievements z DB | Test utrwala tylko `achievements == []`. | Do zmiany po implementacji |
| Journal tests goal/challenge/achievement timeline | Brak modeli i eventow. | Pelna luka |
| Seed tests goals/challenge/achievements | Brak seedow i testow. | Pelna luka |
| Frontend typecheck/build po integracji | Skrypty istnieja, ale nie byly uruchamiane w tej analizie. | Wymaga osobnej bramki |

## 4. Blokery i edge cases

### Blokery implementacyjne

1. **Brak modeli progression**: nie ma `Goal`, `GoalSkill`, `Challenge`, `ChallengeReward`, `Achievement`, `AchievementUnlock`.
2. **Brak choices progression**: nie ma `GoalStatus`, `ChallengeStatus`, `AchievementRarity`, `AchievementTriggerType`; `JournalEntryType.GOAL` tez nie istnieje.
3. **Brak migracji `rpg.0005_...`**: rollback target ze specu ma sens dopiero po dodaniu tej migracji.
4. **Brak API**: `GET/POST/PATCH /api/goals/`, `GET /api/challenges/`, `POST /api/challenges/<id>/progress/`, `POST /api/challenges/<id>/complete/`, `GET /api/achievements/`, `POST /api/achievements/<id>/unlock/` nie istnieja.
5. **Brak dashboard service dla progression**: `active_challenge` i `achievements` sa stale, nie z bazy.
6. **Brak achievement stats**: `build_journal_stats()` zwraca `achievements_unlocked: 0`, bo nie ma `AchievementUnlock`.
7. **Brak timeline progression**: `build_journal_activity_timeline()` obsluguje activity, quest, habit, manual journal, ale nie goal/challenge/achievement.
8. **DB test environment nie jest zdrowy**: test runner znajduje 85 testow, ale nie laczy sie z PostgreSQL test DB. Przed akceptacja trzeba naprawic lokalne `DATABASE_URL`/`POSTGRES_*` albo uprawnienia/serwer PostgreSQL.

### Edge cases do zachowania w specu

- `active_challenge: null` musi pozostac poprawnym kontraktem; React `ChallengePanel` juz renderuje empty state dla `null`.
- Aktualny frontend mapper `frontend/src/api/dashboard.ts` dla challenge oczekuje starych pol `name`, `day`, `total`, `progress`, `reward`; spec docelowo chce `title`, `current_value`, `target_value`, `target_unit`, `progress_percent`, `reward_title`, `reward_xp`. To wymaga migracji mappera albo przejsciowych aliasow.
- `achievements` w `frontend/src/api/dashboard.ts` obecnie oczekuja `title`, `meta`, `rarity`; spec chce `id`, `description`, `icon`, `unlocked_at`, `unlocked_at_label`. Bez zmiany mappera realny DTO moze byc gubiony.
- `App.tsx` uzywa `localStorage` tylko dla theme; nie widac domenowego `localStorage` dla goals/challenges/achievements. To jest akceptowalne.
- `activities.services.create_activity_entry(...)` tworzy XP i nie wywoluje achievement evaluation. Jesli `skill_level` ma dzialac po aktywnosciach, trzeba dopiac ewaluacje po utworzeniu XP bez importu `rpg` w `skills.models`.
- `XpEvent` ma FK tylko do `ActivityEntry`; XP z quest/challenge/habit milestone jest audytowane przez `source_type` i `note`. Dla MVP to zgodne ze specem, ale rollback/korekta XP po challenge bedzie manualna.
- `complete_quest(...)` tworzy journal po transakcji i best-effort; analogiczny wzorzec trzeba zachowac dla goal/challenge/achievement, zeby journal nie rollbackowal domeny.
- Achievement trigger config musi byc `snake_case` i oparty na ID rekordow; seed moze resolve'owac po nazwie, ale DB nie powinna trzymac nazw jako glownego kontraktu.
- `Goal` nie moze dawac XP; `Achievement` nie moze dawac XP; `Challenge` daje XP tylko raz przy complete, nigdy przy progress.
- Adminowa edycja `ChallengeReward` po `xp_awarded_at` nie moze przeliczac historii automatycznie.

## 5. Rollback i smoke plan

### Przed implementacja progression

Aktualny rollback DB dla progression nie jest potrzebny, bo nie ma migracji `rpg.0005_...`. Bezpieczny smoke baseline:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py test rpg dashboard
```

Warunek wejscia: testy musza przejsc do `OK`, a nie tylko pokazac `Found 85 test(s)`.

### Po dodaniu migracji `rpg.0005_...`

Smoke backend:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test rpg dashboard activities planner
.venv/bin/python manage.py seed_life_rpg
.venv/bin/python manage.py seed_life_rpg
```

Smoke API po uruchomieniu serwera:

```bash
curl http://127.0.0.1:8000/api/dashboard/
curl http://127.0.0.1:8000/api/journal/
curl http://127.0.0.1:8000/api/goals/
curl http://127.0.0.1:8000/api/challenges/
curl http://127.0.0.1:8000/api/achievements/
```

Smoke mutacyjny tylko na lokalnej/dev DB:

1. Seed dwa razy.
2. Potwierdzic brak `QuestCompletion`, `HabitCheckIn`, `HabitMilestoneUnlock`, `AchievementUnlock` po seedzie.
3. Pobrac `30 Days No Sugar`.
4. Wywolac challenge progress i potwierdzic brak nowych `XpEvent(source_type="challenge")`.
5. Wywolac challenge complete i potwierdzic:
   - jeden `XpEvent` per `ChallengeReward`;
   - `xp_awarded_at` ustawione;
   - `JournalEntry(source_type="challenge_completed")`;
   - pasujacy `AchievementUnlock`;
   - `JournalEntry(source_type="achievement_unlock")`.
6. Wywolac complete drugi raz i potwierdzic brak dodatkowego XP, unlockow i journal entries.

Rollback po migracji lokalnej:

```bash
.venv/bin/python manage.py migrate rpg 0004_journalentry_reflection_challenge_and_more
```

Konsekwencja: tabele goals/challenges/achievements z migracji `0005` zostana usuniete. Po przyznaniu XP z challenge MVP nie ma automatycznego cofania; na dev DB opcje to backup restore albo reczne usuniecie testowych `XpEvent(source_type="challenge")` i powiazanych wpisow journala/unlockow.

## 6. Minimalne acceptance criteria realne dla obecnego repo

### Baseline przed implementacja progression

Realne i mierzalne teraz:

1. `manage.py check` przechodzi bez issue.
2. `makemigrations --check --dry-run` nie wykrywa zmian modeli.
3. `manage.py test rpg dashboard` znajduje 85 testow i po naprawie lokalnego PostgreSQL konczy sie `OK`.
4. `GET /api/dashboard/` zwraca:
   - realne `daily_quests`;
   - realne `habits`;
   - realne `journal_entries`;
   - `active_challenge: null`;
   - `achievements: []`.
5. `GET /api/journal/` zwraca overview journala i `achievements_unlocked: 0`.
6. `seed_life_rpg` jest idempotentny dla obecnych obszarow: skills, activities, questy, habity, milestones, statusy, journal, identity, calendar.
7. Seed nie tworzy `QuestCompletion`, `HabitCheckIn`, `HabitMilestoneUnlock`.
8. Frontend nie uzywa `localStorage` jako zrodla prawdy dla goals/challenges/achievements; obecne uzycie theme jest poza domena.

### Minimalny zakres pierwszej akceptacji progression

Dopiero po implementacji `rpg.0005_...` realne minimum powinno byc wezsze niz pelna lista 19 punktow ze specu:

1. Dodane modele i migracja: `Goal`, `GoalSkill`, `Challenge`, `ChallengeReward`, `Achievement`, `AchievementUnlock`.
2. Admin rejestruje te modele z inline dla `GoalSkill` i `ChallengeReward`.
3. Seed tworzy idempotentnie:
   - 4 goals;
   - aktywny `30 Days No Sugar`;
   - reward 250 XP do `Fitness`;
   - 10 definicji achievementow;
   - zero `AchievementUnlock`;
   - zero XP challenge.
4. `GET /api/dashboard/` zwraca realny `active_challenge` albo `null`.
5. `GET /api/dashboard/` zwraca odblokowane achievementy z bazy albo `[]`.
6. `GET /api/journal/` liczy `achievements_unlocked` z `AchievementUnlock`.
7. `POST /api/challenges/<id>/progress/` nie tworzy XP.
8. `POST /api/challenges/<id>/complete/` tworzy XP tylko przez `skills.XpEvent`, tylko raz.
9. `AchievementUnlock` nie tworzy XP i jest idempotentny po achievement.
10. Automatyczne wpisy journala dla goal/challenge/achievement sa idempotentne i best-effort.
11. Testy backendowe obejmuja co najmniej: empty dashboard, active challenge, repeated complete, achievement unlock without XP, seed idempotence.
12. Komendy koncowe przechodza na sprawnym PostgreSQL:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py test rpg dashboard activities planner
cd frontend
npm run typecheck
npm run build
```

Pelna akceptacja ze specu jest sensowna jako docelowy gate, ale na obecnym repo jest zbyt szeroka, bo wymaga gotowych widokow/endpointow i testow dla modeli, ktore jeszcze nie istnieja.
