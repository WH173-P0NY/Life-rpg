# Life RPG Tracker - specyfikacja modulow 5-7: progression layer

## 1. Cel dokumentu

Ten dokument opisuje implementacje trzech modulow rozszerzajacych mechaniki RPG:

- Modul 5: Challenge,
- Modul 6: Achievementy,
- Modul 7: Journal.

Moduly 5-7 maja ozywic warstwe progresji ponad questami i habitami:

- challenge pokazuje dluzszy cel i postep,
- achievementy zamieniaja wazne zdarzenia w odznaki,
- journal zapisuje reczna i automatyczna historie rozwoju.

Dokument jest specyfikacja implementacyjna. Nie zastepuje ogolnej specyfikacji etapu 2, ale doprecyzowuje zakres, modele, endpointy, serwisy, testy i kryteria akceptacji dla modulow 5-7.

## 2. Decyzje projektu

Obowiazujace decyzje:

- mechaniki RPG mieszkaja w jednej aplikacji Django `rpg`,
- XP jest zapisywane tylko przez `skills.XpEvent`,
- React jest glownym frontendem aplikacji,
- Django udostepnia standardowe widoki JSON,
- nie dodajemy DRF,
- nie dodajemy Celery,
- logika domenowa nie powinna mieszkac bezposrednio w widokach,
- frontend nie liczy XP i nie tworzy progresu z pominieciem API,
- dashboard ma korzystac z realnych danych z bazy, a nie z mockow.

## 3. Zaleznosci miedzy modulami

### Moduly bazowe

Moduly 5-7 zakladaja, ze istnieje fundament z modulow 0-4:

- aplikacja `rpg`,
- questy,
- habity,
- streaki,
- dashboard API,
- podstawowe endpointy Reacta.

### Zasada niezaleznosci

Challenge, Achievementy i Journal moga korzystac z questow i habitow, ale nie powinny blokowac modulow 0-4.

W praktyce:

- Modul 5 moze dzialac samodzielnie z recznym postepem challenge,
- Modul 6 moze zaczac od manual unlock i prostych triggerow,
- Modul 7 moze zaczac od recznych wpisow oraz wpisow automatycznych z tych zdarzen, ktore juz istnieja,
- brak triggera nie moze blokowac wykonania questa, habitu albo challenge,
- blad tworzenia wpisu journala nie powinien cofac podstawowej akcji uzytkownika, jezeli XP i glowna akcja zostaly zapisane poprawnie.

Kolejnosc implementacyjna wewnatrz pakietu 5-7:

1. Bazowy `JournalEntry` i reczny `POST /api/journal/`.
2. `Challenge` i `ChallengeReward`.
3. `Achievement` i `AchievementUnlock`.
4. Integracje automatyczne miedzy questami, habitami, challenge, achievementami i journalem.

Numeracja modulow 5, 6 i 7 zostaje produktowa, ale powyzsza kolejnosc jest rekomendowanym porzadkiem implementacji.

## 4. Wspolne zasady techniczne

### 4.1. Pliki

Docelowo moduly 5-7 powinny korzystac z tych plikow:

- `rpg/models.py`,
- `rpg/admin.py`,
- `rpg/services.py`,
- `rpg/views.py`,
- `rpg/urls.py`,
- `rpg/tests.py` albo osobne pliki testow, jezeli projekt zostanie podzielony,
- `dashboard/views.py`,
- `activities/management/commands/seed_life_rpg.py`,
- `frontend/src/api/dashboard.ts`,
- komponenty React dashboardu odpowiedzialne za challenge, achievementy i journal.

### 4.2. Kontrakt JSON

Backendowe endpointy Django zwracaja i przyjmuja JSON w `snake_case`.

Zasady:

- requesty do Django API uzywaja `snake_case`,
- response z Django API uzywa `snake_case`,
- React moze mapowac payloady API na typy i komponenty `camelCase`,
- przyklady w tej specyfikacji pokazuja kontrakt backendowy, wiec pozostaja w `snake_case`,
- pola modeli nagrod uzywaja `xp_amount`,
- jezeli dashboard API pokazuje wyliczona laczna nagrode XP, moze uzyc pola `reward_xp`,
- payloady zwracajace faktyczne wpisy XP z `skills.XpEvent` uzywaja `xp_events` oraz `amount`, bo `amount` jest polem ledgera XP,
- pola powiazania zdarzen uzywaja `source_type` i `source_id`.

### 4.3. TextChoices

Statusy techniczne powinny uzywac `models.TextChoices`.

Przyklady:

- status challenge,
- typ triggera achievementu,
- rarity achievementu,
- typ wpisu journalowego.

Nie robimy `choices` dla danych, ktore maja byc swobodnie edytowane przez uzytkownika, np. tytuly questow, nazwy habitow albo nazwy skilli.

### 4.4. Daty

Zasady:

- daty dzienne uzywaja `DateField`,
- moment zdarzenia uzywa `DateTimeField`,
- dla dzisiejszych operacji uzywamy `timezone.localdate()`,
- dla timestampow uzywamy `timezone.now()`.

### 4.5. XP

Jedynym miejscem zapisu XP pozostaje `skills.XpEvent`.

