# Life RPG - Campaigns Module Spec

## 1. Cel modulu

Modul kampanii dodaje warstwe dluzszych, powiazanych ze soba questow.

Kampania reprezentuje wiekszy cel, projekt albo arc rozwoju, np.:

- Django Foundations,
- 30 Days Fitness Reset,
- Build Life RPG MVP,
- Financial Discipline Arc,
- AI Developer Path.

Kampania sklada sie z questow, ktore moga byc:

- sekwencyjne - kolejny quest odblokowuje sie po ukonczeniu poprzedniego,
- rownolegle - kilka questow moze byc aktywnych jednoczesnie,
- mieszane - etapy liniowe i rownolegle lacza sie w jedna mape progresu.

Kazda dobra kampania musi miec widok mapy, ktory pokazuje uzytkownikowi sciezke, odblokowane questy, zablokowane questy i postep calej kampanii.

## 2. Decyzje projektowe

### 2.1. Aplikacja Django

Nie tworzymy nowej aplikacji Django.

Kampanie trafiaja do istniejacej aplikacji `rpg`, poniewaz:

- kampanie sa bezposrednio powiazane z questami,
- `rpg` zawiera juz questy, habity, challenge, achievementy i journal,
- zaleznosci kampanii powinny korzystac z tej samej logiki completion i XP,
- unikamy duplikowania mechanik progresji.

### 2.2. Questy kampanii

Kampania uzywa istniejacego modelu `Quest`.

Nie tworzymy osobnego typu mini-questa.

Powiazanie kampanii z questem obsluguje model `CampaignQuest`, ktory dodaje:

- etap,
- kolejnosc,
- pozycje na mapie,
- informacje czy quest jest wymagany,
- zaleznosci od innych questow.

### 2.3. XP

XP pozostaje zapisywane tylko przez `skills.XpEvent`.

Zasady:

- pojedyncze questy kampanii daja XP przez istniejacy `QuestReward`,
- kampania moze miec bonus completion XP,
- bonus kampanii tez musi byc zapisany jako `XpEvent`,
- kampania nie przechowuje alternatywnego licznika XP,
- nie cofamy XP automatycznie po zmianie statusu kampanii.

### 2.4. AI generuje tylko draft

AI moze projektowac kampanie dla uzytkownika, ale nie aktywuje ich automatycznie.

Workflow:

```txt
user goal
-> AI generates campaign draft
-> user reviews and edits
-> user activates campaign
-> campaign becomes part of progression
```

Uzytkownik zawsze musi zatwierdzic kampanie przed aktywacja.

### 2.5. JSON API

Backend:

- zwykle widoki Django JSON,
- bez DRF,
- request i response w `snake_case`,
- React mapuje dane na `camelCase`,
- logika domenowa w `rpg/services.py`, nie bezposrednio w widokach.

## 3. Slownik domenowy

### Campaign

Wiekszy arc/projekt rozwoju skladajacy sie z wielu questow.

### Campaign Quest

Powiazanie kampanii z normalnym questem.

### Dependency

Relacja blokujaca quest do czasu ukonczenia innego questa.

### Stage

Logiczny etap kampanii, np. `Setup`, `Core Skills`, `Final Project`.

### Map

Widok grafu kampanii. Pokazuje questy jako wezly i zaleznosci jako polaczenia.

## 4. TextChoices

Nowe choices powinny trafic do `rpg/choices.py`.

### CampaignStatus

```python
class CampaignStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"
```

Zasady:

- `draft` - kampania edytowalna, nieaktywna,
- `active` - kampania widoczna w progresji,
- `completed` - wszystkie wymagane questy sa ukonczone,
- `archived` - ukryta z glownych widokow.

### CampaignCreatedBy

```python
class CampaignCreatedBy(models.TextChoices):
    USER = "user", "User"
    AI = "ai", "AI"
    SYSTEM = "system", "System"
```

### CampaignDifficulty

```python
class CampaignDifficulty(models.TextChoices):
    EASY = "easy", "Easy"
    NORMAL = "normal", "Normal"
    HARD = "hard", "Hard"
    EPIC = "epic", "Epic"
    LEGENDARY = "legendary", "Legendary"
```

### CampaignQuestUnlockMode

```python
class CampaignQuestUnlockMode(models.TextChoices):
    IMMEDIATE = "immediate", "Immediate"
    AFTER_DEPENDENCIES = "after_dependencies", "After dependencies"
    MANUAL = "manual", "Manual"
```

