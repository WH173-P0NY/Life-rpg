# Campaign Studio Canvas-First QA Checklist

Ten dokument jest reczna lista kontroli dla przebudowy `Campaigns` na Campaign
Studio w stylu Make/n8n. Obowiazujacy UX contract znajduje sie w
`docs/campaign-studio-workflow-canvas-redesign-spec.md`.

## Cel QA

- Upewnic sie, ze kampanie tworzy sie na canvasie jako workflow graph.
- Sprawdzic, ze domyslny widok nie pokazuje stalej biblioteki, palety,
  inspectora ani readiness panelu.
- Sprawdzic, ze backend zapisuje strukture grafu i odtwarza ja po odswiezeniu.
- Sprawdzic, ze PL/EN sa kompletne, a widoczny copy nie jest hardcoded w
  komponentach.

## Smoke

- [ ] `Campaigns` otwiera sie bez bledu przy dzialajacym Django API.
- [ ] Empty state pokazuje CTA do utworzenia pierwszej kampanii.
- [ ] Campaign switcher pozwala wyszukac i wybrac draft, active, completed i archived.
- [ ] Po odswiezeniu strony wybrana kampania laduje realne node'y i edge'e z API.
- [ ] Bledy API sa widoczne jako czytelny komunikat, nie jako surowy traceback albo pusty alert.

## Canvas-First Layout

- [ ] Desktop pokazuje top bar i canvas jako glowna powierzchnie pracy.
- [ ] Domyslnie nie ma stalego lewego panelu biblioteki.
- [ ] Domyslnie nie ma stalej palety node'ow.
- [ ] Domyslnie nie ma stalego prawego inspectora.
- [ ] Domyslnie nie ma stalego readiness panelu.
- [ ] Canvas zajmuje wiekszosc workbench viewportu.
- [ ] Campaign switcher otwiera sie jako popover/sheet i zamyka po wyborze.
- [ ] Node picker otwiera sie tylko po akcji dodawania node'a.
- [ ] Validation details otwieraja sie tylko po kliknieciu statusu, Validate albo zablokowanym Publish.

## Canvas

- [ ] Canvas ma staly wymiar rodzica i nie zapada sie do zera.
- [ ] Pan dziala mysza lub trackpadem.
- [ ] Zoom in/out dziala i nie rozbija layoutu.
- [ ] Node mozna przesunac drag & drop w builder mode.
- [ ] Po drag stop pozycja zapisuje sie w backendzie przez `PATCH /nodes/positions/`.
- [ ] Po odswiezeniu strony node zostaje w zapisanej pozycji.
- [ ] Minimap/controls nie zaslaniaja istotnych akcji.
- [ ] Hover controls nie zmieniaja rozmiaru node'a i nie przesuwaja grafu.

## Overlap And Geometry

- [ ] Node'y nie nachodza na siebie po initial load.
- [ ] Node'y nie nachodza na siebie po dodaniu node'a.
- [ ] Node'y nie nachodza na siebie po auto-layout.
- [ ] Node'y nie nachodza na siebie po drag-stop.
- [ ] Hover controls, status badges, XP badges i selected ring nie powoduja overlapu.
- [ ] Sprawdzone dla 3 node'ow.
- [ ] Sprawdzone dla 10 node'ow.
- [ ] Sprawdzone dla 30 node'ow.

## Node Creation

- [ ] Plus na output connectorze otwiera node picker.
- [ ] Node picker pozwala dodac node typu Quest.
- [ ] Node picker pozwala dodac node typu Milestone.
- [ ] Node picker pozwala dodac node typu Reward.
- [ ] Node picker pozwala dodac node typu Reflection.
- [ ] Node picker pozwala dodac node typu Gate.
- [ ] Add from node tworzy nowy node i edge od source node do nowego node'a.
- [ ] Add from empty canvas tworzy node bez edge'a w okolicy viewport center.
- [ ] Add from branch placeholder w first pass dziala jako add-after-source, bez splicowania edge'a.
- [ ] Gdy create-edge po create-node sie nie powiedzie, UI odswieza studio state i pokazuje blad.
- [ ] Nowy node zapisuje sie w backendzie.
- [ ] Po odswiezeniu nowy node nadal istnieje.

