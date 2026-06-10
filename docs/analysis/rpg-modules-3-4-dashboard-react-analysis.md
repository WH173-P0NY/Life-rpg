# Analiza modulow 3-4: Dashboard API i React live

Data analizy: 2026-06-10.

Zakres: `docs/rpg-modules-3-4-dashboard-react-spec.md`, aktualny backend `dashboard/` oraz frontend `frontend/src/`. Nie analizowano zmian wdrozeniowych poza odczytem kodu.

## 1. Werdykt gotowosci modulow 3-4

**Werdykt: moduly 3-4 nie sa gotowe do uznania za zakonczone i nie powinny byc wdrazane przed domknieciem modulow 0-2.**

Powod glowny: spec modulow 3-4 zaklada istnienie aplikacji Django `rpg` z questami, habitami, completion/check-in, milestone i serwisami domenowymi (`docs/rpg-modules-3-4-dashboard-react-spec.md:10`, `docs/rpg-modules-3-4-dashboard-react-spec.md:52`). W aktualnym kodzie nie ma katalogu `rpg/`, a `config/settings.py` rejestruje tylko `skills`, `activities`, `statuses` i `dashboard` (`config/settings.py:60`). Brakuje tez endpointow:

- `POST /api/quests/<id>/complete/`,
- `POST /api/quests/<id>/progress/`,
- `POST /api/habits/<id>/toggle/`.

Status szczegolowy:

- **Modul 3: niegotowy.** `GET /api/dashboard/` istnieje, ale sekcje `daily_quests`, `habits`, `active_challenge`, `achievements` i `journal_entries` sa nadal budowane z aktywnosci/statusow albo jako placeholdery w `dashboard/services.py`, dokladnie wbrew kryteriom modulu 3 (`dashboard/services.py:391`, `dashboard/services.py:398`, `dashboard/services.py:463`, `dashboard/services.py:478`, `dashboard/services.py:504`). Brakuje realnych `id` z bazy dla questow/habitow i brak danych z `rpg.Quest`, `rpg.Habit`, `rpg.QuestCompletion`, `rpg.HabitCheckIn`.
- **Modul 4: niegotowy.** React nadal zapisuje wykonanie questow i habitow w `localStorage` (`frontend/src/components/QuestsPanel.tsx:22`, `frontend/src/components/QuestsPanel.tsx:55`, `frontend/src/components/HabitsPanel.tsx:22`, `frontend/src/components/HabitsPanel.tsx:52`). Mapper generuje domenowe ID z tytulow/labeli i indeksow (`frontend/src/api/dashboard.ts:206`, `frontend/src/api/dashboard.ts:218`), co spec jawnie zakazuje (`docs/rpg-modules-3-4-dashboard-react-spec.md:157`, `docs/rpg-modules-3-4-dashboard-react-spec.md:350`).
- **Gotowe elementy infrastrukturalne:** root `/` serwuje React shell (`dashboard/urls.py:8`, `dashboard/views.py:23`), API zostaje pod `/api/*` (`dashboard/urls.py:10`), Vite proxy wskazuje Django (`frontend/vite.config.ts:7`), CSRF cookie jest wystawiane dla dashboard API i `/api/csrf/` (`dashboard/views.py:66`, `dashboard/views.py:73`), a manual activity API dziala przez standardowy Django JSON view (`dashboard/views.py:79`).

## 2. Obecny kontrakt JSON i roznice wzgledem docelowego

### Obecny endpoint

Aktualny endpoint to:

```txt
GET /api/dashboard/
```

Zakresy `today`, `week`, `month`, `custom` sa obslugiwane przez `get_dashboard_range(...)` (`dashboard/services.py:42`). `custom` z odwrocona kolejnoscia dat uzywa `min()` i `max()` (`dashboard/services.py:59`), co jest zgodne ze specem.

Serializer `dashboard/views.py` zwraca obecnie:

```txt
selected_range
range_options
stats
hero
resource_cards
attribute_rows
daily_quests
active_challenge
habits
habits_summary
weekly_progress
achievements
journal_entries
skill_rows
latest_statuses
activity_definitions
xp_chart
time_chart
```

Zrodlo: `dashboard/views.py:129`.

### Sekcje zgodne lub bliskie docelowemu kontraktowi

