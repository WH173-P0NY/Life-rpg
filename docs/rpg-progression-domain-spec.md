# Life RPG - Progression Domain Spec

## Cel modulu

Modul `Goals, Challenges, Achievements` domyka podstawowa petle progresji RPG:

```txt
activity / quest / habit / manual progress
-> XP
-> goal progress / challenge check-in
-> achievement unlock
-> journal chronicle entry
```

Specyfikacja opisuje backend domeny dla aktualnego repo. Nie opiera sie na starym `docs/rpg-modules-implementation-index.md`.

## Aktualny stan repo

Sprawdzone elementy backendu:

- Django 6.0.6.
- PostgreSQL jako jedyna baza.
- Aktywne aplikacje: `skills`, `activities`, `statuses`, `dashboard`, `rpg`, `planner`.
- Istniejaca aplikacja `rpg` zawiera questy, habity, habit milestones, journal i character identity.
- `skills.XpEvent` jest jedynym audytem XP.
- Questy przyznaja XP przez `QuestReward` i `Skill.add_xp(...)`.
- Habit streaki same nie daja XP, ale `HabitMilestoneUnlock` moze przyznac XP.
- `JournalEntry` wspiera wpisy systemowe przez `entry_type`, `source_type`, `source_id`.
- API jest zwyklym Django JSON, bez DRF.
- JSON zwracany przez backend ma pozostac w `snake_case`.

## Decyzje architektoniczne

### Aplikacja Django

Nie tworzymy nowej aplikacji Django.

Nowe modele nalezy dodac do istniejacej aplikacji `rpg`, poniewaz:

- progresja jest bezposrednio powiazana z questami, habitami i journalem,
- `rpg.choices`, `rpg.services`, `rpg.views` maja juz wzorce domenowe,
- unikamy sztucznego podzialu na kilka mini-aplikacji,
- latwiej utrzymac jedna transakcje dla XP, unlockow i journala.

### XP

XP musi byc przyznawane tylko przez `skills.XpEvent`.

Nie przechowujemy alternatywnego licznika XP w `Goal`, `Challenge` ani `Achievement`.

W tym module:

- `Goal` nie daje XP,
- `Achievement` nie daje XP,
- XP moze dac tylko `Challenge` przy ukonczeniu.

Modele domenowe przechowuja tylko:

- definicje nagrod,
- stan progresu,
- znacznik `xp_awarded_at` tam, gdzie XP faktycznie moze zostac przyznane,
- audyt unlock/completion.

`XpEvent` pozostaje append-only. Nie usuwamy i nie cofamy XP automatycznie.

### Brak automatycznego odejmowania XP

Dla MVP nie implementujemy usuwania XP po cofnieciu postepu.

Zasada:

- przed finalnym ukończeniem goal/challenge mozna zmieniac progress,
- po przyznaniu XP `xp_awarded_at` blokuje ponowne naliczenie,
- cofanie przyznanego XP moze byc osobnym przyszlym mechanizmem korekty, np. `XpAdjustment`, ale nie w tym module.

### JSON API

Backend API:

- bez DRF,
- widoki funkcyjne Django,
- `JsonResponse`,
- request/response w `snake_case`,
- walidacja payloadu w stylu istniejacego `rpg.views`,
- bledy domenowe przez `RpgDomainError` / `RpgValidationError`.

## TextChoices

Nowe choices powinny trafic do `rpg/choices.py`.

### GoalStatus

```python
class GoalStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"
```

Zasady:

- `draft` - cel zapisany, ale nieaktywny,
- `active` - cel widoczny w systemie progresji,
- `paused` - cel tymczasowo wstrzymany,
- `completed` - cel zakonczony i zablokowany przed zwykla edycja progresu,
- `archived` - cel ukryty z aktywnych widokow.

### GoalPriority

```python
class GoalPriority(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"
    LEGENDARY = "legendary", "Legendary"
```

