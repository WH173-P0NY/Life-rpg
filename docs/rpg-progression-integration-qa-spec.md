# Life RPG - Progression Integration & QA Spec

## 1. Cel dokumentu

Ten dokument opisuje plan integracji, seedow, testow i wdrozenia nastepnego modulu Life RPG:

- Goals,
- Challenges,
- Achievements.

Dokument jest specyfikacja wdrozeniowo-QA. Nie zastepuje pelnych specyfikacji produktowych, ale precyzuje jak bezpiecznie podpiac nowy modul do obecnego kodu w repo `/home/wh173-p0ny/ProjectLevel`.

AI quest generation zostaje poza zakresem tego modulu. Modele moga dalej wspierac `created_by="ai"` i `status="draft"`, ale generowanie questow przez OpenAI/Claude bedzie osobnym etapem.

## 2. Stan wejsciowy repo

Sprawdzony stan na start modulu:

- Django 6.0.6, PostgreSQL, React/Vite/Tailwind.
- `rpg` jest w `INSTALLED_APPS`.
- `config/urls.py` podpina `path("api/", include("rpg.urls"))`.
- Istnieja modele: `Quest`, `QuestReward`, `QuestCompletion`, `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock`, `JournalEntry`, `CharacterIdentity`.
- Istnieja endpointy:
  - `POST /api/quests/<id>/complete/`,
  - `POST /api/quests/<id>/progress/`,
  - `POST /api/habits/<id>/toggle/`,
  - `GET /api/journal/`,
  - `POST /api/journal/`,
  - `PATCH /api/journal/<id>/`.
- `dashboard/services.py` zwraca realne questy, habity i journal z `rpg`.
- `dashboard/services.py` nadal zwraca:
  - `active_challenge: None`,
  - `achievements: []`.
- `JournalEntryType` ma juz typy:
  - `challenge`,
  - `achievement`.
- `JournalEntry` ma idempotencje automatycznych wpisow przez unique constraint na `(source_type, source_id)`, gdy `source_type` nie jest puste i `source_id` nie jest null.
- Aktualny seed `seed_life_rpg` tworzy definicje, ale nie tworzy historii quest completion ani habit check-in.
- Aktualne testy `rpg dashboard` przechodza:

```bash
.venv/bin/python manage.py test rpg dashboard
# Ran 85 tests - OK
```

## 3. Decyzje obowiazujace dla modulu

1. Wszystkie nowe mechaniki zostaja w jednej aplikacji Django `rpg`.
2. Backend JSON uzywa `snake_case`.
3. React mapuje `snake_case` na `camelCase` w mapperach frontendu.
4. XP zapisujemy tylko przez `skills.XpEvent`.
5. Goal nie daje XP sam z siebie.
6. Achievement nie daje XP.
7. Challenge moze dawac XP, ale tylko przy ukonczeniu i tylko raz.
8. Journal automatyczny jest best-effort: blad utworzenia wpisu nie cofa glownej akcji domenowej.
9. Seed tworzy definicje i przykladowe aktywne rekordy robocze, ale nie tworzy historii wykonania, unlockow ani XP.
10. Nie dodajemy DRF.
11. Nie dodajemy Celery.
12. Nie dodajemy AI quest generation w tym module.

## 4. Zakres modulu

### W zakresie

- Modele Goals.
- Modele Challenges.
- Modele Achievements.
- Admin dla nowych modeli.
- Migracje.
- Serwisy domenowe.
- Endpointy JSON.
- Integracja dashboardu:
  - `active_challenge` z bazy,
  - `achievements` z bazy,
  - docelowo dane dla widokow sidebar `Goals` i `Achievements`.
- Integracja Journala:
  - automatyczny wpis po ukonczeniu goal,
  - automatyczny wpis po ukonczeniu challenge,
  - automatyczny wpis po odblokowaniu achievementu,
  - statystyka `achievements_unlocked`,
  - activity timeline z goal/challenge/achievement.
- Seed danych startowych.
- Test matrix.
- Smoke testy.
- Plan rollbacku i edge cases.

### Poza zakresem

- AI-generated quests.
- AI-generated achievements.
- AI-generated journal insights.
- Automatyczne planowanie kalendarza przez AI.
- Zaawansowany silnik regul.
- Cofanie XP przez UI.
- Multi-user.
- Inventory rewards.
- Achievement points.
- ActivityWatch integration.

## 5. Model danych - rekomendowany kontrakt

### 5.1. Goal

Model: `rpg.Goal`

Cel: dlugoterminowy kierunek rozwoju uzytkownika.

Pola:

- `id`
- `title` - `CharField(max_length=160)`
- `description` - `TextField(blank=True)`
- `status` - `TextChoices`
- `starts_on` - `DateField(null=True, blank=True)`
- `due_on` - `DateField(null=True, blank=True)`
- `progress_value` - `PositiveIntegerField(default=0)`
- `target_value` - `PositiveIntegerField(default=1)`
- `target_unit` - `CharField(max_length=40, default="count")`
- `created_by` - `CreationSource`
- `completed_at` - `DateTimeField(null=True, blank=True)`
- `created_at`
- `updated_at`

Statusy:

- `draft`
- `active`
- `completed`
- `archived`

Walidacja:

- `title` nie moze byc puste.
- `target_value` musi byc wieksze od `0`.
- `progress_value` nie moze byc ujemne.
- Serwis powinien ograniczac `progress_value` do `0..target_value`.
- `completed_at` ustawia tylko serwis `complete_goal(...)`.

Zasady:

- Goal nie tworzy XP.
- Goal moze byc powiazany ze skillami przez `GoalSkill`.
- Goal moze miec powiazane challenge przez FK z `Challenge`.
- Ukonczenie goal moze odblokowac achievement.
- Ukonczenie goal tworzy automatyczny wpis journala z `source_type="goal_completion"`.

