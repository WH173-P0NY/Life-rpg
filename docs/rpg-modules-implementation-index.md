# RPG Modules - implementation index

## Cel

Ten dokument jest mapa wdrozenia modulow RPG. Szczegoly implementacyjne sa rozbite na trzy osobne specyfikacje:

- `docs/rpg-modules-0-2-backend-core-spec.md` - fundament `rpg`, questy, habity, streaki i milestone XP,
- `docs/rpg-modules-3-4-dashboard-react-spec.md` - dashboard API z realnych danych i React live dla questow/habitow,
- `docs/rpg-modules-5-7-progression-spec.md` - challenge, achievementy i journal.

Zrodlem prawdy dla ogolnych decyzji produktowych pozostaje `docs/phase-2-rpg-mechanics-spec.md`.

## Aktualny stan repo

Kod aplikacji jest jeszcze przed modulem 0.

Istnieje Phase 1:

- `skills`,
- `activities`,
- `statuses`,
- `dashboard`,
- React shell,
- dashboard oparty o aktywnosci i statusy.

Nie istnieja jeszcze:

- aplikacja Django `rpg`,
- modele questow, habitow, challenge, achievementow i journala,
- endpointy `/api/quests/...`,
- endpointy `/api/habits/...`.

Obecne sekcje RPG w dashboardzie sa przejsciowa warstwa UI/API i beda przepinane na realne dane dopiero od modulow 0-4.

## Kontrakt API i nazewnictwo

Backend JSON API ma uzywac `snake_case`.

React ma mapowac `snake_case` z backendu na `camelCase` dopiero w mapperze/typach frontendu. W modelach Django, serwisach domenowych, widokach JSON i testach backendowych trzymamy `snake_case`.

Decyzje kontraktowe po analizie:

- finalny backendowy DTO `active_challenge` ma pola: `id`, `title`, `status`, `current_value`, `target_value`, `target_unit`, `progress_percent`, `reward_title`, `reward_xp`,
- legacy pola `name`, `day`, `total`, `progress`, `reward` sa dozwolone tylko jako przejsciowe aliasy podczas migracji starego Reacta,
- `Achievement.trigger_config` uzywa `snake_case` i stabilnych ID: `streak_days`, `quest_count`, `skill_id`, `habit_id`, `challenge_id`,
- nazwy skilli, habitow albo challenge sa dozwolone tylko jako fallback seedowy, nie jako docelowy kontrakt,
- backendowe `target_unit` dla czasu uzywa wartosci `minutes`; skrot `min` jest tylko displayem po stronie Reacta,
- daily questy i streaki dzialaja wedlug lokalnej daty aplikacji; dla lokalnego MVP rekomendowane ustawienie to `TIME_ZONE = "Europe/Warsaw"`.

## Kolejnosc wdrozenia

Moduly 0-2 sa opisane osobno, bo maja rozne odpowiedzialnosci, ale rekomendacja implementacyjna jest taka, zeby wdrozyc je jako pierwszy backendowy pakiet. Dopiero po nim warto przepinac dashboard API i Reacta, bo bez realnych modeli frontend musialby dalej symulowac stan.

### 1. Modul 0 - fundament `rpg`

Cel: przygotowac jedna aplikacje Django `rpg`, routing API, szkielety plikow, TextChoices i test skeleton.

Nie implementowac jeszcze UI ani logiki domenowej.

### 2. Modul 1 - questy

Cel: realne questy, rewardy, completion, progress i XP przez `skills.XpEvent`.

Najwazniejszy efekt:

- `POST /api/quests/<id>/complete/`,
- `POST /api/quests/<id>/progress/`,
- quest z wieloma rewardami tworzy wiele `XpEvent`,
- ponowne wykonanie nie dubluje XP.

### 3. Modul 2 - habity, streaki i milestone

Cel: realne habity, check-iny, dynamiczny streak i XP tylko przez milestone.

Najwazniejszy efekt:

- `POST /api/habits/<id>/toggle/`,
- habit check-in nie daje XP,
- milestone streaka daje XP tylko raz przez `XpEvent`,
- przerwanie streaka nie cofa milestone ani XP.

### 4. Modul 3 - dashboard API z realnych danych

Cel: `GET /api/dashboard/` przestaje zwracac placeholdery dla sekcji RPG.

Najwazniejszy efekt:

- questy z `rpg.Quest`,
- completions z `rpg.QuestCompletion`,
- habity i check-iny z `rpg.Habit` oraz `rpg.HabitCheckIn`,
- streaki i milestone z serwisow domenowych,
- `active_challenge: null` do czasu modulu 5,
- puste listy/null dla achievementow i journala do czasu modulow 6-7.

### 5. Modul 4 - React live dla questow i habitow