- `selected_range`, `range_options`, `stats`, `hero`, `xp_chart`, `time_chart` sa w `snake_case` i bazuja na danych z `skills.XpEvent`/`activities.ActivityEntry` (`dashboard/views.py:132`, `dashboard/services.py:302`, `dashboard/services.py:371`).
- `skill_rows` maja stabilne `id` z bazy (`dashboard/views.py:166`) i React mapuje je przez `String(skill.id)` (`frontend/src/api/dashboard.ts:237`).
- `latest_statuses` maja stabilne `definition.id` z bazy (`dashboard/views.py:184`) i React mapuje je przez `String(status.definition.id)` (`frontend/src/api/dashboard.ts:244`).
- `activity_definitions` maja stabilne `id` z bazy (`dashboard/views.py:207`) i React mapuje je przez `String(definition.id)` (`frontend/src/api/dashboard.ts:273`).
- `POST /api/activities/manual/` przyjmuje JSON, wspiera aliasy `activity_definition_id` i `activityDefinitionId`, a zapis XP idzie przez backend (`dashboard/views.py:103`, `activities/services.py:7`). Ten endpoint nie jest problemem modulow 3-4.

### Roznice: `daily_quests`

Obecnie backend zwraca stare pola:

```txt
title
reward_xp
current
target
unit
progress
completed
```

Zrodlo: `_quest_row(...)` w `dashboard/services.py:134`.

Docelowo spec wymaga co najmniej:

```txt
id
title
description
quest_type
difficulty
target_value
target_unit
progress_value
progress_percent
completed
completed_at
completion_id
reward_xp
rewards[]
```

Zrodlo: `docs/rpg-modules-3-4-dashboard-react-spec.md:194`.

Najwazniejsze braki:

- brak `id` z backendu,
- brak modelu `rpg.Quest`,
- brak `QuestCompletion`,
- brak `rewards[]` per skill,
- `completed` wynika z aktywnosci dnia, nie z completion z bazy,
- nazwy questow sa zahardkodowane w `dashboard/services.py:391`.

### Roznice: `habits`

Obecnie backend zwraca:

```txt
label
completed
```

Zrodlo: `dashboard/services.py:398`.

Docelowo spec wymaga:

```txt
id
name
description
target_value
target_unit
completed_today
check_in_id
check_in
streak_days
next_milestone
```

Zrodlo: `docs/rpg-modules-3-4-dashboard-react-spec.md:218`.

Najwazniejsze braki:

- brak `id` z backendu,
- brak modelu `rpg.Habit`,
- brak `HabitCheckIn`,
- brak realnego `streak_days`,
- brak `next_milestone`,
- `habits_summary.streak_days` jest wyliczane sztucznie jako `min(14, completed_habits * 2)` (`dashboard/services.py:472`).

### Roznice: `active_challenge`

Obecnie backend zawsze zwraca obiekt:

```txt
name
day
total
progress
reward
xp_reward
```

Zrodlo: `dashboard/services.py:463`.

Docelowo:

- do czasu modulu 5 `active_challenge` moze i powinien byc `null`, jezeli nie ma realnego challenge (`docs/rpg-modules-3-4-dashboard-react-spec.md:300`, `docs/rpg-modules-3-4-dashboard-react-spec.md:403`);
- jezeli istnieje obiekt, musi miec stabilne `id` z bazy.

Frontend obecnie zaklada obiekt nie-null (`frontend/src/types/dashboard.ts:138`, `frontend/src/components/ChallengePanel.tsx:6`) i mapper czyta `raw.active_challenge.name` bez guarda (`frontend/src/api/dashboard.ts:229`). To peknie po poprawnym zwroceniu `active_challenge: null`.

### Roznice: `achievements` i `journal_entries`

Obecne achievementy sa wyliczane z aktywnosci/statusow i nie maja `id`, `description`, `unlocked_at` (`dashboard/services.py:478`). React generuje ich ID z tytulu i indeksu (`frontend/src/api/dashboard.ts:261`).

Obecne journal entries pochodza z ostatnich `ActivityEntry` albo z pustego placeholdera (`dashboard/services.py:267`). Nie maja `id`, `created_at`, `source_type`, a React generuje ID z tytulu i indeksu (`frontend/src/api/dashboard.ts:267`). Spec pozwala na taki fallback tylko przejsciowo i wymaga usuniecia go po module 7 (`docs/rpg-modules-3-4-dashboard-react-spec.md:417`).

