# Life RPG

Local-first Life RPG Tracker built with Django and React. The app turns daily
activities, quests, habits, goals, challenges, achievements, journal entries,
skills, statuses, and calendar items into a personal RPG progression dashboard.

The project is designed for one local user first: simple Django JSON views,
PostgreSQL as the source of truth, explicit domain services for XP/progression,
and a React dashboard served either through Vite during development or through
Django after a frontend build.

## Stack

### Backend

- Python
- Django 6.0.6
- PostgreSQL via `psycopg`
- Standard Django models, admin, management commands, and JSON views
- No Django REST Framework
- No Celery

Main Django apps:

- `skills` - life areas, skills, XP ledger, level/progress helpers
- `activities` - activity definitions, rewards, activity entries, seed command
- `statuses` - local life statuses such as rested, fed, hydrated, entertainment
- `rpg` - quests, habits, goals, challenges, achievements, journal, identity
- `planner` - calendar events
- `dashboard` - React shell, dashboard API, settings API, manual activity API

### Frontend

- React 19
- TypeScript
- Vite 7
- Tailwind CSS
- Chart.js
- lucide-react icons

## Requirements

- Python compatible with Django 6.0
- Node.js and npm
- PostgreSQL running locally or available through `DATABASE_URL`

## Environment

Create a local `.env` from the example:

```bash
cp .env.example .env
```

Default local database settings:

```env
POSTGRES_DB=life_rpg_tracker
POSTGRES_USER=life_rpg
POSTGRES_PASSWORD=<set-a-local-password>
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Alternatively, set:

```env
DATABASE_URL=postgres://life_rpg:<set-a-local-password>@127.0.0.1:5432/life_rpg_tracker
```

The app intentionally has no SQLite fallback.

## Backend Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Seed starter data:

```bash
python manage.py seed_life_rpg
```

Run the Django server:

```bash
python manage.py runserver 127.0.0.1:8000
```

Useful backend checks:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Frontend Setup

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the Vite dev server:

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

Vite proxies `/api/*` to Django at `http://127.0.0.1:8000`, so keep the Django
server running in another terminal.

Frontend checks:

```bash
npm run typecheck
npm run build
```

## Running Through Django

Build the frontend:

```bash
cd frontend
npm run build
```

Then run Django:

```bash
cd ..
python manage.py runserver 127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000/
```

Django serves the built React app from `frontend/dist`.

## Docker

Build and run the Django image with PostgreSQL:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000/
```

The Compose setup builds the React app into the image, starts PostgreSQL, runs
`python manage.py migrate`, and serves Django on port `8000`.

`docker compose` reads the local `.env` file automatically. Set
`POSTGRES_PASSWORD` there before starting the stack; `.env` is ignored by Git.

Seed starter data inside the running app container:

```bash
docker compose exec app python manage.py seed_life_rpg
```

## Main Local URLs

- `http://127.0.0.1:8000/` - React shell served by Django build
- `http://127.0.0.1:5173/` - Vite dev frontend
- `http://127.0.0.1:8000/admin/` - Django Admin
- `GET /api/dashboard/` - dashboard data
- `GET /api/csrf/` - CSRF cookie helper
- `POST /api/activities/manual/` - manual activity entry
- `POST /api/quests/<id>/complete/` - complete quest
- `POST /api/habits/<id>/toggle/` - toggle habit check-in
- `GET /api/goals/` - goals
- `GET /api/challenges/` - challenges
- `GET /api/achievements/` - achievements
- `GET /api/journal/` - journal overview/entries
- `GET /api/calendar/events/` - planner calendar events

## Development Notes

- Backend JSON uses `snake_case`.
- React maps API payloads to `camelCase`.
- Domain state should live in PostgreSQL, not `localStorage`.
- XP is recorded through `skills.XpEvent`.
- Skill XP is derived from the XP ledger; `Skill` does not store an `xp` field.
- Goal and achievement completion do not award XP in MVP.
- Challenge completion may award XP, but only once.

## Project Structure

```text
.
  activities/
  config/
  dashboard/
  docs/
  frontend/
  planner/
  rpg/
  skills/
  statuses/
  manage.py
  requirements.txt
```
