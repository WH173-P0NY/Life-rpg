# Campaign Studio QA Checklist

Ten dokument jest reczna lista kontroli dla przebudowy `Campaigns` na Campaign Studio w stylu workflow/n8n.

## Cel QA

- Upewnic sie, ze kampanie tworzy sie wizualnie na canvasie, a nie przez zestaw luznych formularzy.
- Sprawdzic, ze backend zapisuje strukture grafu i odtwarza ja po odswiezeniu.
- Sprawdzic, ze PL/EN sa kompletne, a widoczny copy nie jest hardcoded w komponentach.

## Smoke

- [ ] `Campaigns` otwiera sie bez bledu przy dzialajacym Django API.
- [ ] Empty state pokazuje CTA do utworzenia pierwszej kampanii.
- [ ] Lista kampanii pozwala wybrac draft, active, completed i archived.
- [ ] Po odswiezeniu strony wybrana kampania laduje realne node'y i edge'e z API.
- [ ] Bledy API sa widoczne jako czytelny komunikat, nie jako surowy traceback albo pusty alert.

## Canvas

- [ ] Canvas ma staly wymiar rodzica i nie zapada sie do zera.
- [ ] Pan dziala mysza lub trackpadem.
- [ ] Zoom in/out dziala i nie rozbija layoutu.
- [ ] Node mozna przesunac drag & drop.
- [ ] Po drag stop pozycja zapisuje sie w backendzie.
- [ ] Po odswiezeniu strony node zostaje w zapisanej pozycji.
- [ ] Node'y nie nachodza na toolbar, palete ani inspector.
- [ ] Minimap/controls nie zaslaniaja istotnych akcji.

## Node Creation

- [ ] Paleta pozwala dodac node typu Quest.
- [ ] Paleta pozwala dodac node typu Milestone.
- [ ] Paleta pozwala dodac node typu Reward.
- [ ] Paleta pozwala dodac node typu Reflection.
- [ ] Paleta pozwala dodac node typu Gate.
- [ ] Nowy node pojawia sie na canvasie i od razu zostaje zaznaczony.
- [ ] Nowy node otwiera inspector.
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

## Inspector

- [ ] Klikniecie node'a otwiera prawy inspector.
- [ ] Klikniecie tla canvasu czysci selection albo pokazuje neutralny empty state.
- [ ] Inspector opisuje, czym jest dany typ node'a.
- [ ] Inspector pozwala zapisac tytul.
- [ ] Inspector pozwala zapisac opis.
- [ ] Inspector pozwala zapisac stage.
- [ ] Inspector pozwala ustawic required/optional.
- [ ] Inspector pozwala ustawic reward XP.
- [ ] Inspector pozwala wybrac reward skill.
- [ ] Inspector pozwala wybrac unlock mode.
- [ ] Save nie tworzy duplikatu questa.
- [ ] Bledy walidacji sa pokazane przy formularzu albo w panelu errorow.

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

- [ ] Validate wykrywa brak startu.
- [ ] Validate wykrywa brak questow.
- [ ] Validate wykrywa cykle.
- [ ] Validate wykrywa nieosiagalne required node'y.
- [ ] Validate wykrywa brak finalnego node'a, jezeli final node jest wymagany w danym etapie.
- [ ] Readiness panel pokazuje checkliste, a nie tylko ogolny blad.
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
- [ ] Akcje AI pokazuje jasny pending state.
- [ ] Blad AI pokazuje czytelny komunikat.
- [ ] Draft AI mozna poprawic recznie przed publikacja.

## Responsive

- [ ] Desktop: lewy panel, canvas i inspector mieszcza sie bez poziomego scrolla strony.
- [ ] Tablet: inspector nie zaslania canvasu.
- [ ] Mobile: widok ma sensowny tryb przelaczania miedzy lista/canvas/inspector.
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
cd frontend
npm run build
```

Manual smoke with API:

```bash
.venv/bin/python manage.py runserver 127.0.0.1:8000
cd frontend
npm run dev
```

## Acceptance

- [ ] Uzytkownik moze stworzyc kampanie wizualnie.
- [ ] Node'y da sie przesuwac, laczyc, usuwac i edytowac.
- [ ] Po refreshu struktura kampanii zostaje zachowana.
- [ ] Play Mode pokazuje realny progres bez edycji struktury.
- [ ] Validate/Publish jasno tlumaczy, co trzeba poprawic.
- [ ] PL/EN sa kompletne dla nowych widocznych tekstow.
- [ ] Backend tests i frontend build przechodza.
