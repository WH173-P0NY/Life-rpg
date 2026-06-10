# Life RPG - specyfikacja API i React: Goals, Challenges, Achievements

## 1. Cel dokumentu

Ten dokument opisuje nastepny modul aplikacji Life RPG:

- `Goals` - dlugoterminowe cele uzytkownika,
- `Challenges` - wyzwania z check-inami i nagroda XP,
- `Achievements` - odznaki odblokowywane przez zdarzenia i milestone.

Zakres dokumentu to kontrakt Django JSON API oraz React frontend. Dokument nie
wdraza modeli ani widokow, ale ma byc bezposrednia specyfikacja dla
implementacji.

## 2. Aktualny stan repo po sprawdzeniu

Sprawdzone obszary:

- React shell: `frontend/src/App.tsx`,
- sidebar i widoki: `frontend/src/components/Sidebar.tsx`,
- dashboard API client: `frontend/src/api/dashboard.ts`,
- typy dashboardu: `frontend/src/types/dashboard.ts`,
- Journal: `frontend/src/api/journal.ts`, `frontend/src/components/HeroJournalView.tsx`,
- Calendar: `frontend/src/api/calendar.ts`, `frontend/src/components/CalendarView.tsx`,
- backend routing: `config/urls.py`, `rpg/urls.py`, `planner/urls.py`,
- obecne modele RPG: `rpg/models.py`,
- dashboard context: `dashboard/services.py`, `dashboard/views.py`.

Wnioski:

- aplikacja `rpg` juz istnieje,
- questy, habity, milestone habitu, journal i identity juz istnieja,
- `planner` i osobny widok Calendar juz istnieja,
- React ma osobne widoki sidebar przez `activeView` i hash URL,
- `Goals` jest teraz placeholderem: pokazuje `ChallengePanel` i pusty panel goals,
- `Achievements` jest teraz prosta lista z `dashboard.achievements`,
- `dashboard/services.py` nadal zwraca `active_challenge: None` oraz `achievements: []`,
- API clienty trzymaja prawidlowy wzorzec: backend DTO w `snake_case`, mapper Reacta do `camelCase`,
- `QuestsPanel` i `HabitsPanel` uzywaja mutacji API i po sukcesie wywoluja refresh dashboardu,
- `localStorage` jest uzywany dla theme; nie powinien byc uzywany dla danych domenowych.

## 3. Decyzje techniczne

- Mechaniki progression zostaja w jednej aplikacji Django `rpg`.
- Django udostepnia standardowe widoki JSON, bez DRF.
- Backend request/response uzywa `snake_case`.
- Reactowe typy i komponenty uzywaja `camelCase`.
- Mapowanie `snake_case` -> `camelCase` odbywa sie w `frontend/src/api/progression.ts`
  oraz w istniejacym `frontend/src/api/dashboard.ts`.
- Backend pozostaje source of truth dla goalow, challenge, achievementow, XP i unlockow.
- React nie zapisuje danych domenowych w `localStorage`.
- Dozwolone `localStorage`: theme i ustawienia UI, jezeli nie sa domenowym stanem RPG.
- XP jest zapisywane tylko przez `skills.XpEvent`.
- Achievement nie daje XP.
- Goal w MVP nie daje XP bezposrednio.
- Challenge moze dac XP przy ukonczeniu, przez `skills.XpEvent`.
- Cofniecie progressu nie usuwa XP ani achievementow.
- Mutacje musza byc idempotentne dla podwojnego klikniecia.

## 4. Modele domenowe - zakres implementacyjny

Ta sekcja opisuje oczekiwany ksztalt modeli tylko jako tlo dla API.

### 4.1. Goal

Model: `rpg.Goal`

Pola:

- `id`,
- `title`,
- `description`,
- `status`,
- `priority`,
- `progress_value`,
- `target_value`,
- `target_unit`,
- `starts_on`,
- `due_on`,
- `created_by`,
- `created_at`,
- `updated_at`,
- `completed_at`,
- `archived_at`.

Statusy:

- `draft`,
- `active`,
- `completed`,
- `archived`.

Priorytety:

- `low`,
- `normal`,
- `high`,
- `legendary`.

Zasady:

- `title` nie moze byc puste,
- `target_value` musi byc wieksze od `0`,
- `progress_value` nie moze byc ujemne,
- serwis obcina `progress_value` do `target_value`,
- goal completion tworzy wpis journala z `source_type="goal_completion"`,
- goal completion nie tworzy XP w MVP,
- goal moze miec powiazane skille jako kontekst, ale bez automatycznego XP.

Opcjonalny model powiazania:

- `rpg.GoalSkill`
- pola: `goal`, `skill`, `weight`
- sluzy tylko do filtrowania i UI, nie do naliczania XP.

### 4.2. Challenge

Model: `rpg.Challenge`

Pola:

- `id`,
- `title`,
- `description`,
- `status`,
- `start_date`,
- `end_date`,
- `target_value`,
- `target_unit`,
- `current_value`,
- `reward_title`,
- `created_by`,
- `created_at`,
- `updated_at`,
- `completed_at`,
- `xp_awarded_at`.

Statusy:

- `draft`,
- `active`,
- `completed`,
- `failed`,
- `archived`.

Zasady:

- dashboard pokazuje jeden aktywny challenge,
- wybor aktywnego challenge: `status=active`, najblizsze `end_date`, najnowszy `created_at`,
- progres challenge jest zapisywany jako dzienne `ChallengeCheckIn`,
- `current_value` jest cachem przeliczanym z udanych check-inow,
- `toggle` check-inu nie konczy challenge automatycznie,
- ukonczenie challenge wymaga osobnej akcji `complete`,
- ukonczenie challenge moze przyznac XP z `ChallengeReward`,
- XP challenge jest idempotentne przez `xp_awarded_at`,
- brak rewardow XP jest dozwolony.

Model: `rpg.ChallengeReward`

Pola:

- `id`,
- `challenge`,
- `skill`,
- `xp_amount`,
- `created_at`.

Zasady:

- para `challenge` + `skill` jest unikalna,
- `xp_amount` musi byc wieksze od `0`,
- jeden challenge moze nagradzac kilka skilli.

Model: `rpg.ChallengeCheckIn`

Pola:

- `id`,
- `challenge`,
- `checked_on`,
- `value`,
- `successful`,
- `note`,
- `created_at`,
- `updated_at`.

Zasady:

- `checked_on` jest unikalne w ramach challenge,
- `checked_on` musi byc w zakresie `start_date <= checked_on <= end_date`,
- successful check-in zwieksza `current_value` przez przeliczenie cache,
- drugie klikniecie usuwa check-in, jezeli challenge nie jest zakonczony,
- check-in nie daje XP i nie odblokowuje achievementow bez osobnego `complete`.

### 4.3. Achievement

Model: `rpg.Achievement`

Pola:

- `id`,
- `title`,
- `description`,
- `rarity`,
- `trigger_type`,
- `trigger_config`,
- `is_active`,
- `created_at`,
- `updated_at`.

Rarity:

- `common`,
- `rare`,
- `epic`,
- `legendary`.

Trigger types:

- `manual`,
- `habit_streak`,
- `skill_level`,
- `quest_count`,
- `challenge_completed`,
- `goal_completed`,
- `total_xp`.

`trigger_config` uzywa w bazie `snake_case`, np.:

```json
{
  "streak_days": 7,
  "habit_id": 3
}
```

```json
{
  "skill_id": 2,
  "level": 10
}
```

```json
{
  "quest_count": 30
}
```

Model: `rpg.AchievementUnlock`

Pola:

- `id`,
- `achievement`,
- `unlocked_at`,
- `source_type`,
- `source_id`,
- `note`.

Zasady:

- jeden achievement moze byc odblokowany tylko raz,
- unlock jest idempotentny,
- achievement nie tworzy `XpEvent`,
- unlock moze tworzyc automatyczny wpis journala,
- usuniecie/zmiana zrodla nie usuwa unlocku.

## 5. Wspolny kontrakt API

### 5.1. Format bledow

Wszystkie nowe endpointy zwracaja bledy w tym formacie:

```json
{
  "error": {
    "code": "validation_error",
    "message": "title is required.",
    "fields": {
      "title": ["This field is required."]
    }
  }
}
```

`fields` jest opcjonalne.

Statusy:

- `400` - niepoprawny JSON albo walidacja,
- `404` - brak rekordu,
- `409` - konflikt domenowy, np. proba ukonczenia archiwalnego challenge,
- `405` - zla metoda HTTP.

### 5.2. CSRF

Mutacje `POST`, `PATCH`, `DELETE` wysylaja naglowek:

```txt
X-CSRFToken: <csrftoken>
```

Tak samo jak obecne klienty `dashboard.ts`, `journal.ts` i `calendar.ts`.

### 5.3. Daty

- `DateField` w JSON: `YYYY-MM-DD`,
- `DateTimeField` w JSON: ISO datetime z timezone,
- backend uzywa lokalnej daty aplikacji dla dziennych operacji.

## 6. Goals API

### 6.1. `GET /api/goals/`

Query params:

- `status` - opcjonalnie: `draft`, `active`, `completed`, `archived`, `all`,
- `query` - opcjonalny tekst wyszukiwania,
- `skill_id` - opcjonalny filtr,
- `limit` - domyslnie `50`, maksymalnie `100`.

Response `200`:

```json
{
  "goals": [
    {
      "id": 1,
      "title": "Build Life RPG MVP",
      "description": "Create the first usable version.",
      "status": "active",
      "priority": "legendary",
      "progress_value": 35,
      "target_value": 100,
      "target_unit": "percent",
      "progress_percent": 35,
      "starts_on": "2026-06-10",
      "due_on": "2026-07-31",
      "created_by": "manual",
      "linked_skills": [
        {
          "id": 2,
          "name": "Programming",
          "weight": 100
        }
      ],
      "created_at": "2026-06-10T12:00:00+02:00",
      "updated_at": "2026-06-10T12:00:00+02:00",
      "completed_at": null,
      "archived_at": null
    }
  ],
  "stats": {
    "active": 1,
    "completed": 0,
    "archived": 0
  }
}
```

### 6.2. `POST /api/goals/`

Request:

```json
{
  "title": "Build Life RPG MVP",
  "description": "Create the first usable version.",
  "status": "active",
  "priority": "legendary",
  "progress_value": 0,
  "target_value": 100,
  "target_unit": "percent",
  "starts_on": "2026-06-10",
  "due_on": "2026-07-31",
  "skill_ids": [2]
}
```

Response `201`:

```json
{
  "goal": {
    "id": 1,
    "title": "Build Life RPG MVP",
    "description": "Create the first usable version.",
    "status": "active",
    "priority": "legendary",
    "progress_value": 0,
    "target_value": 100,
    "target_unit": "percent",
    "progress_percent": 0,
    "starts_on": "2026-06-10",
    "due_on": "2026-07-31",
    "created_by": "manual",
    "linked_skills": [
      {
        "id": 2,
        "name": "Programming",
        "weight": 100
      }
    ],
    "created_at": "2026-06-10T12:00:00+02:00",
    "updated_at": "2026-06-10T12:00:00+02:00",
    "completed_at": null,
    "archived_at": null
  }
}
```

### 6.3. `PATCH /api/goals/<id>/`

Request zawiera dowolny podzbior pol:

```json
{
  "title": "Build Life RPG Beta",
  "progress_value": 50,
  "due_on": "2026-08-15",
  "skill_ids": [2, 4]
}
```

Response `200`:

```json
{
  "goal": {
    "id": 1,
    "title": "Build Life RPG Beta",
    "description": "Create the first usable version.",
    "status": "active",
    "priority": "legendary",
    "progress_value": 50,
    "target_value": 100,
    "target_unit": "percent",
    "progress_percent": 50,
    "starts_on": "2026-06-10",
    "due_on": "2026-08-15",
    "created_by": "manual",
    "linked_skills": [],
    "created_at": "2026-06-10T12:00:00+02:00",
    "updated_at": "2026-06-10T12:05:00+02:00",
    "completed_at": null,
    "archived_at": null
  }
}
```

### 6.4. `POST /api/goals/<id>/complete/`

Request:

```json
{
  "note": "MVP is usable."
}
```

Response `200`:

```json
{
  "goal": {
    "id": 1,
    "title": "Build Life RPG Beta",
    "status": "completed",
    "progress_value": 100,
    "target_value": 100,
    "target_unit": "percent",
    "progress_percent": 100,
    "completed_at": "2026-06-10T12:10:00+02:00"
  },
  "journal_entry": {
    "id": 18,
    "title": "Goal completed: Build Life RPG Beta",
    "source_type": "goal_completion",
    "source_id": 1
  },
  "dashboard_refresh_required": true
}
```

### 6.5. `POST /api/goals/<id>/archive/`

Request:

```json
{
  "note": "Goal replaced by a more specific one."
}
```

Response `200`:

```json
{
  "goal": {
    "id": 1,
    "title": "Build Life RPG Beta",
    "status": "archived",
    "archived_at": "2026-06-10T12:15:00+02:00"
  },
  "dashboard_refresh_required": true
}
```

## 7. Challenges API

### 7.1. `GET /api/challenges/`

Query params:

- `status` - opcjonalnie: `draft`, `active`, `completed`, `failed`, `archived`, `all`,
- `limit` - domyslnie `50`, maksymalnie `100`.

Response `200`:

```json
{
  "challenges": [
    {
      "id": 1,
      "title": "30 Days No Sugar",
      "description": "Build discipline by avoiding sugar.",
      "status": "active",
      "start_date": "2026-06-01",
      "end_date": "2026-06-30",
      "elapsed_days": 10,
      "total_days": 30,
      "current_value": 10,
      "target_value": 30,
      "target_unit": "days",
      "progress_percent": 33,
      "reward_title": "Epic Willpower Badge",
      "reward_xp": 500,
      "reward_skills": [
        {
          "id": 4,
          "name": "Fitness",
          "xp_amount": 250
        },
        {
          "id": 6,
          "name": "Health",
          "xp_amount": 250
        }
      ],
      "created_by": "manual",
      "created_at": "2026-06-01T09:00:00+02:00",
      "updated_at": "2026-06-10T09:00:00+02:00",
      "completed_at": null,
      "xp_awarded_at": null
    }
  ],
  "active_challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "active",
    "start_date": "2026-06-01",
    "end_date": "2026-06-30",
    "elapsed_days": 10,
    "total_days": 30,
    "current_value": 10,
    "target_value": 30,
    "target_unit": "days",
    "progress_percent": 33,
    "reward_title": "Epic Willpower Badge",
    "reward_xp": 500,
    "reward_skills": []
  }
}
```

### 7.2. `POST /api/challenges/`

Request:

```json
{
  "title": "30 Days No Sugar",
  "description": "Build discipline by avoiding sugar.",
  "status": "active",
  "start_date": "2026-06-01",
  "end_date": "2026-06-30",
  "target_value": 30,
  "target_unit": "days",
  "current_value": 0,
  "reward_title": "Epic Willpower Badge",
  "rewards": [
    {
      "skill_id": 4,
      "xp_amount": 250
    },
    {
      "skill_id": 6,
      "xp_amount": 250
    }
  ]
}
```

Response `201`:

```json
{
  "challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "active",
    "current_value": 0,
    "target_value": 30,
    "target_unit": "days",
    "progress_percent": 0,
    "reward_title": "Epic Willpower Badge",
    "reward_xp": 500,
    "reward_skills": []
  },
  "dashboard_refresh_required": true
}
```

### 7.3. `PATCH /api/challenges/<id>/`

Request zawiera dowolny podzbior pol:

```json
{
  "title": "30 Days No Sugar",
  "end_date": "2026-06-30",
  "reward_title": "Epic Willpower Badge"
}
```

Response `200`:

```json
{
  "challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "active",
    "progress_percent": 33,
    "reward_xp": 500
  },
  "dashboard_refresh_required": true
}
```

### 7.4. `POST /api/challenges/<id>/toggle/`

Tworzy albo usuwa dzienny `ChallengeCheckIn`, przelicza `current_value` i zwraca
informacje, czy challenge jest gotowy do recznego ukończenia.

Request:

```json
{
  "checked_on": "2026-06-14",
  "value": 1,
  "note": "Day 14 completed."
}
```

Response `200`:

```json
{
  "challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "active",
    "current_value": 14,
    "target_value": 30,
    "target_unit": "check",
    "progress_percent": 47,
    "completed_at": null,
    "xp_awarded_at": null
  },
  "check_in": {
    "id": 12,
    "checked_on": "2026-06-14",
    "value": 1,
    "successful": true
  },
  "checked": true,
  "completion_ready": false,
  "journal_entry": null,
  "xp_events": [],
  "dashboard_refresh_required": true
}
```

Decyzja: `toggle` nie przyznaje XP i nie konczy challenge automatycznie.
Jezeli request zawiera `note`, backend zapisuje ja na `ChallengeCheckIn.note`;
toggle nie tworzy automatycznego wpisu journala w MVP.

### 7.5. `POST /api/challenges/<id>/complete/`

Request:

```json
{
  "note": "Completed without breaking the streak."
}
```

Response `200`:

```json
{
  "challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "completed",
    "current_value": 30,
    "target_value": 30,
    "target_unit": "days",
    "progress_percent": 100,
    "completed_at": "2026-06-30T21:00:00+02:00",
    "xp_awarded_at": "2026-06-30T21:00:00+02:00"
  },
  "xp_events": [
    {
      "id": 101,
      "skill": {
        "id": 4,
        "name": "Fitness"
      },
      "amount": 250,
      "source_type": "challenge",
      "note": "Challenge: 30 Days No Sugar; challenge_id=1",
      "earned_at": "2026-06-30T21:00:00+02:00"
    }
  ],
  "achievement_unlocks": [
    {
      "id": 7,
      "achievement_id": 3,
      "title": "Iron Discipline",
      "rarity": "epic",
      "unlocked_at": "2026-06-30T21:00:00+02:00"
    }
  ],
  "journal_entry": {
    "id": 22,
    "title": "Challenge completed: 30 Days No Sugar",
    "source_type": "challenge_completion",
    "source_id": 1
  },
  "dashboard_refresh_required": true
}
```