### 5.2. GoalSkill

Model: `rpg.GoalSkill`

Cel: wskazanie, ktore skille wspiera dany goal.

Pola:

- `id`
- `goal` - FK do `Goal`
- `skill` - FK do `skills.Skill`
- `created_at`

Constraint:

- unique `(goal, skill)`.

Zasady:

- `GoalSkill` nie daje XP.
- To tylko powiazanie do UI, analiz i przyszlych questow AI.

### 5.3. Challenge

Model: `rpg.Challenge`

Cel: dluzsze wyzwanie z dziennymi check-inami i opcjonalna nagroda XP.

Pola:

- `id`
- `goal` - FK do `Goal`, null/blank
- `title` - `CharField(max_length=160)`
- `description` - `TextField(blank=True)`
- `status` - `TextChoices`
- `start_date` - `DateField`
- `end_date` - `DateField`
- `target_value` - `PositiveIntegerField`
- `target_unit` - `CharField(max_length=40)`
- `current_value` - `PositiveIntegerField(default=0)`
- `reward_title` - `CharField(max_length=160, blank=True)`
- `created_by` - `CreationSource`
- `completed_at` - `DateTimeField(null=True, blank=True)`
- `xp_awarded_at` - `DateTimeField(null=True, blank=True)`
- `created_at`
- `updated_at`

Statusy:

- `draft`
- `active`
- `completed`
- `failed`
- `archived`

Walidacja:

- `title` nie moze byc puste.
- `target_value` musi byc wieksze od `0`.
- `current_value` nie moze byc ujemne.
- `end_date` nie moze byc przed `start_date`.
- `current_value` jest cachem liczby udanych `ChallengeCheckIn`.
- Serwis przelicza `current_value` do zakresu `0..target_value`.

Zasady:

- Jeden glowny panel dashboardu pokazuje jeden aktywny challenge.
- Wybor aktywnego challenge:
  - `status="active"`,
  - najblizszy `end_date`,
  - najnowszy `created_at`,
  - najnizszy `id` jako stabilny tie-breaker.
- Toggle check-inu nie daje XP.
- Toggle check-inu nie konczy challenge automatycznie.
- XP jest przyznawane tylko przez complete endpoint.
- Ponowne complete nie tworzy kolejnych `XpEvent`.
- Po `xp_awarded_at` rewardy sa traktowane jako zamrozone operacyjnie. Admin moze je technicznie edytowac, ale korekta XP jest reczna i poza UI MVP.

### 5.4. ChallengeCheckIn

Model: `rpg.ChallengeCheckIn`

Cel: dzienny zapis wykonania challenge.

Pola:

- `id`
- `challenge` - FK do `Challenge`
- `checked_on` - `DateField`
- `value` - `PositiveIntegerField(default=1)`
- `successful` - `BooleanField(default=True)`
- `note` - `TextField(blank=True)`
- `created_at`
- `updated_at`

Constraint:

- unique `(challenge, checked_on)`.

Walidacja:

- `checked_on` musi byc w zakresie `start_date <= checked_on <= end_date`.
- `value >= 0`.
- dla `successful=True`, `value > 0`.

Zasady:

- Pierwszy toggle tworzy check-in.
- Drugi toggle usuwa check-in, jezeli challenge nie jest zakonczony.
- Po kazdym toggle serwis przelicza `Challenge.current_value`.
- Check-in nie daje XP i nie tworzy automatycznego wpisu journala.

### 5.5. ChallengeReward

Model: `rpg.ChallengeReward`

Pola:

- `id`
- `challenge` - FK do `Challenge`
- `skill` - FK do `skills.Skill`
- `xp_amount` - `PositiveIntegerField`
- `created_at`

Constraint:

- unique `(challenge, skill)`.
- `xp_amount > 0`.

Zasady:

- Challenge moze nagradzac kilka skilli.
- Brak rewardow jest dozwolony.
- XP zapisujemy przez `skill.add_xp(...)` z `source_type="challenge"`.
- Note XP powinien zawierac `challenge_id=<id>`.

### 5.6. Achievement

Model: `rpg.Achievement`

Pola:

- `id`
- `title` - `CharField(max_length=160)`
- `description` - `TextField(blank=True)`
- `rarity` - `TextChoices`
- `trigger_type` - `TextChoices`
- `trigger_config` - `JSONField(default=dict, blank=True)`
- `icon` - `CharField(max_length=80, blank=True)`
- `is_active` - `BooleanField(default=True)`
- `sort_order` - `PositiveIntegerField(default=0)`
- `created_at`
- `updated_at`

Rarity:

- `common`
- `rare`
- `epic`
- `legendary`

Trigger types:

- `manual`
- `quest_count`
- `habit_streak`
- `skill_level`
- `challenge_completed`
- `goal_completed`

Zasady `trigger_config`:

- Backend przechowuje tylko `snake_case`.
- Docelowo uzywamy stabilnych ID: `skill_id`, `habit_id`, `challenge_id`, `goal_id`.
- Seed moze resolve'owac rekord po nazwie, ale do bazy zapisuje ID.
- Dopuszczalne pola:
  - `quest_count`
  - `period`
  - `habit_id`
  - `streak_days`
  - `skill_id`
  - `level`
  - `challenge_id`
  - `goal_id`

Przyklady:

```json
{"quest_count": 10, "period": "all_time"}
```

```json
{"habit_id": 1, "streak_days": 7}
```

```json
{"skill_id": 2, "level": 5}
```

```json
{"challenge_id": 1}
```

```json
{"goal_id": 1}
```

### 5.7. AchievementUnlock

Model: `rpg.AchievementUnlock`

Pola:

- `id`
- `achievement` - FK do `Achievement`
- `unlocked_at` - `DateTimeField(default=timezone.now)`
- `source_type` - `CharField(max_length=40, blank=True)`
- `source_id` - `PositiveIntegerField(null=True, blank=True)`
- `note` - `TextField(blank=True)`
- `created_at`