Dozwolone `source_type` dla tych modulow:

- `challenge` - XP za ukonczenie challenge,
- `habit_milestone` - XP za milestone habitu z modulow 0-4,
- `quest` - XP za quest z modulow 0-4,
- `manual` - reczna korekta w przyszlosci.

Achievement sam nie daje XP. Achievement jest odznaka za zdarzenie, a XP daje czyn, quest, milestone albo challenge.

### 4.6. Idempotencja

Wazne akcje musza byc odporne na podwojne klikniecie:

- ukonczenie challenge nie moze przyznac XP dwa razy,
- odblokowanie achievementu nie moze stworzyc duplikatu,
- automatyczny wpis journala dla tego samego zdarzenia nie powinien byc tworzony wielokrotnie, jezeli serwis zostanie wywolany ponownie.

## 5. Modul 5: Challenge

### 5.1. Cel

Challenge reprezentuje dluzszy cel, ktory uzytkownik sledzi przez wiele dni.

Pierwsza implementacja ma pozwalac:

- tworzyc challenge w adminie,
- seedowac challenge `30 Days No Sugar`,
- pokazac aktywny challenge na dashboardzie,
- recznie aktualizowac postep,
- opcjonalnie przyznac XP po ukonczeniu challenge,
- tworzyc wpis journala po zmianie postepu albo ukonczeniu,
- uruchomic trigger achievementu `challenge_completed`.

### 5.2. Zakres

W zakresie:

- model `Challenge`,
- model `ChallengeReward`,
- serwis aktualizacji postepu,
- serwis ukonczenia challenge,
- endpoint do recznej aktualizacji postepu,
- endpoint do ukonczenia challenge,
- dane challenge w `/api/dashboard/`,
- admin,
- seed `30 Days No Sugar`,
- testy domenowe i API.

Poza zakresem:

- automatyczne laczenie challenge z ActivityWatch,
- automatyczne zliczanie postepu z habitow i questow,
- wiele rownoczesnych challenge na dashboardzie,
- rozbudowane widoki listy challenge w React,
- cofanie XP po cofnieciu challenge.

### 5.3. Model `Challenge`

Model: `rpg.Challenge`

Pola:

- `id`,
- `title` - `CharField(max_length=160)`,
- `description` - `TextField(blank=True)`,
- `status` - `CharField` z `TextChoices`,
- `start_date` - `DateField`,
- `end_date` - `DateField`,
- `target_value` - `PositiveIntegerField`,
- `target_unit` - `CharField(max_length=40)`,
- `current_value` - `PositiveIntegerField(default=0)`,
- `reward_title` - `CharField(max_length=160, blank=True)`,
- `created_by` - `CharField` z `TextChoices`,
- `completed_at` - `DateTimeField(null=True, blank=True)`,
- `xp_awarded_at` - `DateTimeField(null=True, blank=True)`,
- `created_at`,
- `updated_at`.

Rekomendowane `status`:

- `planned`,
- `active`,
- `completed`,
- `failed`,
- `archived`.

Rekomendowane `created_by`:

- `manual`,
- `system`,
- `ai`.

Zasady walidacji:

- `title` nie moze byc puste,
- `target_value` musi byc wieksze od `0`,
- `current_value` nie moze byc ujemne,
- `current_value` nie powinno przekraczac `target_value` po zapisaniu przez serwis,
- `end_date` nie moze byc wczesniejsze niz `start_date`,
- tylko challenge ze statusem `active` jest kandydatem do glownej sekcji dashboardu.

### 5.4. Model `ChallengeReward`

Model: `rpg.ChallengeReward`

Pola:

- `id`,
- `challenge` - `ForeignKey` do `Challenge`,
- `skill` - `ForeignKey` do `skills.Skill`,
- `xp_amount` - `PositiveIntegerField`,
- `created_at`.

Zasady:

- para `challenge` + `skill` musi byc unikalna,
- `xp_amount` musi byc wieksze od `0`,
- challenge moze nagradzac kilka skilli,
- XP jest przyznawane tylko po ukonczeniu challenge,
- XP z challenge musi byc zapisane wylacznie jako `skills.XpEvent`,
- `ChallengeReward` nie aktualizuje XP skilla bezposrednio,
- brak rewardow XP jest dozwolony, jezeli challenge ma byc tylko motywacyjny.

### 5.5. Reguly domenowe

Aktywny challenge:

- dashboard pokazuje jeden najwazniejszy aktywny challenge,
- wybor: najpierw `status=active`, potem najblizsze `end_date`, potem najnowszy `created_at`,
- do czasu wdrozenia Modulu 5 API moze zwracac `active_challenge: null`,
- jezeli nie ma aktywnego challenge, API zwraca `active_challenge: null`,
- frontend musi traktowac `active_challenge` jako nullable i pokazac pusty stan albo ukryc panel.

Postep:

- na start postep jest aktualizowany recznie,
- endpoint przyjmuje wartosc bezwzgledna `current_value`,
- serwis obcina wartosc do zakresu `0..target_value`,
- progress procentowy liczony jest jako `current_value / target_value * 100`,
- `POST /api/challenges/<id>/progress/` nie przyznaje XP automatycznie,
- `current_value >= target_value` nie powinno samo tworzyc `XpEvent`,
- XP z challenge jest przyznawane dopiero przez osobne `POST /api/challenges/<id>/complete/`.