Powtorne wywolanie `complete` zwraca ten sam stan domenowy i nie tworzy nowych
`XpEvent`.

### 7.6. `POST /api/challenges/<id>/fail/`

Zamyka challenge jako nieudany. Nie przyznaje XP, nie usuwa check-inow i tworzy
systemowy wpis journala z `source_type="challenge_failure"`.

Request:

```json
{
  "note": "Missed a required day."
}
```

Response `200`:

```json
{
  "challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "failed",
    "current_value": 14,
    "target_value": 30,
    "target_unit": "check",
    "progress_percent": 47,
    "failed_at": "2026-06-15T21:00:00+02:00",
    "xp_awarded_at": null
  },
  "xp_events": [],
  "achievement_unlocks": [],
  "journal_entry": {
    "id": 23,
    "title": "Challenge failed: 30 Days No Sugar",
    "source_type": "challenge_failure",
    "source_id": 1
  },
  "dashboard_refresh_required": true
}
```

Powtorne wywolanie `fail` zwraca ten sam stan domenowy i nie tworzy nowych
`JournalEntry`.

## 8. Achievements API

### 8.1. `GET /api/achievements/`

Query params:

- `status` - `all`, `unlocked`, `locked`; domyslnie `all`,
- `rarity` - opcjonalny filtr,
- `query` - opcjonalne wyszukiwanie.

Response `200`:

```json
{
  "achievements": [
    {
      "id": 3,
      "title": "Iron Discipline",
      "description": "Complete a 30-day challenge.",
      "rarity": "epic",
      "trigger_type": "challenge_completed",
      "trigger_config": {
        "challenge_id": 1
      },
      "is_active": true,
      "unlocked": true,
      "unlock": {
        "id": 7,
        "unlocked_at": "2026-06-30T21:00:00+02:00",
        "source_type": "challenge_completion",
        "source_id": 1,
        "note": "30 Days No Sugar completed."
      },
      "progress": {
        "current": 1,
        "target": 1,
        "unit": "challenge",
        "progress_percent": 100
      }
    },
    {
      "id": 4,
      "title": "Book Worm",
      "description": "Complete 30 reading quests.",
      "rarity": "rare",
      "trigger_type": "quest_count",
      "trigger_config": {
        "quest_count": 30
      },
      "is_active": true,
      "unlocked": false,
      "unlock": null,
      "progress": {
        "current": 12,
        "target": 30,
        "unit": "quests",
        "progress_percent": 40
      }
    }
  ],
  "stats": {
    "total": 2,
    "unlocked": 1,
    "locked": 1,
    "legendary_unlocked": 0
  }
}
```

### 8.2. `POST /api/achievements/<id>/unlock/`

Endpoint do recznego unlocku i testow MVP. Triggerowe unlocki powinny isc przez
serwisy domenowe po zdarzeniach.

Request:

```json
{
  "source_type": "manual",
  "source_id": null,
  "note": "Unlocked manually from the achievement screen."
}
```

Response `200`:

```json
{
  "unlock": {
    "id": 7,
    "achievement_id": 3,
    "title": "Iron Discipline",
    "rarity": "epic",
    "unlocked_at": "2026-06-30T21:00:00+02:00",
    "source_type": "manual",
    "source_id": null,
    "note": "Unlocked manually from the achievement screen."
  },
  "journal_entry": {
    "id": 24,
    "title": "Achievement unlocked: Iron Discipline",
    "source_type": "achievement_unlock",
    "source_id": 7
  },
  "xp_events": [],
  "dashboard_refresh_required": true
}
```

Powtorne wywolanie nie tworzy nowego unlocku i nadal zwraca `200`.

### 8.3. `POST /api/achievements/evaluate/`

Endpoint pomocniczy dla MVP, do recznego odpalenia triggerow bez Celery.

Request:

```json
{
  "trigger_types": ["habit_streak", "skill_level", "quest_count", "total_xp"]
}
```

Response `200`:

```json
{
  "unlocks": [
    {
      "id": 8,
      "achievement_id": 4,
      "title": "Book Worm",
      "rarity": "rare",
      "unlocked_at": "2026-06-30T21:05:00+02:00"
    }
  ],
  "dashboard_refresh_required": true
}
```

Ten endpoint nie jest wymagany do codziennego flow, ale ulatwia MVP i testy.

## 9. Dashboard API integration

