# Life RPG Tracker - specyfikacja modulow 3-4: Dashboard API i React live

## 1. Cel dokumentu

Ten dokument opisuje implementacje dwoch modulow integracyjnych etapu RPG Core:

- Modul 3: Dashboard API z realnych danych RPG.
- Modul 4: React live dla questow i habitow.

Moduly 3-4 nie definiuja od zera domeny RPG. Zakladaja, ze moduly 0-2 dostarczaja jedna aplikacje Django `rpg` z modelami, migracjami, adminem, seedem oraz serwisami domenowymi dla questow, habitow, streakow i milestone.

Glowny cel: dashboard ma przestac uzywac danych fikcyjnych oraz lokalnego stanu questow/habitow w `localStorage`. Backend ma byc jedynym zrodlem prawdy dla postepu RPG, XP i wykonania zadan.

## 2. Decyzje projektowe

Obowiazujace decyzje:

- jedna aplikacja Django `rpg` dla mechanik RPG,
- backend jako source of truth,
- React + TypeScript + Vite + Tailwind jako frontend,
- standardowe Django JSON views,
- bez DRF,
- bez Celery,
- XP naliczane tylko po stronie backendu,
- wspolny ledger XP przez `skills.XpEvent`,
- root `/` serwuje React build przez Django,
- Vite dev dziala pod `http://127.0.0.1:5173/`,
- Vite dev proxy przekazuje `/api` do Django pod `http://127.0.0.1:8000/`,
- obecne endpointy pozostaja:
  - `GET /api/dashboard/`,
  - `GET /api/csrf/`,
  - `POST /api/activities/manual/`.

### 2.1. Aktualny stan repo przed modulem 0

Na moment przygotowania tej specyfikacji repo jest przed modulem 0 mechanik RPG:

- nie ma jeszcze Django app `rpg`,
- nie ma modeli `rpg.Quest`, `rpg.Habit`, `rpg.Challenge`, `rpg.Achievement` ani `rpg.JournalEntry`,
- nie ma endpointow quest/habit:
  - `POST /api/quests/<id>/complete/`,
  - `POST /api/quests/<id>/progress/`,
  - `POST /api/habits/<id>/toggle/`,
- `GET /api/dashboard/` istnieje, ale sekcje `daily_quests`, `habits`, `active_challenge`, `achievements` i `journal_entries` sa jeszcze budowane w `dashboard.services` z aktywnosci/statusow albo jako placeholdery,
- React ma juz dashboard, theme switching i range controls,
- `QuestsPanel` nadal trzyma stan wykonanych questow w `localStorage` pod kluczami `life-rpg-quests-*`,
- `HabitsPanel` nadal trzyma stan habitow w `localStorage` pod kluczami `life-rpg-habits-*`,
- usuniecie tego `localStorage` jest czescia modulu 4, nie modulu 0.

## 3. Zaleznosci od modulow 0-2

Przed modulem 3 powinny istniec:

- `rpg.Quest`,
- `rpg.QuestReward`,
- `rpg.QuestCompletion`,
- `rpg.Habit`,
- `rpg.HabitCheckIn`,
- `rpg.HabitMilestone`,
- `rpg.HabitMilestoneReward`,
- `rpg.HabitMilestoneUnlock`,
- serwisy:
  - `complete_quest(...)`,
  - `update_quest_progress(...)`,
  - `toggle_habit(...)`,
  - funkcje liczace streaki,
  - funkcje wykrywajace milestone.

Przed pelnym domknieciem modulu 3 mile widziane sa takze:

- `rpg.Challenge`,
- `rpg.ChallengeReward`,
- `rpg.Achievement`,
- `rpg.AchievementUnlock`,
- `rpg.JournalEntry`.

Jezeli challenge, achievementy albo journal nie sa jeszcze zaimplementowane, dashboard API moze zwracac puste listy albo `null` dla tych sekcji, ale nie powinien tworzyc fikcyjnych rekordow.

## 4. Modul 3 - Dashboard API z realnych danych RPG

### 4.1. Cel

Rozszerzyc `GET /api/dashboard/`, zeby zwracal realne dane z modeli `rpg`:

- questy aktywne na dany dzien,
- postep i completions questow,
- habity aktywne,
- check-iny habitow dla dzisiaj,
- streaki habitow,
- milestone streakow,
- aktywny challenge,
- achievementy i unlocki,
- ostatnie wpisy journala.

Obecne dane z aplikacji `skills`, `activities` i `statuses` pozostaja czescia dashboardu.

### 4.2. Zakres backendu

W zakresie:

- rozbudowa `dashboard.services.build_dashboard_context(...)`,
- dodanie selektorow albo helperow pobierajacych dane RPG,
- rozbudowa serializacji w `dashboard.views._serialize_dashboard_context(...)`,
- zachowanie obslugi zakresow czasu:
  - `today`,
  - `week`,
  - `month`,
  - `custom`,
- zastapienie obecnych wyliczanych placeholderow:
  - `daily_quests`,
  - `habits`,
  - `habits_summary`,
  - `active_challenge`,
  - `achievements`,
  - `journal_entries`,
