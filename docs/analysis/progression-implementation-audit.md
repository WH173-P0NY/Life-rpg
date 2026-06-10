# Progression Implementation Audit

Data audytu: 2026-06-10

Zakres: niezalezny audit wdrozeniowy po implementacji progression w
`/home/wh173-p0ny/ProjectLevel`. Kod nie byl edytowany. Jedyny plik
utworzony w workspace w ramach audytu to ten raport.

## Werdykt

**Blokowane**.

Implementacja modeli/API/React jest w wiekszosci zgodna z kanonicznym
kontraktem progression, ale modulu nie mozna uznac za gotowy, dopoki:

1. PostgreSQL nie bedzie dostepny i nie przejda migracje/testy.
2. Nie zostanie domkniety brakujacy flow `challenge_failure`.
3. Nie zostanie rozstrzygniety seed, ktory przez sample aktywnosci moze
   odpalac `evaluate_achievements()` na bazie z istniejacym XP.
4. Stare dokumenty `docs/rpg-modules-*` nie zostana oznaczone jako legacy albo
   poprawione, bo nadal zawieraja stary kontrakt challenge progress.

## 1. Zgodnosc z kanonicznym kontraktem

Zrodlo kanoniczne: `docs/rpg-progression-spec-index.md`.

### Modele

Status: **zgodne w glownej sciezce**.

- `Goal` uzywa `starts_on` i `due_on`, nie `target_date`:
  `rpg/models.py:426-536`.
- `GoalSkill` i `GoalProgressEntry` istnieja:
  `rpg/models.py:539-627`.
- `Challenge` uzywa `start_date`, `end_date`, `current_value`:
  `rpg/models.py:629-760`.
- `ChallengeCheckIn` istnieje jako historia/source of truth:
  `rpg/models.py:798-840`.
- `ChallengeReward` trzyma nagrody XP do skilli:
  `rpg/models.py:763-795`.
- `Achievement` uzywa `trigger_type + trigger_config`, bez jawnych FK
  `skill/habit/goal/challenge`: `rpg/models.py:842-890`.
- `AchievementUnlock` jest unikalny per achievement:
  `rpg/models.py:893-925`.

### Serwisy domenowe

Status: **zgodne w happy path, z jednym brakiem**.

- Goal progress/complete nie tworzy XP i tworzy journal
  `source_type="goal_completion"`: `rpg/services.py:370-459`.
- Challenge toggle tworzy/usuwa `ChallengeCheckIn`, przelicza
  `current_value`, zwraca `completion_ready` i nie tworzy XP:
  `rpg/services.py:580-628`.
- Challenge complete przyznaje XP tylko przez `skills.XpEvent` z
  `source_type="challenge"` i opiera sie o `xp_awarded_at`:
  `rpg/services.py:631-700`.
- Achievement unlock/evaluate nie tworzy XP:
  `rpg/services.py:703-753`.
- Automatyczne wpisy journala uzywaja:
  - `goal_completion`: `rpg/services.py:2062-2071`
  - `challenge_completion`: `rpg/services.py:2076-2090`
  - `achievement_unlock`: `rpg/services.py:2097-2104`

Brak: kanoniczny indeks wymienia `challenge_failure`, a domain spec opisuje
`fail_challenge`, ale kod nie ma serwisu, URL-a ani testu dla fail challenge.
W kodzie sa tylko pola/statusy `FAILED` i `failed_at`.

### API Django

Status: **zgodne w glownej sciezce**.

- Goals: `GET/POST /api/goals/`, `PATCH /api/goals/<id>/`,
  `/progress/`, `/complete/`, `/archive/`: `rpg/urls.py:24-39`,
  `rpg/views.py:108-234`.
- Challenges: `GET/POST /api/challenges/`, `PATCH /api/challenges/<id>/`,
  `/toggle/`, `/complete/`: `rpg/urls.py:41-55`,
  `rpg/views.py:237-357`.
- Achievements: `/api/achievements/`, `/unlock/`, `/evaluate/`:
  `rpg/urls.py:57-66`, `rpg/views.py:361-410`.
- Nie ma starego `/api/challenges/<id>/progress/` w aktualnym routingu.