`GET /api/dashboard/` musi zostac rozszerzone bez lamania obecnych sekcji.

### 9.1. `active_challenge`

Docelowy backend DTO:

```json
{
  "active_challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "active",
    "start_date": "2026-06-01",
    "end_date": "2026-06-30",
    "elapsed_days": 10,
    "total_days": 30,
    "current_value": 10,
    "target_value": 30,
    "target_unit": "days",
    "progress_percent": 33,
    "reward_title": "Epic Willpower Badge",
    "reward_xp": 500,
    "reward_skills": [
      {
        "id": 4,
        "name": "Fitness",
        "xp_amount": 250
      }
    ]
  }
}
```

Jezeli nie ma aktywnego challenge:

```json
{
  "active_challenge": null
}
```

Legacy pola `name`, `day`, `total`, `progress`, `reward`, `xp_reward` nie sa
docelowym kontraktem. Jezeli beda potrzebne na czas migracji, musza zostac
usuniete w stabilizacji.

### 9.2. `achievements`

Dashboard pokazuje ostatnie odblokowane achievementy, nie pelny katalog.

```json
{
  "achievements": [
    {
      "id": 7,
      "achievement_id": 3,
      "title": "Iron Discipline",
      "description": "Complete a 30-day challenge.",
      "rarity": "epic",
      "unlocked_at": "2026-06-30T21:00:00+02:00",
      "source_type": "challenge_completion",
      "source_id": 1
    }
  ]
}
```

Pelny katalog jest pobierany przez `GET /api/achievements/`.

### 9.3. Journal integration

Automatyczne wpisy journala:

- `source_type="goal_completion"` dla ukonczonego goalu,
- `source_type="challenge_completion"` dla ukonczonego challenge,
- `source_type="achievement_unlock"` dla achievement unlock.

Tworzenie journala jest best-effort:

- blad wpisu journala nie cofa XP challenge,
- response moze zwrocic `journal_entry: null`,
- blad journala moze byc dopisany jako warning w przyszlosci, ale nie jest
  wymagany w MVP.

## 10. React API client i typy

Dodac:

- `frontend/src/api/progression.ts`,
- `frontend/src/types/progression.ts`.

Zaktualizowac:

- `frontend/src/api/dashboard.ts`,
- `frontend/src/types/dashboard.ts`,
- `frontend/src/App.tsx`,
- komponenty `Goals`, `ChallengePanel`, `Achievements`.

### 10.1. Typy frontendowe

Przykladowy ksztalt:

```ts
export interface ProgressionGoal {
  id: string;
  title: string;
  description: string;
  status: "draft" | "active" | "completed" | "archived";
  priority: "low" | "normal" | "high" | "legendary";
  progressValue: number;
  targetValue: number;
  targetUnit: string;
  progressPercent: number;
  startsOn: string | null;
  dueOn: string | null;
  linkedSkills: Array<{ id: string; name: string; weight: number }>;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  archivedAt: string | null;
}

export interface ProgressionChallenge {
  id: string;
  title: string;
  description: string;
  status: "draft" | "active" | "completed" | "failed" | "archived";
  startDate: string;
  endDate: string;
  elapsedDays: number;
  totalDays: number;
  currentValue: number;
  targetValue: number;
  targetUnit: string;
  progressPercent: number;
  rewardTitle: string;
  rewardXp: number;
  rewardSkills: Array<{ id: string; name: string; xpAmount: number }>;
  completedAt: string | null;
  xpAwardedAt: string | null;
}

export interface ProgressionAchievement {
  id: string;
  title: string;
  description: string;
  rarity: "common" | "rare" | "epic" | "legendary";
  triggerType: string;
  triggerConfig: Record<string, unknown>;
  isActive: boolean;
  unlocked: boolean;
  unlock: AchievementUnlock | null;
  progress: {
    current: number;
    target: number;
    unit: string;
    progressPercent: number;
  };
}
```

### 10.2. Mappery

`frontend/src/api/progression.ts` ma zawierac lokalne typy `Raw*` w
`snake_case`, np.:

```ts
type RawProgressionChallenge = {
  id: number;
  title: string;
  start_date: string;
  end_date: string;
  current_value: number;
  target_value: number;
  target_unit: string;
  progress_percent: number;
  reward_title: string;
  reward_xp: number;
};
```

I mapowanie:

```ts
function transformChallenge(raw: RawProgressionChallenge): ProgressionChallenge {
  return {
    id: String(raw.id),
    title: raw.title,
    startDate: raw.start_date,
    endDate: raw.end_date,
    currentValue: raw.current_value,
    targetValue: raw.target_value,
    targetUnit: raw.target_unit,
    progressPercent: raw.progress_percent,
    rewardTitle: raw.reward_title,
    rewardXp: raw.reward_xp
  };
}
```