Constraint:

- unique `(achievement)`.

Zasady:

- MVP jest single-user, wiec jeden achievement moze byc odblokowany tylko raz.
- Achievement nie daje XP.
- Jeden event moze odblokowac kilka achievementow, wiec nie robimy globalnego unique na `(source_type, source_id)` w `AchievementUnlock`.
- Automatyczny wpis journala uzywa `source_type="achievement_unlock"` i `source_id=<unlock.id>`.

## 6. Serwisy domenowe

Nowa logika ma trafic do `rpg/services.py`. Widoki JSON powinny byc cienka warstwa parsowania requestu i serializacji response.

### 6.1. Goals

Rekomendowane funkcje:

```py
def build_goal_rows() -> list[dict[str, Any]]:
    ...

def update_goal_progress(
    *,
    goal: Goal,
    progress_value: int,
    note: str = "",
) -> Goal:
    ...

def complete_goal(
    *,
    goal: Goal,
    note: str = "",
) -> Goal:
    ...
```

Reguly:

- `update_goal_progress(...)` nie daje XP.
- `progress_value` jest wartoscia bezwzgledna.
- `progress_value` jest ograniczany do `0..target_value`.
- `complete_goal(...)` ustawia `status="completed"`, `progress_value=target_value`, `completed_at`.
- `complete_goal(...)` uruchamia:
  - `evaluate_achievements(event_type="goal_completed", context={...})`,
  - automatyczny journal `source_type="goal_completion"`, `source_id=goal.id`.

### 6.2. Challenges

Rekomendowane funkcje:

```py
def get_active_challenge() -> Challenge | None:
    ...

def serialize_challenge(challenge: Challenge | None) -> dict[str, Any] | None:
    ...

def toggle_challenge_check_in(
    *,
    challenge: Challenge,
    checked_on: date | None = None,
    value: int | None = None,
    note: str = "",
) -> dict[str, Any]:
    ...

def complete_challenge(
    *,
    challenge: Challenge,
    note: str = "",
) -> dict[str, Any]:
    ...

def award_challenge_xp(challenge: Challenge) -> list[XpEvent]:
    ...
```

Reguly:

- `toggle_challenge_check_in(...)` tworzy albo usuwa dzienny `ChallengeCheckIn`.
- `toggle_challenge_check_in(...)` przelicza `current_value`.
- `toggle_challenge_check_in(...)` nie daje XP i nie konczy automatycznie challenge.
- `complete_challenge(...)` jest osobna akcja.
- `complete_challenge(...)` uzywa `transaction.atomic()` i `select_for_update()`.
- Jezeli `xp_awarded_at` juz istnieje, serwis zwraca istniejace XP events i nie tworzy nowych.
- Brak rewardow jest poprawnym przypadkiem.
- Po complete:
  - status `completed`,
  - `current_value=target_value`,
  - `completed_at` ustawiony raz,
  - `xp_awarded_at` ustawiony raz, jezeli istnieja rewardy; dopuszczalne ustawienie rowniez przy pustych rewardach, aby oznaczyc zamknieta akcje.
- Po complete uruchamiamy:
  - `evaluate_achievements(event_type="challenge_completed", context={...})`,
  - automatyczny journal `source_type="challenge_completion"`, `source_id=challenge.id`.

### 6.3. Achievements

Rekomendowane funkcje:

```py
def unlock_achievement(
    *,
    achievement: Achievement,
    source_type: str = "",
    source_id: int | None = None,
    note: str = "",
) -> AchievementUnlock:
    ...

def evaluate_achievements(
    *,
    event_type: str,
    context: dict[str, Any],
) -> list[AchievementUnlock]:
    ...

def build_achievement_rows(limit: int = 6) -> list[dict[str, Any]]:
    ...
```

Reguly:

- `unlock_achievement(...)` jest idempotentne po `achievement`.
- `unlock_achievement(...)` nie tworzy XP.
- `unlock_achievement(...)` tworzy automatyczny wpis journala:
  - `entry_type="achievement"`,
  - `source_type="achievement_unlock"`,
  - `source_id=unlock.id`.
- `evaluate_achievements(...)` nie moze przerwac glownej akcji domenowej. Wywolanie powinno byc best-effort, analogicznie do aktualnych `_try_create_..._journal(...)`.
- `skill_level` nie powinien byc realizowany przez import `rpg` w `skills.models`, zeby uniknac zaleznosci cyklicznej. MVP: wywolywac ewaluacje skill level w serwisach, ktore tworza XP:
  - `activities.services.create_activity_entry(...)`,
  - `rpg.services.complete_quest(...)`,
  - `rpg.services.unlock_due_habit_milestones(...)`,
  - `rpg.services.complete_challenge(...)`.

## 7. Integracja z JournalEntry

### 7.1. Typy wpisow

Obecne `JournalEntryType` zawiera `challenge` i `achievement`.

Dla Goals rekomendacja:

- dodac `JournalEntryType.GOAL = "goal", "Goal"`.

Jesli zespol chce uniknac migracji alter field dla choices, mozna tymczasowo uzyc `entry_type="system"` dla goal completion, ale docelowo lepszy jest osobny typ `goal`.

### 7.2. Automatyczne wpisy

Nowe automatyczne wpisy:

| Zdarzenie | entry_type | source_type | source_id | Kiedy |
| --- | --- | --- | --- | --- |
| Goal completed | `goal` | `goal_completion` | `Goal.id` | Po pierwszym complete goal |
| Challenge completed | `challenge` | `challenge_completion` | `Challenge.id` | Po pierwszym complete challenge |
| Achievement unlocked | `achievement` | `achievement_unlock` | `AchievementUnlock.id` | Po pierwszym unlock |