`legendary` oznacza dlugoterminowy cel o duzej wadze narracyjnej.

### ChallengeStatus

```python
class ChallengeStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    ARCHIVED = "archived", "Archived"
```

Zasady:

- `active` challenge przyjmuje check-iny,
- `completed` challenge ma przyznane nagrody albo jest gotowy do nagrod,
- `failed` zachowuje historie, ale nie przyznaje nagrod completion,
- `archived` ukrywa challenge z aktywnych widokow.

### ChallengeCadence

```python
class ChallengeCadence(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
```

MVP implementuje realnie `daily`. `weekly` zostaje jako bezpieczne rozszerzenie.

### AchievementRarity

```python
class AchievementRarity(models.TextChoices):
    COMMON = "common", "Common"
    RARE = "rare", "Rare"
    EPIC = "epic", "Epic"
    LEGENDARY = "legendary", "Legendary"
```

### AchievementTrigger

```python
class AchievementTrigger(models.TextChoices):
    MANUAL = "manual", "Manual"
    TOTAL_XP = "total_xp", "Total XP"
    SKILL_LEVEL = "skill_level", "Skill level"
    QUEST_COUNT = "quest_count", "Quest count"
    HABIT_STREAK = "habit_streak", "Habit streak"
    CHALLENGE_COMPLETED = "challenge_completed", "Challenge completed"
    GOAL_COMPLETED = "goal_completed", "Goal completed"
    JOURNAL_STREAK = "journal_streak", "Journal streak"
```

`manual` sluzy do recznego unlocku z admina lub serwisu.

### ProgressSource

Opcjonalne choice dla czytelnego `source_type` w progresie:

```python
class ProgressSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    QUEST_COMPLETION = "quest_completion", "Quest completion"
    CHALLENGE_COMPLETION = "challenge_completion", "Challenge completion"
    ACTIVITY_ENTRY = "activity_entry", "Activity entry"
    SYSTEM = "system", "System"
    AI = "ai", "AI"
```

Mozna tez uzyc zwyklego `CharField` bez choices, jezeli chcemy zachowac pelna elastycznosc.

## Modele

### Goal

Reprezentuje dlugoterminowy cel uzytkownika.

Przyklady:

- Build Life RPG MVP
- Read 12 books
- Lose 8 kg
- Save emergency fund
- Learn AI engineering

Pola:

```python
class Goal(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=GoalStatus.choices, default=GoalStatus.DRAFT)
    priority = models.CharField(max_length=20, choices=GoalPriority.choices, default=GoalPriority.NORMAL)
    life_area = models.ForeignKey("skills.LifeArea", on_delete=models.SET_NULL, null=True, blank=True, related_name="goals")
    target_value = models.PositiveIntegerField(default=1)
    progress_value = models.PositiveIntegerField(default=0)
    target_unit = models.CharField(max_length=20, choices=TargetUnit.choices, default=TargetUnit.COUNT)
    starts_on = models.DateField(null=True, blank=True)
    due_on = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=20, choices=CreationSource.choices, default=CreationSource.MANUAL)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Relacje:

- `GoalSkill` wskazuje skille, ktore cel wspiera kontekstowo.
- `Challenge.goal` moze wskazywac cel, ktory challenge wspiera.
- `GoalProgressEntry` jest historia zmian postepu.
- Journal wpis systemowy powstaje po ukonczeniu celu.

Walidacje:

- `title` po `strip()` nie moze byc pusty.
- `target_value > 0`.
- `progress_value >= 0`.
- `progress_value <= target_value`, chyba ze cel ma dopuszczac overcompletion; dla MVP nie dopuszczamy.
- `due_on >= starts_on`, jezeli oba pola istnieja.
- `completed_at` moze byc ustawione tylko gdy `status == completed`.
- `created_by == ai` musi zaczynac jako `draft`, tak jak questy AI.

Constrainty:

- check `title != ""`,
- check `target_value > 0`,
- check `progress_value >= 0`,
- check `progress_value <= target_value`,
- check `due_on IS NULL OR starts_on IS NULL OR due_on >= starts_on`.

Metody:

```python
def progress_percent(self) -> int
def is_complete(self) -> bool
```

### GoalSkill

Definiuje, ktore skille sa zwiazane z celem. Nie przyznaje XP.

```python
class GoalSkill(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="goal_skills")
    skill = models.ForeignKey("skills.Skill", on_delete=models.CASCADE, related_name="goals")
    weight = models.PositiveIntegerField(default=1)
