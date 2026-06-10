# Life RPG Tracker - specyfikacja etapu 2: mechaniki RPG

## 1. Cel etapu

Etap 2 ma zamienic obecny dashboard z interaktywnym prototypem UI w prawdziwy system mechanik RPG oparty o baze danych.

Po zakonczeniu etapu aplikacja ma pozwalac jednemu lokalnemu uzytkownikowi:

- definiowac questy dzienne i jednorazowe,
- oznaczac questy jako wykonane,
- przyznawac XP z questow do jednego albo wielu skilli,
- definiowac habity,
- odhaczac habity w konkretnym dniu,
- liczyc streaki habitow,
- przyznawac XP za milestone streakow,
- definiowac wyzwania dlugoterminowe,
- sledzic postep wyzwan,
- odblokowywac achievementy,
- prowadzic osobny journal,
- pokazywac te dane na dashboardzie bez fikcyjnych placeholderow,
- zachowac wspolny ledger XP przez `skills.XpEvent`.

Etap 2 nadal nie obejmuje pelnej integracji z AI. Questy AI powinny byc uwzglednione architektonicznie, ale ich generowanie moze zostac zrealizowane w osobnym etapie.

## 2. Zakres

### W zakresie

- nowa aplikacja Django `rpg`,
- modele dla questow, habitow, milestone streakow, wyzwan, achievementow i journala,
- migracje,
- Django Admin,
- serwisy domenowe do kompletowania questow i habitow,
- tworzenie `XpEvent` dla nagrod questow, challenge i milestone streakow,
- standardowe endpointy JSON dla klikniec z dashboardu React,
- dashboard korzystajacy z prawdziwych danych,
- seed danych startowych,
- testy modeli, serwisow i dashboardu.

### Poza zakresem

- automatyczne generowanie questow przez OpenAI API albo Claude API,
- ActivityWatch importer,
- multi-user,
- modul finansow,
- DRF,
- Celery,
- rozbudowany sklep/inventory/cosmetics.

## 3. Proponowana architektura

Decyzja: dodac jedna aplikacje:

- `rpg` - questy, habity, milestone streakow, wyzwania, achievementy, journal i mechaniki progresji.

Uzasadnienie:

- zakres jest powiazany funkcjonalnie,
- dla lokalnego MVP osobne aplikacje `quests`, `habits`, `achievements` bylyby przedwczesnym rozbiciem,
- modele nadal moga byc czytelnie podzielone plikami w przyszlosci, jezeli aplikacja urosnie.

Relacje do istniejacych aplikacji:

- `rpg` tworzy XP przez `skills.XpEvent`,
- nagrody wskazuja na `skills.Skill`,
- dashboard pobiera dane z `rpg`,
- aktywnosci z `activities` pozostaja osobnym zrodlem XP,
- statusy z `statuses` pozostaja osobnym systemem, bez levelowania.

Decyzja po analizie modulow: jedna aplikacja `rpg` zastepuje wszystkie wczesniejsze pomysly osobnych aplikacji typu `quests`, `habits` albo `achievements`.

Backend JSON API dla mechanik RPG uzywa `snake_case`. React mapuje payloady do `camelCase` tylko w mapperze/typach frontendu.

Daily questy i streaki dzialaja wedlug lokalnej daty aplikacji. Dla lokalnego MVP rekomendowane ustawienie projektu to `TIME_ZONE = "Europe/Warsaw"`.

## 4. Zasady XP

Wspolnym zrodlem prawdy dla XP pozostaje `skills.XpEvent`.

Dozwolone wartosci `source_type`:

- `activity` - XP z aktywnosci,
- `quest` - XP z questa,
- `habit_milestone` - XP za osiagniecie progu streaka,
- `challenge` - XP za ukonczenie wyzwania,
- `manual` - reczne korekty w przyszlosci.

Zasady:

- quest moze dawac XP do wielu skilli,
- challenge moze dawac XP do wielu skilli,
- achievement nie daje XP w MVP,
- pojedynczy habit check-in nie daje XP,
- streak habitow moze dawac XP tylko przez milestone,
- kazde przyznanie XP musi tworzyc osobny `XpEvent`,
- nie dodawac pola `xp` bezposrednio do `Skill`.

## 5. Questy

### 5.1. Quest

Model: `rpg.Quest`

Quest reprezentuje zadanie, ktore uzytkownik moze wykonac i odebrac nagrode.

Pola:

- `id`,
- `title` - `CharField`, wymagane,
- `description` - `TextField`, opcjonalne,
- `quest_type` - `CharField`, np. `daily`, `weekly`, `one_time`, `ai_generated`,
- `status` - `CharField`, np. `draft`, `active`, `archived`,
- `difficulty` - `CharField`, np. `easy`, `normal`, `hard`, `epic`,
- `target_value` - `PositiveIntegerField`, domyslnie `1`,
- `target_unit` - `CharField`, np. `count`, `minutes`, `steps`, `pages`,
- `created_by` - `CharField`, np. `manual`, `system`, `ai`,
- `available_from` - `DateField`, opcjonalne,
- `available_until` - `DateField`, opcjonalne,
- `created_at`,
- `updated_at`.

Zasady:

- `title` nie moze byc puste,
- `target_value` musi byc wieksze od `0`,
- quest dzienny powinien miec wykonanie liczone per data,
- quest jednorazowy moze zostac wykonany tylko raz,
- quest z `created_by=ai` musi startowac jako `status=draft`,
- AI generuje propozycje questa, a uzytkownik zatwierdza ja przed aktywacja.

### 5.2. QuestReward

Model: `rpg.QuestReward`

Opisuje nagrode XP z questa do konkretnego skilla.

Pola:

- `id`,
- `quest` - `ForeignKey` do `Quest`,
- `skill` - `ForeignKey` do `skills.Skill`,
- `xp_amount` - `PositiveIntegerField`.

Zasady:

- para `quest` + `skill` musi byc unikalna,
- `xp_amount` musi byc wieksze od `0`,
- quest moze miec wiele nagrod,
- kompletowanie questa tworzy jeden `XpEvent` per `QuestReward`.

### 5.3. QuestCompletion

Model: `rpg.QuestCompletion`

Reprezentuje wykonanie questa w konkretnym dniu albo czasie.

Pola:

- `id`,
- `quest` - `ForeignKey` do `Quest`,
- `completed_on` - `DateField`,
- `progress_value` - `PositiveIntegerField`, domyslnie `0`,
- `completed_at` - `DateTimeField`, opcjonalne,
- `xp_awarded_at` - `DateTimeField`, opcjonalne,
- `note` - `TextField`, opcjonalne,
- `created_at`,
- `updated_at`.

Zasady:

- dla questow dziennych para `quest` + `completed_on` musi byc unikalna,
- `completed_at` ustawiamy dopiero po osiagnieciu celu,
- `xp_awarded_at` ustawiamy po utworzeniu wszystkich `XpEvent`,
- XP przyznajemy tylko raz dla jednego wykonania,
- questy musza obslugiwac czastkowy `progress_value`, nawet jezeli UI zaczyna od prostego checkboxa,
- trzeba miec zabezpieczenie przed podwojnym kliknieciem i podwojnym XP.

## 6. Habity

### 6.1. Habit

Model: `rpg.Habit`

Habit reprezentuje powtarzalny nawyk.

Pola:

- `id`,
- `name` - `CharField`, wymagane,
- `description` - `TextField`, opcjonalne,
- `frequency` - `CharField`, np. `daily`, `weekly`,
- `target_value` - `PositiveIntegerField`, domyslnie `1`,
- `target_unit` - `CharField`, np. `check`, `minutes`, `pages`, `steps`,
- `is_active` - `BooleanField`, domyslnie `True`,
- `sort_order` - `PositiveIntegerField`, domyslnie `0`,
- `created_at`,
- `updated_at`.

Zasady:

- habit nie musi dawac XP za kazde odhaczenie,
- habit powinien budowac streak,
- habit moze pozniej generowac quest dzienny,
- habit musi byc edytowalny w adminie.

### 6.2. HabitCheckIn

Model: `rpg.HabitCheckIn`

Reprezentuje wykonanie habitu w konkretnym dniu.

Pola:

- `id`,
- `habit` - `ForeignKey` do `Habit`,
- `checked_on` - `DateField`,
- `value` - `PositiveIntegerField`, domyslnie `1`,
- `note` - `TextField`, opcjonalne,
- `created_at`,
- `updated_at`.

Zasady:

- para `habit` + `checked_on` musi byc unikalna,
- check-in mozna wlaczac i wylaczac z dashboardu,
- streak liczymy z kolejnych dni, w ktorych check-in istnieje i spelnia target,
- pojedynczy check-in nie przyznaje XP,
- XP moze byc przyznane dopiero przez milestone streaka.

### 6.3. HabitMilestone

Model: `rpg.HabitMilestone`

Reprezentuje prog streaka, ktory moze odblokowac nagrode.

Pola:

- `id`,
- `habit` - `ForeignKey` do `Habit`, opcjonalny,
- `title` - `CharField`, wymagane,
- `streak_days` - `PositiveIntegerField`,
- `is_active` - `BooleanField`, domyslnie `True`,
- `created_at`,
- `updated_at`.