- zachowanie kompatybilnosci z Reactem przez kontrolowana migracje JSON.

Poza zakresem:

- tworzenie nowych modeli RPG,
- generowanie questow AI,
- ActivityWatch,
- modul finansow,
- produkcyjny deployment poza lokalnym Django.

### 4.3. Endpoint

Endpoint pozostaje ten sam:

```txt
GET /api/dashboard/
```

Query params:

```txt
range=today|week|month|custom
start=YYYY-MM-DD
end=YYYY-MM-DD
```

Zasady:

- brak `range` oznacza `today`,
- `custom` bez poprawnego `start` i `end` wraca do `today`,
- dla `custom` z odwrocona kolejnoscia dat backend powinien uzyc `min(start, end)` i `max(start, end)`,
- zakres czasu dotyczy statystyk, wykresow, journala i podsumowan,
- daily quests i today habit check-ins domyslnie odnosza sie do `timezone.localdate()`, niezaleznie od zakresu wykresow,
- w przyszlosci mozna dodac parametr `day=YYYY-MM-DD`, ale nie jest wymagany w tym module.

### 4.4. Backend DTO JSON: snake_case

Wszystkie endpointy `GET /api/*` i `POST /api/*` przyjmuja oraz zwracaja JSON w `snake_case`.

React nie powinien wysylac ani oczekiwac backendowych pol w `camelCase`. `camelCase` istnieje dopiero po stronie frontendu, po transformacji w `frontend/src/api/dashboard.ts`.

Najwazniejsza zmiana wzgledem obecnego kontraktu: questy, habity, challenge, achievementy i journal musza miec stabilne `id` dostarczone przez backend. Mapper Reacta moze co najwyzej zamienic liczbe na string, np. `String(raw.id)`. Mapper nie moze generowac ID z tytulu, labela, indeksu tablicy ani kombinacji typu `${title}-${index}`.

Przykladowa odpowiedz backend DTO:

```json
{
  "selected_range": {
    "key": "today",
    "label": "Today",
    "start_date": "2026-06-10",
    "end_date": "2026-06-10",
    "start_at": "2026-06-10T00:00:00+02:00",
    "end_at": "2026-06-11T00:00:00+02:00"
  },
  "range_options": [
    { "key": "today", "label": "Today" },
    { "key": "week", "label": "Week" },
    { "key": "month", "label": "Month" },
    { "key": "custom", "label": "Custom" }
  ],
  "stats": {
    "range_xp": 120,
    "total_xp": 2340,
    "global_level": 23,
    "activity_count": 4,
    "range_minutes": 95
  },
  "hero": {
    "name": "Wojownik",
    "subtitle": "The journey shapes the legend.",
    "level": 23,
    "total_xp": 2340,
    "next_level_xp": 3500,
    "progress_percent": 67,
    "rank": { "label": "Gold", "threshold": "15" },
    "main_skill": "Programming"
  },
  "daily_quests": [
    {
      "id": 1,
      "title": "Workout 30 minutes",
      "description": "",
      "quest_type": "daily",
      "difficulty": "normal",
      "target_value": 30,
      "target_unit": "minutes",
      "progress_value": 10,
      "progress_percent": 33,
      "completed": false,
      "completed_at": null,
      "completion_id": 15,
      "reward_xp": 25,
      "rewards": [
        {
          "skill_id": 3,
          "skill_name": "Fitness",
          "xp_amount": 25
        }
      ]
    }
  ],
  "habits": [
    {
      "id": 1,
      "name": "Hydrate",
      "description": "",
      "target_value": 1,
      "target_unit": "check",
      "completed_today": true,
      "check_in_id": 11,
      "check_in": {
        "id": 11,
        "checked_on": "2026-06-10",
        "value": 1
      },
      "streak_days": 14,
      "next_milestone": {
        "id": 3,
        "title": "30 Day Streak",
        "streak_days": 30,
        "remaining_days": 16,
        "reward_xp": 100
      }
    }
  ],
  "habits_summary": {
    "completed": 6,
    "total": 7,
    "streak_days": 14
  },
  "active_challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "active",
    "current_value": 14,
    "target_value": 30,
    "target_unit": "days",
    "progress_percent": 47,
    "reward_title": "Epic Willpower Badge",
    "reward_xp": 450
  },
  "achievements": [
    {
      "id": 1,
      "title": "Iron Discipline",
      "description": "Complete 5 habits in one day.",
      "rarity": "epic",
      "unlocked": true,
      "unlocked_at": "2026-06-10T08:30:00+02:00",
      "meta": "Unlocked today"
    }
  ],
  "journal_entries": [
    {
      "id": 1,
      "title": "Quest completed",
      "body": "Workout 30 minutes. +25 XP.",
      "meta": "10 Jun, 08:30",
      "created_at": "2026-06-10T08:30:00+02:00",
      "source_type": "quest"
    }
  ],
  "skill_rows": [],
  "latest_statuses": [],
  "activity_definitions": [],
  "weekly_progress": {
    "bars": [],
    "xp": 850,
    "quests": 12,
    "levels": 1
  },
  "xp_chart": {
    "labels": ["2026-06-10"],
    "values": [120]
  },
  "time_chart": {
    "labels": ["2026-06-10"],
    "values": [95]
  }
}
```

