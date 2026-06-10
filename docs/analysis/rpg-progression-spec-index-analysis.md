# Analiza `docs/rpg-progression-spec-index.md`

## 1. Werdykt

**Werdykt: warunkowo gotowe jako indeks planistyczny, ale nie jako bezposrednia bramka implementacji.**

`docs/rpg-progression-spec-index.md` dobrze rozpoznaje, ze repo nie jest juz w stanie opisanym przez stary `docs/rpg-modules-implementation-index.md`. Indeks poprawnie wskazuje nowy zakres: `Goals`, `Challenges`, `Achievements`, realne `active_challenge`, realne `achievements` i automatyczne wpisy journala dla nowych zdarzen.

Blokerem startu kodowania jest jednak brak jednego finalnego kontraktu miedzy trzema nowymi specami:

- `docs/rpg-progression-domain-spec.md`,
- `docs/rpg-progression-api-react-spec.md`,
- `docs/rpg-progression-integration-qa-spec.md`.

Najwieksze rozjazdy dotycza nazw i semantyki modeli `Goal`, `Challenge`, `Achievement`, endpointow progress/check-in oraz `source_type` journala. Indeks powinien byc traktowany jako mapa, ale przed implementacja trzeba zamknac decyzje kontraktowe.

## 2. Czy "Aktualny punkt startowy" zgadza sie z realnym repo

**Tak, zasadniczo sie zgadza.** Potwierdzenia w repo:

- Aplikacja `rpg` jest aktywna w `config/settings.py:60-73`.
- `planner` jest aktywny w `config/settings.py:60-73`, a API Calendar jest pod `/api/calendar/events/` przez `planner/urls.py:8-14`.
- PostgreSQL jest jedyna konfiguracja bazy w `config/settings.py:105-151`; `requirements.txt:1` wymusza `Django==6.0.6`.
- Istnieja modele questow: `Quest`, `QuestReward`, `QuestCompletion` w `rpg/models.py:22`, `rpg/models.py:105`, `rpg/models.py:139`.
- Istnieja habity i milestone streakow: `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock` w `rpg/models.py:189`, `rpg/models.py:231`, `rpg/models.py:267`, `rpg/models.py:333`, `rpg/models.py:367`.
- Istnieje `JournalEntry` z idempotencja po `(source_type, source_id)` w `rpg/models.py:419-455`.
- Istnieje `CharacterIdentity` w `rpg/models.py:488`.
- Dashboard bierze realne questy, habity i journal przez `build_daily_quest_rows`, `build_habit_rows`, `build_journal_entry_rows` w `dashboard/services.py:11-15` i uzywa ich w `dashboard/services.py:322-329`.
- Dashboard nadal zwraca `active_challenge: None` i `achievements: []` w `dashboard/services.py:384-390`.
- React ma sidebar z widokami `goals`, `achievements`, `calendar` w `frontend/src/components/Sidebar.tsx:18-28`.
- Widok `Goals` jest placeholderem z `ChallengePanel` i pustym panelem w `frontend/src/App.tsx:160-168`.
- Widok `Achievements` jest tylko lista z `dashboard.achievements` w `frontend/src/App.tsx:170-186`.

Korekta/niescislosc: decyzja z indeksu, ze seed nie tworzy XP, wymaga doprecyzowania. Aktualny `seed_life_rpg` tworzy sample `ActivityEntry` przez `create_activity_entry(...)` w `activities/management/commands/seed_life_rpg.py:47` i `activities/management/commands/seed_life_rpg.py:372-395`, a `create_activity_entry(...)` tworzy `XpEvent` w `activities/services.py:31-38`. Dla nowego modulu sensowna interpretacja brzmi: seed nie powinien tworzyc historii wykonania, unlockow ani XP dla `Goal`/`Challenge`/`Achievement`, ale obecny seed MVP juz tworzy XP z przykladowych aktywnosci.

## 3. Mapa dokumentow i zaleznosci

**Nowy indeks progression**