```

Walidacje i constrainty:

- `weight > 0`,
- unique `(goal, skill)`.

### GoalProgressEntry

Historia zmian postepu celu.

Nie przyznaje XP. Uzywamy jej do audytu, UI, przyszlych questow AI i journala.

```python
class GoalProgressEntry(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="progress_entries")
    previous_value = models.PositiveIntegerField()
    new_value = models.PositiveIntegerField()
    delta = models.IntegerField()
    note = models.TextField(blank=True)
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
```

Walidacje:

- `previous_value >= 0`,
- `new_value >= 0`,
- `new_value <= goal.target_value`,
- `delta == new_value - previous_value`,
- jezeli `source_type` jest puste, `source_id` musi byc `None`,
- jezeli `source_id` istnieje, `source_type` nie moze byc puste.

Constrainty:

- unique `(goal, source_type, source_id)` dla niepustego `source_type` i niepustego `source_id`.

Idempotencja:

- jezeli ta sama integracja/system sprobuje ponownie zapisac ten sam progress event, serwis zwraca istniejacy `GoalProgressEntry` i nie zmienia progresu drugi raz.

### Challenge

Reprezentuje ograniczony w czasie challenge, np. `30 Days No Sugar`.

```python
class Challenge(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ChallengeStatus.choices, default=ChallengeStatus.DRAFT)
    cadence = models.CharField(max_length=20, choices=ChallengeCadence.choices, default=ChallengeCadence.DAILY)
    goal = models.ForeignKey(Goal, on_delete=models.SET_NULL, null=True, blank=True, related_name="challenges")
    target_value = models.PositiveIntegerField(default=30)
    target_unit = models.CharField(max_length=20, choices=TargetUnit.choices, default=TargetUnit.CHECK)
    current_value = models.PositiveIntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    xp_awarded_at = models.DateTimeField(null=True, blank=True)
    reward_title = models.CharField(max_length=180, blank=True)
    created_by = models.CharField(max_length=20, choices=CreationSource.choices, default=CreationSource.MANUAL)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Zasady:

- `target_value` oznacza liczbe wymaganych successful check-inow.
- Dla `daily` typowy `target_value` to liczba dni.
- `current_value` jest cachem liczby udanych check-inow.
- Zrodlem prawdy dla progresu jest `ChallengeCheckIn`; `current_value` sluzy do szybkiego dashboardu.
- Challenge moze wspierac `Goal` przez opcjonalne `goal`.

Walidacje:

- `title` po `strip()` nie moze byc pusty.
- `target_value > 0`.
- `current_value >= 0`.
- `current_value <= target_value`.
- `end_date >= start_date`.
- `completed_at` tylko dla `status == completed`.
- `failed_at` tylko dla `status == failed`.
- `completed_at` i `failed_at` nie moga byc ustawione jednoczesnie.
- `xp_awarded_at` tylko po `completed_at`.
- `created_by == ai` musi zaczynac jako `draft`.

Constrainty:

- check `title != ""`,
- check `target_value > 0`,
- check `current_value >= 0`,
- check `current_value <= target_value`,
- check `end_date >= start_date`,
- check nie pozwalajacy na jednoczesne `completed_at` i `failed_at`.

Metody:

```python
def progress_percent(self) -> int
def reward_xp_total(self) -> int
def current_day(self, day: date | None = None) -> int
```

