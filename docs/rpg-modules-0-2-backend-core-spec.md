# RPG Modules 0-2 - backend core implementation spec

## 1. Cel dokumentu

Ten dokument rozbija pierwsza implementacje backendowego core RPG na trzy moduly:

- Modul 0: fundament aplikacji Django `rpg`,
- Modul 1: questy i XP z questow,
- Modul 2: habity, streaki i milestone XP.

Dokument jest specyfikacja implementacyjna. Nie opisuje calego etapu RPG, tylko pierwszy backendowy zakres, ktory ma usunac mocki/localStorage z najwazniejszych interakcji dashboardu.

## 2. Decyzje projektowe

Obowiazujace decyzje:

- jedna aplikacja Django: `rpg`,
- Django 6.0.6,
- PostgreSQL jako baza lokalnego MVP,
- React + TypeScript + Vite jako frontend,
- endpointy JSON przez standardowe Django views,
- bez DRF,
- bez Celery,
- bez sygnalow do naliczania XP,
- frontend komunikuje sie przez `/api/*`,
- `skills.XpEvent` pozostaje jedynym zrodlem prawdy dla XP i levelowania,
- `activities` i `statuses` zostaja osobnymi aplikacjami,
- pojedynczy habit check-in nie daje XP,
- milestone streaka moze dawac XP,
- quest moze dawac XP do kilku skilli.

Decyzje doprecyzowane po analizie:

- backend JSON API dla nowych endpointow RPG przyjmuje i zwraca `snake_case`,
- React mapuje dane na `camelCase` dopiero w mapperze/typach frontendu,
- backendowe `target_unit` dla czasu uzywa `minutes`; `min` jest tylko skrotem displayowym po stronie Reacta,
- daily questy, check-iny i streaki uzywaja `timezone.localdate()` w lokalnej strefie aplikacji,
- dla lokalnego MVP rekomendowane ustawienie projektu to `TIME_ZONE = "Europe/Warsaw"`.

Praktyczna rekomendacja wdrozeniowa:

- moduly 0-2 mozna zaimplementowac jako jeden backendowy pakiet zmian, bo modele questow i habitow beda wspoldzielic choices, URL-e, serwisy i testy,
- dokument nadal rozdziela moduly, zeby jasno oddzielic odpowiedzialnosci: fundament app, questy, habity/streaki,
- jezeli wdrazamy je jednym PR-em/commitem, kryteria akceptacji trzeba sprawdzic osobno dla kazdego modulu.

## 3. Istniejaca architektura, ktora trzeba respektowac

### 3.1. XP

Aktualnie `skills.Skill` nie ma pola `xp`. XP jest liczone przez:

- `skills.XpEvent.amount`,
- `Skill.get_total_xp()`,
- `calculate_level(total_xp)`,
- `progress_for_xp(total_xp)`.

Nowe mechaniki musza tworzyc `XpEvent`, zamiast zapisywac XP na modelach `Skill`.

Dozwolone `source_type` po modulach 0-2:

- `activity` - juz istnieje,
- `quest` - XP z wykonania questa,
- `habit_milestone` - XP z odblokowania milestone streaka,
- `manual` - przyszla korekta reczna.

### 3.2. Activity i statusy

`activities.ActivityDefinition` juz obsluguje wzorzec "jedna definicja daje XP do wielu skilli" przez `ActivityReward`.

Questy i milestone powinny uzyc analogicznego wzorca:

- definicja zadania/milestone,
- wiele rekordow reward,
- przy wykonaniu jeden `XpEvent` per reward.

`statuses` pozostaje niezalezne od levelowania. Statusy nie przyznaja XP.

### 3.3. Dashboard API

Istniejacy endpoint:

- `GET /api/dashboard/`

zwraca dzisiaj m.in.:

- `daily_quests`,
- `habits`,
- `habits_summary`,
- `active_challenge`,
- `achievements`,
- `journal_entries`.

Moduly 0-2 przygotowuja realne dane dla:

- `daily_quests`,
- `habits`,
- `habits_summary`.

Challenge, achievementy i journal zostaja na pozniejsze moduly.

## 4. Modul 0 - fundament `rpg` app

### 4.1. Cel

Utworzyc aplikacje `rpg` i wspolne fundamenty dla mechanik RPG bez implementowania jeszcze pelnej logiki domenowej.

Efekt modulu:

- aplikacja `rpg` istnieje,
- jest dodana do Django,
- ma podstawowa strukture plikow,
- ma skeleton URL-i pod przyszle endpointy `/api/*`,
- ma TextChoices wspolne dla questow i habitow,
- ma admin/test skeleton,
- ma pusty katalog migracji.

### 4.2. Zakres

W zakresie:

- `python manage.py startapp rpg`,
- dodanie `"rpg"` do `INSTALLED_APPS`,
- utworzenie `rpg/urls.py`,
- podpiecie `rpg.urls` w `config/urls.py` albo `dashboard/urls.py`,
- przygotowanie `rpg/models.py`,
- przygotowanie `rpg/services.py`,
- przygotowanie `rpg/views.py`,
- przygotowanie `rpg/admin.py`,
- przygotowanie `rpg/tests.py` albo katalogu `rpg/tests/`,
- wspolne TextChoices,
- test smoke, ze URL-e i app config laduja sie poprawnie.

Poza zakresem:

- React UI,
- AI,
- ActivityWatch,
- challenge,
- achievementy,
- journal,
- cofanie XP po usunieciu completion/check-in.

### 4.3. Pliki do zmiany

Nowe pliki:

- `rpg/__init__.py`,
- `rpg/apps.py`,
- `rpg/models.py`,
- `rpg/services.py`,
- `rpg/views.py`,
- `rpg/urls.py`,
- `rpg/admin.py`,
- `rpg/tests.py` albo `rpg/tests/__init__.py`,
- `rpg/migrations/__init__.py`.

Istniejace pliki:

- `config/settings.py`,
- `config/urls.py` albo `dashboard/urls.py`,
- `activities/management/commands/seed_life_rpg.py`.

### 4.4. URL-e

Rekomendowany wariant:

```python
# config/urls.py
urlpatterns = [
    path("", include("dashboard.urls")),
    path("api/", include("rpg.urls")),
    path("admin/", admin.site.urls),
]
```

`rpg.urls` powinno zawierac tylko endpointy RPG:

```python
app_name = "rpg"

urlpatterns = []
```

Wazne:

- modul 0 podlacza tylko `rpg.urls` pod prefix `/api/`,
- modul 0 nie wymaga jeszcze dzialajacych endpointow questow ani habitow,
- endpointy questow zostana dodane w module 1,
- endpoint habitu zostanie dodany w module 2,
- nie przenosic istniejacego `/api/dashboard/` w module 0,
- nie zmieniac `/api/activities/manual/`,
- React ma dalej uzywac wzglednych sciezek `/api/...`.

### 4.5. TextChoices

TextChoices mozna trzymac w `rpg/models.py` na start. Jezeli plik urosnie, pozniej wydzielic do `rpg/choices.py`.

Minimalne choices:

```python
class QuestType(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    ONE_TIME = "one_time", "One time"
    AI_GENERATED = "ai_generated", "AI generated"


class QuestStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class QuestDifficulty(models.TextChoices):
    EASY = "easy", "Easy"
    NORMAL = "normal", "Normal"
    HARD = "hard", "Hard"
    EPIC = "epic", "Epic"


class CreationSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    SYSTEM = "system", "System"
    AI = "ai", "AI"


class TargetUnit(models.TextChoices):
    COUNT = "count", "Count"
    MINUTES = "minutes", "Minutes"
    STEPS = "steps", "Steps"
    PAGES = "pages", "Pages"
    CHECK = "check", "Check"


class HabitFrequency(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
```

Regula:

- choices maja ograniczac statusy techniczne,
- nazwy uzytkownika jak `Quest.title` i `Habit.name` nie powinny byc enumami.

### 4.6. Zasady architektoniczne dla modulow 1-2

- `rpg` nie moze naliczac XP przez sygnaly.
- Serwisy domenowe sa jedynym miejscem do tworzenia `XpEvent` z questow i milestone.
- Widoki API sa cienkie: parsuja JSON, wolaja serwis, zwracaja JSON.
- Modele musza miec `clean()` dla walidacji podstawowych danych.
- Operacje przyznawania XP musza dzialac w `transaction.atomic()`.
- Przyszle endpointy POST musza byc chronione CSRF tak jak obecne endpointy Django.

### 4.7. Kolejnosc implementacji

1. Utworzyc app `rpg`.
2. Dodac `"rpg"` do `INSTALLED_APPS`.
3. Dodac `rpg/urls.py` i podpiac przez `path("api/", include("rpg.urls"))`.
4. Dodac TextChoices.
5. Dodac puste serwisy i widoki dopiero z modulami 1-2.
6. Dodac admin/test skeleton.
7. Dodac test smoke dla app config i pustego `rpg.urls`.

### 4.8. Kryteria akceptacji

- `python manage.py check` przechodzi.
- `python manage.py makemigrations --check --dry-run` nie wykazuje brakujacych migracji po samym module 0.
- `python manage.py test rpg` przechodzi.
- `path("api/", include("rpg.urls"))` jest podpiete, ale `rpg.urls` moze byc jeszcze puste.
- Brak DRF w zaleznosciach i kodzie.

### 4.9. Testy

Minimalne testy:

- app `rpg` jest w `INSTALLED_APPS`,
- `rpg.urls` importuje sie bez bledu,
- `python manage.py check` nie zglasza problemow z konfiguracja.

## 5. Modul 1 - questy

### 5.1. Cel

Wprowadzic realne questy dzienne/jednorazowe, ich postep, kompletowanie oraz przyznawanie XP do jednego albo wielu skilli przez `skills.XpEvent`.

Efekt modulu:

- questy mozna tworzyc w adminie,
- quest moze miec kilka nagrod XP,
- quest mozna wykonac przez JSON API,
- XP jest przyznawane tylko raz dla danego wykonania,
- `GET /api/dashboard/` moze pozniej pobrac realne questy z bazy.

### 5.2. Zakres

W zakresie:

- model `Quest`,
- model `QuestReward`,
- model `QuestCompletion`,
- serwis `complete_quest`,
- serwis `update_quest_progress`,
- endpoint `POST /api/quests/<id>/complete/`,
- endpoint `POST /api/quests/<id>/progress/`,
- admin z inline rewards,
- seed 5 questow dziennych,
- testy modeli, serwisow i API.

Poza zakresem:

- AI generation,
- tygodniowe questy w UI,
- pelny ekran zarzadzania questami w React,
- cofanie XP po usunieciu wykonania,
- achievementy za questy.

### 5.3. Modele i pola

#### 5.3.1. `rpg.Quest`

Pola:

- `id`,
- `title` - `CharField(max_length=160)`,
- `description` - `TextField(blank=True)`,
- `quest_type` - `CharField(max_length=20, choices=QuestType.choices, default=QuestType.DAILY)`,
- `status` - `CharField(max_length=20, choices=QuestStatus.choices, default=QuestStatus.ACTIVE)`,
- `difficulty` - `CharField(max_length=20, choices=QuestDifficulty.choices, default=QuestDifficulty.NORMAL)`,
- `target_value` - `PositiveIntegerField(default=1)`,
- `target_unit` - `CharField(max_length=20, choices=TargetUnit.choices, default=TargetUnit.COUNT)`,
- `created_by` - `CharField(max_length=20, choices=CreationSource.choices, default=CreationSource.MANUAL)`,
- `available_from` - `DateField(null=True, blank=True)`,
- `available_until` - `DateField(null=True, blank=True)`,
- `sort_order` - `PositiveIntegerField(default=0)`,
- `created_at` - `DateTimeField(auto_now_add=True)`,
- `updated_at` - `DateTimeField(auto_now=True)`.

Meta:

- `ordering = ["sort_order", "title"]`.

Walidacja:

- `title.strip()` nie moze byc puste,
- `target_value > 0`,
- `available_until >= available_from`, jezeli oba sa ustawione,
- `created_by=ai` powinno wymuszac `status=draft` przy pierwszym zapisie albo w serwisie generowania AI w pozniejszym etapie.

Przydatne metody:

- `is_available_on(day: date) -> bool`,
- `is_repeatable_daily() -> bool`,
- `reward_xp_total() -> int`.

#### 5.3.2. `rpg.QuestReward`

Pola:

- `id`,
- `quest` - `ForeignKey("rpg.Quest", on_delete=models.CASCADE, related_name="rewards")`,
- `skill` - `ForeignKey("skills.Skill", on_delete=models.CASCADE, related_name="quest_rewards")`,
- `xp_amount` - `PositiveIntegerField()`.

Meta:

- `ordering = ["quest__title", "skill__name"]`,
- `UniqueConstraint(fields=["quest", "skill"], name="rpg_quest_reward_unique_quest_skill")`,
- `CheckConstraint(condition=Q(xp_amount__gt=0), name="rpg_quest_reward_xp_gt_0")`.

Walidacja:

- `xp_amount > 0`.

#### 5.3.3. `rpg.QuestCompletion`

Pola:

- `id`,
- `quest` - `ForeignKey("rpg.Quest", on_delete=models.CASCADE, related_name="completions")`,
- `completed_on` - `DateField()`,
- `progress_value` - `PositiveIntegerField(default=0)`,
- `completed_at` - `DateTimeField(null=True, blank=True)`,
- `xp_awarded_at` - `DateTimeField(null=True, blank=True)`,
- `note` - `TextField(blank=True)`,
- `created_at` - `DateTimeField(auto_now_add=True)`,
- `updated_at` - `DateTimeField(auto_now=True)`.

Meta:

- `ordering = ["-completed_on", "quest__sort_order", "quest__title"]`,
- `UniqueConstraint(fields=["quest", "completed_on"], name="rpg_quest_completion_unique_quest_day")`.

Regula dla `one_time`:

- w serwisie zabronic drugiego completion dla tego samego questa, niezaleznie od `completed_on`,
- mozna pozniej dodac osobny partial constraint, ale MVP moze trzymac to w serwisie.

Walidacja:

- `progress_value >= 0`,
- jezeli `completed_at` jest ustawione, `progress_value >= quest.target_value`.

### 5.4. Reguly domenowe

- Quest musi miec status `active`, zeby byl wykonywalny.
- Quest musi byc dostepny w danym dniu (`available_from`/`available_until`).
- Quest dzienny ma jeden `QuestCompletion` na dzien.
- Quest jednorazowy moze miec tylko jeden `QuestCompletion` lacznie.
- `update_quest_progress` aktualizuje `progress_value`.
- Jezeli `progress_value >= target_value`, serwis oznacza completion jako wykonane.
- `complete_quest` ustawia `progress_value = target_value` i `completed_at`, jezeli nie bylo wykonane.
- XP przyznajemy tylko, jezeli `xp_awarded_at is None`.
- Dla kazdego `QuestReward` tworzymy osobny `XpEvent`.
- `XpEvent.source_type = "quest"`.
- `XpEvent.note` powinien zawierac czytelny trop audytowy, np. `Quest: Read 20 minutes; completion_id=123`.
- Operacja musi byc w `transaction.atomic()`.
- Dla ochrony przed podwojnym kliknieciem serwis powinien blokowac completion przez `select_for_update()`.
- Usuniecie completion nie cofa XP w modulach 0-2. To osobna decyzja pozniejsza.

### 5.5. Serwisy

Plik: `rpg/services.py`.

#### 5.5.1. `complete_quest`

Sygnatura:

```python
def complete_quest(
    *,
    quest: Quest,
    completed_on: date | None = None,
    note: str = "",
) -> QuestCompletion:
    ...
```

Zachowanie:

1. Ustal `completed_on = timezone.localdate()`, jezeli brak.
2. Zweryfikuj status i dostepnosc questa.
3. Utworz albo pobierz `QuestCompletion`.
4. Zablokuj rekord completion w transakcji.
5. Ustaw `progress_value = quest.target_value`.
6. Ustaw `completed_at`, jezeli brak.
7. Jezeli `xp_awarded_at is None`, utworz `XpEvent` dla kazdego reward.
8. Ustaw `xp_awarded_at`.
9. Zapisz completion.
10. Zwroc completion z prefetchowanymi rewardami/eventami tam, gdzie potrzebne dla API.