## Connections

- [ ] Przeciagniecie handle'a tworzy edge.
- [ ] Edge tworzy dependency w backendzie.
- [ ] Po odswiezeniu edge nadal istnieje.
- [ ] Nie da sie utworzyc self-edge.
- [ ] Nie da sie utworzyc edge'a miedzy node'ami z roznych kampanii.
- [ ] Proba utworzenia cyklu pokazuje czytelny blad i nie zapisuje edge'a.
- [ ] Usuniecie edge'a usuwa dependency w backendzie.
- [ ] Po odswiezeniu usuniety edge nie wraca.
- [ ] Edge label/route summary jest read-only i derivowany z istniejacych danych.

## Inspector Drawers

- [ ] Klikniecie node'a otwiera `NodeInspectorDrawer`.
- [ ] Klikniecie edge'a otwiera `EdgeInspectorDrawer`.
- [ ] Klikniecie tla canvasu zamyka tylko clean drawer.
- [ ] `Esc` zamyka tylko clean drawer.
- [ ] Dirty drawer wymaga explicit Save albo Discard.
- [ ] Node drawer pozwala zapisac tytul.
- [ ] Node drawer pozwala zapisac opis.
- [ ] Node drawer pozwala zapisac stage.
- [ ] Node drawer pozwala ustawic required/optional.
- [ ] Node drawer pozwala ustawic reward XP i reward skill.
- [ ] Add quest z node pickera pozwala wybrac reward skill i XP przed utworzeniem node'a.
- [ ] Save node nie wysyla pustego `rewardSkillId` i nie czysci istniejacego reward skill, chyba ze uzytkownik ustawi XP na `0`.
- [ ] Node drawer pozwala wybrac unlock mode.
- [ ] Save nie tworzy duplikatu questa.
- [ ] Bledy walidacji sa pokazane przy formularzu albo w drawerze errorow.

## Delete

- [ ] Delete node usuwa node z canvasu.
- [ ] Delete node usuwa edge'e wchodzace i wychodzace.
- [ ] Delete node zapisuje sie w backendzie.
- [ ] Po odswiezeniu usuniety node i jego edge'e nie wracaja.
- [ ] Delete edge usuwa tylko wskazane polaczenie.
- [ ] Delete jest zablokowany lub wymaga potwierdzenia dla destructive akcji na aktywnej kampanii.

## Auto Layout

- [ ] Auto-layout dziala dla 3 node'ow.
- [ ] Auto-layout dziala dla 10 node'ow.
- [ ] Auto-layout dziala dla 30 node'ow.
- [ ] Po auto-layout node'y sie nie zaslaniaja.
- [ ] Po auto-layout edge'e sa czytelne.
- [ ] Po auto-layout pozycje zapisuja sie w backendzie.
- [ ] Po odswiezeniu auto-layout zostaje zachowany.

## Validation And Publish

- [ ] Top bar pokazuje status: Ready, Needs work albo Draft.
- [ ] Validate wykrywa brak startu.
- [ ] Validate wykrywa brak questow.
- [ ] Validate wykrywa cykle.
- [ ] Validate wykrywa nieosiagalne required node'y.
- [ ] Validate wykrywa brak finalnego node'a, jezeli final node jest wymagany w danym etapie.
- [ ] Validation drawer pokazuje checkliste, a nie tylko ogolny blad.
- [ ] Klikniecie issue wybiera albo centruje powiazany node/edge, jezeli payload ma id.
- [ ] Publish/activate jest zablokowany, gdy walidacja ma bledy.
- [ ] Publish/activate pokazuje konkretne powody blokady.
- [ ] Udany publish/activate zmienia status kampanii i odswieza widok.

## Play Mode

