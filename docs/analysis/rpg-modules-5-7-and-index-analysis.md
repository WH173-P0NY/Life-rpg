# Analiza modulow RPG 5-7 oraz indeksu wdrozenia

## Zakres analizy

Analiza traktuje nastepujace dokumenty jako jeden plan etapowy:

- `docs/rpg-modules-implementation-index.md`
- `docs/rpg-modules-5-7-progression-spec.md`
- `docs/phase-2-rpg-mechanics-spec.md`

Kontekst zaleznosci zostal sprawdzony wzgledem:

- `docs/rpg-modules-0-2-backend-core-spec.md`
- `docs/rpg-modules-3-4-dashboard-react-spec.md`
- `docs/life-rpg-tracker-mvp-spec.md`

## 1. Ocena spojnosci indeksu i Phase 2

Ocena ogolna: dokumenty sa spojne kierunkowo. `docs/phase-2-rpg-mechanics-spec.md` definiuje produktowy zakres etapu 2, a `docs/rpg-modules-implementation-index.md` poprawnie rozbija go na pakiety wdrozeniowe 0-8. `docs/rpg-modules-5-7-progression-spec.md` doprecyzowuje modele, endpointy, serwisy, testy i akceptacje dla warstwy progression bez zmiany podstawowych decyzji Phase 2.

Najwazniejsze spojne decyzje:

- jedna aplikacja Django `rpg` dla questow, habitow, milestone, challenge, achievementow i journala;
- XP zawsze przez `skills.XpEvent`;
- `Skill` nie dostaje pola `xp`;
- achievement nie przyznaje XP;
- habit check-in nie przyznaje XP;
- backend JSON API uzywa `snake_case`;
- React mapuje dane na `camelCase` dopiero w `frontend/src/api/dashboard.ts` i typach frontendu;
- brak DRF i Celery;
- dashboard ma przejsc z placeholderow/localStorage na realne dane z PostgreSQL.

Glowne niespojnosci lub miejsca do doprecyzowania:

- `docs/rpg-modules-implementation-index.md` opisuje kolejnosc modulowa jako 5 Challenge, 6 Achievementy, 7 Journal, ale `docs/rpg-modules-5-7-progression-spec.md` rekomenduje wdrozenie wewnatrz pakietu w kolejnosci: modul 7 Journal, modul 5 Challenge, modul 6 Achievementy, integracje, React. To nie musi byc konflikt, ale powinno zostac nazwane jako "kolejnosc implementacyjna wewnatrz pakietu 5-7", zeby agent nie uznal numeracji za twardy porzadek prac.
- Kontrakt `active_challenge` nie jest jeszcze jednolity miedzy `docs/rpg-modules-3-4-dashboard-react-spec.md` i `docs/rpg-modules-5-7-progression-spec.md`. Spec 3-4 pokazuje ksztalt frontendowo-przejsciowy z polami typu `name`, `day`, `total`, `progress`, `reward`, `xp_reward`, a spec 5-7 pokazuje backendowy kontrakt z `title`, `current_value`, `target_value`, `target_unit`, `progress_percent`, `reward_title`, `reward_xp`, `status`. Przed modulem 5 trzeba wybrac finalny backend DTO.
- `Achievement.trigger_config` w `docs/rpg-modules-5-7-progression-spec.md` ma przyklady z kluczami `streakDays` i `questCount`, mimo ze backendowe API i serwisy maja trzymac `snake_case`. Dla spojnosc backendu lepsze sa `streak_days` i `quest_count`, a mapowanie do `camelCase` zostaje tylko w React.
- `docs/phase-2-rpg-mechanics-spec.md` opisuje `Challenge` bez `completed_at` i `xp_awarded_at`, a spec 5-7 dodaje te pola. To jest dobra implementacyjna korekta pod idempotencje XP, ale warto traktowac spec 5-7 jako precyzyjniejszy kontrakt modelu.
- `JournalEntry` w Phase 2 i 5-7 uzywa `content`, natomiast spec 3-4 pokazuje historyczny/tymczasowy ksztalt dashboardu z `body` dla journala. Modul 8 powinien usunac aliasy i pozostawic jednoznaczny kontrakt.