Bledy domenowe:

- `QuestNotActiveError`,
- `QuestNotAvailableError`,
- `QuestAlreadyCompletedError` dla `one_time`, jezeli juz wykonany i XP przyznane.

Na start mozna uzyc `ValueError`, ale lepiej dodac male klasy wyjatkow w `rpg/services.py`.

#### 5.5.2. `update_quest_progress`

Sygnatura:

```python
def update_quest_progress(
    *,
    quest: Quest,
    progress_value: int,
    completed_on: date | None = None,
    note: str = "",
) -> QuestCompletion:
    ...
```

Zachowanie:

1. `progress_value` nie moze byc ujemne.
2. Ustal date.
3. Pobierz albo utworz completion.
4. Zapisz `progress_value`.
5. Jezeli progress przekracza target, traktuj jak wykonanie.
6. XP przyznaj tylko raz.
7. Jezeli progress spada ponizej target po wczesniejszym wykonaniu, nie cofaj XP w module 1; endpoint powinien raczej nie pozwalac obnizyc wykonanej wartosci bez osobnej funkcji korekty.

### 5.6. Endpointy JSON

#### 5.6.1. `POST /api/quests/<id>/complete/`

Request JSON:

```json
{
  "completed_on": "2026-06-10",
  "note": "Read before sleep"
}
```

Pola opcjonalne:

- `completed_on` - domyslnie dzisiaj lokalnie,
- `note`.

Response `200 OK`:

```json
{
  "quest": {
    "id": 1,
    "title": "Read 20 minutes",
    "completed": true,
    "progress_value": 20,
    "target_value": 20,
    "unit": "minutes",
    "reward_xp": 25
  },
  "completion": {
    "id": 10,
    "completed_on": "2026-06-10",
    "completed_at": "2026-06-10T20:30:00+00:00",
    "xp_awarded_at": "2026-06-10T20:30:00+00:00"
  },
  "xp_events": [
    {
      "id": 101,
      "skill": {"id": 2, "name": "Reading"},
      "amount": 20,
      "source_type": "quest"
    }
  ]
}
```

Statusy:

- `200 OK` przy sukcesie,
- `400 Bad Request` dla blednych danych,
- `404 Not Found` dla braku questa,
- `409 Conflict` dla konfliktu domenowego, np. one-time quest juz wykonany.

#### 5.6.2. `POST /api/quests/<id>/progress/`

Request JSON:

```json
{
  "progress_value": 12,
  "completed_on": "2026-06-10",
  "note": "12 minutes done"
}
```

Response:

- taki sam ksztalt jak `complete`, z aktualnym stanem completion.

Regula:

- frontend moze uzyc tego endpointu dla questow licznikowych,
- checkbox moze dalej wolac `complete`.

### 5.7. Admin

Plik: `rpg/admin.py`.

Admin:

- `QuestAdmin`,
- `QuestRewardInline`,
- `QuestCompletionAdmin`.

Wymagania:

- `QuestRewardInline` jako `TabularInline` pod `Quest`,
- `list_display`: `title`, `quest_type`, `status`, `difficulty`, `target_value`, `target_unit`, `sort_order`,
- `list_filter`: `quest_type`, `status`, `difficulty`, `created_by`,
- `search_fields`: `title`, `description`,
- `readonly_fields`: `created_at`, `updated_at`,
- `QuestCompletionAdmin.list_filter`: `completed_on`, `quest__quest_type`,
- `QuestCompletionAdmin.search_fields`: `quest__title`, `note`,
- `QuestCompletionAdmin.readonly_fields`: `created_at`, `updated_at`, `xp_awarded_at`.

### 5.8. Seed

Plik: `activities/management/commands/seed_life_rpg.py`.

Dopisac metode:

- `_seed_daily_quests(skills: dict[str, Skill]) -> dict[str, Quest]`.

Przykladowe questy:

- `Workout 30 minutes` -> `Fitness +25 XP`, `target_value=30`, `target_unit=minutes`,
- `Read 20 minutes` -> `Reading +20 XP`, `Learning +5 XP`,
- `Study AI` -> `Learning +25 XP`, `Research +15 XP`,
- `Write notes` -> `Writing +20 XP`,
- `Plan tomorrow` -> `Writing +10 XP`.

Seed musi byc idempotentny:

- `update_or_create` dla questow,
- `update_or_create` dla rewardow,
- nie tworzyc completion jako domyslnej historii, chyba ze testowo w fixture.

### 5.9. Integracja z dashboardem

W module 1 mozna jeszcze nie przepinac `GET /api/dashboard/`, ale trzeba przygotowac serializer/helper:

```python
def build_daily_quest_rows(day: date) -> list[dict[str, Any]]:
    ...
```

Docelowy ksztalt dla obecnego React transformera:

```json
{
  "title": "Read 20 minutes",
  "reward_xp": 25,
  "current": 0,
  "target": 20,
  "unit": "minutes",
  "progress": 0,
  "completed": false
}
```

Rozszerzenie zalecane dla przyszlego React live:

```json
{
  "id": 1,
  "completion_id": null,
  "title": "Read 20 minutes",
  "reward_xp": 25,
  "reward_skills": [{"id": 2, "name": "Reading", "xp": 20}],
  "current": 0,
  "target": 20,
  "unit": "minutes",
  "progress": 0,
  "completed": false
}
```

### 5.10. Kolejnosc implementacji