Ukonczenie:

- ukonczenie ustawia `status=completed`,
- ukonczenie ustawia `completed_at`, jezeli jeszcze nie bylo ustawione,
- XP z `ChallengeReward` jest przyznawane tylko raz,
- po przyznaniu XP ustawiane jest `xp_awarded_at`,
- ukonczenie moze odblokowac achievement z triggerem `challenge_completed`,
- ukonczenie powinno utworzyc automatyczny wpis journala.

Cofanie:

- w MVP nie cofamy XP z challenge,
- jezeli challenge ma juz `xp_awarded_at`, nie pozwalamy cofnac go do statusu aktywnego przez endpoint Reacta,
- ewentualne reczne korekty zostaja w adminie i sa odpowiedzialnoscia uzytkownika.

### 5.6. Serwisy

Rekomendowane funkcje w `rpg/services.py`:

```py
def get_active_challenge() -> Challenge | None:
    ...

def update_challenge_progress(
    challenge: Challenge,
    current_value: int,
    *,
    note: str = "",
) -> Challenge:
    ...

def complete_challenge(
    challenge: Challenge,
    *,
    note: str = "",
) -> Challenge:
    ...

def award_challenge_xp(challenge: Challenge) -> list[XpEvent]:
    ...
```

Serwisy powinny:

- uzywac transakcji dla ukonczenia i XP,
- nie duplikowac `XpEvent`,
- wywolywac ewaluacje achievementow po ukonczeniu,
- tworzyc wpisy journala po istotnych zdarzeniach,
- zwracac obiekt lub dane potrzebne do odswiezenia dashboardu.

### 5.7. Endpointy

Standardowe Django JSON views, bez DRF.

#### `POST /api/challenges/<id>/progress/`

Cel: reczna aktualizacja postepu.

Ten endpoint nie przyznaje XP. Zwraca tylko zaktualizowany progress. XP za challenge moze powstac dopiero po wywolaniu endpointu `complete`.

Request:

```json
{
  "current_value": 14,
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
    "target_unit": "days",
    "progress_percent": 47,
    "reward_title": "Epic Willpower Badge",
    "reward_xp": 250
  }
}
```

#### `POST /api/challenges/<id>/complete/`

Cel: ukonczenie challenge.

Request:

```json
{
  "note": "Finished the challenge"
}
```

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
      "skill": "Discipline",
      "amount": 250,
      "source_type": "challenge"
    }
  ],
  "unlocked_achievements": [
    {
      "title": "Unstoppable",
      "rarity": "epic"
    }
  ]
}
```

### 5.8. Dashboard API

`GET /api/dashboard/` powinien zwracac `active_challenge` z bazy albo `null`.

`active_challenge` jest nullable:

- przed wdrozeniem Modulu 5,
- gdy nie istnieje aktywny challenge,
- gdy wszystkie challenge maja status inny niz `active`.

Przyklad:

```json
{
  "active_challenge": {
    "id": 1,
    "title": "30 Days No Sugar",
    "current_value": 14,
    "target_value": 30,
    "target_unit": "days",
    "progress_percent": 47,
    "reward_title": "Epic Willpower Badge",
    "reward_xp": 250,
    "status": "active"
  }
}
```

Przyklad braku aktywnego challenge:

```json
{
  "active_challenge": null
}
```

Backend API pozostaje w `snake_case`. React mapper moze przemapowac te pola na `camelCase` dla komponentow.

Finalny backendowy DTO `active_challenge` ma pola: `id`, `title`, `status`, `current_value`, `target_value`, `target_unit`, `progress_percent`, `reward_title`, `reward_xp`.

Legacy pola `name`, `day`, `total`, `progress`, `reward` sa dopuszczalne tylko jako przejsciowe aliasy, jezeli trzeba utrzymac stary React przez jeden etap migracji.

### 5.9. Admin

Admin dla `Challenge`:

- `list_display`: `title`, `status`, `current_value`, `target_value`, `start_date`, `end_date`, `completed_at`,
- `list_filter`: `status`, `created_by`, `start_date`, `end_date`,
- `search_fields`: `title`, `description`, `reward_title`,
- `readonly_fields`: `created_at`, `updated_at`, `completed_at`, `xp_awarded_at`,
- inline dla `ChallengeReward`.

Admin dla `ChallengeReward`:

- mozliwy osobny widok albo inline,
- filtrowanie po `skill`,
- walidacja dodatniego XP.

### 5.10. Seed

`seed_life_rpg` powinien tworzyc idempotentnie:

- challenge `30 Days No Sugar`,
- `status=active`,
- `start_date=today - 13 days`,
- `end_date=start_date + 29 days`,
- `target_value=30`,
- `target_unit=days`,
- `current_value=14`,
- `reward_title=Epic Willpower Badge`,
- reward XP opcjonalny, rekomendacja: `Discipline +250 XP`.

Seed nie powinien duplikowac challenge przy kolejnym uruchomieniu.

### 5.11. Pliki do zmiany

- `rpg/models.py`,
- `rpg/admin.py`,
- `rpg/services.py`,
- `rpg/views.py`,
- `rpg/urls.py`,
- `rpg/tests.py`,
- `dashboard/views.py`,
- `config/urls.py`, jezeli endpointy `rpg` nie sa jeszcze podpiete,
- `activities/management/commands/seed_life_rpg.py`,
- `frontend/src/api/dashboard.ts`,
- komponent React dla active challenge.

### 5.12. Kolejnosc implementacji

1. Dodac modele `Challenge` i `ChallengeReward`.
2. Dodac migracje.
3. Dodac admin i inline rewardow.
4. Dodac serwis `get_active_challenge`.
5. Rozszerzyc dashboard API.
6. Dodac seed `30 Days No Sugar`.
7. Dodac endpoint progress.
8. Dodac endpoint complete i XP.
9. Podpiac trigger achievementow, jezeli modul 6 jest juz dostepny.
10. Podpiac automatyczny journal, jezeli modul 7 jest juz dostepny.
11. Podpiac React challenge panel do realnych danych.

### 5.13. Kryteria akceptacji

- `python manage.py migrate` tworzy tabele challenge,
- admin pozwala utworzyc challenge i rewardy,
- seed tworzy `30 Days No Sugar`,
- dashboard pokazuje aktywny challenge z bazy,
- endpoint progress aktualizuje `current_value`,
- endpoint complete ustawia `completed`,
- XP z challenge jest tworzone tylko raz,
- ponowne wywolanie complete nie duplikuje XP,
- testy challenge przechodza na PostgreSQL.

### 5.14. Testy

Minimalne testy:

- challenge nie pozwala na `end_date < start_date`,
- `current_value` jest ograniczany do `target_value`,
- `get_active_challenge` zwraca aktywny challenge z najblizszym koncem,
- dashboard zwraca `active_challenge` z bazy,
- progress endpoint aktualizuje challenge,
- complete endpoint ustawia status `completed`,
- complete endpoint tworzy `XpEvent` dla kazdego rewardu,
- powtorne complete nie tworzy dodatkowych `XpEvent`,
- seed jest idempotentny.

## 6. Modul 6: Achievementy

### 6.1. Cel

Achievementy reprezentuja odznaki za wazne zdarzenia w systemie.

Pierwsza implementacja ma pozwalac:

- definiowac achievementy w adminie,
- odblokowywac achievementy recznie,
- odblokowywac achievementy przez proste triggery,
- pokazac badge na dashboardzie,
- tworzyc wpis journala po odblokowaniu.

Achievement nie przyznaje XP. XP moze przyjsc z questa, habitu, milestone albo challenge, ale nie z samej odznaki.

### 6.2. Zakres

W zakresie:

- model `Achievement`,
- model `AchievementUnlock`,
- manual unlock,
- trigger `habit_streak`,
- trigger `skill_level`,
- trigger `quest_count`,
- trigger `challenge_completed`,
- dashboard badges,
- admin,
- seed achievementow,
- testy domenowe i API.

Poza zakresem:

- achievement points,
- XP za achievement,
- sklep nagrod,
- inventory,
- zaawansowany silnik reguly,
- UI pelnego archiwum achievementow.

### 6.3. Model `Achievement`

Model: `rpg.Achievement`

Pola:

- `id`,
- `title` - `CharField(max_length=160)`,
- `description` - `TextField(blank=True)`,
- `rarity` - `CharField` z `TextChoices`,
- `trigger_type` - `CharField` z `TextChoices`,
- `trigger_config` - `JSONField(default=dict, blank=True)`,
- `icon` - `CharField(max_length=80, blank=True)`,
- `is_active` - `BooleanField(default=True)`,
- `sort_order` - `PositiveIntegerField(default=0)`,
- `created_at`,
- `updated_at`.

Rekomendowane `rarity`:

- `common`,
- `rare`,
- `epic`,
- `legendary`.

Rekomendowane `trigger_type`:

- `manual`,
- `habit_streak`,
- `skill_level`,
- `quest_count`,
- `challenge_completed`.

Przyklady `trigger_config`:

```json
{
  "habit_id": 1,
  "streak_days": 7
}
```

```json
{
  "skill_id": 2,
  "level": 5
}
```

```json
{
  "quest_count": 25,
  "period": "all_time"
}
```

```json
{
  "challenge_id": 1
}
```

`trigger_config` w bazie uzywa `snake_case` i stabilnych ID. Nazwy, np. `skill_name`, `habit_name` albo `challenge_title`, sa dozwolone tylko jako fallback seedowy, jezeli rekord nie ma jeszcze znanego ID w momencie tworzenia danych.

### 6.4. Model `AchievementUnlock`

Model: `rpg.AchievementUnlock`

Pola:

- `id`,
- `achievement` - `OneToOneField` albo `ForeignKey(unique=True)` do `Achievement`,
- `unlocked_at` - `DateTimeField`,
- `source_type` - `CharField(max_length=40)`,
- `source_id` - `PositiveIntegerField(null=True, blank=True)`,
- `note` - `TextField(blank=True)`,
- `created_at`.

Zasady:

- w wersji single-user jeden achievement mozna odblokowac tylko raz,
- `AchievementUnlock` nie ma pola XP,
- `source_type` zapisuje skad przyszlo odblokowanie, np. `manual`, `quest`, `habit`, `challenge`, `skill`,
- `source_id` jest opcjonalne i sluzy do lekkiego powiazania ze zdarzeniem,
- brak `GenericForeignKey` w MVP.

### 6.5. Reguly domenowe

Manual unlock:

- achievement z dowolnym `trigger_type` mozna odblokowac recznie w adminie,
- endpoint manual unlock powinien byc dostepny tylko lokalnie i w MVP moze nie miec rozbudowanych uprawnien,
- odblokowanie reczne uzywa `source_type=manual`.

Trigger `habit_streak`:

- serwis habitow po zmianie check-inu moze przekazac `habit` i aktualny streak do ewaluacji,
- trigger odblokowuje achievement, jezeli streak jest rowny albo wiekszy niz wymagany,
- `trigger_config` moze ograniczac achievement do konkretnego habitu albo dzialac globalnie.

Trigger `skill_level`:

- po utworzeniu XP eventu mozna sprawdzic aktualny level skilla,
- trigger odblokowuje achievement, jezeli skill osiagnal wymagany level,
- konfiguracja powinna wspierac konkretny skill przez `skill_id`,
- trigger powinien byc ewaluowany po kazdym nowym `skills.XpEvent`, takze po XP z aktywnosci, a nie tylko po XP z mechanik `rpg`.

Trigger `quest_count`:

- po wykonaniu questa mozna policzyc laczna liczbe ukonczonych questow jako liczbe `QuestCompletion` z `completed_at IS NOT NULL`,
- trigger odblokowuje achievement, jezeli liczba jest rowna albo wieksza od progu,
- na start wystarczy `period=all_time`.

Trigger `challenge_completed`:

- po ukonczeniu challenge serwis achievementow sprawdza aktywne achievementy tego typu,
- konfiguracja moze wskazywac konkretny challenge przez `challenge_id`,
- brak konkretnego challenge w konfiguracji oznacza dowolny ukonczony challenge.

### 6.6. Serwisy

Rekomendowane funkcje w `rpg/services.py`:

```py
def unlock_achievement(
    achievement: Achievement,
    *,
    source_type: str,
    source_id: int | None = None,
    note: str = "",
) -> AchievementUnlock:
    ...

