# Life RPG - Progression Spec Index

## Cel

Ten indeks zbiera specyfikacje nastepnego modulu RPG:

- Goals,
- Challenges,
- Achievements.

Modul ma domknac petle:

```txt
activity / quest / habit / manual progress
-> progression
-> challenge completion XP
-> achievement unlock
-> journal chronicle entry
```

## Aktualny punkt startowy

Repo nie jest juz na etapie opisanym w starszym `docs/rpg-modules-implementation-index.md`.

Aktualnie istnieja:

- aplikacja `rpg`,
- questy,
- habity,
- milestone streakow,
- Journal z `JournalEntry`,
- `CharacterIdentity`,
- dashboard API z realnymi questami, habitami i journalem,
- React sidebar z osobnymi widokami,
- `planner` i widok Calendar.

Do wdrozenia w tym module zostaja:

- Goals,
- Challenges,
- Achievements,
- realne `active_challenge` w dashboardzie,
- realne `achievements` w dashboardzie i widoku sidebar,
- automatyczne wpisy journala dla goal/challenge/achievement.

## Dokumenty

### 1. Domena backendu

Plik: `docs/rpg-progression-domain-spec.md`

Zakres:

- modele Django,
- TextChoices,
- walidacje,
- serwisy domenowe,
- idempotencja,
- XP ledger przez `skills.XpEvent`,
- Journal integration od strony domeny.

### 2. API i React

Plik: `docs/rpg-progression-api-react-spec.md`

Zakres:

- endpointy Django JSON,
- kontrakty request/response w `snake_case`,
- mappery React do `camelCase`,
- widoki `Goals`, `Achievements` i dashboard,
- empty/loading/error states,
- refresh po mutacjach.

### 3. Integracja i QA

Plik: `docs/rpg-progression-integration-qa-spec.md`

Zakres:

- seed,
- migracje,
- test matrix,
- smoke testy,
- integracja z Journalem,
- edge cases,
- acceptance criteria.

## Decyzje obowiazujace

- Wszystko zostaje w jednej aplikacji Django `rpg`.
- Nie dodajemy DRF.
- Nie dodajemy Celery.
- Backend JSON uzywa `snake_case`.
- React mapuje dane API na `camelCase`.
- React nie zapisuje danych domenowych w `localStorage`.
- XP jest zapisywane tylko przez `skills.XpEvent`.
- Goal nie daje XP w MVP.
- Achievement nie daje XP w MVP.
- Challenge moze dac XP tylko przy `complete` i tylko raz.
- Goal uzywa pary dat `starts_on` i `due_on`.
- Challenge uzywa `start_date`, `end_date`, `current_value` oraz `ChallengeCheckIn`.
- `ChallengeCheckIn` jest zrodlem prawdy historii; `current_value` jest cachem.
- Toggle check-inu challenge nie daje XP i nie konczy challenge automatycznie.
- Achievement uzywa `trigger_type + trigger_config`, bez jawnych FK typu `skill`, `habit`, `goal`, `challenge` na modelu.
- Kanoniczne `JournalEntry.source_type`: `goal_completion`, `challenge_completion`, `challenge_failure`, `achievement_unlock`.
- Journal auto wpisy sa best-effort i idempotentne przez `source_type/source_id`.
- Seed tworzy definicje i przykladowe rekordy robocze, ale nie tworzy historii wykonania, unlockow ani XP.
- AI quest generation jest poza tym modulem.

## Rekomendowana kolejnosc wdrozenia

1. Backend choices i modele:
   - `Goal`,
   - `GoalSkill`,
   - `GoalProgressEntry`,
   - `Challenge`,
   - `ChallengeReward`,
   - `ChallengeCheckIn`,
   - `Achievement`,
   - `AchievementUnlock`.

2. Admin, migracje i seed.

3. Serwisy domenowe:
   - goals,
   - challenges,
   - achievements,
   - journal auto entries.

4. Endpointy JSON.

5. Dashboard selectors:
   - `active_challenge`,
   - `achievements`.

6. React:
   - `frontend/src/api/progression.ts`,
   - typy progression,
   - widok Goals,
   - widok Achievements,
   - dashboard integration.

7. Testy i smoke testy.

## Minimalna bramka akceptacji

Backend:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```