1. Dodac TextChoices z modulu 0.
2. Dodac `Quest`, `QuestReward`, `QuestCompletion`.
3. Dodac migracje.
4. Dodac admin z inline rewards.
5. Dodac serwis `complete_quest`.
6. Dodac serwis `update_quest_progress`.
7. Dodac widoki JSON.
8. Dodac URL-e.
9. Rozszerzyc seed.
10. Dodac testy modeli, serwisow i API.
11. Opcjonalnie dodac helper do dashboard rows.

### 5.11. Kryteria akceptacji

- Admin pozwala stworzyc questa i kilka rewardow XP.
- Quest z dwoma rewardami tworzy dwa `XpEvent`.
- Drugie klikniecie tego samego questa dzisiaj nie tworzy dodatkowego XP.
- One-time quest nie moze byc wykonany drugi raz.
- Nieaktywny albo niedostepny quest nie moze byc wykonany przez API.
- `POST /api/quests/<id>/complete/` zwraca JSON z completion i XP.
- `POST /api/quests/<id>/progress/` aktualizuje `progress_value`.
- `python manage.py test rpg` przechodzi.

### 5.12. Testy

Testy modeli:

- `Quest.clean()` odrzuca pusty title,
- `Quest.clean()` odrzuca `target_value <= 0`,
- `Quest.clean()` odrzuca zakres dat z `available_until < available_from`,
- `QuestReward` wymaga dodatniego XP,
- `QuestReward` jest unikalny dla `quest + skill`,
- `QuestCompletion` jest unikalny dla `quest + completed_on`.

Testy serwisow:

- `complete_quest` tworzy completion,
- `complete_quest` ustawia `completed_at`,
- `complete_quest` tworzy jeden `XpEvent` per reward,
- ponowne `complete_quest` dla daily tego samego dnia nie dubluje XP,
- `complete_quest` blokuje archived/draft quest,
- `update_quest_progress` zapisuje czesciowy progress,
- `update_quest_progress` po przekroczeniu targetu przyznaje XP raz.

Testy API:

- POST complete success,
- POST progress success,
- bledny JSON zwraca `400`,
- brak questa zwraca `404`,
- konflikt domenowy zwraca `409`.

## 6. Modul 2 - habity, streaki i milestone

### 6.1. Cel

Wprowadzic realne habity, check-iny dzienne, dynamiczne liczenie streakow oraz milestone streakow, ktore moga przyznac XP przez `skills.XpEvent`.

Efekt modulu:

- habity mozna tworzyc w adminie,
- dashboard moze odhaczyc habit przez API,
- stan check-in jest zapisany w PostgreSQL,
- streak jest liczony z `HabitCheckIn`,
- milestone XP jest przyznawane tylko raz.

### 6.2. Zakres

W zakresie:

- model `Habit`,
- model `HabitCheckIn`,
- model `HabitMilestone`,
- model `HabitMilestoneReward`,
- model `HabitMilestoneUnlock`,
- serwis `toggle_habit`,
- serwis `calculate_habit_streak`,
- serwis `unlock_due_habit_milestones`,
- endpoint `POST /api/habits/<id>/toggle/`,
- admin,
- seed 7 habitow i milestone 7/14/30 dni,
- testy modeli, serwisow i API.

Poza zakresem:

- rozbudowany habit editor w React,
- tygodniowe habity w UI,
- automatyczne questy generowane z habitow,
- achievementy za streaki,
- cofanie XP po usunieciu milestone unlock.

### 6.3. Modele i pola

#### 6.3.1. `rpg.Habit`

Pola:

- `id`,
- `name` - `CharField(max_length=120)`,
- `description` - `TextField(blank=True)`,
- `frequency` - `CharField(max_length=20, choices=HabitFrequency.choices, default=HabitFrequency.DAILY)`,
- `target_value` - `PositiveIntegerField(default=1)`,
- `target_unit` - `CharField(max_length=20, choices=TargetUnit.choices, default=TargetUnit.CHECK)`,
- `is_active` - `BooleanField(default=True)`,
- `sort_order` - `PositiveIntegerField(default=0)`,
- `created_at` - `DateTimeField(auto_now_add=True)`,
- `updated_at` - `DateTimeField(auto_now=True)`.

Meta:

- `ordering = ["sort_order", "name"]`,
- `UniqueConstraint(fields=["name"], name="rpg_habit_unique_name")`.

Walidacja:

- `name.strip()` nie moze byc puste,
- `target_value > 0`.

#### 6.3.2. `rpg.HabitCheckIn`

Pola:

- `id`,
- `habit` - `ForeignKey("rpg.Habit", on_delete=models.CASCADE, related_name="checkins")`,
- `checked_on` - `DateField()`,
- `value` - `PositiveIntegerField(default=1)`,
- `note` - `TextField(blank=True)`,
- `created_at` - `DateTimeField(auto_now_add=True)`,
- `updated_at` - `DateTimeField(auto_now=True)`.

Meta:

- `ordering = ["-checked_on", "habit__sort_order", "habit__name"]`,
- `UniqueConstraint(fields=["habit", "checked_on"], name="rpg_habit_checkin_unique_habit_day")`.

Walidacja:

- `value >= 0`,
- `checked_on` wymagane.

Regula zaliczenia dnia:

- dzien jest zaliczony, jezeli `checkin.value >= habit.target_value`.

#### 6.3.3. `rpg.HabitMilestone`

Pola:

- `id`,
- `habit` - `ForeignKey("rpg.Habit", on_delete=models.CASCADE, null=True, blank=True, related_name="milestones")`,
- `title` - `CharField(max_length=160)`,
- `streak_days` - `PositiveIntegerField()`,
- `is_active` - `BooleanField(default=True)`,
- `created_at` - `DateTimeField(auto_now_add=True)`,
- `updated_at` - `DateTimeField(auto_now=True)`.

Meta:

- `ordering = ["streak_days", "title"]`,
- `UniqueConstraint(fields=["habit", "streak_days"], name="rpg_habit_milestone_unique_habit_days")`.

Uwaga:

- dla `habit = null` unikalnosc globalnych milestone moze wymagac dodatkowej walidacji w `clean()`, bo SQL unique pozwala na wiele NULL.

Walidacja:

- `title.strip()` nie moze byc puste,
- `streak_days > 0`.

#### 6.3.4. `rpg.HabitMilestoneReward`

Pola:

- `id`,
- `milestone` - `ForeignKey("rpg.HabitMilestone", on_delete=models.CASCADE, related_name="rewards")`,
- `skill` - `ForeignKey("skills.Skill", on_delete=models.CASCADE, related_name="habit_milestone_rewards")`,
- `xp_amount` - `PositiveIntegerField()`.

Meta:

- `ordering = ["milestone__streak_days", "skill__name"]`,
- `UniqueConstraint(fields=["milestone", "skill"], name="rpg_habit_milestone_reward_unique_milestone_skill")`,
- `CheckConstraint(condition=Q(xp_amount__gt=0), name="rpg_habit_milestone_reward_xp_gt_0")`.

Walidacja:

- `xp_amount > 0`.

#### 6.3.5. `rpg.HabitMilestoneUnlock`

Pola:

- `id`,
- `milestone` - `ForeignKey("rpg.HabitMilestone", on_delete=models.CASCADE, related_name="unlocks")`,
- `habit` - `ForeignKey("rpg.Habit", on_delete=models.CASCADE, related_name="milestone_unlocks")`,
- `unlocked_at` - `DateTimeField(default=timezone.now)`,
- `xp_awarded_at` - `DateTimeField(null=True, blank=True)`,
- `streak_days` - `PositiveIntegerField()`,
- `note` - `TextField(blank=True)`.

Meta:

- `ordering = ["-unlocked_at"]`,
- `UniqueConstraint(fields=["milestone", "habit"], name="rpg_habit_milestone_unlock_unique_milestone_habit")`.

Walidacja:

- `streak_days > 0`,
- `milestone.habit` musi byc puste albo takie samo jak `habit`.

### 6.4. Reguly domenowe

- Tylko aktywne habity sa pokazywane na dashboardzie.
- `toggle_habit` dla braku check-in tworzy check-in.
- `toggle_habit` dla istniejacego check-in usuwa `HabitCheckIn`; w MVP nie wprowadzamy nieaktywnego check-in ani `value=0` jako cofniecia.
- Pojedynczy check-in nie tworzy XP.
- Streak liczymy dynamicznie z kolejnych dni wstecz.
- Dzien zaliczony, jezeli check-in istnieje i `value >= habit.target_value`.
- Streak dzienny liczymy od wskazanej daty, domyslnie dzisiaj.
- Jezeli dzisiaj nie ma check-in, streak dla dashboardu moze wynosic 0. Dla wyswietlania "current streak before today" mozna pozniej dodac oddzielny tryb.
- Milestone globalny (`habit is null`) dotyczy kazdego habitu.
- Milestone z przypisanym habitem dotyczy tylko tego habitu.
- Milestone moze zostac odblokowany tylko raz dla danego habitu.
- Odblokowanie milestone tworzy `XpEvent` z `source_type="habit_milestone"` dla kazdej nagrody.
- Przerwanie streaka pozniej nie cofa milestone ani XP.
- Usuniecie check-in, ktory wywolal milestone, nie cofa XP w module 2.

### 6.5. Serwisy

Plik: `rpg/services.py`.

#### 6.5.1. `calculate_habit_streak`

Sygnatura:

```python
def calculate_habit_streak(
    *,
    habit: Habit,
    end_on: date | None = None,
) -> int:
    ...
```

Zachowanie:

1. `end_on = timezone.localdate()`, jezeli brak.
2. Pobierz check-iny habitu do `end_on`.
3. Idz dzien po dniu wstecz.
4. Zatrzymaj sie na pierwszym dniu bez zaliczonego check-in.
5. Zwroc liczbe kolejnych dni.

Wydajnosc:

- dla MVP prosta petla jest OK,
- pobrac check-iny jednym query do slownika `{checked_on: value}`.

#### 6.5.2. `toggle_habit`

Sygnatura:

```python
def toggle_habit(
    *,
    habit: Habit,
    checked_on: date | None = None,
    value: int | None = None,
    note: str = "",
) -> dict[str, Any]:
    ...
```

Zachowanie:

1. Zweryfikuj `habit.is_active`.
2. Ustal `checked_on = timezone.localdate()`, jezeli brak.
3. Jezeli check-in nie istnieje:
   - utworz `HabitCheckIn`,
   - `value = value or habit.target_value`,
   - policz streak,
   - odblokuj nalezne milestone,
   - zwroc `checked=True`.
4. Jezeli check-in istnieje:
   - usun `HabitCheckIn`,
   - nie cofaj milestone ani XP,
   - policz nowy streak,
   - zwroc `checked=False`.
5. Operacja w `transaction.atomic()`.

Response serwisu powinien zawierac:

- `habit`,
- `check_in` albo `None`,
- `checked`,
- `streak_days`,
- `milestone_unlocks`,
- `next_milestone`,
- `xp_events`.

