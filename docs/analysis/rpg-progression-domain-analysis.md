# Analiza domeny RPG progression

Data analizy: 2026-06-10
Zakres: `docs/rpg-progression-domain-spec.md` vs aktualny backend w `/home/wh173-p0ny/ProjectLevel`.
Tryb: analiza statyczna plikow. Testow i komend Django nie uruchamialem, zeby nie generowac artefaktow poza tym raportem.

## 1. Werdykt gotowosci domeny

**Werdykt: domena `Goals, Challenges, Achievements` nie jest gotowa do akceptacji ani integracji produktowej.** Repo ma juz mocny fundament pod te prace: `rpg` istnieje, questy i habity sa zaimplementowane, XP idzie przez `skills.XpEvent`, journal ma wpisy systemowe, planner ma kalendarz, a dashboard ma miejsca na challenge/achievements. Brakuje jednak calej docelowej domeny ze specu: `Goal`, `GoalSkill`, `GoalProgressEntry`, `Challenge`, `ChallengeReward`, `ChallengeCheckIn`, `Achievement`, `AchievementUnlock`, nowych choices, serwisow mutujacych, endpointow, admina, seedow i testow.

Ocena praktyczna:

| Obszar | Status | Uzasadnienie |
|---|---|---|
| Fundament RPG | Gotowy | `rpg` jest w `INSTALLED_APPS`, `rpg.urls` jest pod `/api/`, modele questow/habitow/journala istnieja. |
| XP ledger | Gotowy jako zaleznosc | `Skill.add_xp()` tworzy `XpEvent`; aktywnosci, questy i habit milestone uzywaja jawnych serwisow. |
| Journal/system events | Czesc gotowa | `JournalEntry` ma `source_type/source_id` z unikalnoscia, `create_system_journal_entry()` jest idempotentne; brakuje `JournalEntryType.GOAL`. |
| Planner | Gotowy jako osobna zaleznosc | `planner.CalendarEvent` istnieje i ma JSON API, ale spec progression nie definiuje jeszcze bezposredniej integracji z goal/challenge. |
| Goals | Brak | Brak modeli, choices, serwisow, API, admina, seedow i testow. |
| Challenges | Brak | Brak modeli i XP completion gate; dashboard ma tylko placeholder `active_challenge: None`. |
| Achievements | Brak | Brak definicji odznak, unlockow, evaluatora i realnych licznikow w dashboard/journal. |

Wniosek: backend jest gotowy do rozpoczecia implementacji tej domeny bez tworzenia nowej aplikacji, ale spec wymaga korekt/uzgodnien w kilku miejscach przed migracjami, zeby nie utrwalic niespojnych modeli.

## 2. Walidacja zalozen specu o istniejacym `rpg` / `planner` / `journal`

| Zalozenie ze specu | Stan kodu | Ocena |
|---|---|---|
| Django 6.0.6 | Settings wygenerowane przez Django 6.0.6, `requirements.txt` zawiera Django 6.0.6. | Potwierdzone |
| PostgreSQL jako jedyna baza | `config/settings.py` buduje `DATABASES` z `DATABASE_URL` albo `POSTGRES_*`, bez SQLite fallbacku. | Potwierdzone |
| Aktywne aplikacje: `skills`, `activities`, `statuses`, `dashboard`, `rpg`, `planner` | Wszystkie sa w `INSTALLED_APPS`; `config/urls.py` podpina `rpg.urls` i `planner.urls` pod `/api/`. | Potwierdzone |
| `rpg` zawiera questy | Sa `Quest`, `QuestReward`, `QuestCompletion`; sa serwisy `complete_quest()` i `update_quest_progress()`. | Potwierdzone |
| `rpg` zawiera habity i milestone | Sa `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock`; sa `toggle_habit()` i `unlock_due_habit_milestones()`. | Potwierdzone |
| `rpg` zawiera journal | Jest `JournalEntry`, typy wpisow, refleksje, tagi, `source_type/source_id`, widoki API i serwisy journala. | Potwierdzone |
| `rpg` zawiera character identity | Jest `CharacterIdentity` z constraintem pojedynczej aktywnej tozsamosci. | Potwierdzone |
| `planner` istnieje | Jest `CalendarEvent`, `CalendarEventType`, serwisy i endpointy `/api/calendar/events/`. | Potwierdzone |
| `skills.XpEvent` jest jedynym audytem XP | W obecnym kodzie XP jest suma z `XpEvent`; brak alternatywnych licznikow XP w skillach, questach i habitach. | Potwierdzone |
| Questy przyznaja XP przez `QuestReward` i `Skill.add_xp()` | `_mark_completed_and_award_xp()` iteruje po rewards i tworzy `XpEvent` z `source_type="quest"`. | Potwierdzone |
| Habit streaki same nie daja XP, milestone unlock moze dac XP | `toggle_habit()` bez milestone daje 0 XP; `unlock_due_habit_milestones()` tworzy XP z rewardow milestone. | Potwierdzone |
| API bez DRF, zwykle Django JSON | Widoki uzywaja `JsonResponse`, dekoratorow Django i recznego parsowania JSON. | Potwierdzone |
| JSON w `snake_case` | Obecne payloady RPG/journal/dashboard sa zasadniczo `snake_case`; manual activity nadal toleruje camelCase jako kompatybilnosc frontendowa. | Potwierdzone z uwaga |
| Journal wspiera `CHALLENGE` i `ACHIEVEMENT` | `JournalEntryType` ma `CHALLENGE` i `ACHIEVEMENT`. | Potwierdzone |
| Journal wspiera `GOAL` | `JournalEntryType.GOAL` nie istnieje. | Brak |