- `docs/rpg-progression-spec-index.md` - mapa modulu `Goals, Challenges, Achievements`; decyzje przekrojowe, kolejnosc prac i minimalna bramka. Wskazuje trzy dokumenty wykonawcze w `docs/rpg-progression-spec-index.md:46-87`.
- `docs/rpg-progression-domain-spec.md` - backend domeny: choices, modele, walidacje, serwisy, XP przez `skills.XpEvent`, Journal i dashboard selectors. Najbardziej szczegolowy dokument backendowy.
- `docs/rpg-progression-api-react-spec.md` - kontrakty JSON, mappery React `snake_case` -> `camelCase`, widoki `GoalsView` i `AchievementsView`, refresh po mutacjach.
- `docs/rpg-progression-integration-qa-spec.md` - migracje, seed, test matrix, smoke testy, rollback i edge cases.

**Stare specy modulow RPG**

- `docs/rpg-modules-implementation-index.md` - historyczny indeks modulow 0-8. Jego sekcja "Aktualny stan repo" jest juz nieaktualna, bo zaklada brak aplikacji `rpg` i brak modeli RPG w `docs/rpg-modules-implementation-index.md:13-33`.
- `docs/rpg-modules-0-2-backend-core-spec.md` - fundament `rpg`, questy, habity, streaki, milestone XP. Ten zakres jest w duzej mierze zaimplementowany.
- `docs/rpg-modules-3-4-dashboard-react-spec.md` - dashboard API i React live dla questow/habitow. Repo odzwierciedla ten etap: realne questy/habity, mutacje API i brak domenowego localStorage dla questow/habitow.
- `docs/rpg-modules-5-7-progression-spec.md` - stary plan Challenge/Achievement/Journal. Journal zostal juz w duzej czesci zaimplementowany, ale Challenge i Achievement nie.

**Zaleznosci kodowe dla nowego modulu**

1. `rpg/choices.py` i `rpg/models.py` - nowe choices oraz modele. Obecnie `JournalEntryType` ma `CHALLENGE` i `ACHIEVEMENT`, ale nie ma `GOAL` w `rpg/choices.py:43-50`.
2. `skills/models.py` - `Skill.add_xp(...)` i `XpEvent` pozostaja ledgerem XP w `skills/models.py:94-114` i `skills/models.py:117-153`.
3. `rpg/services.py` - obecny wzorzec transakcji, idempotencji i best-effort journal jest juz dostepny w `complete_quest(...)`, `toggle_habit(...)`, `create_system_journal_entry(...)` i helperach journala.
4. `rpg/views.py` i `rpg/urls.py` - obecnie istnieja tylko quest/habit/journal endpointy w `rpg/urls.py:8-34`.
5. `dashboard/services.py` i `dashboard/views.py` - dashboard musi zamienic placeholdery `active_challenge` i `achievements` na realne selektory.
6. `frontend/src/api/dashboard.ts`, przyszle `frontend/src/api/progression.ts`, `frontend/src/types/progression.ts`, `frontend/src/App.tsx` - frontend musi dostac osobny klient progression i realne widoki, bez domenowego `localStorage`.

## 4. Niespojnosci wzgledem starszych specow `docs/rpg-modules-*.md`

1. **Stary indeks ma nieaktualny punkt startowy.** `docs/rpg-modules-implementation-index.md:13-33` mowi, ze repo jest przed modulem 0 i nie ma `rpg`, questow, habitow ani journala. Realne repo ma te elementy. Nowy indeks slusznie to nadpisuje.

2. **Nowy zakres dodaje `Goals`, ktorych nie ma w starym pakiecie 5-7.** Stary `docs/rpg-modules-5-7-progression-spec.md:5-9` obejmuje `Challenge`, `Achievementy`, `Journal`; nowy indeks obejmuje `Goals`, `Challenges`, `Achievements` w `docs/rpg-progression-spec-index.md:5-9`. To jest rozszerzenie zakresu, nie tylko kontynuacja starego modulu 5.

3. **Kolejnosc wdrozenia zmienila sie po faktycznej implementacji journala.** Stary pakiet rekomendowal wewnetrznie: `JournalEntry`, potem `Challenge`, potem `Achievement` w `docs/rpg-modules-5-7-progression-spec.md:58-65` i `docs/rpg-modules-5-7-progression-spec.md:1169-1184`. Nowy indeks zaklada, ze journal juz istnieje, i zaczyna od modeli `Goal`, `Challenge`, `Achievement` w `docs/rpg-progression-spec-index.md:106-139`. To jest uzasadnione stanem repo, ale wymaga jawnego uznania starego planu 5-7 za historyczny.