Wniosek: plan etapowy jest wystarczajaco spojny do implementacji, ale wejscie w moduly 5-7 powinno byc poprzedzone krotka decyzja kontraktowa dla `active_challenge`, `Achievement.trigger_config` i kolejnosci prac wewnatrz pakietu.

## 2. Zaleznosci modulow 5-7 od 0-4

### Zaleznosci od modulu 0

Moduly 5-7 zakladaja, ze istnieje fundament z `docs/rpg-modules-0-2-backend-core-spec.md`:

- aplikacja Django `rpg` w `INSTALLED_APPS`;
- `rpg/models.py`, `rpg/services.py`, `rpg/views.py`, `rpg/urls.py`, `rpg/admin.py`;
- routing `path("api/", include("rpg.urls"))` w `config/urls.py`;
- wspolne `TextChoices` dla statusow technicznych;
- test smoke aplikacji `rpg`;
- brak DRF/Celery.

Bez modulu 0 nie ma gdzie bezpiecznie dodac modeli `Challenge`, `Achievement` i `JournalEntry`.

### Zaleznosci od modulu 1

Modul 6 i modul 7 zaleza od questow:

- `rpg.Quest`, `rpg.QuestReward`, `rpg.QuestCompletion`;
- serwisy `complete_quest(...)` i `update_quest_progress(...)`;
- idempotentne tworzenie `skills.XpEvent` z `source_type="quest"`;
- endpointy `POST /api/quests/<id>/complete/` i `POST /api/quests/<id>/progress/`;
- realne `QuestCompletion` potrzebne dla triggera achievementu `quest_count`;
- zdarzenie quest completion potrzebne dla automatycznych wpisow `JournalEntry`.

Jesli modul 1 nie jest domkniety, modul 7 moze jeszcze obslugiwac reczny journal, ale nie powinien deklarowac pelnej integracji z quest completion.

### Zaleznosci od modulu 2

Modul 6 i modul 7 zaleza od habitow i milestone:

- `rpg.Habit`, `rpg.HabitCheckIn`;
- `rpg.HabitMilestone`, `rpg.HabitMilestoneReward`, `rpg.HabitMilestoneUnlock`;
- `calculate_habit_streak(...)`;
- `toggle_habit(...)`;
- `unlock_due_habit_milestones(...)`;
- idempotentne XP z `source_type="habit_milestone"`;
- realny streak wymagany dla achievement triggera `habit_streak`;
- `HabitMilestoneUnlock` wymagany dla automatycznego journala.

Bez modulu 2 achievementy moga zaczac od `manual`, `skill_level` i pozniej `challenge_completed`, ale `habit_streak` bedzie niepelny.

### Zaleznosci od modulu 3

Moduly 5-7 powinny wejsc dopiero po tym, jak `GET /api/dashboard/` ma realny kontrakt:

- `daily_quests` i `habits` pochodza z modeli `rpg`, nie z placeholderow;
- `daily_quests[].id` i `habits[].id` sa realnymi ID z bazy;
- `active_challenge` jest jawnie nullable do czasu modulu 5;
- `achievements` i `journal_entries` sa puste albo realne, ale nie fikcyjne;
- serializacja w `dashboard/views.py` nie wymaga od Reacta generowania ID;
- zakresy `today`, `week`, `month`, `custom` nadal dzialaja.

To jest wazne, bo moduly 5-7 dopinaja kolejne sekcje do tego samego dashboard API.

### Zaleznosci od modulu 4

React powinien miec juz wzorzec live API:

- `frontend/src/api/dashboard.ts` rozdziela backend DTO `snake_case` od frontendowych typow `camelCase`;
- `frontend/src/types/dashboard.ts` uzywa realnych ID;
- `QuestsPanel` i `HabitsPanel` nie trzymaja stanu domenowego w `localStorage`;
- CSRF i `requestJson` sa gotowe dla POST-ow;
- `App.tsx` umie odswiezyc dashboard po mutacji;
- UI traktuje `activeChallenge` jako `ActiveChallenge | null`.

