# Life RPG Frontend

React + TypeScript + Vite + Tailwind CSS frontend for the Life RPG dashboard.

The dashboard is now the primary frontend experience. It renders the Legendary
Hero layout with sidebar, top bar, hero progression, resources, attributes,
quests, habits, skills, statuses, weekly chart, achievements, journal and manual
activity input.

## Setup

Install dependencies from inside `frontend/`:

```bash
npm install
```

Run the dev server:

```bash
npm run dev
```

Build for production:

```bash
npm run build
```

Production builds use Vite `base: "/static/frontend/"`, so generated asset
URLs are ready for Django `staticfiles` when `frontend/dist` is mounted under
the `frontend` static namespace.

## API Contract

The frontend expects Django JSON endpoints:

- `GET /api/dashboard/`
- `POST /api/activities/manual/`

During local development Vite proxies `/api/*` to `http://127.0.0.1:8000`.
Application code should keep using relative `/api/...` URLs so the same build
works through the Vite proxy in development and as same-origin requests when
served by Django.

The app tries the live dashboard API first. Mock dashboard data is used only as
a visible fallback when `/api/dashboard/` is unavailable.

## UI State

- Theme switching supports `minimal-dark`, `cyberpunk`, `living-world`,
  `adventurers-journal` and `premium-hybrid` / Legendary Hero.
- The selected theme is stored in `localStorage`.
- Range controls support `today`, `week`, `month` and `custom`.
- Custom ranges send `range=custom`, `start` and `end` query parameters from
  the frontend. The backend can ignore them until server-side custom date range
  filtering is implemented.
- Quest and habit clicks are local UI interactions stored per day in
  `localStorage`; they are not persisted to Django until RPG models/endpoints
  are added.