Wpisy musza byc tworzone przez obecny helper `create_system_journal_entry(...)` albo jego rozszerzenie.

Idempotencja:

- unique constraint `JournalEntry(source_type, source_id)` zostaje zrodlem prawdy.
- Re-run serwisu nie tworzy drugiego wpisu.
- Manualne wpisy bez source pozostaja wielokrotne.

### 7.3. Journal stats

`build_journal_stats()` powinno zostac rozszerzone:

- `achievements_unlocked` = liczba `AchievementUnlock`.
- `completed_goals` moze zostac dodane pozniej, jezeli frontend dostanie nowe pole.
- `xp_logged` dalej liczy `XpEvent`, nie achievementy.

Minimalny kontrakt dla obecnego frontendu:

```json
{
  "stats": {
    "achievements_unlocked": 3
  }
}
```

### 7.4. Activity timeline

`build_journal_activity_timeline(day)` powinno dodac eventy:

- `goal_completed`,
- `challenge_completed`,
- `achievement_unlock`.

Eventy powinny miec:

- stabilne `id`, np. `goal-<id>`, `challenge-<id>`, `achievement-<unlock_id>`,
- `occurred_at`,
- `time_label`,
- `title`,
- `description`,
- `source_type`,
- `xp`.

XP dla achievementu zawsze `0`.

### 7.5. Journal nie rollbackuje domeny

Zasada:

- jezeli complete challenge zapisalo XP poprawnie, ale journal nie dal sie utworzyc, complete nadal ma sie udac;
- blad journala mozna logowac w przyszlosci, ale nie blokuje MVP.

Aktualny kod juz stosuje ten wzorzec przy quest completion i habit milestone przez `_try_create_quest_completion_journal(...)` oraz `_try_create_habit_milestone_journal(...)`.

## 8. Integracja z dashboard API

### 8.1. active_challenge

`GET /api/dashboard/` ma zwracac realny `active_challenge` albo `null`.

Finalny backend DTO:

```json
{
  "active_challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "active",
    "current_value": 14,
    "target_value": 30,
    "target_unit": "days",
    "progress_percent": 47,
    "reward_title": "Epic Willpower Badge",
    "reward_xp": 250
  }
}
```

Przejsciowe aliasy dla istniejacego Reacta sa dozwolone tylko podczas jednej migracji frontendu:

- `name`
- `day`
- `total`
- `progress`
- `reward`

Docelowo React powinien mapowac finalne pola `snake_case`.

### 8.2. achievements

`GET /api/dashboard/` ma zwracac ostatnio odblokowane achievementy z bazy.

Minimalny DTO:

```json
{
  "achievements": [
    {
      "id": 1,
      "title": "Iron Discipline",
      "description": "Maintained a 7 day habit streak.",
      "rarity": "rare",
      "icon": "shield",
      "unlocked_at": "2026-06-10T20:15:00+02:00",
      "unlocked_at_label": "Unlocked today"
    }
  ]
}
```

Zasady:

- Dashboard pokazuje unlocki, nie wszystkie definicje.
- Pelny widok sidebar `Achievements` moze pokazac definicje + stan unlocku.
- Brak unlockow zwraca `[]`.

### 8.3. goals

Dashboard glowny nie musi pokazywac pelnej listy goals w pierwszym kroku.

Minimalny endpoint dla osobnego widoku sidebar:

- `GET /api/goals/`
- `POST /api/goals/`
- `PATCH /api/goals/<id>/`
- `POST /api/goals/<id>/progress/`
- `POST /api/goals/<id>/complete/`

W dashboard API mozna pozniej dodac krotkie `goals_summary`, ale nie jest to wymagane do pierwszej akceptacji modulu.

## 9. Endpointy API

Standard: Django JSON views, bez DRF.

### 9.1. Goals

#### `GET /api/goals/`

Response:

```json
{
  "goals": [
    {
      "id": 1,
      "title": "Build Life RPG foundation",
      "description": "Create the core system for self-development.",
      "status": "active",
      "progress_value": 4,
      "target_value": 10,
      "target_unit": "milestones",
      "progress_percent": 40,
      "starts_on": "2026-06-10",
      "due_on": "2026-07-31",
      "skills": [
        {"id": 1, "name": "Programming"}
      ],
      "completed_at": null
    }
  ]
}
```

#### `POST /api/goals/`

Tworzy reczny goal. Minimalny request:

```json
{
  "title": "Improve health discipline",
  "description": "Build consistent training and recovery.",
  "target_value": 30,
  "target_unit": "days",
  "starts_on": "2026-06-10",
  "due_on": "2026-07-10",
  "skill_ids": [3]
}
```

#### `PATCH /api/goals/<id>/`

Aktualizuje pola opisowe i status, ale nie powinien recznie przyznawac XP.

#### `POST /api/goals/<id>/progress/`

Request:

```json
{
  "progress_value": 5,
  "note": "Milestone finished"
}
```

#### `POST /api/goals/<id>/complete/`

Request:

```json
{
  "note": "The goal was completed."
}
```

Response:

```json
{
  "goal": {
    "id": 1,
    "status": "completed",
    "progress_value": 10,
    "target_value": 10,
    "progress_percent": 100,
    "completed_at": "2026-06-10T20:15:00+02:00"
  },
  "unlocked_achievements": []
}
```

### 9.2. Challenges

#### `GET /api/challenges/`

Lista challenge dla osobnego widoku sidebar. Moze wspierac `?status=active`.

#### `POST /api/challenges/<id>/toggle/`

Tworzy albo usuwa dzienny `ChallengeCheckIn`. Nie daje XP.

Request:

```json
{
  "checked_on": "2026-06-14",
  "value": 1,
  "note": "Day 14 completed"
}
```

Response:

```json
{
  "challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "active",
    "current_value": 14,
    "target_value": 30,
    "progress_percent": 47
  },
  "check_in": {
    "id": 12,
    "checked_on": "2026-06-14",
    "value": 1,
    "successful": true
  },
  "checked": true,
  "completion_ready": false,
  "xp_events": [],
  "dashboard_refresh_required": true
}
```

#### `POST /api/challenges/<id>/complete/`

Daje XP tylko raz.

Response:

```json
{
  "challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "completed",
    "current_value": 30,
    "target_value": 30,
    "progress_percent": 100
  },
  "xp_events": [
    {
      "id": 1,
      "skill": {"id": 4, "name": "Fitness"},
      "amount": 250,
      "source_type": "challenge",
      "earned_at": "2026-06-10T20:15:00+02:00"
    }
  ],
  "unlocked_achievements": [
    {
      "id": 2,
      "title": "Unstoppable",
      "rarity": "epic"
    }
  ],
  "dashboard_refresh_required": true
}
```

#### `POST /api/challenges/<id>/fail/`

Zamyka challenge bez XP i tworzy journal `source_type="challenge_failure"`.

Response:

```json
{
  "challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "status": "failed",
    "current_value": 14,
    "target_value": 30,
    "progress_percent": 47,
    "failed_at": "2026-06-15T21:00:00+02:00"
  },
  "xp_events": [],
  "achievement_unlocks": [],
  "journal_entry": {
    "id": 2,
    "source_type": "challenge_failure",
    "source_id": 1
  },
  "dashboard_refresh_required": true
}
```

### 9.3. Achievements

#### `GET /api/achievements/`

Response:

```json
{
  "achievements": [
    {
      "id": 1,
      "title": "First Quest",
      "description": "Complete your first quest.",
      "rarity": "common",
      "trigger_type": "quest_count",
      "trigger_config": {"quest_count": 1, "period": "all_time"},
      "is_unlocked": true,
      "unlock": {
        "id": 10,
        "unlocked_at": "2026-06-10T20:15:00+02:00",
        "source_type": "quest_completion",
        "source_id": 42
      }
    }
  ]
}
```

#### `POST /api/achievements/<id>/unlock/`

Manual unlock. Dozwolone tylko dla `trigger_type="manual"` albo jako admin/debug MVP endpoint.

Request:

```json
{
  "note": "Unlocked manually during testing."
}
```

Response:

```json
{
  "unlock": {
    "id": 10,
    "achievement_id": 1,
    "unlocked_at": "2026-06-10T20:15:00+02:00"
  },
  "dashboard_refresh_required": true
}
```

## 10. Seed danych

Seed pozostaje w `activities/management/commands/seed_life_rpg.py`.

### 10.1. Zasady seeda

- Uzywac `update_or_create`.
- Seed ma byc idempotentny.
- Seed nie tworzy:
  - `QuestCompletion`,
  - `HabitCheckIn`,
  - `HabitMilestoneUnlock`,
  - `AchievementUnlock`,
  - XP z challenge,
  - automatycznych wpisow journala dla nowych unlockow.
- Seed moze tworzyc definicje i aktywne rekordy do UI.
- Seed moze tworzyc manualne/systemowe wpisy journala startowego, jak obecnie.

### 10.2. Goals seed

Rekomendowane rekordy:

1. `Build the Life RPG foundation`
   - status: `active`
   - target_unit: `milestones`
   - target_value: `10`
   - progress_value: `4`
   - skills: `Programming`, `Writing`, `Learning`

2. `Improve health discipline`
   - status: `active`
   - target_unit: `days`
   - target_value: `30`
   - progress_value: `14`
   - skills: `Fitness`

3. `Learn AI consistently`
   - status: `active`
   - target_unit: `sessions`
   - target_value: `20`
   - progress_value: `3`
   - skills: `Learning`, `Research`

4. `Strengthen financial awareness`
   - status: `draft`
   - target_unit: `reviews`
   - target_value: `8`
   - progress_value: `0`
   - skills: none until finance module exists, albo `Writing` jako tymczasowe planowanie

### 10.3. Challenge seed

Rekomendowany rekord:

- title: `30 Days No Sugar`
- goal: `Improve health discipline`
- status: `active`
- start_date: `today - 13 days`
- end_date: `start_date + 29 days`
- target_value: `30`
- target_unit: `days`
- current_value: `14`
- reward_title: `Epic Willpower Badge`
- created_by: `system`

Reward:

- skill: `Fitness`
- xp_amount: `250`

Uwaga:

- Nie uzywamy `Discipline` jako skilla seedowego, bo w obecnym kodzie Discipline jest atrybutem UI, nie seedowym skillem MVP.

### 10.4. Achievement seed

Seed ma tworzyc definicje achievementow, ale nie unlocki.

Rekomendowane 10 definicji:

| Title | Rarity | Trigger | Config |
| --- | --- | --- | --- |
| First Quest | common | quest_count | `{"quest_count": 1, "period": "all_time"}` |
| Quest Initiate | common | quest_count | `{"quest_count": 10, "period": "all_time"}` |
| Book Worm | rare | skill_level | `{"skill_id": <Reading.id>, "level": 5}` |
| Deep Learner | rare | skill_level | `{"skill_id": <Learning.id>, "level": 5}` |
| Code Artisan | rare | skill_level | `{"skill_id": <Programming.id>, "level": 5}` |
| Iron Discipline | epic | habit_streak | `{"streak_days": 7}` |
| Unstoppable | epic | habit_streak | `{"streak_days": 30}` |
| Willpower Oath | epic | challenge_completed | `{"challenge_id": <30 Days No Sugar.id>}` |
| Goal Crusher | rare | goal_completed | `{"goal_id": <Build the Life RPG foundation.id>}` |
| Legendary Foundation | legendary | quest_count | `{"quest_count": 100, "period": "all_time"}` |

Zasady:

- Seed resolve'uje `skill_id`, `challenge_id`, `goal_id` po utworzonych rekordach.
- Jezeli skill nie istnieje, achievement zalezy od seeda skilli i powinien zostac utworzony po `_seed_skills(...)`.
- `trigger_config` w DB uzywa `snake_case`.

## 11. Migracje

Rekomendowana kolejnosc migracji:

1. Dodac TextChoices w `rpg/choices.py`:
   - `GoalStatus`,
   - `ChallengeStatus`,
   - `AchievementRarity`,
   - `AchievementTriggerType`,
   - opcjonalnie `JournalEntryType.GOAL`.
2. Dodac modele w `rpg/models.py`:
   - `Goal`,
   - `GoalSkill`,
   - `Challenge`,
   - `ChallengeCheckIn`,
   - `ChallengeReward`,
   - `Achievement`,
   - `AchievementUnlock`.
3. Utworzyc migracje `rpg.0005_...`.
4. Nie modyfikowac historycznych migracji.
5. Sprawdzic:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py migrate
```

### Constrainty wymagane w migracji

Goal:

- title not empty.
- target_value > 0.
- progress_value >= 0.

GoalSkill:

- unique `(goal, skill)`.

Challenge:

- title not empty.
- target_value > 0.
- current_value >= 0.
- end_date >= start_date.

ChallengeCheckIn:

- unique `(challenge, checked_on)`.
- `checked_on` in challenge date range.
- `value >= 0`.

ChallengeReward:

- unique `(challenge, skill)`.
- xp_amount > 0.

Achievement:

- title not empty.
- sort_order >= 0.

AchievementUnlock:

- unique `(achievement)`.

## 12. Test matrix

### 12.1. Model tests

| Area | Test | Expected |
| --- | --- | --- |
| Goal | empty title | `ValidationError` |
| Goal | target_value <= 0 | `ValidationError` |
| Goal | progress_value < 0 | `ValidationError` |
| GoalSkill | duplicate skill per goal | `IntegrityError` |
| Challenge | empty title | `ValidationError` |
| Challenge | end_date before start_date | `ValidationError` |
| Challenge | current_value < 0 | `ValidationError` |
| ChallengeReward | duplicate skill per challenge | `IntegrityError` |
| ChallengeReward | xp_amount <= 0 | `ValidationError` |
| Achievement | empty title | `ValidationError` |
| Achievement | invalid trigger_config type | `ValidationError` albo service validation error |
| AchievementUnlock | duplicate achievement unlock | no duplicate, returns existing unlock |

### 12.2. Goal service tests

| Test | Expected |
| --- | --- |
| `update_goal_progress` stores absolute value | progress updated |
| progress above target is clamped | progress = target |
| progress below zero rejected | validation/domain error |
| `complete_goal` sets completed state | status completed, completed_at set |
| repeated `complete_goal` is idempotent | no duplicate journal, no duplicate unlock |
| goal completion creates journal | `JournalEntry(source_type="goal_completion")` |
| goal completion evaluates achievements | matching `goal_completed` achievement unlocked |

### 12.3. Challenge service tests

| Test | Expected |
| --- | --- |
| `get_active_challenge` returns nearest active | deterministic row |
| no active challenge | returns `None` |
| challenge toggle creates check-in | `ChallengeCheckIn` created, `current_value` recalculated |
| repeated challenge toggle removes check-in | no duplicate check-in, `current_value` recalculated |
| challenge toggle does not award XP | `XpEvent.count()` unchanged |
| toggle after completed challenge is rejected | 409 domain error |
| complete challenge with reward | one `XpEvent` per reward |
| complete challenge without reward | OK, empty xp_events |
| repeated complete | no duplicate `XpEvent` |
| complete challenge creates journal | `source_type="challenge_completion"` |
| complete challenge evaluates achievement | challenge achievement unlock created |
| failed/archived challenge cannot be completed by API | 409 domain error |

### 12.4. Achievement service tests

| Test | Expected |
| --- | --- |
| manual unlock creates unlock | one `AchievementUnlock` |
| repeated manual unlock | same unlock returned |
| unlock does not create XP | `XpEvent.count()` unchanged |
| unlock creates journal | `source_type="achievement_unlock"` |
| quest_count trigger | unlock after required completed quests |
| habit_streak trigger | unlock after required streak |
| skill_level trigger from activity XP | unlock after activity-created XP reaches level |
| skill_level trigger from challenge XP | unlock after challenge XP reaches level |
| challenge_completed trigger | unlock only for matching challenge config |
| goal_completed trigger | unlock only for matching goal config |
| inactive achievement | not unlocked automatically |

### 12.5. API tests

| Endpoint | Test | Expected |
| --- | --- | --- |
| `GET /api/goals/` | empty DB | `{"goals": []}` |
| `POST /api/goals/` | valid payload | 201 |
| `POST /api/goals/` | empty title | 400 |
| `PATCH /api/goals/<id>/` | update title | 200 |
| `POST /api/goals/<id>/progress/` | valid progress | 200 snake_case |
| `POST /api/goals/<id>/complete/` | complete | 200 |
| `POST /api/goals/999/complete/` | missing | 404 |
| `GET /api/challenges/` | seeded challenge | returns list |
| `POST /api/challenges/<id>/toggle/` | valid check-in | 200 |
| `POST /api/challenges/<id>/complete/` | complete | 200, xp_events |
| repeated challenge complete | 200 or 409, but no duplicate XP |
| `GET /api/achievements/` | definitions and unlock state | 200 |
| `POST /api/achievements/<id>/unlock/` | manual unlock | 200 |
| `POST /api/achievements/999/unlock/` | missing | 404 |

### 12.6. Dashboard tests

| Test | Expected |
| --- | --- |
| dashboard empty DB | `active_challenge is None`, `achievements == []` |
| dashboard with active challenge | serialized challenge from DB |
| dashboard with multiple active challenges | nearest end_date chosen |
| dashboard with completed challenge only | `active_challenge is None` |
| dashboard after achievement unlock | `achievements` includes unlocked badge |
| dashboard does not generate fake achievements | list based on DB only |
| dashboard journal entries still filter by range | existing behavior preserved |

### 12.7. Journal tests

| Test | Expected |
| --- | --- |
| goal complete creates journal entry | one entry |
| challenge complete creates journal entry | one entry |
| achievement unlock creates journal entry | one entry |
| repeated source event | no duplicate entry |
| journal stats count achievements | `achievements_unlocked` equals unlock count |
| journal timeline includes challenge complete | event visible for selected day |
| journal timeline includes achievement unlock | event visible for selected day |
| journal failure best-effort | core action still saved |

### 12.8. Seed tests

| Test | Expected |
| --- | --- |
| seed creates goals idempotently | same counts after second run |
| seed creates challenge idempotently | one `30 Days No Sugar` |
| seed creates challenge reward idempotently | no duplicate rewards |
| seed creates achievements idempotently | same definitions count |
| seed does not create unlocks | `AchievementUnlock.count() == 0` |
| seed does not create challenge XP | no `XpEvent(source_type="challenge")` |
| seed does not create goal completion journal | no automatic goal completion entry |
| seed preserves existing journal seed behavior | existing 2 seed entries remain idempotent |

### 12.9. Frontend tests / checks

Minimum after frontend integration:

```bash
cd frontend
npm run typecheck
npm run build
```

Manual UI checks:

- `#goals` loads real goals from API.
- `#achievements` loads definitions and unlock state.
- Dashboard challenge panel handles `activeChallenge === null`.
- Challenge complete refreshes dashboard.
- Achievement unlock appears in dashboard and journal.
- No domain state is stored in `localStorage`.