Bez modulu 4 latwo powtorzyc stary blad: panel challenge, achievements albo journal zacznie dzialac jako lokalny mock zamiast jako widok danych z backendu.

## 3. Ryzyka modeli challenge, achievement i journal

### Challenge

- Idempotencja XP zalezy od `xp_awarded_at` na `rpg.Challenge` oraz od serwisu `award_challenge_xp(...)`. Trzeba zablokowac podwojne klikniecie `POST /api/challenges/<id>/complete/` przez transakcje i/lub `select_for_update()`.
- `ChallengeReward` moze zostac zmieniony w adminie po przyznaniu XP. Trzeba zdecydowac, czy po `xp_awarded_at` rewardy sa praktycznie zamrozone, czy pozniejsze zmiany wymagaja recznej korekty `XpEvent`.
- Dashboard pokazuje jeden aktywny challenge, ale model dopuszcza wiele rekordow `status=active`. Serwis `get_active_challenge()` musi miec deterministyczne sortowanie: `status=active`, najblizsze `end_date`, najnowszy `created_at`.
- `update_challenge_progress(...)` przyjmuje wartosc bezwzgledna i obcina do `0..target_value`, ale spec zostawia decyzje, czy `current_value >= target_value` automatycznie konczy challenge. To musi byc ustalone przed UI.
- Brak rewardow XP jest dozwolony. Endpoint complete musi obsluzyc pusta liste `xp_events` bez bledu i bez sugerowania, ze XP zawsze istnieje.
- `XpEvent` nie ma neutralnego FK do challenge. Audyt opiera sie na `source_type="challenge"`, `note` i polach modelu domenowego. To wystarcza dla MVP, ale utrudni przyszle cofanie lub szczegolowy audyt.

### Achievement

- `AchievementUnlock` jest single-user i powinien byc unikalny per `achievement`. To zgodne z MVP, ale wymaga twardego constraintu i idempotentnego serwisu `unlock_achievement(...)`.
- `trigger_config` moze odwolywac sie do skilli, habitow, questow lub challenge po nazwie albo po `id`. Nazwy sa edytowalne w adminie, wiec stabilniejsze jest `id` z opcjonalnym fallbackiem po nazwie dla seedow.
- Trigger `skill_level` wymaga wywolania po kazdym utworzeniu `XpEvent`, nie tylko po questach i challenge. Jezeli aktywnosci z `activities` nadal dodaja XP, trzeba zdecydowac, czy tez maja odpalac achievementy w module 6.
- Trigger `quest_count` wymaga definicji liczenia: wszystkie `QuestCompletion`, tylko ukonczone z `completed_at`, tylko aktywne questy, daily liczone per dzien czy per definicja. Bez tego seed `Legendary` moze byc niejednoznaczny.
- Trigger `habit_streak` powinien dzialac po utworzeniu check-inu i milestone, ale usuniecie check-inu nie powinno cofac unlocku ani XP. Test musi potwierdzic brak cofania.
- Achievement nie daje XP. To musi byc pokryte testem, bo naturalna pokusa UI to dodac "achievement points" lub XP badge.

### Journal

- Idempotencja automatycznych wpisow po `source_type` i `source_id` wymaga ostroznego constraintu. Reczne wpisy moga miec puste `source_type` i `source_id`, wiec nie wolno zablokowac wielu recznych wpisow przez zbyt szeroki unique constraint.
- `source_id` bez `GenericForeignKey` jest swiadoma decyzja MVP, ale oznacza brak integralnosci referencyjnej po usunieciu zrodla. Wpis journalowy jest wtedy audytowym sladem, nie aktywnym FK.
- Spec mowi, ze blad automatycznego journala nie powinien cofac glownej akcji, jezeli XP i akcja domenowa zostaly zapisane. Jesli journal jest tworzony wewnatrz tej samej transakcji co completion lub challenge complete, trzeba jawnie obsluzyc blad, albo przeniesc wpis po udanym zapisie glownej akcji.
- Challenge progress moze latwo spamowac journal. Rekomendacja spec 5-7: wpis tylko przy `note` albo completion. To powinno byc twarda decyzja implementacyjna.
- Dashboard powinien filtrowac journal konsekwentnie po `entry_date` albo `created_at`. Spec 5-7 eksponuje oba pola, ale nie rozstrzyga, ktore steruje zakresem dashboardu.