Do czasu modulu 5 `active_challenge` moze byc `null`:

```json
{
  "active_challenge": null
}
```

Frontend musi traktowac to pole jako nullable i wyrenderowac empty state, zamiast zakladac istnienie challenge.

Finalny backendowy DTO dla `active_challenge` ma pola: `id`, `title`, `status`, `current_value`, `target_value`, `target_unit`, `progress_percent`, `reward_title`, `reward_xp`.

Legacy pola `name`, `day`, `total`, `progress`, `reward` moga pojawic sie tylko jako przejsciowe aliasy podczas migracji. Nowy kod Reacta powinien czytac finalny DTO i mapowac go na `camelCase`.

### 4.5. Kompatybilnosc z obecnym frontendem i mapowanie

Obecny React oczekuje:

- `daily_quests[].title`,
- `daily_quests[].reward_xp`,
- `daily_quests[].current`,
- `daily_quests[].target`,
- `daily_quests[].unit`,
- `daily_quests[].progress`,
- `daily_quests[].completed`,
- `habits[].label`,
- `habits[].completed`.

Docelowy kontrakt powinien przejsc na stabilniejsze pola:

- `daily_quests[].id`,
- `daily_quests[].progress_value`,
- `daily_quests[].target_value`,
- `daily_quests[].target_unit`,
- `daily_quests[].progress_percent`,
- `habits[].id`,
- `habits[].name`,
- `habits[].completed_today`.

Strategia migracji:

1. Backend przez jeden krok moze zwracac oba zestawy pol:
   - stare: `current`, `target`, `unit`, `progress`, `label`, `completed`,
   - nowe: `progress_value`, `target_value`, `target_unit`, `progress_percent`, `name`, `completed_today`.
2. React zostaje przestawiony na nowe pola i realne ID z backendu.
3. Po stabilizacji usunac stare aliasy z backendu.

Reguly mappera w `frontend/src/api/dashboard.ts`:

- `RawDashboardResponse` opisuje backend DTO w `snake_case`,
- `DashboardResponse` opisuje frontendowy model w `camelCase`,
- `raw.daily_quests[].id` mapujemy na `DailyQuest.id`,
- `raw.habits[].id` mapujemy na `Habit.id`,
- `raw.active_challenge` mapujemy na `ActiveChallenge | null`,
- `raw.check_in_id` mapujemy na `checkInId`,
- `raw.next_milestone` mapujemy na `nextMilestone`,
- `raw.reward_xp` mapujemy na `reward.xp`,
- zakazane jest tworzenie domenowego ID przez `toId(title)`, `toId(label)`, indeks tablicy albo wartosc daty.
- backendowe `target_unit="minutes"` moze byc wyswietlane w React jako `min`, ale mapper nie powinien wysylac ani oczekiwac `min` od API.

### 4.6. Pobieranie danych RPG

Rekomendowane rozbicie w backendzie:

```txt
rpg/selectors.py
```

albo lokalnie w `dashboard/services.py`, jezeli zakres zostanie maly.

Preferowane funkcje:

- `get_daily_quest_rows(day: date) -> list[dict]`,
- `get_habit_rows(day: date) -> list[dict]`,
- `get_habits_summary(day: date) -> dict`,
- `get_active_challenge_row(day: date) -> dict | None`,
- `get_achievement_rows(limit: int = 6) -> list[dict]`,
- `get_journal_rows(start_at: datetime, end_at: datetime, limit: int = 3) -> list[dict]`.

Zasady wydajnosci:

- uzywac `select_related` dla FK,
- uzywac `prefetch_related` dla rewardow,
- unikac zapytan per quest/habit w petli,
- testy nie musza mierzyc liczby query w MVP, ale kod nie powinien miec oczywistego N+1.

### 4.7. Zasady danych dla dashboardu

Questy:

- zwracac tylko aktywne questy dostepne dzisiaj,
- sortowanie: `quest_type`, `difficulty`, `title` albo docelowo `sort_order`,
- `completion_id` moze byc `null`, jezeli nie ma jeszcze `QuestCompletion`,
- `completed=true`, jezeli `completed_at` istnieje albo `progress_value >= target_value`,
- `reward_xp` to suma wszystkich rewardow questa,
- `rewards` zawiera XP per skill.

Habity:

- zwracac tylko `is_active=True`,
- `completed_today=true`, jezeli istnieje check-in dla dzisiaj i spelnia target,
- `check_in_id=null`, jezeli habit nie jest dzisiaj odhaczony,
- `streak_days` liczone przez serwis domenowy,
- `habits_summary.streak_days` oznacza globalny/najlepszy aktywny streak na dashboardzie.

Milestone:

- `next_milestone` pokazuje najblizszy aktywny milestone jeszcze nieodblokowany dla danego habitu,
- `reward_xp` jest suma rewardow milestone,
- milestone juz odblokowany nie powinien byc zwracany jako nastepny.

Challenge:

- na MVP wystarczy jeden aktywny challenge,
- do czasu modulu 5 `active_challenge` moze byc `null`,
- brak aktywnego challenge musi zwrocic `null`, a nie fikcyjny placeholder,
- po module 5 dashboard uzywa finalnego DTO `id`, `title`, `status`, `current_value`, `target_value`, `target_unit`, `progress_percent`, `reward_title`, `reward_xp`,
- React typuje challenge jako `ActiveChallenge | null`,
- React powinien umiec ukryc panel albo pokazac stan pusty.

Achievementy:

- zwracac odblokowane i kilka zablokowanych, zeby UI mial kontekst progresu,
- `unlocked_at=null` dla zablokowanych,
- `meta` jest tekstem gotowym do pokazania w UI.

Journal:

- zwracac prawdziwe `JournalEntry`,
- nie generowac wpisow z `ActivityEntry` jako falszywego journala po wdrozeniu modelu journal,
- w okresie przejsciowym mozna miec fallback z aktywnosci, ale powinien byc usuniety po module 7.

### 4.8. Pliki do zmiany

Backend:

- `dashboard/services.py`,
- `dashboard/views.py`,
- `dashboard/tests.py`,
- opcjonalnie `rpg/selectors.py`,
- opcjonalnie `rpg/tests/test_dashboard_selectors.py`.

Nie zmieniac:

- konfiguracji Vite,
- routingu root `/`,
- endpointu `/api/activities/manual/`, poza testami regresji jezeli trzeba.

### 4.9. Kolejnosc implementacji modulu 3

1. Dodac selektory RPG dla questow i habitow.
2. Podmienic `daily_quests` w `build_dashboard_context(...)` na dane z `rpg`.
3. Podmienic `habits` i `habits_summary`.
4. Dodac realne `active_challenge`, jezeli model istnieje.
5. Dodac realne `achievements`, jezeli model istnieje.
6. Dodac realne `journal_entries`, jezeli model istnieje.
7. Rozszerzyc `_serialize_dashboard_context(...)`.
8. Utrzymac tymczasowe aliasy JSON dla Reacta, jezeli modul 4 nie jest jeszcze gotowy.
9. Dodac testy API.

### 4.10. Kryteria akceptacji modulu 3

Modul 3 jest gotowy, gdy:

- `GET /api/dashboard/` zwraca questy z `rpg.Quest`,
- `GET /api/dashboard/` zwraca completions z `rpg.QuestCompletion`,
- `GET /api/dashboard/` zwraca habity z `rpg.Habit`,
- `GET /api/dashboard/` zwraca check-iny z `rpg.HabitCheckIn`,
- streaki pochodza z serwisu domenowego,
- `daily_quests[].id` i `habits[].id` sa realnymi ID z bazy,
- backend nie wymaga od Reacta generowania ID z tytulu albo indeksu,
- `active_challenge` zwraca realny obiekt albo `null`,
- dashboard nie generuje fikcyjnych questow i habitow na podstawie aktywnosci/statusow,
- obecne sekcje `skills`, `statuses`, `activity_definitions`, `xp_chart`, `time_chart` nadal dzialaja,
- zakresy `today`, `week`, `month`, `custom` nadal dzialaja,
- testy backendu przechodza.

### 4.11. Testy modulu 3

Minimalne testy:

- dashboard zwraca aktywne questy z bazy,
- dashboard nie zwraca archived/draft questow,
- dashboard pokazuje `completed=true` dla wykonanego questa na dzisiaj,
- dashboard pokazuje progress czastkowy questa,
- dashboard sumuje XP rewardow questa,
- dashboard zwraca aktywne habity,
- dashboard pokazuje `completed_today=true` dla check-inu dzisiaj,
- dashboard liczy `habits_summary.completed`,
- dashboard zwraca realny streak,
- dashboard zwraca najblizszy milestone,
- dashboard zwraca aktywny challenge albo `null`,
- dashboard zwraca achievementy z unlockami,
- dashboard zwraca ostatnie journal entries,
- `range=custom` nadal dziala po dodaniu RPG danych.

## 5. Modul 4 - React live dla questow i habitow

### 5.1. Cel

Podpiac panele React do realnych mutacji backendowych:

- `QuestsPanel` ma konczyc questy przez API,
- `QuestsPanel` ma aktualizowac progress przez API, jezeli UI pozwala na czastkowy postep,
- `HabitsPanel` ma wlaczac/wylaczac check-in przez API,
- po mutacji dashboard ma odswiezac dane z `GET /api/dashboard/`,
- `localStorage` nie moze trzymac stanu wykonania questow ani habitow.

`localStorage` zostaje tylko dla UI-only, np. aktywny theme.

### 5.2. Endpointy mutacji

Modul 4 uzywa endpointow przygotowanych przez moduly 1-2.

#### Complete quest