## 3. Mapa spec -> aktualny kod

### Choices

| Element specu | Stan kodu | Ocena |
|---|---|---|
| `GoalStatus` | Brak w `rpg/choices.py`. | Brak |
| `GoalPriority` | Brak. | Brak |
| `ChallengeStatus` | Brak. | Brak |
| `ChallengeCadence` | Brak. | Brak |
| `AchievementRarity` | Brak. | Brak |
| `AchievementTrigger` | Brak. | Brak |
| `ProgressSource` | Brak; obecnie `source_type` jest wolnym `CharField` w kilku modelach. | Brak / decyzja otwarta |
| `CreationSource` | Istnieje: `manual`, `system`, `ai`. | Gotowe |
| `TargetUnit` | Istnieje: `count`, `minutes`, `steps`, `pages`, `check`. | Gotowe, ale brak `percent` |
| `JournalEntryType.CHALLENGE`, `ACHIEVEMENT` | Istnieja. | Gotowe |
| `JournalEntryType.GOAL` | Brak. | Brak |

### Modele

| Model ze specu | Stan kodu | Ocena |
|---|---|---|
| `Goal` | Nie istnieje. | Brak |
| `GoalSkill` | Nie istnieje. | Brak |
| `GoalProgressEntry` | Nie istnieje. | Brak |
| `Challenge` | Nie istnieje. | Brak |
| `ChallengeReward` | Nie istnieje. | Brak |
| `ChallengeCheckIn` | Nie istnieje. | Brak |
| `Achievement` | Nie istnieje. | Brak |
| `AchievementUnlock` | Nie istnieje. | Brak |
| `Quest` / `QuestReward` / `QuestCompletion` | Istnieja i sa dobrym wzorcem dla rewardow, completion, `xp_awarded_at` i journala. | Gotowe jako wzorzec |
| `Habit` / `HabitCheckIn` / milestone | Istnieja i sa dobrym wzorcem toggle, streak, unlock, XP tylko przez milestone. | Gotowe jako wzorzec |
| `JournalEntry` | Istnieje, ma idempotentne `source_type/source_id`. | Gotowe z brakiem typu `goal` |
| `CalendarEvent` | Istnieje w `planner`, ma `source_type/source_id`. | Gotowe jako przyszla integracja |
| `XpEvent` | Istnieje, ale ma tylko FK do `ActivityEntry`; quest/habit/challenge audyt opiera sie na `source_type` i `note`. | Gotowe z ograniczeniem audytu |

### Serwisy

| Serwis ze specu | Stan kodu | Ocena |
|---|---|---|
| `create_goal()` | Brak. | Brak |
| `update_goal_progress()` | Brak. | Brak |
| `complete_goal()` | Brak. | Brak |
| `create_challenge()` | Brak. | Brak |
| `toggle_challenge_check_in()` | Brak. | Brak |
| `complete_challenge()` | Brak. | Brak |
| `fail_challenge()` | Brak. | Brak |
| `unlock_achievement()` | Brak. | Brak |
| `evaluate_achievements()` | Brak. | Brak |
| `complete_quest()` | Istnieje; uzywa transakcji, `select_for_update()`, `xp_awarded_at`, journala. | Gotowy wzorzec |
| `toggle_habit()` | Istnieje; tworzy/usuwa check-in, nalicza milestone XP raz. | Gotowy wzorzec |
| `create_system_journal_entry()` | Istnieje i uzywa unikalnosci `source_type/source_id`. | Gotowy wzorzec |
| `build_journal_stats()` | Istnieje, ale `achievements_unlocked` jest placeholderem `0`. | Do zmiany po achievements |