### ChallengeReward

XP za ukonczenie challenge.

```python
class ChallengeReward(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="rewards")
    skill = models.ForeignKey("skills.Skill", on_delete=models.CASCADE, related_name="challenge_rewards")
    xp_amount = models.PositiveIntegerField()
```

Walidacje i constrainty:

- `xp_amount > 0`,
- unique `(challenge, skill)`.

### ChallengeCheckIn

Pojedynczy wpis progresu challenge.

```python
class ChallengeCheckIn(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="checkins")
    checked_on = models.DateField()
    value = models.PositiveIntegerField(default=1)
    successful = models.BooleanField(default=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Walidacje:

- `checked_on` musi byc w zakresie `start_date <= checked_on <= end_date`.
- `value >= 0`.
- dla `successful=True`, `value > 0`.
- nie mozna tworzyc/edytowac check-inow dla `completed`, `failed`, `archived` przez zwykly serwis.

Constrainty:

- unique `(challenge, checked_on)`,
- check `value >= 0`.

Zasady toggle:

- pierwsze klikniecie tworzy successful check-in,
- drugie klikniecie usuwa check-in tylko jezeli challenge nie jest zakonczony,
- po `completed_at` zwykly toggle nie usuwa check-inow, zeby nie wprowadzac ukrytego cofania XP.

### Achievement

Definicja odznaki.

```python
class Achievement(models.Model):
    code = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    rarity = models.CharField(max_length=20, choices=AchievementRarity.choices, default=AchievementRarity.COMMON)
    trigger_type = models.CharField(max_length=40, choices=AchievementTrigger.choices, default=AchievementTrigger.MANUAL)
    trigger_config = models.JSONField(default=dict, blank=True)
    icon = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Kanoniczna decyzja:

- Achievement uzywa `trigger_type + trigger_config`.
- Nie dodajemy jawnych pol/FK typu `skill`, `habit`, `goal`, `challenge` na modelu `Achievement`.
- `trigger_config` przechowuje `snake_case` i stabilne ID.
- Seed moze wyszukac rekord po nazwie, ale do bazy zapisuje ID.

Zasady `trigger_config`:

- `manual`: `{}`.
- `total_xp`: `{"xp": 1000}`.
- `skill_level`: `{"skill_id": 2, "level": 10}`.
- `quest_count`: `{"quest_count": 30, "period": "all_time"}`.
- `habit_streak`: `{"streak_days": 7}` albo `{"habit_id": 3, "streak_days": 7}`.
- `challenge_completed`: `{}` albo `{"challenge_id": 1}`.
- `goal_completed`: `{}` albo `{"goal_id": 1}`.
- `journal_streak`: `{"streak_days": 7}`.

Walidacje:

- `code` nie moze byc pusty.
- `title` nie moze byc pusty.
- `trigger_config` musi byc obiektem JSON.
- wymagane klucze zaleznie od `trigger_type` musza istniec i miec poprawne typy,
- pola ID musza wskazywac istniejace rekordy, jezeli zostaly podane,
- `trigger_type == manual` wymaga pustego configu albo ignoruje config,
- dla triggerow innych niz `manual` `is_active=True` oznacza, ze evaluator moze je automatycznie odblokowac.

### AchievementUnlock

Fakt odblokowania achievementu.