## 3. Miejsca mockow, localStorage i stabilnych ID

### Mocki

- `frontend/src/App.tsx:14` importuje `mockDashboard`.
- `frontend/src/App.tsx:42` w razie bledu `fetchDashboard(...)` ustawia `setDashboard(mockDashboard)` i `apiState="fallback"`.
- `frontend/src/data/mockDashboard.ts` zawiera kompletne fikcyjne dane, w tym questy (`frontend/src/data/mockDashboard.ts:87`), habity (`frontend/src/data/mockDashboard.ts:125`), challenge (`frontend/src/data/mockDashboard.ts:156`), skille (`frontend/src/data/mockDashboard.ts:164`), achievementy (`frontend/src/data/mockDashboard.ts:224`) i journal (`frontend/src/data/mockDashboard.ts:244`).

Ten fallback moze zostac jako preview awaryjne, ale po modulach 3-4 nie moze maskowac regresji kontraktu w testach ani sterowac stanem domenowym.

### localStorage

Dozwolone/UI-only:

- theme w React: `life-rpg-dashboard-theme` (`frontend/src/App.tsx:20`, `frontend/src/App.tsx:56`);
- legacy Django template/static theme state (`dashboard/static/dashboard/themes.js`) jest poza glownym React flow i dotyczy UI.

Niedozwolone po module 4:

- questy: `life-rpg-quests-${YYYY-MM-DD}` w `frontend/src/components/QuestsPanel.tsx:22`;
- odczyt questow z `localStorage`: `frontend/src/components/QuestsPanel.tsx:11`;
- zapis questow do `localStorage`: `frontend/src/components/QuestsPanel.tsx:55`;
- habity: `life-rpg-habits-${YYYY-MM-DD}` w `frontend/src/components/HabitsPanel.tsx:22`;
- odczyt habitow z `localStorage`: `frontend/src/components/HabitsPanel.tsx:11`;
- zapis habitow do `localStorage`: `frontend/src/components/HabitsPanel.tsx:52`.

### Stabilne ID

Miejsca poprawne albo neutralne:

- `skill_rows` -> `String(skill.id)` (`frontend/src/api/dashboard.ts:237`);
- `latest_statuses` -> `String(status.definition.id)` (`frontend/src/api/dashboard.ts:244`);
- `activity_definitions` -> `String(definition.id)` (`frontend/src/api/dashboard.ts:273`);
- `resource_cards` i `attribute_rows` generuja UI-only ID z nazw (`frontend/src/api/dashboard.ts:191`, `frontend/src/api/dashboard.ts:198`); to nie sa rekordy domenowe RPG.

Miejsca do zmiany:

- `dailyQuests.id` jest `${toId(quest.title)}-${index}` (`frontend/src/api/dashboard.ts:206`);
- `habits.id` jest `${toId(habit.label)}-${index}` (`frontend/src/api/dashboard.ts:218`);
- `activeChallenge.id` jest `toId(raw.active_challenge.name)` (`frontend/src/api/dashboard.ts:229`);
- `achievements.id` jest `${toId(achievement.title)}-${index}` (`frontend/src/api/dashboard.ts:261`);
- `journalEntries.id` jest `${toId(entry.title)}-${index}` (`frontend/src/api/dashboard.ts:267`);
- backendowe `daily_quests`, `habits`, `active_challenge`, `achievements` i `journal_entries` nie dostarczaja obecnie stabilnych `id` (`dashboard/services.py:391`, `dashboard/services.py:398`, `dashboard/services.py:463`, `dashboard/services.py:478`, `dashboard/services.py:267`).

## 4. Ryzyka migracji