### API / dashboard / seed

| Element specu | Stan kodu | Ocena |
|---|---|---|
| `/api/goals/*` | Brak route'ow. | Brak |
| `/api/challenges/*` | Brak route'ow. | Brak |
| `/api/achievements/*` | Brak route'ow. | Brak |
| Admin goals/challenges/achievements | Brak rejestracji, bo brak modeli. | Brak |
| `seed_life_rpg` goals/challenges/achievements | Seeduje life areas, skills, aktywnosci, questy, habity, journal, identity, calendar; nie seeduje goals/challenges/achievements. | Brak dla nowej domeny |
| Dashboard `active_challenge` | `dashboard/services.py` zwraca `None`; test potwierdza placeholder. | Brak |
| Dashboard `achievements` | Zwraca pusta liste. | Brak |
| Journal `achievements_unlocked` | Placeholder `0`. | Brak |

## 4. Blokery

1. **Brak modeli domeny progression** - nie da sie wygenerowac migracji ani admina bez `Goal*`, `Challenge*`, `Achievement*`.
2. **Brak choices** - spec wymaga nowych `TextChoices`, a obecne `rpg/choices.py` konczy sie na quest/habit/journal.
3. **Brak `JournalEntryType.GOAL`** - completion celu nie ma docelowego typu wpisu. Spec raz dopuszcza `SYSTEM`, a pozniej wymaga `GOAL`; trzeba przyjac jedna decyzje przed migracja.
4. **Brak serwisow idempotentnych** - nie ma `complete_goal`, `complete_challenge`, `unlock_achievement`, `evaluate_achievements`, wiec nie ma gate'ow XP/unlockow ani journala.
5. **Brak endpointow** - `rpg/urls.py` ma quest, habit i journal; nie ma goals/challenges/achievements.
6. **Brak dashboard selectors** - `active_challenge`, `achievements` i `achievements_unlocked` sa placeholderami.
7. **Brak seed data dla nowej domeny** - seed nie utworzy danych do recznego smoke testu goals/challenges/achievements.
8. **Brak testow nowej domeny** - obecne `rpg/tests.py` dobrze pokrywaja questy, habity i journal, ale nie ma testow wymaganych przez ten spec.
9. **Ograniczony audyt `XpEvent`** - `XpEvent` nie ma ogolnego `source_id`; challenge XP bedzie musial polegac na `Challenge.xp_awarded_at` i konwencji `note`, tak jak questy.

## 5. Niespojnosci w modelach `Goal` / `Challenge` / `Achievement`