```txt
POST /api/quests/<id>/complete/
```

Backend request DTO `snake_case`:

```json
{
  "completed_on": "2026-06-10",
  "note": ""
}
```

`completed_on` jest opcjonalne. Jezeli brak, backend uzywa `timezone.localdate()`.

Backend response DTO `snake_case`, `200 OK`:

```json
{
  "quest": {
    "id": 1,
    "title": "Workout 30 minutes",
    "progress_value": 30,
    "target_value": 30,
    "target_unit": "minutes",
    "progress_percent": 100,
    "completed": true,
    "completion_id": 15,
    "reward_xp": 25
  },
  "xp_events": [
    {
      "id": 101,
      "skill_id": 3,
      "skill_name": "Fitness",
      "amount": 25
    }
  ],
  "dashboard_refresh_required": true
}
```

Zasady:

- endpoint jest idempotentny dla danego dnia,
- podwojny klik nie tworzy podwojnego XP,
- jezeli quest juz byl wykonany, response nadal moze byc `200 OK`, ale bez nowych `xp_events`.

#### Update quest progress

```txt
POST /api/quests/<id>/progress/
```

Backend request DTO `snake_case`:

```json
{
  "completed_on": "2026-06-10",
  "progress_value": 15
}
```

Backend response DTO `snake_case`, `200 OK`:

```json
{
  "quest": {
    "id": 1,
    "progress_value": 15,
    "target_value": 30,
    "target_unit": "minutes",
    "progress_percent": 50,
    "completed": false,
    "completion_id": 15,
    "reward_xp": 25
  },
  "xp_events": [],
  "dashboard_refresh_required": true
}
```

Zasady:

- `progress_value` nie moze byc mniejsze niz `0`,
- po osiagnieciu targetu backend moze automatycznie zakonczyc questa i naliczyc XP,
- XP nadal nalicza tylko backend.

#### Toggle habit

```txt
POST /api/habits/<id>/toggle/
```

Backend request DTO `snake_case`:

```json
{
  "checked_on": "2026-06-10"
}
```

`checked_on` jest opcjonalne. Jezeli brak, backend uzywa `timezone.localdate()`.

Backend response DTO `snake_case`, pierwsze klikniecie i utworzenie check-inu, `200 OK`:

```json
{
  "habit": {
    "id": 1,
    "name": "Hydrate",
    "checked": true,
    "completed_today": true,
    "check_in_id": 11,
    "check_in": {
      "id": 11,
      "checked_on": "2026-06-10",
      "value": 1
    },
    "streak_days": 14,
    "next_milestone": {
      "id": 3,
      "title": "30 Day Streak",
      "streak_days": 30,
      "remaining_days": 16,
      "reward_xp": 100
    }
  },
  "milestone_unlocks": [],
  "xp_events": [],
  "dashboard_refresh_required": true
}
```

Backend response DTO `snake_case`, drugie klikniecie i usuniecie check-inu, `200 OK`:

```json
{
  "habit": {
    "id": 1,
    "name": "Hydrate",
    "checked": false,
    "completed_today": false,
    "check_in_id": null,
    "check_in": null,
    "streak_days": 13,
    "next_milestone": {
      "id": 3,
      "title": "30 Day Streak",
      "streak_days": 30,
      "remaining_days": 17,
      "reward_xp": 100
    }
  },
  "milestone_unlocks": [],
  "xp_events": [],
  "dashboard_refresh_required": true
}
```

Zasady:

- pierwsze klikniecie tworzy check-in,
- drugie klikniecie usuwa `HabitCheckIn` w MVP,
- response po usunieciu musi pokazac `checked=false`, `completed_today=false`, `check_in_id=null` i `check_in=null`,
- pojedynczy check-in nie daje XP,
- XP moze pojawic sie tylko w `xp_events`, jezeli toggle odblokowal milestone,
- milestone moze zostac odblokowany tylko raz.

### 5.3. CSRF

React musi wysylac CSRF dla mutacji:

- przed pierwszym POST zapewnic cookie przez:
  - `GET /api/csrf/`,
  - albo `GET /api/dashboard/`, jezeli endpoint ma `ensure_csrf_cookie`,
- czytac cookie `csrftoken`,
- wysylac header:

```txt
X-CSRFToken: <token>
```

Fetch:

- `credentials: "include"`,
- `Content-Type: "application/json"` dla requestow z body,
- `Accept: "application/json"`.

W dev:

- requesty ida wzglednie na `/api/...`,
- Vite proxy przekazuje je do Django,
- nie uzywac twardego `http://127.0.0.1:8000` w kodzie aplikacji.

### 5.4. Backend DTO vs frontend types

Zaktualizowac `frontend/src/api/dashboard.ts` i `frontend/src/types/dashboard.ts`, rozdzielajac:

- backend DTO w `snake_case`, lokalne dla API clienta,
- frontendowe typy domenowe w `camelCase`, eksportowane z `frontend/src/types/dashboard.ts`.

Przykladowe fragmenty backend DTO w `frontend/src/api/dashboard.ts`:

```ts
type RawQuestRewardDto = {
  skill_id: number;
  skill_name: string;
  xp_amount: number;
};

type RawDailyQuestDto = {
  id: number;
  title: string;
  description: string;
  quest_type: "daily" | "weekly" | "one_time" | "ai_generated";
  difficulty: "easy" | "normal" | "hard" | "epic";
  progress_value: number;
  target_value: number;
  target_unit: string;
  progress_percent: number;
  completed: boolean;
  completed_at: string | null;
  completion_id: number | null;
  reward_xp: number;
  rewards: RawQuestRewardDto[];
};

type RawHabitCheckInDto = {
  id: number;
  checked_on: string;
  value: number;
};

type RawHabitDto = {
  id: number;
  name: string;
  description: string;
  target_value: number;
  target_unit: string;
  checked?: boolean;
  completed_today: boolean;
  check_in_id: number | null;
  check_in: RawHabitCheckInDto | null;
  streak_days: number;
  next_milestone: RawHabitMilestoneDto | null;
};

type RawHabitMilestoneDto = {
  id: number;
  title: string;
  streak_days: number;
  remaining_days: number;
  reward_xp: number;
};

type RawActiveChallengeDto = {
  id: number;
  title: string;
  status: string;
  current_value: number;
  target_value: number;
  target_unit: string;
  progress_percent: number;
  reward_title: string;
  reward_xp: number;
};

type RawDashboardResponse = {
  daily_quests: RawDailyQuestDto[];
  habits: RawHabitDto[];
  active_challenge: RawActiveChallengeDto | null;
};

type CompleteQuestRequestDto = {
  completed_on?: string;
  note?: string;
};

type UpdateQuestProgressRequestDto = {
  completed_on?: string;
  progress_value: number;
};

type ToggleHabitRequestDto = {
  checked_on?: string;
};
```

Docelowe fragmenty frontend types w `frontend/src/types/dashboard.ts`:

```ts
export interface QuestReward {
  xp: number;
  skillIds: string[];
}

export interface DailyQuest {
  id: string;
  title: string;
  description?: string;
  questType: "daily" | "weekly" | "one_time" | "ai_generated";
  difficulty: "easy" | "normal" | "hard" | "epic";
  progressValue: number;
  targetValue: number;
  unit: string;
  progressPercent: number;
  completed: boolean;
  completionId: string | null;
  reward: QuestReward;
}

export interface HabitMilestonePreview {
  id: string;
  title: string;
  streakDays: number;
  remainingDays: number;
  rewardXp: number;
}

export interface Habit {
  id: string;
  name: string;
  description?: string;
  completedToday: boolean;
  checkInId: string | null;
  checkIn: HabitCheckIn | null;
  streakDays: number;
  nextMilestone: HabitMilestonePreview | null;
}

export interface HabitCheckIn {
  id: string;
  checkedOn: string;
  value: number;
}

export interface ActiveChallenge {
  id: string;
  title: string;
  status: string;
  currentValue: number;
  targetValue: number;
  targetUnit: string;
  progressPercent: number;
  rewardTitle: string;
  rewardXp: number;
}

export interface DashboardResponse {
  dailyQuests: DailyQuest[];
  habits: Habit[];
  activeChallenge: ActiveChallenge | null;
}

export interface QuestMutationResponse {
  quest: DailyQuest;
  xpEvents: XpEventPreview[];
  dashboardRefreshRequired: boolean;
}

export interface HabitToggleResponse {
  habit: Habit;
  milestoneUnlocks: MilestoneUnlockPreview[];
  xpEvents: XpEventPreview[];
  dashboardRefreshRequired: boolean;
}

export interface XpEventPreview {
  id: string;
  skillId: string;
  skillName: string;
  amount: number;
}

export interface MilestoneUnlockPreview {
  id: string;
  milestoneId: string;
  title: string;
}
```

### 5.5. API client frontendowy

Zaktualizowac `frontend/src/api/dashboard.ts`.

Dodac funkcje:

```ts
export async function completeQuest(questId: string): Promise<QuestMutationResponse>;

export async function updateQuestProgress(
  questId: string,
  progressValue: number
): Promise<QuestMutationResponse>;

export async function toggleHabit(habitId: string): Promise<HabitToggleResponse>;
```

Wymagania:

- uzywac istniejacego `requestJson`,
- dodac `X-CSRFToken`,
- nie duplikowac logiki CSRF w komponentach,
- mapper odpowiedzi mutacji powinien uzywac tych samych funkcji mapujacych co dashboard,
- request body wysylane do Django musi byc `snake_case`, nawet jezeli parametry funkcji TypeScript sa `camelCase`,
- response DTO z Django mapowac z `snake_case` do `camelCase` przed zwroceniem do komponentow,
- `id` z backendu mapowac przez `String(raw.id)`, bez generowania slugow ani indeksow,
- bledy requestow maja byc propagowane do komponentow.

### 5.6. QuestsPanel

Zmiany:

- usunac `readStoredIds(...)`,
- usunac `life-rpg-quests-*` z `localStorage`,
- stan lokalny moze trzymac tylko:
  - `pendingQuestIds`,
  - `error`,
  - `lastReward`,
- klik na quest:
  - jezeli quest jest wykonany, w MVP mozna zablokowac odklikniecie albo dodac osobny endpoint w przyszlosci,
  - jezeli quest nie jest wykonany, wywolac `completeQuest(quest.id)`,
  - po sukcesie wywolac `onDashboardRefresh()`,
  - pokazac krotka animacje XP z response `xpEvents`,
  - podczas requestu disable dla kliknietego questa.

Props:

```ts
interface QuestsPanelProps {
  quests: DailyQuest[];
  onDashboardRefresh: () => Promise<void> | void;
}
```

Stan pusty:

- jezeli `quests.length === 0`, pokazac spokojny empty state typu `No active quests today`.

Error state:

- blad przy konkretnym quescie pokazac w panelu,
- nie przelaczac UI na completed bez potwierdzenia backendu,
- po bledzie przycisk wraca do aktywnego stanu.

### 5.7. HabitsPanel

Zmiany:

- usunac `readStoredIds(...)`,
- usunac `life-rpg-habits-*` z `localStorage`,
- stan lokalny moze trzymac tylko:
  - `pendingHabitIds`,
  - `error`,
  - opcjonalnie `lastMilestone`,
- klik na habit:
  - wywolac `toggleHabit(habit.id)`,
  - po sukcesie wywolac `onDashboardRefresh()`,
  - pokazac milestone/XP, jezeli response zawiera unlock albo XP,
  - podczas requestu disable dla kliknietego habitu.

Props:

```ts
interface HabitsPanelProps {
  habits: Habit[];
  summary: HabitsSummary;
  onDashboardRefresh: () => Promise<void> | void;
}
```

Stan pusty:

- jezeli `habits.length === 0`, pokazac empty state typu `No active habits`.

Error state:

- blad toggla pokazac w panelu,
- nie zmieniac orb/check bez potwierdzenia backendu,
- mozna uzyc optymistic UI dopiero po dodaniu rollbacku; w MVP preferowane jest pessimistic UI.

### 5.8. App.tsx i refresh dashboardu

`App.tsx` juz posiada `refreshDashboard`.

Zmiany:

- przekazac `refreshDashboard` do `QuestsPanel`,
- przekazac `refreshDashboard` do `HabitsPanel`,
- przekazywac `dashboard.activeChallenge` jako `ActiveChallenge | null`,
- `ChallengePanel` musi przyjac `challenge: ActiveChallenge | null` i wyrenderowac empty state, gdy backend zwroci `active_challenge=null`,
- zachowac refresh po `ActivityForm`,
- `mockDashboard` zostaje tylko jako fallback, gdy `GET /api/dashboard/` nie odpowiada,
- fallback mode powinien blokowac realne mutacje albo pokazac komunikat, ze akcje wymagaja API.

Rekomendacja:

- po mutacji zawsze wykonac pelny refresh dashboardu,
- lokalna aktualizacja pojedynczego questa/habitu moze byc dodana pozniej, ale pelny refresh zmniejsza ryzyko niespojnych XP, leveli i streakow.

### 5.9. Pliki do zmiany

Frontend:

- `frontend/src/api/dashboard.ts`,
- `frontend/src/types/dashboard.ts`,
- `frontend/src/components/QuestsPanel.tsx`,
- `frontend/src/components/HabitsPanel.tsx`,
- `frontend/src/App.tsx`,
- opcjonalnie `frontend/src/data/mockDashboard.ts`,
- opcjonalnie `frontend/src/components/ui/*` dla wspolnego error/loading state.

Backend test/regresja:

- `dashboard/tests.py`, jezeli trzeba potwierdzic nowy kontrakt JSON,
- testy endpointow mutacji powinny nalezec do `rpg/tests/...`.

### 5.10. Strategia migracji od mock/localStorage

Kroki:

1. Backend modulu 3 zwraca realne ID i aliasy kompatybilne ze starym Reactem.
2. Frontend mapper zaczyna uzywac realnych ID:
   - `String(raw.id)` dla questow,
   - `String(raw.id)` dla habitow.
3. Frontend mapper przestaje uzywac `toId(title)`, `toId(label)` i indeksow tablic dla domenowych rekordow.
4. `active_challenge=null` zostaje zmapowane na `activeChallenge: null`.
5. `QuestsPanel` dostaje `onDashboardRefresh`.
6. `QuestsPanel` usuwa `localStorage`.
7. `HabitsPanel` dostaje `onDashboardRefresh`.
8. `HabitsPanel` usuwa `localStorage`.
9. Dodac funkcje API mutacji.
10. Po przejsciu na nowe pola JSON usunac aliasy ze starego kontraktu.
11. `localStorage` zostaje tylko dla:
   - theme,
   - ewentualnych ustawien UI bez znaczenia domenowego.

### 5.11. Kolejnosc implementacji modulu 4