### React

Status: **zgodne w glownej sciezce**.

- React mapuje backend `snake_case` na `camelCase`, np. `starts_on -> startsOn`
  i `due_on -> dueOn`: `frontend/src/api/progression.ts:135-155`.
- `ProgressionGoal` ma `startsOn` i `dueOn`, nie `targetDate`:
  `frontend/src/types/progression.ts:9-24`.
- `ProgressionChallenge` ma `startDate`, `endDate`, `currentValue`,
  `targetValue`: `frontend/src/types/progression.ts:26-44`.
- API Reacta uzywa `toggleChallengeCheckIn()` i
  `/api/challenges/<id>/toggle/`: `frontend/src/api/progression.ts:396-433`.
- `ChallengePanel` obsluguje `null`, check-in i complete:
  `frontend/src/components/ChallengePanel.tsx:23-53`,
  `frontend/src/components/ChallengePanel.tsx:55-151`.
- `GoalsView` ma create/update/progress/complete/archive goal oraz create,
  toggle i complete challenge: `frontend/src/components/GoalsView.tsx:103-260`.
- `AchievementsView` ma list/evaluate/manual unlock:
  `frontend/src/components/AchievementsView.tsx:34-95`.

Dashboard bierze realne dane:

- `active_challenge = serialize_challenge(get_active_challenge())`:
  `dashboard/services.py:333`.
- `achievements = build_recent_achievement_rows()`:
  `dashboard/services.py:393`.

## 2. Pozostalosci starych nazw

Komenda dla kodu i aktualnych specow:

```bash
rg -n 'target_date|planned challenge|/api/challenges/<id>/progress|updateChallengeProgress|requirement_value|skill_xp|challenges/.*/progress|update_challenge_progress' docs/rpg-progression-spec-index.md docs/rpg-progression-domain-spec.md docs/rpg-progression-api-react-spec.md docs/rpg-progression-integration-qa-spec.md rpg activities dashboard skills frontend/src
```

Wynik: **brak trafien**.

Komenda dla repo bez `node_modules`, `frontend/dist` i `docs/analysis`:

```bash
rg -n -g '!frontend/node_modules/**' -g '!frontend/dist/**' -g '!docs/analysis/**' 'target_date|planned challenge|/api/challenges/<id>/progress|updateChallengeProgress|requirement_value|skill_xp|challenges/.*/progress|update_challenge_progress' .
```

Wynik: stare nazwy zostaly tylko w starych dokumentach legacy:

- `docs/rpg-modules-implementation-index.md:114`
- `docs/rpg-modules-5-7-progression-spec.md:264`
- `docs/rpg-modules-5-7-progression-spec.md:291`
- `docs/rpg-modules-5-7-progression-spec.md:322`

To nie jest problem runtime, ale jest problem dokumentacyjny przed uznaniem
modulu za domkniety.

## 3. Seed

Status: **czesciowo zgodny, z ryzykiem na niepustej bazie**.

Seed progression:

- Tworzy goals: `activities/management/commands/seed_life_rpg.py:366-433`.
- Tworzy challenge i `ChallengeReward`:
  `activities/management/commands/seed_life_rpg.py:435-467`.
- Tworzy achievement definitions z `trigger_config`:
  `activities/management/commands/seed_life_rpg.py:469-548`.
- Nie importuje i nie tworzy bezposrednio `ChallengeCheckIn`.
- Nie importuje i nie tworzy bezposrednio `AchievementUnlock`.
- Nie tworzy XP z achievementow.

Istotne ryzyko:

- Seed tworzy sample `ActivityEntry` przez `create_activity_entry()`:
  `activities/management/commands/seed_life_rpg.py:569-592`.
- `create_activity_entry()` przyznaje XP z aktywnosci i wywoluje
  `evaluate_achievements(source_type="activity", source_id=entry.id)`:
  `activities/services.py:31-49`.

Na czystej bazie test oczekuje braku `ChallengeCheckIn` i `AchievementUnlock`:
`rpg/tests.py:1438-1468`. Tego testu nie mozna bylo uruchomic w audycie przez
niedostepna baze. Na bazie z istniejacym XP seed moze odblokowac achievement,
jesli sample aktywnosc przepchnie warunek typu `total_xp`.