def evaluate_achievement_triggers(
    *,
    trigger_type: str,
    context: dict,
) -> list[AchievementUnlock]:
    ...

def evaluate_habit_streak_achievements(habit: Habit, streak_days: int) -> list[AchievementUnlock]:
    ...

def evaluate_skill_level_achievements(skill: Skill) -> list[AchievementUnlock]:
    ...

def evaluate_quest_count_achievements() -> list[AchievementUnlock]:
    ...

def evaluate_challenge_completed_achievements(challenge: Challenge) -> list[AchievementUnlock]:
    ...
```

Serwisy powinny:

- filtrowac tylko `is_active=True`,
- byc idempotentne,
- nie rzucac bledu przy juz odblokowanym achievement,
- tworzyc wpis journala po nowym unlocku,
- zwracac tylko nowo odblokowane achievementy.

### 6.7. Endpointy

#### `POST /api/achievements/<id>/unlock/`

Cel: reczne odblokowanie achievementu.

Request:

```json
{
  "note": "Unlocked manually from dashboard"
}
```

Response:

```json
{
  "achievement": {
    "id": 1,
    "title": "Early Riser",
    "rarity": "common",
    "unlocked": true,
    "unlocked_at": "2026-06-10T08:00:00+02:00"
  }
}
```

Endpoint jest przydatny developersko i do lokalnego MVP. Docelowo wiekszosc unlockow powinna isc przez serwisy domenowe.

### 6.8. Dashboard API

`GET /api/dashboard/` powinien zwracac ostatnio odblokowane badge oraz opcjonalnie liste zablokowanych.

Minimalny kontrakt:

```json
{
  "achievements": [
    {
      "id": 1,
      "title": "Early Riser",
      "description": "Wake up before 7 AM",
      "rarity": "common",
      "icon": "sunrise",
      "unlocked": true,
      "unlocked_at": "2026-06-10T08:00:00+02:00"
    }
  ]
}
```

Dashboard powinien zaczac od ostatnich odblokowanych achievementow. Pelne archiwum moze powstac pozniej.

### 6.9. Admin

Admin dla `Achievement`:

- `list_display`: `title`, `rarity`, `trigger_type`, `is_active`, `sort_order`,
- `list_filter`: `rarity`, `trigger_type`, `is_active`,
- `search_fields`: `title`, `description`,
- `readonly_fields`: `created_at`, `updated_at`,
- inline albo osobny link do `AchievementUnlock`.

Admin dla `AchievementUnlock`:

- `list_display`: `achievement`, `source_type`, `unlocked_at`,
- `list_filter`: `source_type`, `unlocked_at`,
- `search_fields`: `achievement__title`, `note`,
- `readonly_fields`: `created_at`.

### 6.10. Seed

Seed powinien tworzyc idempotentnie minimum:

- `Early Riser` - `manual` albo przyszly trigger statusu,
- `Book Worm` - `skill_level`, np. Reading level 3,
- `Warrior` - `habit_streak`, np. Train 7 dni,
- `Iron Discipline` - `habit_streak`, dowolny habit 14 dni,
- `Unstoppable` - `challenge_completed`, `30 Days No Sugar`,
- `Legendary` - `quest_count`, np. 100 questow.

Seed moze odblokowac 1-2 achievementy demonstracyjne, ale powinno byc jasne, ze reszta jest locked.

### 6.11. Pliki do zmiany

- `rpg/models.py`,
- `rpg/admin.py`,
- `rpg/services.py`,
- `rpg/views.py`,
- `rpg/urls.py`,
- `rpg/tests.py`,
- `dashboard/views.py`,
- `activities/management/commands/seed_life_rpg.py`,
- `frontend/src/api/dashboard.ts`,
- komponent React dla achievements.

### 6.12. Kolejnosc implementacji

1. Dodac modele `Achievement` i `AchievementUnlock`.
2. Dodac migracje i constraints.
3. Dodac admin.
4. Dodac serwis `unlock_achievement`.
5. Dodac endpoint manual unlock.
6. Rozszerzyc dashboard API o badges.
7. Dodac seed achievementow.
8. Dodac trigger `challenge_completed`.
9. Dodac trigger `habit_streak`.
10. Dodac trigger `skill_level`.
11. Dodac trigger `quest_count`.
12. Podpiac wpis journala, jezeli modul 7 jest dostepny.
13. Podpiac React achievements panel do realnych danych.

### 6.13. Kryteria akceptacji

- admin pozwala definiowac achievementy,
- achievement mozna odblokowac recznie,
- ten sam achievement nie moze zostac odblokowany dwa razy,
- achievement nie tworzy `XpEvent`,
- trigger `challenge_completed` dziala po ukonczeniu challenge,
- trigger `habit_streak` dziala po osiagnieciu streaka,
- trigger `skill_level` dziala po osiagnieciu levelu skilla,
- trigger `quest_count` dziala po ukonczeniu wymaganej liczby questow,
- dashboard pokazuje odblokowane badge z bazy.

### 6.14. Testy

Minimalne testy:

- `AchievementUnlock` jest unikalny per achievement,
- manual unlock tworzy unlock,
- manual unlock drugi raz nie tworzy duplikatu,
- unlock nie tworzy `XpEvent`,
- `habit_streak` odblokowuje achievement po progu,
- `skill_level` odblokowuje achievement po progu,
- `quest_count` odblokowuje achievement po progu,
- `challenge_completed` odblokowuje achievement po ukonczeniu challenge,
- dashboard zwraca achievementy z bazy,
- seed jest idempotentny.

## 7. Modul 7: Journal

### 7.1. Cel

Journal jest osobnym modelem historii rozwoju uzytkownika.

Pierwsza implementacja ma pozwalac:

- tworzyc reczne wpisy,
- tworzyc automatyczne wpisy po waznych zdarzeniach,
- pokazac ostatnie wpisy na dashboardzie,
- dodac endpoint `POST /api/journal/` dla Reacta.

Journal nie jest tylko feedem skladanym w dashboardzie. Wpisy sa realnymi rekordami w bazie.

### 7.2. Zakres

W zakresie:

- model `JournalEntry`,
- reczne wpisy,
- automatyczne wpisy po quest completion,
- automatyczne wpisy po habit milestone,
- automatyczne wpisy po achievement unlock,
- automatyczne wpisy po challenge progress,
- automatyczne wpisy po challenge completion,
- endpoint `POST /api/journal/`,
- dashboard recent entries,
- admin,
- seed przykladowych wpisow,
- testy.

Poza zakresem:

- edytor markdown rich text,
- tagi,
- wyszukiwanie pelnotekstowe,
- eksport PDF,
- AI podsumowania tygodnia,
- prywatnosc per wpis, bo MVP jest single-user.

### 7.3. Model `JournalEntry`

Model: `rpg.JournalEntry`

Pola:

- `id`,
- `title` - `CharField(max_length=180)`,
- `content` - `TextField(blank=True)`,
- `entry_type` - `CharField` z `TextChoices`,
- `mood` - `CharField(max_length=40, blank=True)`,
- `source_type` - `CharField(max_length=40, blank=True)`,
- `source_id` - `PositiveIntegerField(null=True, blank=True)`,
- `entry_date` - `DateField`,
- `created_at`,
- `updated_at`.

Rekomendowane `entry_type`:

- `manual`,
- `quest`,
- `habit`,
- `habit_milestone`,
- `challenge`,
- `achievement`,
- `system`.

Rekomendowane `source_type`:

- `quest_completion`,
- `habit_checkin`,
- `habit_milestone_unlock`,
- `challenge_progress`,
- `challenge_completed`,
- `achievement_unlock`,
- `manual`.

Zasady:

- `title` nie moze byc puste,
- `entry_date` dla wpisow recznych domyslnie `timezone.localdate()`,
- wpisy automatyczne maja ustawione `source_type` i `source_id`,
- brak `GenericForeignKey` w MVP,
- `(source_type, source_id)` moze byc uzyte do idempotencji automatycznych wpisow tylko wtedy, gdy `source_type` nie jest puste i `source_id` nie jest `null`,
- reczne wpisy nie musza miec `source_type` ani `source_id`.

### 7.4. Reguly domenowe

Reczne wpisy:

- uzytkownik moze dodac wpis z dashboardu,
- wymagany jest `title`,
- `content` jest opcjonalny,
- `mood` jest opcjonalny,
- wpis reczny ma `entry_type=manual`.

Automatyczne wpisy:

- quest completion tworzy wpis typu `quest`,
- habit milestone tworzy wpis typu `habit_milestone`,
- achievement unlock tworzy wpis typu `achievement`,
- challenge progress moze tworzyc wpis typu `challenge`, ale nie musi przy kazdej drobnej zmianie,
- challenge completion tworzy wpis typu `challenge`.

Ograniczenie spamu:

- automatyczny wpis dla tego samego `source_type` i `source_id` powinien byc tworzony tylko raz,
- dla challenge progress mozna tworzyc wpis tylko przy istotnych progach, np. 25%, 50%, 75%, 100%, albo tylko gdy request zawiera `note`,
- w MVP rekomendacja: tworzyc wpis dla challenge progress tylko przy `note` lub completion.

Odpornosc:

- blad utworzenia automatycznego journala nie powinien cofac XP, completion ani innej glownej akcji domenowej,
- blad recznego endpointu journala powinien zwrocic `400` z bledem walidacji.

### 7.5. Serwisy

Rekomendowane funkcje w `rpg/services.py`:

```py
def create_journal_entry(
    *,
    title: str,
    content: str = "",
    entry_type: str = "manual",
    mood: str = "",
    source_type: str = "",
    source_id: int | None = None,
    entry_date: date | None = None,
) -> JournalEntry:
    ...