Request body wysylany do Django zawsze w `snake_case`, nawet jezeli funkcja
Reacta przyjmuje payload w `camelCase`.

### 10.3. Funkcje API

Minimalny zestaw:

```ts
fetchGoals(params): Promise<GoalsResponse>
createGoal(payload): Promise<ProgressionGoal>
updateGoal(goalId, payload): Promise<ProgressionGoal>
completeGoal(goalId, payload): Promise<GoalMutationResponse>
archiveGoal(goalId, payload): Promise<GoalMutationResponse>

fetchChallenges(params): Promise<ChallengesResponse>
createChallenge(payload): Promise<ProgressionChallenge>
updateChallenge(challengeId, payload): Promise<ProgressionChallenge>
toggleChallengeCheckIn(challengeId, payload): Promise<ChallengeMutationResponse>
completeChallenge(challengeId, payload): Promise<ChallengeMutationResponse>

fetchAchievements(params): Promise<AchievementsResponse>
unlockAchievement(achievementId, payload): Promise<AchievementUnlockResponse>
evaluateAchievements(payload): Promise<AchievementEvaluationResponse>
```

## 11. React views

### 11.1. Goals view

`#goals` przestaje byc placeholderem.

Nowy komponent:

- `frontend/src/components/GoalsView.tsx`.

Zawartosc:

- lista celow,
- filtry `Active`, `Draft`, `Completed`, `Archived`,
- formularz tworzenia goalu,
- edycja podstawowych pol,
- progress editor,
- akcje `Complete`, `Archive`,
- panel aktywnego challenge albo lista challenge obok celow.

Stany:

- loading: szkielet listy albo tekst `Loading goals...`,
- empty: `No goals defined yet.`,
- error: panel bledu z `Retry`,
- fallback API: formularze i mutacje disabled.

Po mutacji:

1. ustawic `pendingId` lub `isSaving`,
2. wyslac request,
3. po sukcesie odswiezyc lokalny widok przez `refreshProgression()`,
4. po sukcesie wywolac globalny `refreshDashboard()`,
5. nie aktualizowac domenowego stanu przez `localStorage`.

### 11.2. Challenges UI

MVP moze byc czescia `GoalsView`, ale komponent `ChallengePanel` na dashboardzie
powinien zostac zaktualizowany pod finalny DTO.

Widok challenge powinien obslugiwac:

- aktywny challenge,
- liste draft/active/completed,
- dzienny toggle/check-in,
- przycisk `Complete`,
- reward preview,
- liste skilli nagrody XP,
- blokade podwojnego klikniecia.

Stany:

- brak aktywnego challenge: pusty panel,
- challenge bez XP reward: pokazac badge/reward title bez `+XP`,
- API fallback: disabled actions,
- error przy mutacji: komunikat w panelu.

### 11.3. Achievements view

`#achievements` przestaje byc lista tylko z dashboardu.

Nowy komponent:

- `frontend/src/components/AchievementsView.tsx`.

Zawartosc:

- katalog achievementow,
- filtry `All`, `Unlocked`, `Locked`,
- filtr rarity,
- search,
- progress locked achievementow,
- data unlocku,
- source unlocku,
- opcjonalny przycisk manual unlock tylko dla `triggerType === "manual"`.

Stany:

- loading: `Loading achievements...`,
- empty all: `No achievements defined yet.`,
- empty filtered: `No achievements match this filter.`,
- error: panel bledu z `Retry`,
- fallback API: disabled manual unlock/evaluate.

Po mutacji unlock/evaluate:

1. odswiezyc `fetchAchievements()`,
2. wywolac `refreshDashboard()`,
3. nie dodawac lokalnie fake unlockow.

### 11.4. Dashboard integration

`App.tsx`:

- `case "goals"` renderuje `GoalsView`,
- `case "achievements"` renderuje `AchievementsView`,
- oba dostaja `isApiReady` i `onDashboardRefresh={refreshDashboard}`,
- dashboard nadal uzywa `ChallengePanel` w glownej siatce,
- dashboard achievements w `ChartsPanel` pokazuje ostatnie unlocki z
  `GET /api/dashboard/`.

`ChallengePanel`:

- przyjmuje `ActiveChallenge | null`,
- obsluguje finalne pola: `currentValue`, `targetValue`, `targetUnit`,
  `elapsedDays`, `totalDays`, `rewardXp`,
- nie zaklada, ze challenge istnieje.

`frontend/src/types/dashboard.ts`:

- `ActiveChallenge` trzeba rozszerzyc zgodnie z finalnym DTO,
- `Achievement` dashboardowy powinien miec stabilne `id` z unlocku albo
  achievementu, nie generowane z tytulu.

## 12. No localStorage policy

Zakazane:

- zapis goalow,
- zapis challenge check-in,
- zapis achievement unlock,
- cache achievementow jako source of truth,
- symulowanie XP albo unlockow po stronie Reacta.

Dozwolone:

- theme,
- zwijanie/rozwiniecie panelu,
- ostatni wybrany filtr UI, jezeli nie udaje danych domenowych.

Jezeli API nie dziala, widok moze pokazac empty/error/fallback, ale mutacje maja
byc disabled.

## 13. Seed

`seed_life_rpg` powinien dodac idempotentnie:

Goals:

- `Build Life RPG MVP`,
- `Improve Health System`,
- `Create Finance Module`.

Challenge:

- `30 Days No Sugar`,
- status `active`,
- reward title `Epic Willpower Badge`,
- rewardy XP do istniejacych skilli, jezeli istnieja.

Achievements:

- `Early Riser` - `manual` albo przyszly habit trigger,
- `Book Worm` - `quest_count`,
- `Iron Discipline` - `challenge_completed`,
- `Unstoppable` - `habit_streak`,
- `Legendary` - `total_xp`.

Seed nie powinien tworzyc domyslnych completion, unlockow ani historii XP poza
tym, co jest potrzebne w istniejacych seedach testowych.

## 14. Testy i kryteria akceptacji

Backend:

- modele maja walidacje pustych tytulow i zakresow progressu,
- `Goal` create/update/complete/archive dziala przez API,
- goal completion nie tworzy `XpEvent`,
- `Challenge` toggle/check-in nie tworzy XP,
- `Challenge` complete tworzy XP przez `skills.XpEvent`,
- podwojne `Challenge` complete nie duplikuje XP,
- `Achievement` unlock jest idempotentny,
- achievement nie tworzy XP,
- trigger `challenge_completed` dziala po ukonczeniu challenge,
- `GET /api/dashboard/` zwraca realny `active_challenge`,
- `GET /api/dashboard/` zwraca ostatnie odblokowane achievementy,
- seed jest idempotentny.

Frontend:

- `npm run typecheck` przechodzi,
- `npm run build` przechodzi,
- `GoalsView` pokazuje loading/empty/error,
- `GoalsView` po mutacji odswieza widok i dashboard,
- `AchievementsView` pokazuje loading/empty/error,
- unlock/evaluate odswieza widok i dashboard,
- `ChallengePanel` obsluguje `null`,
- React nie uzywa `localStorage` dla goalow, challenge ani achievementow.

Komendy koncowe:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py test
cd frontend
npm run typecheck
npm run build
```

## 15. Rekomendowana kolejnosc implementacji

1. Dodac modele `Goal`, `GoalSkill`, `Challenge`, `ChallengeCheckIn`,
   `ChallengeReward`, `Achievement`, `AchievementUnlock`.
2. Dodac migracje i admin.
3. Dodac serwisy domenowe w `rpg/services.py`.
4. Dodac endpointy w `rpg/views.py` i `rpg/urls.py`.
5. Dodac testy backendowe dla API, XP i idempotencji.
6. Rozszerzyc `seed_life_rpg`.
7. Rozszerzyc `dashboard/services.py` i `dashboard/views.py`.
8. Dodac `frontend/src/api/progression.ts` i `frontend/src/types/progression.ts`.
9. Dodac `GoalsView` i `AchievementsView`.
10. Zaktualizowac `ChallengePanel`, `App.tsx`, `dashboard.ts` i typy dashboardu.
11. Uruchomic pelna bramke testow backend/frontend.

## 16. Decyzje do utrzymania przy implementacji

- Goal jest planowaniem i trackingiem celu, nie zrodlem XP w MVP.
- Challenge jest dlugoterminowa mechanika RPG i moze dawac XP przy ukonczeniu.
- Achievement jest odznaka i nie daje XP.
- `POST /api/challenges/<id>/toggle/` nie konczy challenge automatycznie.
- `POST /api/challenges/<id>/complete/` jest jedynym miejscem awardu XP challenge.
- Dashboard pokazuje tylko jeden aktywny challenge.
- Achievements dashboard pokazuje ostatnie unlocki, a pelny katalog jest w
  osobnym widoku `#achievements`.
- Backend API pozostaje w `snake_case`.
- Reactowe komponenty pracuja na `camelCase`.
- Brak domenowego `localStorage`.