Zasady:

- `immediate` - quest dostepny od startu kampanii,
- `after_dependencies` - quest dostepny po ukonczeniu zaleznosci,
- `manual` - quest odblokowywany recznie przez uzytkownika/admina.

### CampaignQuestState

To moze byc wartosc wyliczana, niekoniecznie pole w bazie:

```txt
locked
available
completed
skipped
```

MVP moze zaczac od:

- `locked`,
- `available`,
- `completed`.

## 5. Modele

### 5.1. Campaign

Model: `rpg.Campaign`

Pola:

```python
class Campaign(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT)
    created_by = models.CharField(max_length=20, choices=CampaignCreatedBy.choices, default=CampaignCreatedBy.USER)
    difficulty = models.CharField(max_length=20, choices=CampaignDifficulty.choices, default=CampaignDifficulty.NORMAL)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns")
    life_area = models.ForeignKey("skills.LifeArea", on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns")
    starts_on = models.DateField(null=True, blank=True)
    due_on = models.DateField(null=True, blank=True)
    reward_xp = models.PositiveIntegerField(default=0)
    reward_skill = models.ForeignKey("skills.Skill", on_delete=models.SET_NULL, null=True, blank=True, related_name="campaign_rewards")
    reward_title = models.CharField(max_length=180, blank=True)
    ai_prompt = models.TextField(blank=True)
    ai_provider = models.CharField(max_length=40, blank=True)
    ai_model = models.CharField(max_length=120, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    xp_awarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Walidacja:

- `title` nie moze byc puste,
- `due_on` nie moze byc przed `starts_on`,
- `reward_xp > 0` wymaga `reward_skill`,
- kampania `completed` musi miec `completed_at`,
- kampania `draft` nie przyznaje XP.

Uwagi:

- `owner` jest opcjonalny, bo MVP jest lokalne dla jednego uzytkownika,
- pole zostaje dodane, zeby pozniej nie przebudowywac modelu przy multi-user,
- `created_by=ai` oznacza kampanie wygenerowana przez AI, ale nadal zatwierdzona przez uzytkownika przed aktywacja.

### 5.2. CampaignQuest

Model: `rpg.CampaignQuest`

```python
class CampaignQuest(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="campaign_quests")
    quest = models.ForeignKey("rpg.Quest", on_delete=models.CASCADE, related_name="campaign_links")
    stage = models.CharField(max_length=120, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    unlock_mode = models.CharField(max_length=30, choices=CampaignQuestUnlockMode.choices, default=CampaignQuestUnlockMode.AFTER_DEPENDENCIES)
    map_x = models.PositiveIntegerField(default=0)
    map_y = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Constraints:

- unikalne `(campaign, quest)`,
- `order >= 0`,
- `map_x >= 0`,
- `map_y >= 0`.

Zasady:

- `stage` grupuje questy na mapie i w liscie,
- `order` sortuje questy w stage,
- `map_x` i `map_y` sa pozycja wezla na mapie,
- `is_required=False` pozwala dodac quest poboczny.

### 5.3. CampaignQuestDependency

Model: `rpg.CampaignQuestDependency`

```python
class CampaignQuestDependency(models.Model):
    campaign_quest = models.ForeignKey(CampaignQuest, on_delete=models.CASCADE, related_name="dependencies")
    depends_on = models.ForeignKey(CampaignQuest, on_delete=models.CASCADE, related_name="unlocks")
    created_at = models.DateTimeField(auto_now_add=True)
```

Constraints:

- unikalne `(campaign_quest, depends_on)`,
- `campaign_quest != depends_on`,
- oba wezly musza nalezec do tej samej kampanii.

Walidacja domenowa:

- graf kampanii nie moze miec cykli,
- quest nie moze zalezec od samego siebie,
- zaleznosci miedzy kampaniami sa niedozwolone.

## 6. Logika domenowa

### 6.1. Dostepnosc questa

Quest kampanii jest dostepny, gdy:

```txt
campaign.status == active
AND quest is not completed
AND (
  unlock_mode == immediate
  OR all dependencies are completed
  OR unlock_mode == manual and quest was manually unlocked
)
```

Dla MVP `manual unlock` moze zostac pominiety, jezeli nie dodajemy osobnego pola.

### 6.2. Ukonczenie kampanii

Kampania jest ukonczona, gdy:

```txt
all required CampaignQuest rows are completed
```

Questy poboczne (`is_required=False`) nie blokuja ukonczenia.

Po ukonczeniu:

- ustawiamy `Campaign.status = completed`,
- ustawiamy `completed_at`,
- przyznajemy bonus XP, jezeli `reward_xp > 0`,
- tworzymy wpis `JournalEntry`,
- odpalamy trigger achievementu, jezeli istnieje.

### 6.3. Idempotencja

Serwisy musza byc odporne na ponowne wywolanie:

- aktywacja draftu nie tworzy duplikatow questow,
- ukonczenie kampanii nie przyznaje XP dwa razy,
- wpis journalowy dla tego samego completion nie powinien powstac wielokrotnie,
- AI draft moze zostac wygenerowany ponownie jako nowy draft, ale nie nadpisuje aktywnej kampanii bez decyzji uzytkownika.

## 7. Serwisy

Docelowe funkcje w `rpg/services.py` albo `rpg/campaign_services.py`.

### create_campaign

Tworzy kampanie manualna.

Input:

- title,
- description,
- difficulty,
- starts_on,
- due_on,
- life_area,
- reward.

### add_quest_to_campaign

Dodaje istniejacy quest do kampanii.

Input:

- campaign,
- quest,
- stage,
- order,
- is_required,
- unlock_mode,
- map_x,
- map_y.

### create_campaign_quest

Tworzy nowy `Quest` i od razu przypina go do kampanii.

Uzywane przez:

- manual campaign builder,
- AI campaign designer.

### set_campaign_dependencies

Ustawia zaleznosci miedzy questami.

Musi walidowac:

- ta sama kampania,
- brak cykli,
- brak self-dependency.

### activate_campaign

Zmienia `draft -> active`.

Zasady:

- kampania musi miec co najmniej jeden wymagany quest,
- graf musi byc poprawny,
- nie wolno aktywowac kampanii z cyklem,
- nie wolno aktywowac kampanii bez dostepnego pierwszego questa.

### complete_campaign_if_ready

Sprawdza, czy kampania jest gotowa do ukonczenia.

Wywolania:

- po ukonczeniu questa,
- po recznym refreshu statusu kampanii.

### generate_campaign_draft

Tworzy draft kampanii na podstawie odpowiedzi AI.

AI nie zapisuje kampanii jako `active`.

## 8. AI Campaign Designer

### 8.1. Cel

AI pomaga uzytkownikowi zaprojektowac kampanie dla siebie.

Uzytkownik podaje:

- cel,
- obecny poziom,
- deadline lub czas trwania,
- czas dziennie/tygodniowo,
- skille do rozwoju,
- preferowana trudnosc,
- styl kampanii.

### 8.2. Formularz AI

Pola:

- `goal` - wymagane,
- `current_level` - opcjonalne,
- `timeframe_days` - opcjonalne,
- `available_minutes_per_day` - opcjonalne,
- `difficulty` - easy/normal/hard/epic/legendary,
- `skill_ids` - lista skilli,
- `notes` - dodatkowy kontekst.

### 8.3. Oczekiwany JSON od AI

AI powinno zwrocic strukture:

```json
{
  "title": "Django Foundations",
  "description": "A 30 day campaign to learn Django basics.",
  "difficulty": "normal",
  "reward_xp": 500,
  "reward_skill_name": "Programming",
  "stages": [
    {
      "name": "Setup",
      "quests": [
        {
          "client_id": "q1",
          "title": "Prepare environment",
          "description": "Install Python, Django and create the project.",
          "target_value": 1,
          "target_unit": "count",
          "reward_xp": 30,
          "skill_names": ["Programming"],
          "map_x": 0,
          "map_y": 0,
          "depends_on": []
        }
      ]
    }
  ]
}
```

Backend musi walidowac ten payload i nie moze zaufac AI bez sprawdzenia:

- wymaganych pol,
- dodatnich targetow,
- dozwolonych unitow,
- braku cykli,
- istnienia skilli albo bezpiecznego mapowania nazw skilli.

### 8.4. Draft review

Po wygenerowaniu AI:

- kampania ma `status=draft`,
- uzytkownik widzi mape i liste questow,
- uzytkownik moze edytowac tytuly, opisy, nagrody i zaleznosci,
- dopiero potem klika `Activate`.

## 9. API

Endpointy w `rpg/urls.py`.

### GET /api/campaigns/

Lista kampanii.

Query params:

- `status`,
- `created_by`,
- `active_only`.

Response:

```json
{
  "campaigns": [
    {
      "id": 1,
      "title": "Django Foundations",
      "status": "active",
      "created_by": "ai",
      "difficulty": "normal",
      "progress_percent": 40,
      "completed_required_quests": 2,
      "total_required_quests": 5,
      "available_quests": 2,
      "locked_quests": 1,
      "reward_xp": 500,
      "reward_title": "Backend Initiate"
    }
  ]
}
```

### POST /api/campaigns/

Tworzy kampanie manualna.

### GET /api/campaigns/<id>/

Szczegoly kampanii, w tym mapa.

Response:

```json
{
  "campaign": {
    "id": 1,
    "title": "Django Foundations",
    "description": "...",
    "status": "active",
    "progress_percent": 40,
    "map": {
      "nodes": [
        {
          "id": 10,
          "quest_id": 44,
          "title": "Prepare environment",
          "stage": "Setup",
          "state": "completed",
          "is_required": true,
          "map_x": 0,
          "map_y": 0,
          "reward_xp": 30
        }
      ],
      "edges": [
        {
          "from": 10,
          "to": 11
        }
      ]
    }
  }
}
```

### POST /api/campaigns/<id>/activate/

Aktywuje kampanie draft.

### POST /api/campaigns/<id>/archive/

Archiwizuje kampanie.

### POST /api/campaigns/<id>/quests/

Dodaje quest do kampanii.

Payload moze:

- podac `quest_id`,
- albo stworzyc nowy quest w tym samym request.

### POST /api/campaigns/<id>/dependencies/

Ustawia zaleznosci.

Payload:

```json
{
  "dependencies": [
    {
      "campaign_quest_id": 12,
      "depends_on_id": 10
    }
  ]
}
```

### POST /api/campaigns/ai-drafts/

Generuje draft kampanii przez AI.

Payload:

```json
{
  "goal": "I want to learn Django in 30 days.",
  "timeframe_days": 30,
  "available_minutes_per_day": 60,
  "difficulty": "normal",
  "skill_ids": [1, 2],
  "notes": "I know Python basics."
}
```

Response:

```json
{
  "campaign": {
    "id": 8,
    "status": "draft",
    "created_by": "ai"
  }
}
```

## 10. Frontend

### 10.1. Sidebar

Dodajemy pozycje:

```txt
Campaigns
```

### 10.2. Widoki

Gorny poziom:

```txt
Campaigns
├── Active
├── Drafts
├── Completed
└── Archived
```

Akcje:

- Create Campaign,
- AI Designer,
- Edit Draft,
- Activate,
- Archive.

### 10.3. Campaign Detail

Layout:

```txt
┌─────────────────────────────────────────────────────┐
│ Campaign Header                                     │
│ title | status | progress | reward | deadline       │
├─────────────────────────────────────────────────────┤
│ Campaign Map                                        │
│ nodes + edges + locked/available/completed states   │
├─────────────────────────────────────────────────────┤
│ Stage List / Quest List                             │
└─────────────────────────────────────────────────────┘
```

### 10.4. Mapa kampanii

Mapa jest obowiazkowa.

MVP mapy:

- render w React jako SVG albo CSS grid,
- wezly questow jako karty/okragi,
- polaczenia jako linie SVG,
- statusy kolorami:
  - locked - muted/gray,
  - available - gold,
  - completed - green,
  - optional - purple border,
- klikniecie wezla pokazuje szczegoly questa.

Nie dodajemy na start biblioteki grafowej, chyba ze mapa stanie sie zbyt zlozona.

### 10.5. Mapa - dane frontendowe

React powinien dostac gotowy model:

```ts
interface CampaignMapNode {
  id: string;
  questId: string;
  title: string;
  stage: string;
  state: "locked" | "available" | "completed";
  isRequired: boolean;
  x: number;
  y: number;
  rewardXp: number;
}

interface CampaignMapEdge {
  from: string;
  to: string;
}
```

Backend zwraca `map_x`, `map_y`, React mapuje na `x`, `y`.

### 10.6. Manual Campaign Builder

Kroki:

1. Campaign Info
2. Rewards
3. Stages
4. Quests
5. Dependencies
6. Map Layout
7. Review

MVP moze zaczac od jednego formularza, ale model UI powinien docelowo wspierac wizard.

### 10.7. AI Campaign Designer

Widok:

```txt
Goal
Timeframe
Minutes per day
Difficulty
Skills
Extra notes
[Generate draft]
```

Po wygenerowaniu:

- pokazujemy kampanie jako draft,
- wyswietlamy mape,
- pozwalamy edytowac przed aktywacja.

## 11. Integracje z istniejacym systemem

### 11.1. Quest completion

Po ukonczeniu questa:

- sprawdzamy, czy quest nalezy do aktywnej kampanii,
- aktualizujemy wyliczany stan mapy,
- sprawdzamy, czy kampania jest gotowa do completion,
- jesli tak, wywolujemy `complete_campaign_if_ready`.

### 11.2. Dashboard

Dashboard moze pokazywac:

- aktywna kampanie,
- nastepny dostepny quest kampanii,
- progress mapy,
- reward preview.

Dla MVP dashboard moze pokazac tylko jedna aktywna kampanie.

### 11.3. Journal

Tworzymy wpisy:

- campaign activated,
- campaign completed,
- AI campaign draft generated.

`JournalEntry.source_type`:

```txt
campaign
campaign_ai_draft
```

### 11.4. Achievements

Nowy trigger:

```python
CAMPAIGN_COMPLETED = "campaign_completed"
```

Przyklady achievementow:

- First Campaign Completed,
- Epic Arc Finished,
- AI Designed Path Completed,
- Legendary Campaign.

## 12. Seed data

Seed powinien dodac jedna kampanie:

```txt
Life RPG MVP Arc
```

Etapy:

1. Foundation
   - Define skills
   - Add activity definitions
2. RPG Core
   - Complete first daily quest
   - Complete first habit milestone
3. Planning
   - Add calendar event
   - Write journal reflection
4. Finish
   - Complete MVP review

Mapa:

```txt
Define skills -> Add activity definitions -> Complete first daily quest
                                     └-----> Complete first habit milestone
Complete first daily quest -> Add calendar event -> Write journal reflection -> Complete MVP review
```

## 13. Kryteria akceptacji MVP

Backend:

- istnieja modele `Campaign`, `CampaignQuest`, `CampaignQuestDependency`,
- mozna stworzyc kampanie draft,
- mozna dodac questy do kampanii,
- mozna ustawic zaleznosci sekwencyjne i rownolegle,
- system wykrywa cykle i odrzuca niepoprawna mape,
- mozna aktywowac poprawny draft,
- endpoint szczegolow zwraca `map.nodes` i `map.edges`,
- questy locked/available/completed sa wyliczane poprawnie,
- ukonczenie wszystkich wymaganych questow konczy kampanie,
- bonus XP kampanii jest przyznawany maksymalnie raz.

Frontend:

- sidebar ma zakladke `Campaigns`,
- lista kampanii pokazuje active/draft/completed,
- szczegoly kampanii pokazuja mape,
- mapa pokazuje locked/available/completed,
- user moze stworzyc kampanie manualnie,
- user moze wygenerowac draft przez AI,
- draft AI nie aktywuje sie automatycznie,
- user moze aktywowac kampanie po review.

Testy:

- test modelu zaleznosci,
- test wykrywania cyklu,
- test dostepnosci questa po ukonczeniu zaleznosci,
- test completion kampanii,
- test idempotencji XP,
- test API list/detail/activate,
- test AI draft zapisuje `status=draft`.

## 14. Kolejnosc implementacji

Rekomendowana kolejnosc:

1. Choices i modele kampanii.
2. Admin dla kampanii, questow kampanii i zaleznosci.
3. Serwisy grafu: dependency validation, availability, progress.
4. API list/detail.
5. API create/activate/archive.
6. Integracja z quest completion.
7. Mapa kampanii w React.
8. Manual Campaign Builder.
9. AI Campaign Designer jako draft generator.
10. Dashboard summary i seed data.

## 15. Poza zakresem MVP

Na pozniej:

- drag and drop map editor,
- wiele map layoutow,
- campaign templates marketplace,
- sharing/import/export kampanii,
- AI auto-adjustment kampanii na podstawie postepu,
- kampanie zespolowe,
- reczne cofanie XP,
- generowanie obrazkow/ikon kampanii.