## 4. Otwarte decyzje wymagajace doprecyzowania

1. Czy oficjalna kolejnosc implementacji pakietu 5-7 to `JournalEntry` -> `Challenge` -> `Achievement`, mimo numeracji modulow 5, 6, 7?
2. Jaki jest finalny backendowy ksztalt `active_challenge` w `GET /api/dashboard/`: pola z `docs/rpg-modules-5-7-progression-spec.md` czy przejsciowy ksztalt z `docs/rpg-modules-3-4-dashboard-react-spec.md`?
3. Czy `POST /api/challenges/<id>/progress/` automatycznie konczy challenge po `current_value >= target_value`, czy zawsze wymaga osobnego `POST /api/challenges/<id>/complete/`?
4. Czy `ChallengeReward` i `Achievement.trigger_config` maja byc traktowane jako edytowalne po unlocku/awardzie, czy admin powinien ostrzegac/blokowac zmiany po fakcie?
5. Czy `Achievement.trigger_config` uzywa w bazie `snake_case` (`streak_days`, `quest_count`) i identyfikatorow rekordow, czy dopuszcza klucze frontendowe oraz nazwy?
6. Czy `skill_level` achievement ma odpalac sie po XP z aktywnosci w `activities`, czy tylko po XP z nowych mechanik `rpg`?
7. Jak dokladnie liczyc `quest_count`: liczba `QuestCompletion` z `completed_at`, liczba definicji questow ukonczonych przynajmniej raz, czy liczba nagrodzonych completion?
8. Czy dashboard achievements pokazuje tylko ostatnio odblokowane badge, czy takze zablokowane definicje dla kontekstu progresu?
9. Czy journal dashboard filtruje po `entry_date`, `created_at`, czy po obu polach zaleznnie od sekcji?
10. Jaki constraint idempotencji dla automatycznego journala: unikalne `(source_type, source_id)` tylko gdy `source_type` nie jest puste i `source_id` nie jest null?
11. Czy automatyczne wpisy journala maja byc best-effort bez rollbacku glownej akcji, czy blad journala ma byc widoczny w response jako ostrzezenie?
12. Czy modul 8 aktualizuje statusy w `docs/rpg-modules-implementation-index.md`, `docs/rpg-modules-5-7-progression-spec.md` i `docs/phase-2-rpg-mechanics-spec.md`, czy tylko usuwa kodowe tymczasowki?

## 5. Rekomendowana bramka wejscia przed modulami 5-7

Nie zaczynac implementacji 5-7, dopoki ponizsze warunki nie sa spelnione albo jawnie oznaczone jako swiadome odstepstwo:

- `rpg` istnieje jako jedna aplikacja Django i jest podpieta w `config/settings.py` oraz `config/urls.py`.
- Modele i migracje z modulow 1-2 istnieja: `Quest`, `QuestReward`, `QuestCompletion`, `Habit`, `HabitCheckIn`, `HabitMilestone`, `HabitMilestoneReward`, `HabitMilestoneUnlock`.
- Serwisy questow i habitow tworza XP tylko przez `skills.XpEvent` i sa idempotentne dla podwojnych klikniec.
- `GET /api/dashboard/` z `dashboard/views.py` i `dashboard/services.py` zwraca realne questy/habity z bazy oraz `active_challenge: null`, puste `achievements` i puste `journal_entries` bez placeholderow.
- `frontend/src/api/dashboard.ts` mapuje backend `snake_case` na frontend `camelCase`, nie generuje ID z tytulu, labela ani indeksu.
- `QuestsPanel` i `HabitsPanel` nie uzywaja `localStorage` jako zrodla prawdy dla wykonania questow lub habitow.
- Seed `activities/management/commands/seed_life_rpg.py` jest idempotentny dla danych Phase 1 oraz modulow 0-2 i nie tworzy domyslnej historii completion/check-in.
- Przed rozpoczeciem prac zapisane sa decyzje z sekcji "Otwarte decyzje" dotyczace `active_challenge`, trigger config i idempotencji journala.
- Przechodza minimalne komendy:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py test
cd frontend
npm run typecheck
npm run build
```

Jesli celem jest tylko osobny start journala, mozna dopuscic waska bramke dla modelu `JournalEntry` i recznego `POST /api/journal/`, ale wtedy raport akceptacji nie moze deklarowac gotowych integracji z questami, habitami, challenge i achievementami.

## 6. Koncowa checklista stabilizacji modulu 8

### Kontrakt i kod martwy

- Usunac mocki i fikcyjne fallbacki RPG z `dashboard/services.py`, `dashboard/views.py` i `frontend/src/data/mockDashboard.ts`, jezeli nie sa juz tylko awaryjnym fallbackiem offline.
- Usunac tymczasowe aliasy JSON po migracji Reacta: stare pola typu `current`, `target`, `unit`, `progress`, `label`, `completed`, jezeli finalne typy uzywaja `progress_value`, `target_value`, `target_unit`, `progress_percent`, `name`, `completed_today`.
- Potwierdzic, ze `active_challenge`, `achievements` i `journal_entries` maja jeden stabilny backend DTO.
- Potwierdzic, ze backend API pozostaje w `snake_case`, a `camelCase` wystepuje tylko po stronie Reacta.

### XP i idempotencja

- Zweryfikowac, ze `Skill` nadal nie ma pola `xp`.
- Zweryfikowac, ze XP z questow, habit milestone i challenge trafia tylko do `skills.XpEvent`.
- Zweryfikowac, ze achievement nie tworzy `XpEvent`.
- Zweryfikowac, ze habit check-in nie tworzy `XpEvent`.
- Przetestowac podwojne `complete_quest`, podwojne `complete_challenge`, powtorne milestone unlock, powtorne achievement unlock i powtorne tworzenie automatycznego journala.

### Modele, admin i seed

- Potwierdzic migracje dla `Challenge`, `ChallengeReward`, `Achievement`, `AchievementUnlock`, `JournalEntry`.
- Sprawdzic admin w `rpg/admin.py` dla wszystkich nowych modeli oraz inline rewardow.
- Uruchomic `seed_life_rpg` kilka razy i potwierdzic brak duplikatow challenge, achievementow, rewardow i journal entries.
- Potwierdzic, ze seed nie tworzy niekontrolowanej historii wykonania, chyba ze konkretna specyfikacja testowa tego wymaga.

### Dashboard i React

- `GET /api/dashboard/` pokazuje realne dane z `rpg`, `skills`, `activities` i `statuses`.
- React nie zapisuje stanu domenowego w `localStorage`; dozwolone sa theme i ustawienia UI.
- Po mutacji challenge/journal/achievement dashboard odswieza dane z backendu albo uzywa zwroconego DTO bez samodzielnego liczenia XP.
- Empty states dzialaja dla braku aktywnego challenge, braku achievementow i braku wpisow journala.
- `frontend/src/api/dashboard.ts` i `frontend/src/types/dashboard.ts` sa zgodne z finalnym JSON.

### Testy i komendy koncowe

- Uruchomic:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py check
.venv/bin/python manage.py test
cd frontend
npm run typecheck
npm run build
```

- Testy backendowe powinny pokrywac:
  - walidacje challenge;
  - idempotencje XP challenge;
  - manual unlock achievementu;
  - idempotencje achievement unlock;
  - brak XP za achievement;
  - reczny journal;
  - idempotencje automatycznego journala;
  - dashboard API z realnymi danymi;
  - idempotencje seedow.

### Dokumentacja

- Zaktualizowac statusy wykonania w `docs/rpg-modules-implementation-index.md`.
- Jezeli implementacja rozstrzygnie otwarte decyzje, dopisac je do `docs/rpg-modules-5-7-progression-spec.md` albo `docs/phase-2-rpg-mechanics-spec.md`.
- Potwierdzic, ze `docs/life-rpg-tracker-mvp-spec.md` nadal pozostaje zrodlem zasad MVP: Django 6.0.6, PostgreSQL, React TypeScript Vite Tailwind, brak DRF i Celery.