1. **Brak fundamentu `rpg`.** Moduly 3-4 sa integracyjne. Bez modulow 0-2 nie da sie spelnic kryteriow realnych questow, habitow, completion/check-in i mutacji.
2. **Przelamanie kontraktu Reacta przy zmianie JSON.** Obecny frontend oczekuje starych pol `current`, `target`, `unit`, `label`, `completed` (`frontend/src/api/dashboard.ts:40`). Docelowy backend ma przejsc na `progress_value`, `target_value`, `target_unit`, `name`, `completed_today`. Potrzebny jest etap aliasow.
3. **`active_challenge=null` rozbije UI.** Aktualne typy i komponent `ChallengePanel` zakladaja obiekt (`frontend/src/types/dashboard.ts:138`, `frontend/src/components/ChallengePanel.tsx:18`). Spec wymaga nullable.
4. **Podwojne naliczenie XP.** Quest completion i habit milestone musza byc idempotentne w backendzie; sam disable w UI nie wystarczy. Ryzyko dotyczy szybkiego podwojnego klikniecia i retry requestu.
5. **Rozjazd lokalnego stanu z baza.** Obecne questy/habity sa optymistycznie przelaczane w React i zapisywane do `localStorage`. Po bledzie backendu UI moze pokazac stan, ktory nigdy nie istnieje w bazie.
6. **N+1 query przy rewardach/streakach.** Selektory RPG powinny uzyc `select_related` i `prefetch_related`, szczegolnie dla quest rewardow, habit milestone i unlockow.
7. **Fake fallbacki moga zostac w produkcyjnym flow lokalnym.** `mockDashboard` i backendowe placeholdery moga ukryc brak danych RPG, jezeli nie bedzie testow kontraktu sprawdzajacych realne modele.
8. **Strefa czasowa.** Spec operuje na `timezone.localdate()` i przykladach z offsetem `+02:00`, a aktualne `TIME_ZONE` to `UTC` (`config/settings.py:176`). Przed finalnym testowaniem "dzisiaj" dla questow/habitow trzeba zdecydowac, czy lokalny tracker ma dzialac w UTC czy w lokalnej strefie uzytkownika.

## 5. Rekomendowany plan przejscia backend -> React

1. **Domknac moduly 0-2 jako warunek wejscia.**
   - Utworzyc `rpg/`, dodac `"rpg"` do `INSTALLED_APPS`, podpiac `rpg.urls` pod `/api/`.
   - Dodac `Quest`, `QuestReward`, `QuestCompletion`, `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock`.
   - Dodac serwisy `complete_quest(...)`, `update_quest_progress(...)`, `toggle_habit(...)`, liczenie streakow i milestone.
   - XP tworzyc tylko przez `skills.XpEvent`.

2. **Modul 3: podpiac dashboard API do realnych danych.**
   - Dodac `rpg/selectors.py` albo male helpery w `dashboard/services.py`.
   - Zastapic `daily_quests`, `habits`, `habits_summary` danymi z `rpg`.
   - Dla challenge do czasu modulu 5 zwracac `active_challenge: null`, nie fikcyjny "30 Days No Sugar".
   - Dla achievementow i journala zwracac puste listy albo realne dane, jezeli modele juz istnieja; nie generowac nowych fake rekordow.
   - Przez jeden krok zwracac aliasy kompatybilne ze starym Reactem: stare pola plus nowe pola docelowe.
   - Rozszerzyc `dashboard/tests.py` o testy kontraktu RPG, a testy mutacji trzymac w `rpg/tests/...`.

3. **Modul 4: przepiac mapper i typy Reacta.**
   - W `frontend/src/api/dashboard.ts` opisac DTO backendu w `snake_case` i mapowac do `camelCase`.
   - Uzywac `String(raw.id)` dla questow, habitow, challenge, achievementow i journala.
   - Zmienic `DashboardResponse.activeChallenge` na `ActiveChallenge | null`.
   - Dodac pola `questType`, `difficulty`, `progressPercent`, `completionId`, `checkInId`, `checkIn`, `nextMilestone`.

4. **Dodac mutacje frontendowe.**
   - W `frontend/src/api/dashboard.ts` dodac `completeQuest(...)`, `updateQuestProgress(...)`, `toggleHabit(...)`.
   - Uzywac istniejacego `requestJson(...)`, `credentials: "include"` i `X-CSRFToken`.
   - Request body wysylac w `snake_case`.