## 4. PostgreSQL / DB

Status: **niedostepny**.

Komenda:

```bash
pg_isready -h 127.0.0.1 -p 5432
```

Wynik:

```txt
127.0.0.1:5432 - no response
```

Komenda:

```bash
.venv/bin/python manage.py showmigrations rpg --plan
```

Wynik: blad polaczenia z DB:

```txt
django.db.utils.OperationalError: connection is bad: no error details available
```

Konsekwencja: nie mozna potwierdzic migracji na realnej bazie, uruchomic
`seed_life_rpg` ani `manage.py test`.

Dodatkowo:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
```

Wynik:

```txt
RuntimeWarning: Got an error checking a consistent migration history performed for database connection 'default': connection is bad: no error details available
No changes detected
```

Czyli modele i migracje sa lokalnie spojne, ale historia migracji w DB nie
zostala zweryfikowana.

## 5. Frontend build/typecheck

Status: **przechodzi**.

Komenda:

```bash
cd frontend
npm run typecheck
```

Wynik:

```txt
> life-rpg-frontend@0.1.0 typecheck
> tsc -b
```

Exit code: `0`.

Komenda build zostala uruchomiona z outDir w `/tmp`, zeby nie nadpisywac
`frontend/dist` podczas audytu:

```bash
cd frontend
npm run build -- --outDir /tmp/projectlevel-progression-audit-vite-build
```

Wynik:

```txt
vite v7.3.5 building client environment for production...
✓ 1773 modules transformed.
✓ built in 1.98s
```

Exit code: `0`.

Vite pokazal tylko ostrzezenie, ze outDir poza rootem projektu nie zostanie
wyczyszczony automatycznie.

## 6. Inne komendy kontrolne

```bash
.venv/bin/python manage.py check
```

Wynik:

```txt
System check identified no issues (0 silenced).
```

Exit code: `0`.

## 7. Blokery przed gotowoscia

1. **DB/Postgres niedostepny.**
   Dopoki `127.0.0.1:5432` nie odpowiada, nie da sie potwierdzic migracji,
   seedu ani testow. Minimalna bramka z indeksu nie jest spelniona.

2. **Brak flow `challenge_failure`.**
   Kanoniczny indeks wymienia `challenge_failure`, a domain spec opisuje
   `fail_challenge`, ale implementacja ma tylko pola/statusy, bez serwisu,
   endpointu, journal entry i testow.

3. **Seed nie jest w pelni neutralny wzgledem achievementow na niepustej DB.**
   Nie tworzy `AchievementUnlock` bezposrednio, ale tworzy sample aktywnosci,
   ktore odpalaja `evaluate_achievements()`. Na czystej DB powinno byc OK,
   ale wymaga to realnego testu DB.

4. **Stare dokumenty legacy nadal zawieraja stary challenge progress contract.**
   W kodzie i aktualnych progression specach nie ma starych nazw, ale stare
   `docs/rpg-modules-*` nadal moga wprowadzac w blad.

5. **Testy backendu nie zostaly uruchomione.**
   Powod: DB niedostepna. Szczegolnie wazne sa testy progression seed i
   idempotencji XP/unlockow.

## 8. Rekomendowana sekwencja domkniecia

1. Uruchomic PostgreSQL i potwierdzic:

   ```bash
   pg_isready -h 127.0.0.1 -p 5432
   .venv/bin/python manage.py migrate
   .venv/bin/python manage.py seed_life_rpg
   .venv/bin/python manage.py test
   ```

2. Dodac `fail_challenge(...)`, endpoint `POST /api/challenges/<id>/fail/`,
   journal `source_type="challenge_failure"` i testy.

3. Zdecydowac, czy `seed_life_rpg` ma dalej tworzyc sample aktywnosci. Jezeli
   seed progression ma byc neutralny, sample aktywnosci powinny byc za flaga
   albo oddzielna komenda.

4. Oznaczyc stare `docs/rpg-modules-*` jako legacy albo usunac z nich
   niekanoniczny challenge progress contract.