```python
class AchievementUnlock(models.Model):
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="unlocks")
    unlocked_at = models.DateTimeField(default=timezone.now)
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Constrainty:

- unique `(achievement)` dla obecnej jednoosobowej wersji aplikacji.

Walidacje:

- `source_id` wymaga niepustego `source_type`.
- `source_type` bez `source_id` jest dopuszczalny dla manual/admin.

Idempotencja:

- `unlock_achievement(...)` zawsze zwraca istniejacy unlock, jezeli achievement byl juz odblokowany.
- Powtorne wywolanie nie tworzy drugiego unlocka ani drugiego wpisu journala.

## Serwisy domenowe

Nowa logika mutujaca trafia do `rpg/services.py`.

Kazdy serwis:

- uzywa type hints,
- wykonuje mutacje w `transaction.atomic()`,
- blokuje rekordy przez `select_for_update()` tam, gdzie istnieje ryzyko podwojnego XP,
- wywoluje `full_clean()` przed `save()`,
- zwraca obiekty domenowe albo proste dict payloady zgodne ze stylem istniejacego `toggle_habit(...)`,
- nie importuje Reacta, formularzy ani logiki widoku.

### create_goal

```python
def create_goal(
    *,
    title: str,
    description: str = "",
    status: str = GoalStatus.DRAFT,
    priority: str = GoalPriority.NORMAL,
    life_area: LifeArea | None = None,
    target_value: int = 1,
    target_unit: str = TargetUnit.COUNT,
    starts_on: date | None = None,
    due_on: date | None = None,
    created_by: str = CreationSource.MANUAL,
) -> Goal
```

Zasady:

- tworzy cel bez XP,
- nie tworzy JournalEntry,
- AI-created goal musi zaczynac jako `draft`.

### update_goal_progress

```python
def update_goal_progress(
    *,
    goal: Goal,
    progress_value: int,
    note: str = "",
    source_type: str = ProgressSource.MANUAL,
    source_id: int | None = None,
    recorded_at: datetime | None = None,
) -> GoalProgressEntry
```

Zasady:

- ustawia absolutny `progress_value`, nie delta,
- jezeli `source_type/source_id` juz istnieje dla danego celu, zwraca istniejacy wpis i nie zmienia ponownie celu,
- jezeli progress osiaga `target_value`, wywoluje `complete_goal(...)`,
- nie przyznaje czastkowego XP.

### complete_goal

```python
def complete_goal(
    *,
    goal: Goal,
    completed_at: datetime | None = None,
    note: str = "",
) -> tuple[Goal, list[AchievementUnlock]]
```

Zasady:

- ustawia `progress_value = target_value`,
- ustawia `status = completed`,
- ustawia `completed_at`,
- nie tworzy `XpEvent`,
- tworzy idempotentny `JournalEntry`:
  - `entry_type=JournalEntryType.SYSTEM` albo nowy `JournalEntryType.GOAL`,
  - `source_type="goal_completion"`,
  - `source_id=goal.id`.
- po ukonczeniu odpala `evaluate_achievements(...)`.

Idempotencja:

- powtorne `complete_goal(...)` zwraca istniejacy stan completed,
- nie tworzy drugiego wpisu journala dla tego samego `source_type/source_id`,
- nie tworzy XP.

### create_challenge

```python
def create_challenge(
    *,
    title: str,
    description: str = "",
    target_value: int = 30,
    start_date: date,
    end_date: date,
    goal: Goal | None = None,
    reward_title: str = "",
    status: str = ChallengeStatus.DRAFT,
    created_by: str = CreationSource.MANUAL,
) -> Challenge
```

Zasady:

- tworzy challenge bez check-inow,
- nie przyznaje XP,
- aktywacja challenge moze byc osobnym `activate_challenge(...)` albo zwykla zmiana statusu przez serwis.

### toggle_challenge_check_in

```python
def toggle_challenge_check_in(
    *,
    challenge: Challenge,
    checked_on: date | None = None,
    value: int | None = None,
    note: str = "",
) -> dict[str, Any]
```

Zasady:

- dziala podobnie do `toggle_habit(...)`,
- tworzy albo usuwa check-in dla dnia,
- tylko `active` challenge przyjmuje zwykle check-iny,
- po kazdej zmianie przelicza `current_value`,
- jezeli `current_value >= target_value`, zwraca `completion_ready=True`,
- nie wywoluje `complete_challenge(...)` automatycznie,
- po `completed` nie usuwa check-inow zwyklym toggle.

Zwracany dict:

```python
{
    "challenge": challenge,
    "check_in": check_in | None,
    "checked": bool,
    "current_value": int,
    "completion_ready": bool,
    "xp_events": list[XpEvent],
    "achievement_unlocks": list[AchievementUnlock],
}
```

### complete_challenge

```python
def complete_challenge(
    *,
    challenge: Challenge,
    completed_at: datetime | None = None,
    note: str = "",
) -> tuple[Challenge, list[XpEvent]]
```

Zasady:

- ustawia `status=completed`,
- ustawia `completed_at`,
- jezeli `xp_awarded_at is None`, tworzy XP z `ChallengeReward`,
- ustawia `xp_awarded_at`,
- jezeli challenge ma `goal`, moze wywolac `update_goal_progress(...)` z `source_type="challenge_completion"` i `source_id=challenge.id`.
- tworzy idempotentny JournalEntry:
  - `entry_type=JournalEntryType.CHALLENGE`,
  - `source_type="challenge_completion"`,
  - `source_id=challenge.id`.
- odpala `evaluate_achievements(...)`.

### fail_challenge

```python
def fail_challenge(
    *,
    challenge: Challenge,
    failed_at: datetime | None = None,
    note: str = "",
) -> Challenge
```

Zasady:

- ustawia `status=failed`,
- ustawia `failed_at`,
- nie przyznaje XP,
- nie usuwa check-inow,
- moze utworzyc JournalEntry systemowy z porazka, ale bez achievement reward.

### unlock_achievement

```python
def unlock_achievement(
    *,
    achievement: Achievement,
    source_type: str = "",
    source_id: int | None = None,
    note: str = "",
    snapshot: dict[str, Any] | None = None,
) -> AchievementUnlock
```

Zasady:

- jezeli unlock istnieje, zwraca istniejacy unlock,
- jezeli unlock nie istnieje, tworzy `AchievementUnlock`,
- nie tworzy `XpEvent`,
- tworzy idempotentny JournalEntry:
  - `entry_type=JournalEntryType.ACHIEVEMENT`,
  - `source_type="achievement_unlock"`,
  - `source_id=unlock.id`.

### evaluate_achievements

```python
def evaluate_achievements(
    *,
    source_type: str = "",
    source_id: int | None = None,
) -> list[AchievementUnlock]
```

Zasady:

- sprawdza tylko `Achievement.objects.filter(is_active=True)`,
- pomija juz odblokowane achievementy,
- dla kazdego spelnionego warunku wywoluje `unlock_achievement(...)`,
- nie wykonuje kosztownych petli po wszystkich wpisach bez potrzeby,
- MVP moze byc wywolywane synchronicznie po:
  - `complete_quest(...)`,
  - `toggle_habit(...)` po milestone/unlock,
  - `complete_goal(...)`,
  - `complete_challenge(...)`,
  - `create_journal_entry(...)`.

Bez Celery:

- weekly/monthly background checks nie sa czescia MVP,
- jezeli trzeba odpalic pelna ewaluacje, mozna dodac management command `evaluate_rpg_achievements`.

## Idempotencja XP

Zasada centralna:

```txt
Challenge completion record -> xp_awarded_at -> XpEvent append-only rows
```

Nie uzywamy Reacta ani widoku jako zrodla prawdy XP.

### Goal XP

Goal nie tworzy XP w MVP. Completion celu jest zdarzeniem narracyjnym i moze odblokowac achievement, ale nie dopisuje `XpEvent`.

### Challenge XP

- gate: `Challenge.xp_awarded_at`,
- source_type w `XpEvent`: `"challenge"`,
- note: `"Challenge: <title>; challenge_id=<id>"`.

### Achievement XP

Achievement nie tworzy XP w MVP. Achievement jest odznaka za zdarzenie, a nie dodatkowym zrodlem punktow.

### Brak cofania XP

MVP nie usuwa `XpEvent`.

Jezeli uzytkownik cofnie progress przed `completed_at`, XP nie bylo jeszcze przyznane.

Jezeli rekord ma `xp_awarded_at`, zwykle akcje UI nie powinny pozwalac na cofniecie stanu. Admin moze poprawic dane recznie, ale to poza zwykla domena MVP.

## Journal integration

Nalezy rozszerzyc `JournalEntryType` o:

```python
class JournalEntryType(models.TextChoices):
    ...
    GOAL = "goal", "Goal"