## 13. Smoke testy po wdrozeniu

### 13.1. Backend smoke

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py test rpg dashboard activities planner
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_life_rpg
.venv/bin/python manage.py seed_life_rpg
```

Oczekiwane:

- brak nowych migracji po wygenerowanej migracji,
- system check OK,
- testy OK,
- seed drugi raz bez duplikatow.

### 13.2. API smoke

Po migracji i seedzie:

```bash
curl http://127.0.0.1:8000/api/dashboard/
curl http://127.0.0.1:8000/api/journal/
curl http://127.0.0.1:8000/api/goals/
curl http://127.0.0.1:8000/api/challenges/
curl http://127.0.0.1:8000/api/achievements/
```

Oczekiwane:

- dashboard ma `active_challenge` z `30 Days No Sugar`,
- journal zwraca overview,
- goals zwraca seedowane goals,
- challenges zwraca seedowany challenge,
- achievements zwraca definicje bez unlockow.

### 13.3. Mutacyjny smoke w dev DB

Tylko na lokalnej/dev bazie.

1. Pobierz ID challenge `30 Days No Sugar`.
2. Wywolaj toggle check-inu.
3. Sprawdz, ze XP sie nie zmienilo.
4. Wywolaj complete.
5. Sprawdz, ze:
   - powstaly `XpEvent(source_type="challenge")`,
   - powstal `JournalEntry(source_type="challenge_completion")`,
   - odblokowal sie pasujacy achievement,
   - powstal `JournalEntry(source_type="achievement_unlock")`.
6. Wywolaj complete drugi raz.
7. Sprawdz brak dodatkowego XP i brak dodatkowych wpisow journala.

## 14. Edge cases

### 14.1. Brak aktywnego challenge

Backend:

- `active_challenge: null`.

Frontend:

- pokazuje empty state albo ukrywa panel.
- nie rzuca bledu.

### 14.2. Wiele aktywnych challenge

Backend:

- wybiera deterministycznie jeden challenge.
- pelna lista pozostaje w `/api/challenges/`.

### 14.3. Complete challenge bez rewardow

Backend:

- complete OK.
- `xp_events: []`.
- journal i achievementy nadal moga powstac.

### 14.4. Podwojne klikniecie complete

Backend:

- nie duplikuje XP.
- nie duplikuje achievement unlock.
- nie duplikuje journal entry.

### 14.5. Reward zmieniony po ukonczeniu challenge

MVP:

- nie przeliczamy historycznego XP.
- `xp_awarded_at` oznacza, ze nagroda zostala juz rozliczona.
- korekta wymaga recznej decyzji admina.

### 14.6. Usuniecie zrodla journal entry

MVP:

- `JournalEntry` zostaje jako audit/chronicle.
- Brak `GenericForeignKey` jest swiadoma decyzja.
- UI nie powinien zakladac, ze zrodlo nadal istnieje.

### 14.7. Achievement z configiem wskazujacym nieistniejacy rekord

Backend:

- trigger ignoruje achievement i nie unlockuje go.
- test powinien potwierdzic brak bledu globalnego.

### 14.8. Skill level achievement po XP z aktywnosci

Ryzyko:

- XP z aktywnosci powstaje w `activities.services`.

Decyzja:

- dodac wywolanie ewaluacji achievementow po utworzeniu XP w `create_activity_entry(...)`.
- nie importowac `rpg` w `skills.models`.

### 14.9. Timezone

Zasady:

- daty dzienne: `timezone.localdate()`.
- timestampy: `timezone.now()`.
- journal `entry_date` dla eventu bierze lokalna date timestampu.

### 14.10. Cofanie progressu po complete

MVP:

- endpoint Reacta nie pozwala cofnac completed goal/challenge do active.
- admin moze edytowac, ale jest to operacja reczna bez automatycznego cofania XP.

## 15. Rollback

### 15.1. Przed migracja

Jesli kod nie zostal zmigrowany:

- cofnac zmiany w kodzie modulu,
- nie trzeba czyscic bazy.

### 15.2. Po migracji na lokalnej bazie

Przed rollbackiem zrobic backup dev DB, jezeli dane sa istotne.

Docelowy rollback migracji:

```bash
.venv/bin/python manage.py migrate rpg 0004_journalentry_reflection_challenge_and_more
```

Uwaga:

- rollback usunie tabele Goals/Challenges/Achievements, jezeli powstaly w migracji `0005`.
- dane w tych tabelach zostana utracone.

### 15.3. Po przyznaniu XP z challenge

MVP nie ma automatycznego cofania XP.

Opcje:

- przywrocic backup bazy,
- recznie usunac testowe `XpEvent(source_type="challenge")` w dev DB,
- w przyszlosci dodac model korekt XP zamiast usuwania ledger entries.

### 15.4. Po unlocku achievementow

W dev DB:

- mozna usunac `AchievementUnlock`,
- journal entry z `source_type="achievement_unlock"` mozna usunac tylko jezeli to byl test smoke.

W danych realnych:

- preferowac korekte/status zamiast kasowania historii.

## 16. Kolejnosc wdrozenia

### Krok 1 - modele i migracje

- Dodac TextChoices.
- Dodac modele.
- Dodac constraints.
- Wygenerowac migracje.
- Uruchomic `makemigrations --check --dry-run` po migracji.

### Krok 2 - admin

- Zarejestrowac:
  - `Goal`,
  - `GoalSkill`,
  - `Challenge`,
  - `ChallengeCheckIn`,
  - `ChallengeReward`,
  - `Achievement`,
  - `AchievementUnlock`.
- Dodac inline:
  - `GoalSkillInline`,
  - `ChallengeCheckInInline`,
  - `ChallengeRewardInline`.
- Ustawic `readonly_fields` dla timestampow, `completed_at`, `xp_awarded_at`, `unlocked_at`.

### Krok 3 - serwisy domain-first

- Dodac serwisy goals.
- Dodac serwisy challenges.
- Dodac serwisy achievements.
- Dodac serializery pomocnicze w `rpg/services.py`.
- Nie pisac logiki XP w views.

### Krok 4 - integracja JournalEntry

- Dodac helpery:
  - `_try_create_goal_completion_journal(...)`,
  - `_try_create_challenge_completion_journal(...)`,
  - `_try_create_achievement_unlock_journal(...)`.
- Rozszerzyc `build_journal_stats`.
- Rozszerzyc `build_journal_activity_timeline`.

### Krok 5 - endpointy JSON

- Dodac URLs:
  - goals,
  - challenges,
  - achievements.
- Request validation zgodna z obecnym stylem `rpg/views.py`.
- Response w `snake_case`.
- Domain errors przez obecny format:

```json
{
  "error": {
    "code": "validation_error",
    "message": "..."
  }
}
```

### Krok 6 - dashboard

- Dodac `get_active_challenge()` do `dashboard/services.py`.
- Zamienic `active_challenge: None` na realny serializer.
- Zamienic `achievements: []` na realne ostatnie unlocki.
- Zachowac empty states.

### Krok 7 - seed

- Dodac `_seed_goals(...)`.
- Dodac `_seed_challenges(...)`.
- Dodac `_seed_achievements(...)`.
- Uruchomic seed dwa razy.
- Dopisac test idempotencji.

### Krok 8 - testy backend

- Modele.
- Serwisy.
- API.
- Dashboard.
- Journal.
- Seed.

### Krok 9 - frontend

- Podpiac `Goals` widok do `/api/goals/`.
- Podpiac `Achievements` widok do `/api/achievements/`.
- Rozszerzyc challenge panel o progress/complete.
- Odpalic `npm run typecheck` i `npm run build`.

### Krok 10 - final smoke

- Backend commands.
- API smoke.
- UI smoke.
- Brak duplikatow po podwojnym complete/unlock.

## 17. Acceptance criteria

Modul jest gotowy, gdy:

1. Migracje przechodza na PostgreSQL.
2. Admin pozwala zarzadzac goals, challenges i achievements.
3. Seed tworzy:
   - goals,
   - `30 Days No Sugar`,
   - 10 achievement definitions.
4. Seed jest idempotentny.
5. Seed nie tworzy unlockow, completion history ani XP challenge.
6. `GET /api/dashboard/` zwraca realny `active_challenge`.
7. `GET /api/dashboard/` zwraca realne odblokowane achievementy albo `[]`.
8. `GET /api/journal/` liczy `achievements_unlocked` z bazy.
9. Complete challenge tworzy XP tylko przez `skills.XpEvent`.
10. Complete challenge drugi raz nie duplikuje XP.
11. Achievement unlock nie tworzy XP.
12. Achievement unlock tworzy automatyczny journal.
13. Goal complete tworzy automatyczny journal.
14. Challenge complete tworzy automatyczny journal.
15. Journal auto entries sa idempotentne.
16. Blad journala nie rollbackuje glownej akcji domenowej.
17. React nie uzywa `localStorage` jako zrodla prawdy dla goals/challenges/achievements.
18. AI quest generation nie jest zaimplementowane w tym module.
19. Przechodza:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py test
cd frontend
npm run typecheck
npm run build
```

## 18. Najwazniejsze decyzje do przekazania agentom implementacyjnym

- Implementowac w `rpg`, nie tworzyc osobnych aplikacji `goals` ani `achievements`.
- Backend `snake_case`, React `camelCase`.
- Goal nie daje XP.
- Achievement nie daje XP.
- Challenge daje XP tylko przy complete.
- Toggle/check-in challenge nie konczy automatycznie challenge.
- Achievement trigger config zapisujemy w `snake_case` i na ID rekordow.
- Seed tworzy definicje, nie historie.
- Journal auto entries przez `source_type/source_id`.
- Journal jest best-effort.
- `active_challenge` nullable pozostaje wymaganym kontraktem.
- AI quest generation zostaje na pozniej.