4. **Model Challenge jest niespojny miedzy starym planem i nowa domena.** Stary plan oraz nowe API/QA uzywaja `start_date`, `end_date`, `current_value` i endpointu `POST /api/challenges/<id>/progress/` (`docs/rpg-modules-5-7-progression-spec.md:181-201`, `docs/rpg-progression-api-react-spec.md:115-154`, `docs/rpg-progression-integration-qa-spec.md:168-220`). Nowy domain spec proponuje `starts_on`, `ends_on`, `progress_value`, `cadence` oraz `ChallengeCheckIn` (`docs/rpg-progression-domain-spec.md:313-424`). Indeks dodatkowo umieszcza `ChallengeCheckIn` w liscie modeli w `docs/rpg-progression-spec-index.md:108-116`. To musi zostac rozstrzygniete przed migracja.

5. **Achievement ma dwa konkurencyjne kontrakty.** Stary plan i API/QA preferuja `trigger_type` + `trigger_config` JSON (`docs/rpg-modules-5-7-progression-spec.md:564-681`, `docs/rpg-progression-api-react-spec.md:172-244`, `docs/rpg-progression-integration-qa-spec.md:246-340`). Nowy domain spec proponuje explicit fields: `code`, `trigger`, `requirement_value`, FK do `skill/habit/goal/challenge` w `docs/rpg-progression-domain-spec.md:425-496`. To zmienia migracje, admin, seed i evaluator.

6. **Seed policy zostala zaostrzona.** Stary `docs/rpg-modules-5-7-progression-spec.md:796-808` dopuszczal 1-2 demonstracyjne unlocki achievementow. Nowy indeks zabrania seedowania historii wykonania, unlockow i XP w `docs/rpg-progression-spec-index.md:102-103`, a QA powtarza to w `docs/rpg-progression-integration-qa-spec.md:54-59` oraz `docs/rpg-progression-integration-qa-spec.md:1081-1090`.

7. **Dashboard achievements zmienil znaczenie.** Stary dashboard spec dopuszczal odblokowane i kilka zablokowanych achievementow dla kontekstu w `docs/rpg-modules-3-4-dashboard-react-spec.md:419-423`. Nowe API/QA rozdzielaja dashboard jako ostatnie unlocki od pelnego katalogu w `GET /api/achievements/` (`docs/rpg-progression-api-react-spec.md:909-930`, `docs/rpg-progression-integration-qa-spec.md:577-602`). To jest dobra zmiana, ale musi byc konsekwentna w React.

## 5. Ryzyka kolejnosci wdrozenia

1. **Migracje przed kontraktem moga utrwalic zle nazwy pol.** Najbardziej ryzykowne sa `Challenge` i `Achievement`: `current_value` vs `progress_value`, `start_date/end_date` vs `starts_on/ends_on`, `trigger_config` vs jawne FK.

2. **Dashboard lub React przed domena stworza kolejna warstwe aliasow.** Obecny frontendowy typ `ActiveChallenge` nadal ma legacy ksztalt `day`, `totalDays`, `rewardLabel` w `frontend/src/types/dashboard.ts:148-155`, a mapper czyta legacy pola `name/day/total/progress/reward` w `frontend/src/api/dashboard.ts:518-527`. Implementacja dashboardu musi najpierw ustalic finalny DTO.

3. **Goal journal moze rozjechac idempotencje.** Obecne `JournalEntryType` nie ma `GOAL` (`rpg/choices.py:43-50`). Nowe specy uzywaja roznych `source_type`: `goal_completion`, `goal_completed`, a przykladowe response API pokazuje nawet `source_type="goal"` (`docs/rpg-progression-domain-spec.md:782-799`, `docs/rpg-progression-api-react-spec.md:448-453`, `docs/rpg-progression-integration-qa-spec.md:482-487`). Idempotencja zalezy od dokladnej wartosci `source_type`.