```

Istniejace wartosci `CHALLENGE` i `ACHIEVEMENT` juz istnieja.

Wpisy systemowe:

- goal completion:
  - `entry_type="goal"`,
  - `source_type="goal_completion"`,
  - `source_id=goal.id`.
- challenge completion:
  - `entry_type="challenge"`,
  - `source_type="challenge_completion"`,
  - `source_id=challenge.id`.
- challenge failed:
  - `entry_type="challenge"`,
  - `source_type="challenge_failure"`,
  - `source_id=challenge.id`.
- achievement unlock:
  - `entry_type="achievement"`,
  - `source_type="achievement_unlock"`,
  - `source_id=achievement_unlock.id`.

Wpisy tworzymy przez istniejacy `create_system_journal_entry(...)`, zeby wykorzystac unikalnosc `source_type/source_id`.

## Dashboard selectors

Po dodaniu domeny `dashboard/services.py` powinien pobierac realne dane:

- `active_challenge` z `Challenge.objects.filter(status=active).order_by("sort_order", "end_date", "-created_at", "id").first()`,
- `achievements` z `AchievementUnlock.objects.select_related("achievement").order_by("-unlocked_at")[:N]`,
- `goals` dla widoku Goals z `Goal.objects.exclude(status=archived)`.

`build_journal_stats()` powinien zastapic placeholder:

```python
"achievements_unlocked": AchievementUnlock.objects.count()
```

## API endpoints

Endpoints powinny trafic do `rpg/urls.py`.

Minimalny zestaw:

```txt
GET    /api/goals/
POST   /api/goals/
PATCH  /api/goals/<id>/
POST   /api/goals/<id>/progress/
POST   /api/goals/<id>/complete/

