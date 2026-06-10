# React-Django Integration - specyfikacja techniczna

## 1. Cel

Celem tej specyfikacji jest opisanie, jak przelaczyc glowny widok aplikacji z Django Templates na React/Vite, zachowujac Django jako backend, API, admin i wlasciciela logiki domenowej.

Docelowy efekt:

- React jest glownym interfejsem aplikacji dla dashboardu i przyszlych modulow RPG,
- Django udostepnia standardowe endpointy JSON bez DRF,
- Django Admin pozostaje dostepny pod `/admin/`,
- logika XP, agregacje, walidacja i zapis danych pozostaja w Django,
- lokalny development jest szybki przez Vite,
- lokalny build produkcyjny nie wymaga osobnego serwera Node.

## 2. Zakres

### W zakresie

- tryb developerski z Vite na `127.0.0.1:5173`,
- Django API na `127.0.0.1:8000`,
- proxy `/api` z Vite do Django,
- lokalny build produkcyjny przez `npm run build`,
- serwowanie React shell przez Django,
- statyczne assety Reacta przez Django `staticfiles`,
- fallback URL dla routingu SPA,
- wymagania CSRF/CORS dla lokalnego developmentu,
- kryteria akceptacji i kolejnosc implementacji.

### Poza zakresem

- wdrozenie publiczne,
- konfiguracja reverse proxy dla zewnetrznego serwera,
- konteneryzacja produkcyjna,
- SSR,
- logowanie wielu uzytkownikow.

## 3. Architektura docelowa

```text
Development:

Browser
  -> http://127.0.0.1:5173/         React/Vite dev server
  -> http://127.0.0.1:5173/api/*    Vite proxy
  -> http://127.0.0.1:8000/api/*    Django JSON API
  -> http://127.0.0.1:8000/admin/   Django Admin

Local production build:

Browser
  -> http://127.0.0.1:8000/         Django React shell view
  -> http://127.0.0.1:8000/static/frontend/assets/*
  -> http://127.0.0.1:8000/api/*    Django JSON API
  -> http://127.0.0.1:8000/admin/   Django Admin
```

Django pozostaje jedynym backendem aplikacji. React nie liczy XP i nie zapisuje danych z pominieciem API.

## 4. Tryb development

### Serwery

W trybie development uruchamiane sa dwa procesy:

```bash
python manage.py runserver 127.0.0.1:8000
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Adresy:

- React/Vite: `http://127.0.0.1:5173/`,
- Django API: `http://127.0.0.1:8000/api/`,
- Django Admin: `http://127.0.0.1:8000/admin/`.

### Proxy API

Vite powinien proxy'owac wszystkie requesty `/api/*` do Django:

```ts
server: {
  port: 5173,
  proxy: {
    "/api": {
      target: "http://127.0.0.1:8000",
      changeOrigin: true
    }
  }
}
```

React powinien wolac endpointy wzglednie, np.:

```ts
fetch("/api/dashboard/")
```

Nie powinien twardo kodowac `http://127.0.0.1:8000` w kodzie aplikacji. Dzieki temu ten sam kod dziala w dev przez proxy i w buildzie produkcyjnym jako same-origin.

### CSRF

Django powinno miec endpoint inicjujacy cookie CSRF:

```text
GET /api/csrf/
```

Frontend przed pierwszym requestem mutujacym dane powinien pobrac CSRF cookie, a requesty `POST`, `PUT`, `PATCH` i `DELETE` powinny wysylac naglowek:

```text
X-CSRFToken: <csrftoken>
```

W local dev Django powinno ufac originowi Vite:

```py
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
```

### CORS

Rekomendowany wariant developmentu nie wymaga CORS, bo React wysyla requesty do `/api/*` na origin Vite, a Vite proxy przekazuje je do Django.

Nie dodajemy `django-cors-headers` w MVP. Jezeli frontend zacznie bezposrednio wolac `http://127.0.0.1:8000/api/*` z originu `http://127.0.0.1:5173`, wtedy trzeba podjac osobna decyzje o CORS. Domyslnie unikamy tego przez proxy.

## 5. Tryb local production build

### Build Reacta

Build wykonywany jest z katalogu `frontend/`:

```bash
npm run build
```

Wynik:

```text
frontend/dist/index.html
frontend/dist/assets/*
```

### Rekomendowany wariant assetow

Rekomendowany minimalny wariant:

1. Vite buduje assety z base ustawionym na `/static/frontend/`.
2. Django serwuje `frontend/dist/index.html` przez zwykly view.
3. Django `staticfiles` wystawia zawartosc `frontend/dist` pod namespace `frontend`.

Przykladowa konfiguracja Vite dla buildu:

```ts
export default defineConfig({
  base: "/static/frontend/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  }
});
```

Przykladowa konfiguracja Django:

```py
STATIC_URL = "static/"
STATICFILES_DIRS = [
    ("frontend", BASE_DIR / "frontend" / "dist"),
]
```

Wtedy pliki z:

```text
frontend/dist/assets/app.js
```

sa dostepne jako:

```text
/static/frontend/assets/app.js
```

`frontend/dist/index.html` moze zawierac odwolania do `/static/frontend/assets/*`.

### Alternatywa

Alternatywnie mozna po buildzie kopiowac `frontend/dist/index.html` do `templates/` i `frontend/dist/assets` do katalogu static aplikacji Django.

Ten wariant jest mniej preferowany w MVP, bo dodaje krok kopiowania i latwiej o niespojnosc miedzy `index.html` oraz zahashowanymi assetami.

## 6. Minimalny wariant implementacji w Django

### React shell view

Django powinno miec view, ktory zwraca zawartosc:

```text
frontend/dist/index.html
```

Minimalne zachowanie:

- jezeli `frontend/dist/index.html` istnieje, zwroc HTML,
- jezeli build nie istnieje, zwroc czytelny komunikat developerski z instrukcja uruchomienia `npm run build` albo uzycia Vite dev servera,
- nie renderuj tu danych domenowych z Django template,
- nie przenos logiki dashboardu do HTML shell.

Przykladowy kierunek implementacji:

```py
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def react_shell(request):
    index_path = Path(settings.BASE_DIR) / "frontend" / "dist" / "index.html"
    if not index_path.exists():
        return HttpResponse(
            "React build not found. Run `cd frontend && npm run build` "
            "or use Vite at http://127.0.0.1:5173/.",
            status=503,
            content_type="text/plain",
        )

    return HttpResponse(index_path.read_text(), content_type="text/html")
```

### URL shell

Minimalny routing:

```py
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("dashboard.urls")),
    path("", react_shell, name="react-shell"),
]
```

Jezeli `dashboard.urls` obecnie zawiera zarowno template dashboardu, jak i API, trzeba rozdzielic odpowiedzialnosci:

- API zostaje pod `/api/*`,
- React shell przejmuje `/`,
- stary template dashboardu moze zostac tymczasowo pod technicznym URL, np. `/legacy-dashboard/`, tylko jezeli jest potrzebny do porownan.

### Fallback dla SPA

Jezeli React zacznie uzywac klientowego routingu, Django musi zwracac React shell dla sciezek frontendowych, np.:

```py
urlpatterns += [
    re_path(r"^(?!api/|admin/|static/).*$", react_shell, name="react-spa-fallback"),
]
```

Fallback nie moze przechwytywac:

- `/api/*`,
- `/admin/*`,
- `/static/*`.

Na start, jezeli aplikacja ma tylko dashboard bez klientowego routingu, wystarczy `path("", react_shell, name="react-shell")`. Fallback dodac dopiero przy pierwszych trasach React Routera.

### Static files

Minimalne ustawienia:

```py
STATIC_URL = "static/"
STATICFILES_DIRS = [
    ("frontend", BASE_DIR / "frontend" / "dist"),
]
```

W lokalnym `DEBUG=True` Django moze serwowac static files przez development server.

W przyszlym deploymentcie publicznym trzeba bedzie dodac standardowy proces `collectstatic` i docelowy serwer statyczny, ale to jest poza MVP tej specyfikacji.

## 7. Kontrakt API dla Reacta

React powinien korzystac tylko z endpointow JSON:

- `GET /api/dashboard/`,
- `GET /api/dashboard/?range=today`,
- `GET /api/dashboard/?range=week`,
- `GET /api/dashboard/?range=month`,
- `GET /api/dashboard/?range=custom&start=YYYY-MM-DD&end=YYYY-MM-DD`,
- `GET /api/csrf/`,
- `POST /api/activities/manual/`.

Zasady:

- requesty z frontendu sa wzgledne, np. `/api/dashboard/`,
- backend zwraca dane gotowe do renderowania,
- React moze trzymac lokalny stan UI, np. wybrany theme, otwarte panele, zakres dat,
- React nie moze samodzielnie przeliczac trwalych XP jako zrodla prawdy,
- przyznanie XP zawsze przechodzi przez Django i `XpEvent`.

## 8. Czego nie robimy

W MVP nie robimy:

- DRF,
- Celery,
- osobnego Node servera dla lokalnej produkcji,
- SSR,
- Next.js,
- publicznego CORS jako domyslnej konfiguracji,
- mieszania logiki XP we froncie,
- twardego kodowania adresu Django API w React,
- utrzymywania dwoch rownorzednych dashboardow: Django template i React.

Django Templates moga zostac tylko jako:

- Django Admin,
- awaryjny/tymczasowy legacy view,
- prosty shell do Reacta, jezeli zdecydujemy sie nie czytac bezposrednio `dist/index.html`.

## 9. Kolejnosc implementacji

1. Uporzadkowac URL-e API tak, aby endpointy JSON byly jednoznacznie pod `/api/*`.
2. Dodac albo przeniesc React shell view do odpowiedniej aplikacji, najpewniej `dashboard`.
3. Ustawic `STATICFILES_DIRS` dla `frontend/dist` pod namespace `frontend`.
4. Ustawic Vite `base: "/static/frontend/"` dla buildu.
5. Przelaczyc root `/` na React shell.
6. Zachowac `/admin/` bez zmian.
7. Zweryfikowac local dev przez Vite:
   - `python manage.py runserver 127.0.0.1:8000`,
   - `cd frontend && npm run dev -- --host 127.0.0.1`,
   - wejscie na `http://127.0.0.1:5173/`.
8. Zweryfikowac local production build:
   - `cd frontend && npm run build`,
   - `python manage.py runserver 127.0.0.1:8000`,
   - wejscie na `http://127.0.0.1:8000/`.
9. Dodac test Django dla shell view:
   - gdy build istnieje, endpoint `/` zwraca `200 text/html`,
   - gdy build nie istnieje, endpoint zwraca czytelny komunikat developerski.
10. Dopiero po tej zmianie usunac lub przeniesc stary template dashboardu, jezeli nie jest juz potrzebny.

## 10. Kryteria akceptacji

Implementacja jest gotowa, gdy:

- `http://127.0.0.1:5173/` dziala w dev i pobiera dane przez `/api/*`,
- Vite proxy przekazuje `/api/*` do `http://127.0.0.1:8000`,
- `http://127.0.0.1:8000/admin/` dziala bez regresji,
- `npm run build` tworzy `frontend/dist/index.html` i `frontend/dist/assets/*`,
- `http://127.0.0.1:8000/` po buildzie zwraca React dashboard,
- assety Reacta laduja sie z `/static/frontend/assets/*`,
- odswiezenie strony Reacta nie psuje routingu, jezeli SPA fallback jest wlaczony,
- endpointy API nadal zwracaja JSON i nie renderuja HTML,
- request mutujacy dane z Reacta dziala z CSRF,
- `python manage.py test` przechodzi,
- `npm run typecheck` i `npm run build` przechodza,
- w kodzie nie pojawia sie DRF, Celery ani osobny Node server produkcyjny.

## 11. Decyzja rekomendowana

Rekomendowany kierunek dla tego projektu:

- w development pracowac na Vite `127.0.0.1:5173` i Django API `127.0.0.1:8000`,
- w lokalnym trybie produkcyjnym serwowac React build przez Django,
- ustawic Vite `base` na `/static/frontend/`,
- dodac `STATICFILES_DIRS = [("frontend", BASE_DIR / "frontend" / "dist")]`,
- przelaczyc root `/` na React shell,
- nie utrzymywac Django template dashboardu jako glownego widoku po przelaczeniu.