1. **`Goal.target_unit` vs seed `percent/count`** - spec proponuje cele typu `100 percent/count`, ale istniejacy `TargetUnit` nie ma wartosci `percent`. Trzeba albo dodac `PERCENT`, albo traktowac procent jako `count` z UI label, zanim powstana migracje.
2. **`Goal.completed_at` i status** - walidacja mowi, ze `completed_at` moze byc ustawione tylko przy `status=completed`, ale nie mowi, czy `status=completed` wymaga `completed_at`. Serwis ma ustawic oba, lecz model/constraint powinien jasno blokowac stany polowiczne albo dopuszczac je celowo.
3. **`GoalProgressEntry` idempotencja** - unique po `(goal, source_type, source_id)` dziala tylko dla niepustego source i source_id. Manualne wpisy bez source_id moga sie duplikowac, co jest OK, ale powinno byc nazwane jako celowe.
4. **`GoalProgressEntry.delta`** - model przechowuje `previous_value`, `new_value` i `delta`; `delta` jest wartoscia pochodna. To jest akceptowalne dla audytu, ale musi byc walidowane w serwisie i `clean()`, inaczej latwo utrwalic niespojny audyt.
5. **`Challenge.progress_value` jako cache** - spec raz opisuje je jako liczbe udanych check-inow, a `ChallengeCheckIn.value` pozwala na wartosci wieksze niz 1. Trzeba zdecydowac, czy progress to liczba successful dni, czy suma `value` z successful check-inow.
6. **`ChallengeCheckIn.successful` i `value`** - dla `successful=False` dopuszczone jest `value=0`, ale pole jest `PositiveIntegerField`. Django dopuszcza 0 dla `PositiveIntegerField`, ale nazwa pola moze mylic; wazniejsze jest, czy nieudane check-iny maja byc zapisywane przez toggle, czy tylko przez osobny serwis/admin.
7. **`toggle_challenge_check_in()` nie konczy automatycznie challenge** - zwraca `completion_ready=True`, ale nie wywoluje `complete_challenge()`. To jest bezpieczne dla XP, lecz UI/API musi miec jawny drugi krok, inaczej challenge moze utknac z `progress_value == target_value` i bez XP.
8. **`complete_challenge()` return type** - spec mowi, ze serwis odpala `evaluate_achievements(...)`, ale sygnatura zwraca tylko `tuple[Challenge, list[XpEvent]]`. Powinna zwracac takze unlocki albo spec powinien powiedziec, ze unlocki sa celowo pomijane w odpowiedzi.
9. **`complete_challenge()` i progres goal** - spec mowi, ze challenge "moze" wywolac `update_goal_progress(...)`. To jest niedookreslone: trzeba okreslic domyslna wartosc delty lub mechanizm mapowania challenge -> goal progress, inaczej integracja bedzie arbitralna.
10. **`Achievement.requirement_value` dla triggerow completion** - dla `quest_count`, `habit_streak`, `journal_streak` znaczenie jest jasne. Dla `challenge_completed` i `goal_completed` spec mowi o opcjonalnym konkretnym obiekcie, ale seed uzywa `requirement_value=1`. Trzeba okreslic, czy `requirement_value` jest wymagane dla completion count, czy opcjonalne przy wskazanym konkretnym goal/challenge.
11. **`Achievement` ma wiele opcjonalnych FK naraz** - `skill`, `habit`, `goal`, `challenge` moga byc jednoczesnie ustawione, mimo ze sens zalezy od triggera. Potrzebna jest walidacja matrycy trigger -> dozwolone/wymagane pola.
12. **`AchievementUnlock` unique per achievement** - dobre dla local-first single-user, ale trzeba opisac, ze to swiadomie zamyka droge do wielu profili bez migracji w przyszlosci.
13. **Achievement nie daje XP** - zgodne z decyzja architektoniczna, ale trzeba uwazac w UI/seedach, zeby achievementy nie mialy ukrytych rewardow ani nie powielaly XP z challenge.

## 6. Rekomendowana kolejnosc implementacji domeny i migracji

1. **Doprecyzowac spec przed kodem**: rozstrzygnac `TargetUnit.PERCENT`, `JournalEntryType.GOAL`, semantyke `Challenge.progress_value`, return type `complete_challenge()`, requirementy triggerow achievements i mapowanie challenge -> goal progress.
2. **Choices first**: dodac `GoalStatus`, `GoalPriority`, `ChallengeStatus`, `ChallengeCadence`, `AchievementRarity`, `AchievementTrigger`, opcjonalnie `ProgressSource`, oraz `JournalEntryType.GOAL`.
3. **Migracja modeli bez serwisow UI**: dodac `Goal`, `GoalSkill`, `GoalProgressEntry`, `Challenge`, `ChallengeReward`, `ChallengeCheckIn`, `Achievement`, `AchievementUnlock` w jednej spojnej migracji `rpg`, z constraintami i `clean()`.
4. **Admin zaraz po modelach**: zarejestrowac modele; inliny `GoalSkill`, read-only `GoalProgressEntry`, inliny `ChallengeReward`/`ChallengeCheckIn`, read-only audit dla `AchievementUnlock`.
5. **Serwisy goals**: `create_goal`, `update_goal_progress`, `complete_goal`; bez XP, z idempotentnym journalem i achievement evaluation.
6. **Serwisy challenges**: `create_challenge`, `toggle_challenge_check_in`, `complete_challenge`, `fail_challenge`; XP tylko przez `ChallengeReward`, gate na `xp_awarded_at`, journal completion/failure.
7. **Serwisy achievements**: `unlock_achievement`, `evaluate_achievements`, trigger matrix i snapshoty; bez XP.
8. **API**: dodac route'y goals/challenges/achievements w `rpg/urls.py`, parsowanie JSON w stylu istniejacych widokow, `snake_case`, `validation_error`, 404 i konflikty 409 dla domeny.
9. **Dashboard/journal selectors**: zastapic `active_challenge: None`, `achievements: []`, `achievements_unlocked: 0` realnymi zapytaniami.
10. **Seed data**: rozszerzyc `seed_life_rpg` o goals, challenges, challenge rewards i achievements; zachowac idempotencje i nie tworzyc XP ani unlockow w seedzie.
11. **Migracje i kontrola dry-run**: po implementacji uruchomic `makemigrations rpg`, przejrzec constrainty, potem `migrate`, a na koniec `makemigrations --check --dry-run`.