GET    /api/challenges/
POST   /api/challenges/
PATCH  /api/challenges/<id>/
POST   /api/challenges/<id>/toggle/
POST   /api/challenges/<id>/complete/
POST   /api/challenges/<id>/fail/

GET    /api/achievements/
POST   /api/achievements/<id>/unlock/
POST   /api/achievements/evaluate/
```

Payloady i odpowiedzi:

- `snake_case`,
- ISO daty i datetimes,
- bledy:

```json
{
  "error": {
    "code": "validation_error",
    "message": "..."
  }
}
```

## Admin

Admin powinien obslugiwac:

- `Goal` z inline `GoalSkill` i `GoalProgressEntry` read-only,
- `Challenge` z inline `ChallengeReward` i `ChallengeCheckIn`,
- `Achievement`,
- `AchievementUnlock` read-only dla podstawowych pol audytu.

W adminie nie ukrywamy danych XP, ale nie implementujemy recznego cofania XP.

## Seed data

`seed_life_rpg` powinien byc idempotentny.

Proponowane dane startowe:

### Goals

- Build Life RPG MVP
  - target: 100 percent/count,
  - skills: Programming, Learning.
- Read 12 Books
  - target: 12 count,
  - skills: Reading, Learning.
- Build Training Consistency
  - target: 30 count,
  - skills: Fitness.
- Financial Foundation
  - target: 100 percent/count,
  - skills: Writing albo przyszly Wealth skill.

### Challenges

- 30 Days No Sugar
  - target: 30 daily check-ins,
  - reward_title: Epic Willpower Badge,
  - rewards: Fitness +150 XP, Discipline proxy przez Learning +50 XP do czasu dodania osobnego skilla.
- 14 Days Planning
  - target: 14 daily check-ins,
  - rewards: Writing +100 XP, Learning +50 XP.

### Achievements

- First Quest
  - trigger_type: quest_count,
  - trigger_config: `{"quest_count": 1, "period": "all_time"}`,
  - rarity: common.
- Seven Day Momentum
  - trigger_type: habit_streak,
  - trigger_config: `{"streak_days": 7}`,
  - rarity: rare.
- First Challenge Complete
  - trigger_type: challenge_completed,
  - trigger_config: `{}`,
  - rarity: rare.
- Goal Finisher
  - trigger_type: goal_completed,
  - trigger_config: `{}`,
  - rarity: epic.
- 1000 XP Earned
  - trigger_type: total_xp,
  - trigger_config: `{"xp": 1000}`,
  - rarity: rare.

## Testy akceptacyjne backendu

Minimalne testy:

### Modele

- pusty `Goal.title` odrzucany.
- `Goal.target_value <= 0` odrzucany.
- `Goal.progress_value > target_value` odrzucany.
- `Challenge.end_date < start_date` odrzucany.
- `ChallengeCheckIn` poza zakresem dat odrzucany.
- `Achievement.code` unikalny.
- `AchievementUnlock` unikalny per achievement.
- challenge rewardy unique per `(challenge, skill)`.
- goal skille unique per `(goal, skill)`.

### Serwisy

- `complete_goal(...)` nie tworzy XP.
- `complete_goal(...)` tworzy jeden JournalEntry.
- `update_goal_progress(...)` z tym samym `source_type/source_id` jest idempotentny.
- `toggle_challenge_check_in(...)` tworzy/usuwa check-in przed completion.
- `complete_challenge(...)` przyznaje XP tylko raz.
- po `completed` toggle challenge nie cofa XP.
- `unlock_achievement(...)` tworzy unlock tylko raz i nie tworzy XP.
- `evaluate_achievements(...)` odblokowuje achievementy dla quest_count, total_xp, goal_completed, challenge_completed.

### API

- endpointy zwracaja `snake_case`.
- invalid JSON daje `400 validation_error`.
- konflikt domenowy daje `409`.
- brak rekordu daje `404`.

## Kolejnosc implementacji

### Krok 1 - Choices i modele

- dodac choices do `rpg/choices.py`,
- dodac modele do `rpg/models.py`,
- przygotowac migracje,
- podpiac admin.

### Krok 2 - Serwisy Goals

- `create_goal`,
- `update_goal_progress`,
- `complete_goal`,
- powiazania przez `GoalSkill`,
- Journal wpis goal completion.

### Krok 3 - Serwisy Challenges

- `create_challenge`,
- `toggle_challenge_check_in`,
- `complete_challenge`,
- `fail_challenge`,
- XP przez `ChallengeReward`,
- Journal wpis challenge completion/failure.

### Krok 4 - Achievements

- `unlock_achievement`,
- `evaluate_achievements`,
- trigger rules,
- Journal wpis achievement unlock.

### Krok 5 - API

- dodac widoki JSON w `rpg/views.py`,
- dodac route'y w `rpg/urls.py`,
- utrzymac `snake_case`.

### Krok 6 - Dashboard i Journal selectors

- zastapic placeholder `active_challenge`,
- zastapic placeholder `achievements`,
- uzupelnic `build_journal_stats()`.

### Krok 7 - Seed i testy

- rozszerzyc `seed_life_rpg`,
- dopisac testy modeli, serwisow i API,
- uruchomic:

```txt
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test rpg
.venv/bin/python manage.py test
```

## Poza zakresem tego modulu

Nie implementujemy tutaj:

- DRF,
- Celery,
- multi-user ownership,
- AI-generated quests/goals,
- weekly/monthly AI chronicle,
- cofania XP,
- zaawansowanego rule engine dla achievementow,
- osobnej aplikacji `progression`.