#### 6.5.3. `unlock_due_habit_milestones`

Sygnatura:

```python
def unlock_due_habit_milestones(
    *,
    habit: Habit,
    streak_days: int,
) -> tuple[list[HabitMilestoneUnlock], list[XpEvent]]:
    ...
```

Zachowanie:

1. Znajdz aktywne milestone:
   - `habit=habit` albo `habit__isnull=True`,
   - `streak_days <= current streak`.
2. Pomin milestone juz odblokowane dla habitu.
3. Utworz `HabitMilestoneUnlock`.
4. Dla kazdego reward utworz `XpEvent`.
5. Ustaw `xp_awarded_at`.
6. Zwroc unlocki i eventy.

Regula:

- jezeli uzytkownik w jednym dniu przeskoczy kilka progow, przyznaj wszystkie brakujace milestone.

### 6.6. Endpoint JSON

#### `POST /api/habits/<id>/toggle/`

Request JSON:

```json
{
  "checked_on": "2026-06-10",
  "value": 1,
  "note": "Done in the morning"
}
```

Pola opcjonalne:

- `checked_on` - domyslnie dzisiaj lokalnie,
- `value` - domyslnie `habit.target_value`,
- `note`.

Response `200 OK`:

```json
{
  "habit": {
    "id": 1,
    "name": "Read",
    "completed_today": true,
    "streak_days": 7
  },
  "check_in": {
    "id": 33,
    "checked_on": "2026-06-10",
    "value": 1
  },
  "milestone_unlocks": [
    {
      "id": 5,
      "title": "7 Day Momentum",
      "streak_days": 7
    }
  ],
  "next_milestone": {
    "id": 6,
    "title": "14 Day Discipline",
    "streak_days": 14,
    "days_remaining": 7
  },
  "xp_events": [
    {
      "id": 200,
      "skill": {"id": 4, "name": "Learning"},
      "amount": 50,
      "source_type": "habit_milestone"
    }
  ]
}
```

Response przy odznaczeniu:

```json
{
  "habit": {
    "id": 1,
    "name": "Read",
    "completed_today": false,
    "streak_days": 0
  },
  "check_in": null,
  "milestone_unlocks": [],
  "next_milestone": {
    "id": 5,
    "title": "7 Day Momentum",
    "streak_days": 7,
    "days_remaining": 7
  },
  "xp_events": []
}
```

Statusy:

- `200 OK` przy sukcesie,
- `400 Bad Request` dla blednych danych,
- `404 Not Found` dla braku habitu,
- `409 Conflict` dla nieaktywnego habitu.

### 6.7. Admin

Admin:

- `HabitAdmin`,
- `HabitCheckInAdmin`,
- `HabitMilestoneAdmin`,
- `HabitMilestoneRewardInline`,
- `HabitMilestoneUnlockAdmin`.

Wymagania:

- `HabitAdmin.list_display`: `name`, `frequency`, `target_value`, `target_unit`, `is_active`, `sort_order`,
- `HabitAdmin.list_filter`: `frequency`, `is_active`,
- `HabitAdmin.search_fields`: `name`, `description`,
- `HabitCheckInAdmin.list_display`: `habit`, `checked_on`, `value`,
- `HabitCheckInAdmin.list_filter`: `checked_on`, `habit`,
- `HabitMilestoneRewardInline` jako `TabularInline`,
- `HabitMilestoneAdmin.list_display`: `title`, `habit`, `streak_days`, `is_active`,
- `HabitMilestoneAdmin.list_filter`: `is_active`, `streak_days`,
- `HabitMilestoneUnlockAdmin.readonly_fields`: `unlocked_at`, `xp_awarded_at`.

### 6.8. Seed

Plik: `activities/management/commands/seed_life_rpg.py`.

Dopisac metody:

- `_seed_habits() -> dict[str, Habit]`,
- `_seed_habit_milestones(skills: dict[str, Skill]) -> None`.

Przykladowe habity:

- `Train`,
- `Read`,
- `Learn`,
- `Hydrate`,
- `Sleep`,
- `Journal`,
- `Review finances`.

Milestone:

- `7 Day Momentum` -> `streak_days=7`, `Learning +50 XP`,
- `14 Day Discipline` -> `streak_days=14`, `Fitness +100 XP` albo `Learning +100 XP`,
- `30 Day Identity Shift` -> `streak_days=30`, `Learning +250 XP`.

Reguly:

- seed idempotentny,
- milestone globalne na start (`habit=null`),
- rewardy przez `update_or_create`.

### 6.9. Integracja z dashboardem

W module 2 przygotowac helper:

```python
def build_habit_rows(day: date) -> tuple[list[dict[str, Any]], dict[str, int]]:
    ...
```

Docelowy ksztalt zgodny z obecnym API:

```json
{
  "habits": [
    {
      "label": "Read",
      "completed": true
    }
  ],
  "habits_summary": {
    "completed": 6,
    "total": 7,
    "streak_days": 14
  }
}
```

Rozszerzenie zalecane dla React live:

```json
{
  "habits": [
    {
      "id": 1,
      "label": "Read",
      "completed": true,
      "streak_days": 7,
      "checkin_id": 33
    }
  ],
  "habits_summary": {
    "completed": 6,
    "total": 7,
    "streak_days": 14
  }
}
```

### 6.10. Kolejnosc implementacji