## 7. Testy wymagane

### Modele

- `Goal.title` po `strip()` nie moze byc pusty.
- `Goal.target_value <= 0` jest odrzucany.
- `Goal.progress_value > target_value` jest odrzucany.
- `Goal.due_on < starts_on` jest odrzucany.
- `Goal.completed_at` bez `status=completed` jest odrzucany.
- `GoalSkill` wymaga `weight > 0` i unique `(goal, skill)`.
- `GoalProgressEntry` waliduje `delta == new_value - previous_value`, range `0..goal.target_value` i source/source_id.
- `GoalProgressEntry` unique `(goal, source_type, source_id)` dziala dla integracji.
- `Challenge.title` pusty jest odrzucany.
- `Challenge.ends_on < starts_on` jest odrzucany.
- `Challenge.progress_value > target_value` jest odrzucany.
- `Challenge.completed_at` tylko dla `completed`, `failed_at` tylko dla `failed`, oba naraz odrzucane.
- `Challenge.xp_awarded_at` bez completion jest odrzucany.
- `ChallengeReward` wymaga `xp_amount > 0` i unique `(challenge, skill)`.
- `ChallengeCheckIn` poza zakresem dat jest odrzucany.
- `ChallengeCheckIn` unique `(challenge, checked_on)` dziala.
- `Achievement.code` i `Achievement.title` nie moga byc puste; `code` jest unique.
- `Achievement` waliduje wymagane pola per trigger.
- `AchievementUnlock` jest unique per achievement i waliduje source/source_id.

### Serwisy

- `create_goal()` tworzy draft/active zgodnie z payloadem i nie tworzy XP ani journala.
- `create_goal(created_by=ai, status!=draft)` jest odrzucany.
- `update_goal_progress()` zapisuje absolutny progress i tworzy `GoalProgressEntry`.
- `update_goal_progress()` z tym samym `source_type/source_id` jest idempotentny.
- `update_goal_progress()` przy target wywoluje `complete_goal()`.
- `complete_goal()` nie tworzy `XpEvent`.
- `complete_goal()` tworzy dokladnie jeden `JournalEntry` i jest idempotentny.
- `complete_goal()` odpala evaluator achievementow.
- `create_challenge()` nie tworzy check-inow ani XP.
- `toggle_challenge_check_in()` tworzy i usuwa check-in przed completion.
- `toggle_challenge_check_in()` przelicza `progress_value` zgodnie z doprecyzowana semantyka.
- `toggle_challenge_check_in()` dla completed/failed/archived nie cofa stanu.
- `complete_challenge()` tworzy XP per `ChallengeReward` tylko raz.
- `complete_challenge()` ustawia `xp_awarded_at`, tworzy journal i odpala achievements.
- `fail_challenge()` nie tworzy XP.
- `unlock_achievement()` tworzy unlock tylko raz, tworzy jeden journal i nie tworzy XP.
- `evaluate_achievements()` pokrywa `total_xp`, `skill_xp`, `skill_level`, `quest_count`, `habit_streak`, `challenge_completed`, `goal_completed`, `journal_streak` i `manual` skip.

### API

- `GET/POST/PATCH/complete/progress/toggle/fail/unlock/evaluate` zwracaja `snake_case`.
- Invalid JSON daje `400` z `error.code = validation_error`.
- Nieistniejacy rekord daje `404`.
- Konflikt domenowy daje `409`.
- Endpointy completion nie duplikuja XP ani journala przy ponowieniu requestu.
- Dashboard API po seedzie zwraca realny `active_challenge`, `achievements` i goals selector po ich dodaniu.

### Regresja

- `python manage.py test rpg` obejmuje nowe modele i serwisy.
- `python manage.py test dashboard` potwierdza brak regresji w dashboard context.
- `python manage.py test planner` potwierdza brak regresji w calendar API.
- `python manage.py test` przechodzi po migracjach.
- `python manage.py makemigrations --check --dry-run` nie wykrywa brakujacych migracji po implementacji.