Zasady:

- jezeli `habit` jest ustawiony, milestone dotyczy konkretnego habitu,
- jezeli `habit` jest pusty, milestone moze byc globalny dla dowolnego habitu,
- `streak_days` musi byc wieksze od `0`,
- milestone moze przyznac XP tylko raz.

### 6.4. HabitMilestoneReward

Model: `rpg.HabitMilestoneReward`

Opisuje XP za osiagniecie milestone streaka.

Pola:

- `id`,
- `milestone` - `ForeignKey` do `HabitMilestone`,
- `skill` - `ForeignKey` do `skills.Skill`,
- `xp_amount` - `PositiveIntegerField`.

Zasady:

- para `milestone` + `skill` musi byc unikalna,
- `xp_amount` musi byc wieksze od `0`,
- milestone moze nagradzac kilka skilli.

### 6.5. HabitMilestoneUnlock

Model: `rpg.HabitMilestoneUnlock`

Reprezentuje odblokowanie milestone dla konkretnego habitu.

Pola:

- `id`,
- `milestone` - `ForeignKey` do `HabitMilestone`,
- `habit` - `ForeignKey` do `Habit`,
- `unlocked_at` - `DateTimeField`,
- `xp_awarded_at` - `DateTimeField`, opcjonalne,
- `streak_days` - `PositiveIntegerField`,
- `note` - `TextField`, opcjonalne.

Zasady:

- para `milestone` + `habit` musi byc unikalna,
- odblokowanie tworzy `XpEvent` z `source_type=habit_milestone` dla kazdej nagrody,
- `xp_awarded_at` ustawiamy po utworzeniu wszystkich `XpEvent`,
- milestone nie powinien byc cofany automatycznie, jezeli uzytkownik przerwie streak pozniej.

## 7. Wyzwania

### 7.1. Challenge

Model: `rpg.Challenge`

Challenge reprezentuje dluzsze wyzwanie z celem i nagroda.

Pola:

- `id`,
- `title` - `CharField`, wymagane,
- `description` - `TextField`, opcjonalne,
- `status` - `CharField`, np. `planned`, `active`, `completed`, `failed`, `archived`,
- `start_date` - `DateField`,
- `end_date` - `DateField`,
- `target_value` - `PositiveIntegerField`,
- `target_unit` - `CharField`, np. `days`, `checkins`, `minutes`, `count`,
- `current_value` - `PositiveIntegerField`, domyslnie `0`,
- `reward_title` - `CharField`, opcjonalne,
- `created_by` - `CharField`, np. `manual`, `system`, `ai`,
- `created_at`,
- `updated_at`.

Zasady:

- `end_date` nie moze byc wczesniejsze niz `start_date`,
- aktywne wyzwanie pokazujemy na dashboardzie,
- `current_value` jest aktualizowane recznie w MVP,
- wyzwanie moze byc powiazane z habitem albo questem w pozniejszej wersji,
- ukonczenie wyzwania moze przyznac XP i achievement.

### 7.2. ChallengeReward

Model: `rpg.ChallengeReward`

Pola:

- `id`,
- `challenge` - `ForeignKey` do `Challenge`,
- `skill` - `ForeignKey` do `skills.Skill`,
- `xp_amount` - `PositiveIntegerField`.

Zasady:

- jedna nagroda per skill w ramach jednego challenge,
- XP przyznajemy tylko raz po ukonczeniu wyzwania.

## 8. Achievementy

### 8.1. Achievement

Model: `rpg.Achievement`

Achievement reprezentuje odznake, ktora moze zostac odblokowana.

Pola:

- `id`,
- `title` - `CharField`, wymagane,
- `description` - `TextField`, opcjonalne,
- `rarity` - `CharField`, np. `common`, `rare`, `epic`, `legendary`,
- `trigger_type` - `CharField`, np. `manual`, `skill_level`, `habit_streak`, `quest_count`, `challenge_completed`,
- `trigger_config` - `JSONField`, opcjonalne,
- `is_active` - `BooleanField`, domyslnie `True`,
- `created_at`,
- `updated_at`.

Zasady:

- achievement definicyjny nie oznacza jeszcze odblokowania,
- `trigger_config` przechowuje parametry w `snake_case` i preferuje stabilne ID, np. `{"skill_id": 2, "level": 5}`, `{"habit_id": 1, "streak_days": 7}`, `{"quest_count": 25}` albo `{"challenge_id": 1}`,
- nazwy rekordow sa dozwolone tylko jako fallback seedowy,
- w MVP mozna zaczac od manualnego odblokowywania i prostych triggerow w serwisie.