5. **Przerobic panele na backend jako source of truth.**
   - `App.tsx` juz ma `refreshDashboard` (`frontend/src/App.tsx:34`); przekazac go do `QuestsPanel` i `HabitsPanel`.
   - `QuestsPanel`: usunac `readStoredIds`, `life-rpg-quests-*`, lokalne completed jako zrodlo prawdy. Dodac `pendingQuestIds`, `error`, opcjonalnie `lastReward`, i po sukcesie robic pelny refresh.
   - `HabitsPanel`: usunac `readStoredIds`, `life-rpg-habits-*`, lokalne completed jako zrodlo prawdy. Dodac `pendingHabitIds`, `error`, opcjonalnie `lastMilestone`, i po sukcesie robic pelny refresh.
   - `ChallengePanel`: przyjac `challenge: ActiveChallenge | null` i pokazac empty state.
   - W fallback mode blokowac mutacje albo pokazac komunikat, ze akcja wymaga live API.

6. **Sprzatnac aliasy i fake dane po stabilizacji.**
   - Po przestawieniu Reacta na nowe pola usunac stare aliasy z backendu.
   - Pozostawic `mockDashboard` co najwyzej jako awaryjny preview, ale testy powinny failowac przy niezgodnym live kontrakcie.
   - Usunac backendowe fake questy/habity/challenge po realnym podpieciu `rpg`.

## 6. Testy i komendy weryfikacyjne

### Aktualne komendy bazowe

Uruchamiac z poprawna konfiguracja PostgreSQL (`DATABASE_URL` albo `.env`):

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

Aktualne `frontend/package.json` ma tylko `dev`, `typecheck`, `build`, `preview` (`frontend/package.json:6`), wiec automatyzacja frontendowa MVP realnie opiera sie na TypeScript i buildzie.

### Testy backendowe modulu 3

Dodac albo rozszerzyc testy w `dashboard/tests.py` oraz ewentualnie `rpg/tests/test_dashboard_selectors.py`:

- dashboard zwraca aktywne questy z `rpg.Quest`;
- dashboard nie zwraca `draft`/`archived`;
- dashboard zwraca `completion_id`, `completed=true` i `progress_value` dla dzisiejszego completion;
- `reward_xp` sumuje wiele `QuestReward`;
- dashboard zwraca aktywne habity z `rpg.Habit`;
- `completed_today=true` i `check_in_id` po dzisiejszym `HabitCheckIn`;
- streak pochodzi z serwisu domenowego;
- `next_milestone` pomija juz odblokowane milestone;
- `active_challenge` moze byc realnym obiektem albo `null`;
- `achievements` i `journal_entries` nie sa fikcyjne po wdrozeniu odpowiednich modeli;
- `range=custom` nadal dziala.

### Testy backendowe modulu 4 / mutacji

Dodac w `rpg/tests/...`:

- `POST /api/quests/<id>/complete/` tworzy completion i jeden `XpEvent` per reward;
- drugi identyczny POST nie dubluje XP;
- `POST /api/quests/<id>/progress/` zapisuje progress i po osiagnieciu targetu nalicza XP tylko raz;
- `POST /api/habits/<id>/toggle/` tworzy check-in;
- drugi toggle usuwa check-in w MVP;
- habit check-in sam nie daje XP;
- milestone daje XP tylko raz;
- CSRF dziala dla requestow z Reacta.

### Testy frontendowe / manualne modulu 4

Manualnie:

```bash
python manage.py runserver 127.0.0.1:8000
cd frontend
npm run dev -- --host 127.0.0.1
```

Sprawdzic w przegladarce:

- `GET /api/dashboard/` idzie przez Vite proxy;
- klik questa wysyla `POST /api/quests/<id>/complete/`;
- klik habitu wysyla `POST /api/habits/<id>/toggle/`;
- po mutacji dashboard odswieza XP, level, streak i status completed z backendu;
- refresh strony nie przywraca stanu z `localStorage`;
- `active_challenge=null` renderuje empty state;
- local production build dziala przez `http://127.0.0.1:8000/`.

Kontrole tekstowe po module 4:

```bash
rg -n "life-rpg-quests|life-rpg-habits" frontend/src
rg -n "toId\\(quest|toId\\(habit|\\$\\{toId\\(.*\\)-\\$\\{index" frontend/src/api/dashboard.ts
rg -n "rest_framework|celery|django-cors-headers" . --glob '!frontend/node_modules/**' --glob '!frontend/dist/**'
```

Oczekiwane:

- pierwsze polecenie nie znajduje stanu domenowego questow/habitow w `localStorage`;
- drugie nie znajduje generowania domenowych ID z tytulu/labela/indeksu;
- trzecie nie znajduje DRF, Celery ani nowego CORS dependency.