1. Zaktualizowac typy `DailyQuest` i `Habit`.
2. Zaktualizowac mapper `transformDashboard(...)`.
3. Dodac API client dla mutacji.
4. Zmienic `App.tsx`, zeby przekazywal `refreshDashboard`.
5. Przerobic `QuestsPanel`.
6. Przerobic `HabitsPanel`.
7. Przetestowac klik questa i habitu w dev Vite.
8. Uruchomic `npm run typecheck`.
9. Uruchomic `npm run build`.

### 5.12. Kryteria akceptacji modulu 4

Modul 4 jest gotowy, gdy:

- klik questa wysyla `POST /api/quests/<id>/complete/`,
- quest po sukcesie jest wykonany po danych z backendu,
- podwojne klikniecie nie tworzy podwojnego XP,
- klik habitu wysyla `POST /api/habits/<id>/toggle/`,
- habit po sukcesie pokazuje stan z backendu,
- streak habitu pochodzi z API,
- milestone unlock pokazuje sie po response z API,
- `localStorage` nie przechowuje wykonanych questow ani habitow,
- mapper nie generuje ID z tytulu, labela ani indeksu,
- `activeChallenge` jest nullable i UI ma empty state dla `null`,
- po kazdej mutacji dashboard odswieza XP, level, weekly progress i sekcje RPG,
- CSRF dziala w trybie Vite dev i przez Django root `/`,
- `npm run typecheck` przechodzi,
- `npm run build` przechodzi.

### 5.13. Testy modulu 4

Minimalne testy manualne:

- wejsc na `http://127.0.0.1:5173/`,
- sprawdzic, ze dashboard pobiera `GET /api/dashboard/`,
- kliknac niewykonanego questa,
- sprawdzic request `POST /api/quests/<id>/complete/`,
- sprawdzic, ze UI odswieza XP i completed state,
- kliknac habit,
- sprawdzic request `POST /api/habits/<id>/toggle/`,
- odswiezyc strone i potwierdzic, ze stan habitu zostal w bazie,
- sprawdzic, ze `localStorage` nie zawiera `life-rpg-quests-*` ani `life-rpg-habits-*`,
- sprawdzic, ze dashboard nie psuje sie przy `active_challenge=null`,
- wykonac build i sprawdzic `http://127.0.0.1:8000/`.

Automatyzacja frontendowa w MVP moze ograniczyc sie do:

- `npm run typecheck`,
- `npm run build`.

Jezeli zostanie dodany Vitest/Testing Library, priorytetowe testy:

- `QuestsPanel` wysyla request i blokuje przycisk w trakcie,
- `QuestsPanel` pokazuje blad bez zmiany completed state,
- `HabitsPanel` wysyla request i odswieza dashboard,
- `HabitsPanel` nie korzysta z `localStorage`.

## 6. Wspolny plan wdrozenia modulow 3-4

Rekomendowana kolejnosc:

1. Zakonczyc moduly 0-2: modele, migracje, seed, serwisy questow i habitow.
2. Modul 3: podlaczyc `GET /api/dashboard/` do realnych danych RPG.
3. Modul 3: dodac testy kontraktu dashboard API.
4. Modul 4: przestawic mapper Reacta na realne ID i nowe pola.
5. Modul 4: dodac mutacje API w `frontend/src/api/dashboard.ts`.
6. Modul 4: usunac `localStorage` z `QuestsPanel`.
7. Modul 4: usunac `localStorage` z `HabitsPanel`.
8. Modul 4: odpalic w Vite dev i sprawdzic requesty.
9. Modul 4: zbudowac React i sprawdzic przez Django root `/`.
10. Usunac tymczasowe aliasy JSON, jezeli nie sa juz potrzebne.

## 7. Ryzyka i decyzje do pilnowania

Ryzyka:

- niespojny kontrakt JSON miedzy backendem i mapperem Reacta,
- podwojne naliczenie XP przy szybkim podwojnym kliknieciu,
- lokalny stan Reacta rozjechany z backendiem po bledzie requestu,
- N+1 query przy rewardach i streakach,
- fake fallbacki pozostawione w dashboardzie po wdrozeniu modeli RPG.

Decyzje:

- w MVP po mutacji robimy pelny refresh dashboardu,
- UI nie nalicza XP samodzielnie,
- UI nie generuje domenowych ID,
- UI nie zapisuje questow/habitow w `localStorage`,
- backend moze tymczasowo trzymac aliasy JSON tylko na czas migracji frontu.

## 8. Definition of Done dla modulow 3-4

Moduly 3-4 mozna uznac za zakonczone, gdy:

- dashboard API zwraca realne dane RPG z bazy,
- React pokazuje realne questy i habity,
- questy i habity zmieniaja stan przez API,
- XP i streaki sa liczone w backendzie,
- mock/localStorage nie steruja stanem domenowym,
- Vite dev dziala na `127.0.0.1:5173`,
- Django root `/` dziala po `npm run build`,
- `python manage.py test` przechodzi,
- `npm run typecheck` przechodzi,
- `npm run build` przechodzi.