### 8.2. AchievementUnlock

Model: `rpg.AchievementUnlock`

Pola:

- `id`,
- `achievement` - `ForeignKey` do `Achievement`,
- `unlocked_at` - `DateTimeField`,
- `source_type` - `CharField`, np. `manual`, `quest`, `habit`, `challenge`, `skill`,
- `note` - `TextField`, opcjonalne.

Zasady:

- jeden achievement mozna odblokowac tylko raz,
- para `achievement` musi byc unikalna w wersji single-user,
- odblokowanie nie daje XP w MVP,
- dashboard pokazuje ostatnie odblokowane achievementy.

## 9. Streaki

Streaki nie musza byc osobnym modelem w pierwszej implementacji.

Rekomendacja:

- liczyc streak habitow dynamicznie z `HabitCheckIn`,
- przechowywac tylko faktyczne check-iny,
- dodac cached streak dopiero, jezeli obliczenia beda problemem.

Zasady liczenia dziennego streaka:

- bierzemy aktywny habit,
- sprawdzamy kolejne dni wstecz od dzisiaj,
- dzien zaliczony, jezeli `HabitCheckIn.value >= Habit.target_value`,
- streak konczy sie na pierwszej luce.

## 10. Journal

### 10.1. JournalEntry

Model: `rpg.JournalEntry`

JournalEntry reprezentuje reczny albo automatyczny wpis w dzienniku.

Pola:

- `id`,
- `title` - `CharField`, wymagane,
- `content` - `TextField`, opcjonalne,
- `entry_type` - `CharField`, np. `manual`, `activity`, `quest`, `habit`, `challenge`, `achievement`,
- `mood` - `CharField`, opcjonalne,
- `source_type` - `CharField`, opcjonalne,
- `source_id` - `PositiveIntegerField`, opcjonalne,
- `entry_date` - `DateField`,
- `created_at`,
- `updated_at`.

Zasady:

- journal jest osobnym modelem, a nie tylko feedem skladanym w dashboardzie,
- uzytkownik moze tworzyc reczne wpisy,
- system moze tworzyc wpisy automatyczne po waznych zdarzeniach,
- `source_type` i `source_id` sluza do lekkiego powiazania z aktywnoscia, questem, habit check-inem, challenge albo achievementem,
- w MVP nie trzeba dodawac `GenericForeignKey`, wystarcza jawne pola referencyjne tekst + id.

## 11. Dashboard

Dashboard powinien zastapic obecne dane prezentacyjne prawdziwymi danymi.

Sekcje:

- `Today's Quests` - aktywne questy dzienne na dzisiaj,
- `Habits` - aktywne habity i check-iny z dzisiaj,
- `Active Challenge` - najwazniejsze aktywne wyzwanie,
- `Achievements` - ostatnio odblokowane achievementy,
- `Journal` - ostatnie rekordy `JournalEntry`,
- `Weekly Progress` - XP z aktywnosci i questow,
- `Skills` - bez zmian, liczone z `XpEvent`.

Interakcje:

- klik questa w React powinien wyslac POST JSON i zapisac `QuestCompletion`,
- klik habitu w React powinien wyslac POST JSON i zapisac albo usunac `HabitCheckIn`,
- po sukcesie backend powinien zwrocic JSON z odswiezonym fragmentem stanu dashboardu,
- localStorage moze zostac tylko jako fallback UI, ale nie jako zrodlo prawdy.

## 12. Django Admin

Admin powinien pozwalac zarzadzac:

- questami,
- nagrodami questow,
- wykonaniami questow,
- habitami,
- check-inami habitow,
- milestone streakow,
- nagrodami milestone streakow,
- odblokowaniami milestone streakow,
- challenge,
- nagrodami challenge,
- achievementami,
- odblokowanymi achievementami,
- wpisami journala.

Wymagania:

- inline rewards dla questow i challenge,
- inline rewards dla milestone streakow,
- filtrowanie po statusie, typie, dacie i rarity,
- wyszukiwarka po tytule/nazwie,
- `readonly_fields` dla dat utworzenia i aktualizacji.

## 13. Seed danych

Seed powinien dodac:

- 5 questow dziennych,
- 7 habitow,
- milestone streakow dla 7, 14 i 30 dni,
- 1 aktywne wyzwanie,
- 6 achievementow,
- 2 przykladowe wpisy journala,
- nagrody XP do istniejacych skilli.

Przykladowe questy:

- Workout 30 minutes -> Fitness +25 XP,
- Read 20 minutes -> Reading +20 XP, Learning +5 XP,
- Study AI -> Learning +25 XP, Research +15 XP,
- Write notes -> Writing +20 XP,
- Plan tomorrow -> Writing +10 XP.

Przykladowe habity:

- Train,
- Read,
- Learn,
- Hydrate,
- Sleep,
- Journal,
- Review finances.

Przykladowe achievementy:

- Early Riser,
- Book Worm,
- Warrior,
- Iron Discipline,
- Unstoppable,
- Legendary.

Przykladowe milestone streakow:

- 7 Day Momentum -> Discipline albo Learning +50 XP,
- 14 Day Discipline -> Discipline albo Fitness +100 XP,
- 30 Day Identity Shift -> wybrany skill +250 XP.

Przykladowe wpisy journala:

- First Entry,
- Weekly Reflection.

## 14. Testy

Minimalny zakres testow:

- quest moze miec wiele nagrod XP,
- ukonczenie questa tworzy `QuestCompletion` i `XpEvent`,
- ponowne klikniecie tego samego questa nie dubluje XP,
- habit check-in jest unikalny per dzien,
- usuniecie check-inu aktualizuje streak,
- milestone streaka przyznaje XP tylko raz,
- challenge nie moze miec `end_date < start_date`,
- achievement moze byc odblokowany tylko raz,
- journal entry mozna utworzyc recznie i pokazac na dashboardzie,
- dashboard renderuje dane z modeli `rpg`,
- endpoint questa zwraca JSON potrzebny do odswiezenia stanu React,
- endpoint habitu zwraca JSON potrzebny do odswiezenia stanu React,
- seed jest idempotentny.

## 15. Decyzje i otwarte pytania

1. Aplikacja Django dla mechanik RPG

   Decyzja: jedna aplikacja `rpg`.

2. XP za habity

   Decyzja: habit check-in nie daje XP. Habity trzymaja streak, a XP moze wejsc dopiero przez milestone streaka.

3. Cofanie questa po ukonczeniu

   Status: otwarte, zalezne od decyzji o cofaniu XP.

4. Cofanie XP

   Status: otwarte.

   Opcje:

   - kasujemy `XpEvent`,
   - dodajemy ujemny korekcyjny event,
   - blokujemy cofanie po odebraniu nagrody.

   Rekomendacja robocza: dla MVP blokowac cofanie po odebraniu XP. Progress mozna zmieniac przed ukonczeniem questa, ale po przyznaniu XP completion staje sie zamkniete.

5. Progress questow

   Decyzja: questy maja `progress_value`.

6. Sposob reprezentacji questow dziennych

   Decyzja robocza: jedna definicja `Quest` + `QuestCompletion` per data.

7. Automatyczne achievementy

   Decyzja robocza: zaczac od manualnych i 2-3 prostych triggerow, np. habit streak i skill level.

8. Progress challenge

   Decyzja: na start reczny `current_value`.

9. Journal

   Decyzja: journal jest osobnym modelem `JournalEntry`.

10. AI-generated quest

    Decyzja: AI quest jest zwyklym `Quest` z `created_by=ai`.

11. Akceptacja AI questow

    Decyzja: AI tworzy draft/propozycje, uzytkownik zatwierdza.

12. XP za achievementy

    Decyzja: nie w MVP. Achievement jest odznaka, XP daje czyn albo milestone.

13. Wealth

    Decyzja robocza: zostaje atrybutem UI bez skilla do czasu modulu finansow.

14. React/API

    Decyzja: klikniecia questow i habitow robimy przez React + standardowe widoki Django zwracajace JSON, bez DRF.

15. `TextChoices`

    Decyzja robocza: `TextChoices` dla statusow technicznych modeli, ale nie dla danych uzytkownika takich jak skille, habity i questy.

## 16. Kryteria akceptacji

- `python manage.py migrate` tworzy tabele `rpg`,
- `python manage.py seed_life_rpg` tworzy startowe questy, habity, milestone, challenge, achievementy i wpisy journala,
- dashboard nie uzywa placeholderow dla questow, habitow, challenge, achievementow i journala,
- klikniecie questa zapisuje stan w bazie i przyznaje XP,
- klikniecie habitu zapisuje stan w bazie i aktualizuje streak,
- milestone streaka moze przyznac XP,
- achievement mozna odblokowac i pokazac na dashboardzie,
- journal jest osobnym modelem i jest widoczny na dashboardzie,
- klikniecia questow i habitow dzialaja w React przez endpointy JSON,
- testy przechodza na PostgreSQL,
- rozwiazanie nie dodaje DRF ani Celery.
