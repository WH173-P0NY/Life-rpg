# Analiza specu RPG Progression API/React

Data analizy: 2026-06-10.

Analizowany spec: `docs/rpg-progression-api-react-spec.md`.
Zakres porownania: aktualne Django API, `dashboard/`, `rpg/`, `planner/` oraz `frontend/src`.

## 1. Werdykt gotowosci API/React

**Werdykt: niegotowe do implementacji UI bez dodatkowego backendu.**

Repo ma gotowy fundament pod integracje: standardowe Django JSON views, CSRF przez cookie/header, React shell, hash-route w sidebarze, dashboard API, questy, habity, journal i calendar. Nie ma jednak domeny progression opisanej w specu:

- brak modeli `Goal`, `GoalSkill`, `Challenge`, `ChallengeReward`, `Achievement`, `AchievementUnlock`,
- brak endpointow `/api/goals/`, `/api/challenges/`, `/api/achievements/`,
- `GET /api/dashboard/` nadal zwraca `active_challenge: null` i `achievements: []`,
- `frontend/src/api/progression.ts` i `frontend/src/types/progression.ts` nie istnieja,
- `#goals` jest placeholderem, a `#achievements` pokazuje tylko liste z `dashboard.achievements`,
- `ChallengePanel`, `ActiveChallenge` i mapper dashboardu pracuja na legacy ksztalcie `name/day/total/progress/reward`, nie na finalnym DTO ze specu.

API i React sa wiec gotowe architektonicznie jako miejsce na modul, ale kontrakt progression nie jest jeszcze zaimplementowany.

## 2. Walidacja zalozen specu

Zalozenia trafne:

- `rpg` istnieje i zawiera questy, habity, milestone habitu, journal oraz identity.
- `planner` istnieje i udostepnia Calendar API przez `/api/calendar/events/` oraz `/api/calendar/events/<id>/`.
- Routing glowny podpina `rpg.urls` i `planner.urls` pod `/api/`, a `dashboard.urls` pod root.
- Obecne endpointy RPG to `/api/quests/<id>/complete/`, `/api/quests/<id>/progress/`, `/api/habits/<id>/toggle/`, `/api/journal/`, `/api/journal/<id>/`.
- Dashboard API jest pod `/api/dashboard/`, manual activity pod `/api/activities/manual/`, CSRF helper pod `/api/csrf/`.
- `Sidebar` ma widoki `goals`, `achievements`, `journal`, `calendar`.
- `App.tsx` uzywa `activeView` i hash URL.
- `Journal` jest realnym widokiem React + API, z `fetchJournalOverview`, create i update.
- `Calendar` jest realnym widokiem React + API, z listowaniem, tworzeniem i usuwaniem eventow.
- `QuestsPanel` i `HabitsPanel` maja wzorzec: pending state, mutacja API, potem refresh dashboardu.
- `localStorage` w React jest obecnie domenowo bezpieczny, bo przechowuje theme, nie dane RPG.

Zalozenia wymagajace korekty albo doprecyzowania:

- Calendar frontend nie obsluguje jeszcze PATCH, chociaz backendowy endpoint wspiera `PATCH` i `DELETE`.
- `JournalEntryType` ma `challenge` i `achievement`, ale nie ma typu `goal`; `source_type` jest jednak wolnym tekstem.
- Spec ma niespojnosc source type: w przykladzie goal completion pojawia sie `source_type: "goal"`, a w sekcji Journal integration `goal_completion`. Trzeba wybrac jeden kanoniczny zapis, bo `JournalEntry` ma unikalnosc po `(source_type, source_id)`.
- Obecny format bledow RPG to `{"error": {"code", "message"}}`; spec oczekuje opcjonalnego `fields`. Manual activity uzywa jeszcze innego formatu: `{"errors": ...}`.

## 3. Docelowy kontrakt JSON i roznice wzgledem kodu

Docelowo backend powinien nadal zwracac `snake_case`, a React powinien mapowac na `camelCase`.

Najwazniejsze roznice:

| Obszar | Docelowy kontrakt ze specu | Aktualny kod |
|---|---|---|
| Goals | `/api/goals/`, `/api/goals/<id>/`, `/complete/`, `/archive/`; `goal`, `stats`, `linked_skills`, `progress_percent` | brak modeli, serwisow, URL-i, API clienta i widoku |
| Challenges | `/api/challenges/`, `/progress/`, `/complete/`; `current_value`, `target_value`, `reward_skills`, `xp_events`, `dashboard_refresh_required` | brak modeli i endpointow; dashboard zawsze `active_challenge: null` |
| Dashboard challenge | `active_challenge` z `title`, `status`, `start_date`, `end_date`, `elapsed_days`, `total_days`, `current_value`, `target_value`, `target_unit`, `reward_xp`, `reward_skills` | React oczekuje legacy `name`, `day`, `total`, `progress`, `reward`, `xp_reward` |
| Achievements API | `/api/achievements/`, `/unlock/`, `/evaluate/`; katalog z `unlocked`, `unlock`, `progress`, `stats` | brak modeli i endpointow |
| Dashboard achievements | ostatnie unlocki: `id`, `achievement_id`, `title`, `description`, `rarity`, `unlocked_at`, `source_type`, `source_id` | backend zwraca `[]`; React typ ma tylko `id`, `title`, `rarity`, `unlockedAtLabel` |
| React progression | `types/progression.ts`, `api/progression.ts`, `GoalsView`, `AchievementsView` | pliki i komponenty nie istnieja |
| Bledy | `error.code`, `error.message`, opcjonalne `error.fields` | RPG ma `code/message`, bez `fields`; dashboard form API ma `errors` |

Kontrakt dashboardu trzeba migrowac atomowo po stronie backendu i Reacta. Najbardziej kruche miejsca to `frontend/src/types/dashboard.ts` oraz `frontend/src/api/dashboard.ts`, bo obecnie `ActiveChallenge` jest legacy i achievement ID jest generowane z tytulu oraz indeksu.

## 4. Ryzyka localStorage, mock i stabilnych ID

- `mockDashboard` zawiera fake `activeChallenge` i fake achievementy. Przy obecnym fallbacku kazdy blad `/api/dashboard/` pokazuje mock jako realnie wygladajacy stan. Dla progression mutacje musza byc w fallbacku disabled, a widoki powinny jasno traktowac mock jako preview, nie source of truth.
- Nie wolno przenosic goalow, challenge progressu ani unlockow do `localStorage`. Aktualnie React zapisuje tylko theme, co jest OK.
- Legacy dashboard template i theme JS uzywaja `localStorage` dla theme/panel state; to nie jest domenowy stan RPG, ale nie powinno byc kopiowane do nowych widokow progression.
- `frontend/src/api/dashboard.ts` generuje `activeChallenge.id` z nazwy, jesli backend nie poda ID. To jest niestabilne przy zmianie tytulu.
- Dashboard achievementy maja ID `${toId(title)}-${index}`. To jest niestabilne przy sortowaniu, duplikatach, zmianie tytulu albo nowym unlocku. Docelowo uzywac backendowego `unlock.id` albo `achievement.id` zgodnie z typem listy.
- Mockowe string ID (`"no-sugar"`, `"early-riser"`) roznia sie od backendowych numerycznych ID mapowanych do stringow. Po dodaniu kontraktu finalnego trzeba zaktualizowac mock, zeby nie maskowal bledow typow.
- `JournalEntry` ma unikalny `(source_type, source_id)`. Niespojny `source_type` dla goal/challenge/achievement stworzy duplikaty albo zablokuje idempotencje.

## 5. Plan implementacji API i React

Backend:

1. Dodac modele i migracje w `rpg`: `Goal`, `GoalSkill`, `Challenge`, `ChallengeReward`, `Achievement`, `AchievementUnlock`.
2. Dodac admin z wysokosygnałowymi `list_display`, filtrami i search.
3. Dodac jawne serwisy w `rpg/services.py`: list/create/update/complete/archive goal, list/create/update/progress/complete challenge, unlock/evaluate achievement.
4. Przy challenge completion tworzyc `XpEvent` przez `Skill.add_xp`, idempotentnie po `xp_awarded_at` i pod kontrola transakcji.
5. Ustalic kanoniczne `source_type` dla automatycznych journal entries, np. `goal_completion`, `challenge_completion`, `achievement_unlock`.
6. Dodac widoki JSON i URL-e w `rpg/views.py` oraz `rpg/urls.py`, bez DRF.
7. Ujednolic helper bledow dla nowych endpointow do `error.code/message/fields`.
8. Rozszerzyc `dashboard/services.py`: realny `active_challenge`, ostatnie achievement unlocki, licznik journal `achievements_unlocked`.
9. Rozszerzyc `seed_life_rpg` o goal, challenge i achievementy, bez tworzenia completion/unlockow/XP poza jawnie oczekiwanymi danymi seed.

React:

1. Dodac `frontend/src/types/progression.ts` z typami `ProgressionGoal`, `ProgressionChallenge`, `ProgressionAchievement` i response/mutation types.
2. Dodac `frontend/src/api/progression.ts` z Raw DTO w `snake_case`, mapperami do `camelCase`, CSRF i funkcjami ze specu.
3. Zmienic `frontend/src/types/dashboard.ts` na finalny `ActiveChallenge` i dashboardowy `AchievementUnlock`.
4. Zmienic `frontend/src/api/dashboard.ts`, usuwajac legacy mapper `name/day/total/progress/reward` oraz generowane ID dla achievementow.
5. Dodac `GoalsView` z lista, filtrami, formularzem, edycja progressu, complete/archive i pending state.
6. Dodac albo rozbudowac challenge UI w `GoalsView`; `ChallengePanel` na dashboardzie ma tylko czytac finalny DTO i obslugiwac `null`.
7. Dodac `AchievementsView` z katalogiem, filtrami, progress locked achievementow, manual unlock dla `manual` i evaluate.
8. Podmienic case `goals` i `achievements` w `App.tsx` na nowe widoki, przekazujac `isApiReady` i `refreshDashboard`.
9. Zaktualizowac `ChartsPanel` i `mockDashboard` do finalnego dashboardowego kontraktu.
10. Nie dodawac domenowego `localStorage`; przy fallbacku API blokowac mutacje.

## 6. Testy i komendy weryfikacyjne

Backend testy do dodania:

- modele: walidacja pustych tytulow, dodatnie target/reward/progress, unikalnosc rewardow i unlockow,
- Goals API: create/update/complete/archive, completion bez `XpEvent`, idempotentny journal,
- Challenges API: create/update/progress bez XP, complete z `XpEvent`, podwojne complete bez duplikacji XP,
- Achievements API: lista katalogu, manual unlock idempotentny, evaluate, unlock bez XP,
- dashboard: realny `active_challenge`, ostatnie unlocki achievementow, empty state,
- seed: idempotentne goal/challenge/achievement bez completion/unlock side effectow,
- regresja obecnych quest/habit/journal/calendar endpointow.

Frontend testy/sprawdzenia:

- `GoalsView` loading/empty/error, disabled fallback, refresh po mutacji,
- `AchievementsView` loading/empty/error, unlock/evaluate refresh,
- `ChallengePanel` obsluguje `null` i finalny DTO,
- dashboard mapper nie generuje domenowych ID z tytulu,
- brak `localStorage` dla goals/challenges/achievements.

Komendy weryfikacyjne po implementacji:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py test rpg dashboard planner
.venv/bin/python manage.py test
cd frontend
npm run typecheck
npm run build
```

Komendy smoke dla API po migracji i seedzie:

```bash
.venv/bin/python manage.py seed_life_rpg
.venv/bin/python manage.py runserver
curl -s http://127.0.0.1:8000/api/dashboard/ | python -m json.tool
curl -s http://127.0.0.1:8000/api/goals/ | python -m json.tool
curl -s http://127.0.0.1:8000/api/challenges/ | python -m json.tool
curl -s http://127.0.0.1:8000/api/achievements/ | python -m json.tool
```