def create_system_journal_entry(
    *,
    title: str,
    content: str = "",
    entry_type: str,
    source_type: str,
    source_id: int,
) -> JournalEntry:
    ...

def get_recent_journal_entries(limit: int = 5) -> QuerySet[JournalEntry]:
    ...
```

Serwisy powinny:

- walidowac pusty tytul,
- ustawiac domyslna date,
- dbac o idempotencje automatycznych wpisow,
- zwracac utworzony wpis.

Selektory journala dla dashboardu powinny filtrowac zakresy po `entry_date`, a sortowac ostatnie wpisy deterministycznie po `created_at` z tie-breakerem po `id`.

### 7.6. Endpointy

#### `POST /api/journal/`

Cel: reczne utworzenie wpisu journalowego z Reacta.

Request:

```json
{
  "title": "Daily reflection",
  "content": "Today I completed every quest.",
  "mood": "focused",
  "entry_date": "2026-06-10"
}
```

Response:

```json
{
  "entry": {
    "id": 1,
    "title": "Daily reflection",
    "content": "Today I completed every quest.",
    "mood": "focused",
    "entry_type": "manual",
    "entry_date": "2026-06-10",
    "created_at": "2026-06-10T21:30:00+02:00"
  }
}
```

Walidacja:

- brak `title` zwraca `400`,
- niepoprawna data zwraca `400`,
- `content` moze byc puste.

### 7.7. Dashboard API

`GET /api/dashboard/` powinien zwracac ostatnie wpisy journala.

Zakres dashboardu filtruje journal po `entry_date`. Lista ostatnich wpisow powinna byc sortowana po `created_at` malejaco, z dodatkowym tie-breakerem po `id`.

Minimalny kontrakt:

```json
{
  "journal_entries": [
    {
      "id": 1,
      "title": "Daily reflection",
      "content": "Today I completed every quest.",
      "entry_type": "manual",
      "mood": "focused",
      "entry_date": "2026-06-10",
      "created_at": "2026-06-10T21:30:00+02:00"
    }
  ]
}
```

React moze mapowac te dane na obecny format `recentJournalEntries`.

### 7.8. Admin

Admin dla `JournalEntry`:

- `list_display`: `title`, `entry_type`, `entry_date`, `source_type`, `created_at`,
- `list_filter`: `entry_type`, `source_type`, `entry_date`, `mood`,
- `search_fields`: `title`, `content`,
- `readonly_fields`: `created_at`, `updated_at`,
- sortowanie domyslne: `-entry_date`, `-created_at`.

Admin powinien pozwalac dodawac reczne wpisy bez uzywania Reacta.

### 7.9. Seed

Seed powinien tworzyc idempotentnie minimum dwa wpisy:

- `First Entry`,
- `Weekly Reflection`.

Przykladowe dane:

- `First Entry` - entry type `manual`, content o starcie systemu,
- `Weekly Reflection` - entry type `system`, content o podsumowaniu tygodnia.

Seed nie powinien tworzyc nowych wpisow przy kazdym uruchomieniu, jezeli wpisy juz istnieja.

### 7.10. Pliki do zmiany

- `rpg/models.py`,
- `rpg/admin.py`,
- `rpg/services.py`,
- `rpg/views.py`,
- `rpg/urls.py`,
- `rpg/tests.py`,
- `dashboard/views.py`,
- `activities/management/commands/seed_life_rpg.py`,
- `frontend/src/api/dashboard.ts`,
- komponent React dla journal,
- komponent lub formularz React do dodawania wpisu.

### 7.11. Kolejnosc implementacji

1. Dodac model `JournalEntry`.
2. Dodac migracje.
3. Dodac admin.
4. Dodac serwis `create_journal_entry`.
5. Dodac endpoint `POST /api/journal/`.
6. Rozszerzyc dashboard API o recent entries.
7. Dodac seed wpisow.
8. Podpiac automatyczny wpis po quest completion, jezeli modul 1 jest gotowy.
9. Podpiac automatyczny wpis po habit milestone, jezeli modul 2 jest gotowy.
10. Podpiac automatyczny wpis po challenge progress/completion, jezeli modul 5 jest gotowy.
11. Podpiac automatyczny wpis po achievement unlock, jezeli modul 6 jest gotowy.
12. Podpiac React journal panel i formularz.

### 7.12. Kryteria akceptacji

- admin pozwala tworzyc i przegladac wpisy journala,
- endpoint `POST /api/journal/` tworzy reczny wpis,
- pusty tytul zwraca `400`,
- dashboard pokazuje ostatnie wpisy z bazy,
- quest completion moze tworzyc automatyczny wpis,
- habit milestone moze tworzyc automatyczny wpis,
- achievement unlock moze tworzyc automatyczny wpis,
- challenge progress albo completion moze tworzyc automatyczny wpis,
- automatyczne wpisy nie duplikuja sie dla tego samego zdarzenia.

### 7.13. Testy

Minimalne testy:

- reczny wpis mozna utworzyc przez serwis,
- reczny wpis mozna utworzyc przez API,
- pusty title zwraca blad,
- domyslna `entry_date` to dzisiejsza data lokalna,
- dashboard zwraca ostatnie wpisy,
- automatyczny wpis z `source_type` i `source_id` jest idempotentny,
- quest completion tworzy wpis, jezeli integracja jest dostepna,
- habit milestone tworzy wpis, jezeli integracja jest dostepna,
- achievement unlock tworzy wpis,
- challenge completion tworzy wpis,
- seed jest idempotentny.

## 8. Kolejnosc wdrozenia modulow 5-7

Rekomendowana kolejnosc:

1. Modul 7: `JournalEntry` jako infrastruktura wpisow.
2. Modul 5: `Challenge` i `ChallengeReward`.
3. Modul 6: `Achievement` i `AchievementUnlock`.
4. Integracje automatyczne:
   - challenge completion -> achievement trigger,
   - achievement unlock -> journal,
   - quest completion -> journal,
   - habit milestone -> journal.
5. React:
   - challenge panel live,
   - achievements badges live,
   - journal recent entries i formularz.

Uzasadnienie:

- Journal jest najprostszy i przyda sie jako wspolny dziennik zdarzen,
- Challenge moze dzialac z recznym postepem bez pelnego silnika achievementow,
- Achievementy maja najwiecej zaleznosci, wiec lepiej dodac je po modelach zdarzen.

Alternatywa:

- jezeli celem jest szybki efekt wizualny dashboardu, mozna zaczac od Modulu 5, potem Modul 6, potem Modul 7,
- wtedy automatyczne wpisy journala trzeba dopiac pozniej.

## 9. Kontrakt React

React pozostaje glownym frontendem.

Zasady:

- React pobiera dane przez `/api/dashboard/`,
- React wysyla mutacje do endpointow Django,
- localStorage moze przechowywac theme i ustawienia UI,
- localStorage nie jest zrodlem prawdy dla challenge, achievementow ani journala,
- po mutacji frontend powinien albo odswiezyc dashboard, albo uzyc danych zwroconych przez endpoint.

Minimalne mutacje React:

- challenge progress,
- challenge complete,
- manual achievement unlock, jezeli UI ma taka akcje,
- create journal entry.

## 10. Kryteria akceptacji calego pakietu

Pakiet modulow 5-7 jest zakonczony, jezeli:

- migracje tworza modele `Challenge`, `ChallengeReward`, `Achievement`, `AchievementUnlock`, `JournalEntry`,
- admin obsluguje wszystkie nowe modele,
- seed tworzy challenge, achievementy i wpisy journala,
- dashboard pokazuje challenge, achievementy i journal z bazy,
- endpointy JSON dzialaja bez DRF,
- XP za challenge jest zapisywane przez `skills.XpEvent`,
- achievementy nie tworza XP,
- manual journal entry dziala przez React/API,
- automatyczne wpisy journala dzialaja dla dostepnych zdarzen,
- testy backendowe przechodza,
- `npm run typecheck` i `npm run build` przechodza po podpieciu Reacta.

## 11. Minimalny zestaw testow regresji

Przed uznaniem implementacji za gotowa uruchomic:

```bash
.venv/bin/python manage.py test
```

Po zmianach React:

```bash
cd frontend
npm run typecheck
npm run build
```

Testy backendowe powinny pokrywac:

- walidacje modelu challenge,
- idempotencje XP challenge,
- manual unlock achievementu,
- idempotencje unlocku achievementu,
- brak XP za achievement,
- tworzenie recznego journala,
- idempotencje automatycznych wpisow journala,
- dashboard API z realnymi danymi,
- idempotencje seedow.