1. Dodac modele `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock`.
2. Dodac migracje.
3. Dodac admin.
4. Dodac `calculate_habit_streak`.
5. Dodac `unlock_due_habit_milestones`.
6. Dodac `toggle_habit`.
7. Dodac endpoint `POST /api/habits/<id>/toggle/`.
8. Rozszerzyc seed.
9. Dodac helpery dashboardowe.
10. Dodac testy modeli, serwisow i API.

### 6.11. Kryteria akceptacji

- Admin pozwala tworzyc habity i milestone z rewardami.
- Klikniecie habitu przez API tworzy `HabitCheckIn`.
- Drugie klikniecie tego samego habitu dla tego samego dnia usuwa check-in.
- Check-in nie tworzy XP sam z siebie.
- Streak liczy kolejne zaliczone dni.
- Osiagniecie milestone tworzy `HabitMilestoneUnlock`.
- Milestone z dwoma rewardami tworzy dwa `XpEvent`.
- Ten sam milestone dla tego samego habitu nie tworzy XP drugi raz.
- Przerwanie streaka nie usuwa milestone unlock.
- `python manage.py test rpg` przechodzi.

### 6.12. Testy

Testy modeli:

- `Habit.clean()` odrzuca pusta nazwe,
- `Habit.clean()` odrzuca `target_value <= 0`,
- `HabitCheckIn` jest unikalny dla `habit + checked_on`,
- `HabitMilestone.clean()` odrzuca `streak_days <= 0`,
- `HabitMilestoneReward` wymaga dodatniego XP,
- `HabitMilestoneUnlock` wymaga zgodnosci `milestone.habit` z `habit`.

Testy serwisow:

- `toggle_habit` tworzy check-in,
- drugi `toggle_habit` usuwa check-in,
- `toggle_habit` blokuje nieaktywny habit,
- `calculate_habit_streak` zwraca 0 bez check-inow,
- `calculate_habit_streak` zwraca poprawna liczbe dla kilku kolejnych dni,
- streak konczy sie na luce,
- milestone 7 dni odblokowuje sie przy streaku 7,
- milestone 7 dni nie odblokowuje sie drugi raz,
- milestone tworzy `XpEvent` dla kazdego reward,
- usuniecie check-in przez toggle nie cofa milestone XP.

Testy API:

- POST toggle success create,
- POST toggle success delete,
- bledny JSON zwraca `400`,
- brak habitu zwraca `404`,
- nieaktywny habit zwraca `409`.

## 7. Wspolny kontrakt API i serializacja

### 7.1. JSON parsing

Widoki powinny miec maly helper:

```python
def parse_json_body(request: HttpRequest) -> dict[str, Any]:
    ...
```

Reguly:

- pusty body -> `{}`,
- niepoprawny JSON -> kontrolowany blad `400`,
- body nie-bedacy obiektem JSON -> `400`,
- backendowy kontrakt JSON przyjmuje i zwraca `snake_case`,
- React mapper moze mapowac `snake_case` z API na `camelCase` w typach frontendu,
- widoki Django nie musza akceptowac `camelCase` dla nowych endpointow RPG.

### 7.2. Daty

Frontend wysyla daty jako `YYYY-MM-DD` w polach backendowego kontraktu:

- `completed_on`,
- `checked_on`.

Backend:

- parsuje przez `date.fromisoformat`,
- brak daty oznacza `timezone.localdate()`,
- nie uzywac naiwnych `datetime.now()`.

### 7.3. CSRF

Zostaje standardowy Django CSRF:

- React pobiera cookie przez `GET /api/csrf/`,
- POST-y wysylaja `X-CSRFToken`,
- nie dodawac globalnego `csrf_exempt`.

## 8. Wspolne testy regresji po modulach 0-2

Po implementacji modulow 0-2 uruchomic:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py test rpg
.venv/bin/python manage.py test
cd frontend && npm run typecheck
cd frontend && npm run build
```

Kryterium:

- backend testy przechodza na PostgreSQL,
- frontend dalej buduje sie po ewentualnym rozszerzeniu typow API,
- brak zaleznosci DRF/Celery.

## 9. Ryzyka i decyzje odlozone

Odlozone poza moduly 0-2:

- cofanie XP po usunieciu questa, completion, check-in albo milestone unlock,
- osobny ledger korekt XP,
- powiazanie `XpEvent` generycznym FK do zrodel innych niz `ActivityEntry`,
- React ekran zarzadzania questami i habitami,
- challenge,
- achievementy,
- journal,
- AI quest generation.

Najwazniejsze ryzyko:

- `skills.XpEvent` dzisiaj ma jawny FK tylko do `activities.ActivityEntry`. Dla questow i milestone w modulach 0-2 wystarczy `source_type`, `note` oraz `xp_awarded_at` na rekordach domenowych. Jezeli pozniej bedziemy chcieli precyzyjne cofanie XP, trzeba dodac jawny model ledger/korekt albo rozszerzyc `XpEvent` o neutralne pola zrodla.

## 10. Rekomendowana kolejnosc prac

1. Modul 0: utworzyc `rpg`, URL-e, choices i skeleton.
2. Modul 1: dodac modele questow, migracje, admin.
3. Modul 1: dodac serwisy questow i testy serwisow.
4. Modul 1: dodac endpointy questow i testy API.
5. Modul 1: rozszerzyc seed.
6. Modul 2: dodac modele habitow/streakow, migracje, admin.
7. Modul 2: dodac serwisy streakow/milestone i testy.
8. Modul 2: dodac endpoint toggle i testy API.
9. Modul 2: rozszerzyc seed.
10. Dopiero po tym przepiac `GET /api/dashboard/` na realne questy i habity w kolejnym module.