Cel: React przestaje trzymac stan questow i habitow w `localStorage`.

Najwazniejszy efekt:

- klik questa wysyla request do Django,
- klik habitu wysyla request do Django,
- po mutacji dashboard odswieza stan z API,
- `localStorage` zostaje tylko dla theme i ustawien UI.

### 6. Modul 5 - challenge

Cel: realne wyzwania dlugoterminowe z postepem, nagroda i dashboardem.

Najwazniejszy efekt:

- aktywny challenge pochodzi z bazy,
- progress jest aktualizowany recznie w MVP,
- `POST /api/challenges/<id>/progress/` nie przyznaje XP automatycznie,
- XP z challenge jest przyznawane dopiero przez osobne ukonczenie challenge,
- ukonczenie challenge moze dac XP przez `XpEvent`,
- seed tworzy `30 Days No Sugar`.

Do czasu wdrozenia tego modulu frontend i backend musza traktowac `active_challenge` jako wartosc nullable.

### 7. Modul 6 - achievementy

Cel: realne odznaki i odblokowania.

Najwazniejszy efekt:

- achievement mozna odblokowac recznie,
- proste triggery: `habit_streak`, `skill_level`, `quest_count`, `challenge_completed`,
- achievement nie tworzy XP,
- dashboard pokazuje badge z bazy.

### 8. Modul 7 - journal

Cel: osobny model journala i wpisy manualne/automatyczne.

Najwazniejszy efekt:

- `POST /api/journal/`,
- dashboard pokazuje ostatnie wpisy z `rpg.JournalEntry`,
- zakresy dashboardu filtruja journal po `entry_date`, a sortowanie ostatnich wpisow uzywa `created_at`,
- wazne akcje moga tworzyc automatyczne wpisy,
- automatyczne wpisy sa idempotentne po `(source_type, source_id)` tylko wtedy, gdy oba pola sa ustawione,
- blad automatycznego journala nie rollbackuje glownej akcji domenowej.

### 9. Modul 8 - stabilizacja

Cel: dopiecie calosci po modulach 0-7.

Zakres:

- usunac martwe mocki i nieuzywany kod UI,
- uzgodnic typy Reacta z finalnym JSON-em,
- dopiac seed jako idempotentny end-to-end,
- uruchomic pelne testy backendu i frontend build,
- zaktualizowac statusy w specyfikacjach.

## Zasady przekrojowe

- Jedna aplikacja Django: `rpg`.
- Backend jest source of truth dla XP, questow, habitow, challenge, achievementow i journala.
- Backend JSON API zwraca `snake_case`; `camelCase` istnieje tylko w mapperze/typach Reacta.
- XP zawsze przez `skills.XpEvent`.
- `Skill` nie dostaje pola `xp`.
- Habit check-in nie daje XP.
- Achievement nie daje XP.
- AI-generated quest zostaje architektonicznie wsparty przez `Quest.created_by = "ai"` i `status = "draft"`, ale generowanie AI nie jest czescia tych modulow.
- Nie dodawac DRF.
- Nie dodawac Celery.
- Nie przenosic logiki XP do Reacta.

## Minimalna bramka po kazdym module

Po kazdym module:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test
```

Po modulach dotykajacych frontendu:

```bash
cd frontend
npm run typecheck
npm run build
```

## Rekomendowany sposob pracy

Najpierw wdrozyc moduly 0-2 jako jeden backendowy pakiet:

- `rpg` app,
- modele questow, habitow i milestone,
- admin,
- migracje,
- serwisy domenowe,
- endpointy JSON,
- testy,
- seed definicji.

Po modulach 0-2 `seed_life_rpg` ma tworzyc definicje questow, habitow i milestone. Nie powinien tworzyc domyslnych historii wykonania, czyli `QuestCompletion` ani `HabitCheckIn`.

Seed `Plan tomorrow` ma jednoznaczna nagrode: `Writing +10 XP`. Nie uzywamy `Discipline` jako skilla seedowego dla tego questa, bo `Discipline` jest atrybutem UI, a nie wymaganym skillem MVP.

Wewnatrz pakietu 5-7 numeracja modulow pozostaje produktowa, ale rekomendowana kolejnosc implementacji jest inna: najpierw bazowy `JournalEntry`, potem `Challenge`, potem `Achievement`, a na koncu integracje automatyczne.

Po backendowym pakiecie 0-2 implementowac kolejne moduly pojedynczo i nie zaczynac nastepnego, dopoki poprzedni nie ma:

- migracji,
- admina,
- seed danych, jezeli dotyczy,
- testow domenowych,
- endpointow JSON, jezeli dotyczy,
- aktualizacji dashboardu albo jawnej informacji, ze integracja dashboardu przyjdzie w module 3.