4. **Achievement evaluator ma zaleznosci poza `rpg`.** Trigger `skill_level` po XP z aktywnosci wymaga integracji z `activities/services.py:create_activity_entry(...)`, ktory obecnie tylko tworzy XP (`activities/services.py:31-38`). QA slusznie ostrzega, aby nie importowac `rpg` w `skills.models`, tylko odpalac ewaluacje z serwisow tworzacych XP.

5. **`XpEvent` nie ma neutralnego source_id.** `skills.XpEvent` ma `source_type`, `note` i opcjonalny FK tylko do `ActivityEntry` (`skills/models.py:117-133`). Questy juz opieraja trop audytowy na `note`, a challenge bedzie musial uzyc `Challenge.xp_awarded_at` jako glownej bramki idempotencji.

6. **Seed moze przypadkiem stworzyc realna historie.** Obecny seed juz tworzy sample activity XP. Dla nowego modulu trzeba pilnowac, zeby `_seed_goals`, `_seed_challenges`, `_seed_achievements` nie tworzyly `GoalProgressEntry`, `ChallengeCheckIn`, `AchievementUnlock`, `XpEvent(source_type="challenge")` ani auto journal completion.

7. **Testy moga zostac dodane za pozno.** Istniejace testy celowo potwierdzaja obecny placeholder `active_challenge is None` i `achievements == []` w `dashboard/tests.py:235-242`. Po wdrozeniu modeli te testy musza zostac zastapione testami realnych danych, inaczej beda blokowac integracje.

## 6. Rekomendowana bramka startu

**Rekomendacja: nie zaczynac implementacji produkcyjnej, dopoki nie przejdzie krotka bramka kontraktowa.**

Minimalna bramka startu:

1. **Contract lock dla modeli i API**
   - Wybrac jeden finalny wariant `Challenge`: albo prosty manual-progress z `current_value/start_date/end_date`, albo domenowy `ChallengeCheckIn` z `progress_value/starts_on/ends_on`.
   - Wybrac jeden finalny wariant `Achievement`: `trigger_type + trigger_config` albo jawne pola/FK z domain spec.
   - Wybrac finalne pola `Goal`: `target_date/archived_at` czy `starts_on/due_on/paused/life_area`.

2. **Contract lock dla journala**
   - Ustalic stale `source_type`: rekomendowane `goal_completed`, `challenge_completed`, `challenge_failed`, `achievement_unlock`, bo sa czytelne i zgodne z QA.
   - Dodac albo odlozyc `JournalEntryType.GOAL`; jezeli odlozyc, to jawnie uzyc `entry_type="system"` dla goal completion w MVP.

3. **Start implementation gate**
   - `docs/rpg-progression-domain-spec.md` jest uznany za backend source of truth albo zostaje dopasowany do API/QA przed kodowaniem.
   - `docs/rpg-progression-api-react-spec.md` i `docs/rpg-progression-integration-qa-spec.md` maja te same nazwy pol, statusow i endpointow co wybrany kontrakt.
   - Aktualny stan repo pozostaje bez nowych modeli `Goal/Challenge/Achievement`, a `GET /api/dashboard/` nadal zwraca `active_challenge: null` i `achievements: []` do czasu migracji.

Po tej bramce rekomendowana kolejnosc prac:

1. Choices i modele w `rpg/choices.py` oraz `rpg/models.py`.
2. Migracja `rpg.0005_...` bez modyfikowania migracji historycznych.
3. Admin i seed bez historii wykonania/unlockow/XP dla nowego modulu.
4. Serwisy domenowe z idempotencja i best-effort journal.
5. Endpointy JSON w `rpg/views.py` i `rpg/urls.py`.
6. Dashboard selectors w `dashboard/services.py`.
7. React `frontend/src/api/progression.ts`, typy i widoki `GoalsView`/`AchievementsView`.
8. Pelna bramka: `.venv/bin/python manage.py makemigrations --check --dry-run`, `.venv/bin/python manage.py check`, `.venv/bin/python manage.py test`, `cd frontend && npm run typecheck`, `cd frontend && npm run build`.