- [ ] Play Mode blokuje edycje struktury.
- [ ] W Play Mode nie da sie przesuwac node'ow.
- [ ] W Play Mode nie da sie tworzyc edge'ow.
- [ ] W Play Mode nie da sie usuwac node'ow ani edge'ow.
- [ ] Locked node jest wizualnie przygaszony.
- [ ] Available node jest wizualnie podswietlony.
- [ ] Completed node jest wizualnie oznaczony jako ukonczony.
- [ ] Klikniecie locked node'a tlumaczy, co trzeba ukonczyc, zeby go odblokowac.
- [ ] Ukonczenie questa aktualizuje progres kampanii.
- [ ] Ukonczenie kampanii nie duplikuje XP po ponownym refreshu/kliknieciu.

## AI Designer

- [ ] AI draft tworzy edytowalna mape, nie ukryty formularz.
- [ ] AI draft nie aktywuje kampanii automatycznie.
- [ ] Akcje AI pokazuja jasny pending state.
- [ ] Blad AI pokazuje czytelny komunikat.
- [ ] Draft AI mozna poprawic recznie przed publikacja.

## Responsive

- [ ] Desktop: top bar i canvas mieszcza sie bez poziomego scrolla strony.
- [ ] Tablet: inspector drawer nie zaslania trwale calego canvasu.
- [ ] Mobile: canvas jest pierwszym ekranem.
- [ ] Mobile: inspector i validation sa bottom sheets.
- [ ] Mobile: node picker jest sheet albo full-screen command surface.
- [ ] Teksty w przyciskach nie wychodza poza kontenery w PL i EN.
- [ ] Canvas nie zaslania sidebaru ani topbara.

## I18n

- [ ] Nowe widoczne teksty uzywaja `t(...)`.
- [ ] PL i EN maja te same klucze.
- [ ] Brak hardcoded copy w glownych komponentach Campaign Studio, poza danymi uzytkownika.
- [ ] Statusy node'ow sa tlumaczone: locked, available, completed.
- [ ] Unlock modes sa tlumaczone: immediate, after_dependencies, manual.
- [ ] Komunikaty walidacji sa tlumaczone.
- [ ] Empty states sa tlumaczone.
- [ ] API errors maja fallback w i18n.

## Regression Risks

- [ ] Nie pokazujemy uzytkownikowi surowych `map_x` / `map_y`.
- [ ] Canvas nie uzywa absolutnie pozycjonowanych recznie buttonow jako glownego grafu.
- [ ] Edge operations nie nadpisuja przypadkiem calego grafu przy edycji pojedynczego edge'a.
- [ ] Backend nie pozwala edytowac struktury zakonczonej albo zarchiwizowanej kampanii.
- [ ] Zapis pozycji node'a jest debounce'owany lub wykonywany na drag stop, nie przy kazdym pikselu.
- [ ] Usuniecie node'a nie zostawia wiszacych edge'ow.
- [ ] Duplicate node nie jest widoczny w first pass, chyba ze osobny kontrakt okresla kopiowanie edge'y, pozycji i reward skill.
- [ ] React build nie ma brakujacych importow CSS React Flow.
- [ ] Duzy bundle Vite jest tylko warningiem, nie blokada.

## Commands

Backend:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
```

Frontend:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Manual smoke with API:

```bash
.venv/bin/python manage.py runserver 127.0.0.1:8000
npm --prefix frontend run dev
```

## Acceptance

- [ ] Uzytkownik moze stworzyc kampanie wizualnie na canvasie.
- [ ] Node'y da sie przesuwac, laczyc, usuwac i edytowac przez drawers/popovers.
- [ ] Po refreshu struktura kampanii zostaje zachowana.
- [ ] Play Mode pokazuje realny progres bez edycji struktury.
- [ ] Validate/Publish jasno tlumaczy, co trzeba poprawic.
- [ ] Canvas-first layout nie wraca do stalego ukladu: library + palette + canvas + inspector.
