# Life RPG Tracker - current project status

Last checked: 2026-06-29.

## Summary

The project is beyond the original local MVP. Phase 1 is implemented in code:

- Django 6.0.6 backend with PostgreSQL-only settings.
- `skills`, `activities`, `statuses`, and `dashboard` MVP apps.
- `LifeArea`, `Skill`, `XpEvent`, activity, reward, rule, entry, status, and dashboard aggregation models/services.
- React, TypeScript, Vite, Tailwind CSS, Chart.js dashboard frontend.
- Django JSON views, CSRF helper, manual activity API, and React mount shell.
- Seed command for starter data.

The codebase also includes post-MVP RPG modules:

- `rpg` app with quests, habits, goals, challenges, achievements, journal, character identity, and campaigns.
- `planner` app with calendar events.
- React sidebar views for dashboard, goals, achievements, journal, calendar, settings, and campaign flows.

## Current blocker

The main blocker is local PostgreSQL availability.

Current `.env` points to:

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

On 2026-06-29, `pg_isready -h 127.0.0.1 -p 5432` returned `no response`, and
`docker ps` did not show a PostgreSQL container for this project. Because of
that, Django cannot create or connect to the test database.

## Verification Snapshot

Passing:

```bash
.venv/bin/python manage.py check
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Partially passing:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
```

This reports `No changes detected`, but also warns that Django cannot check
consistent migration history because the default PostgreSQL connection is bad.

Blocked:

```bash
.venv/bin/python manage.py test
```

The test runner finds 155 tests, then fails before executing them because
PostgreSQL is unavailable:

```text
psycopg.OperationalError: connection is bad: no error details available
```

Do not use the system `python` for backend checks unless the virtualenv is
activated. The system interpreter did not have `psycopg` installed during the
latest check. Use `.venv/bin/python` explicitly when in doubt.

## Known Gaps

- Local PostgreSQL must be started or replaced with a working `DATABASE_URL`.
- The database role must be able to create test databases for `manage.py test`.
- The ActivityWatch importer from MVP stage 2 is not implemented yet.
- `ActivityEntry` does not yet have the stage 2 importer fields:
  `external_id`, `external_source`, and `imported_at`.
- Some older RPG planning documents were written before the current `rpg`
  implementation and should be treated as historical unless their status
  sections say otherwise.
- The frontend production build passes, but Vite warns that the main JS chunk is
  larger than 500 kB. This is a performance follow-up, not a functional blocker.

## Recommended Next Steps

1. Start PostgreSQL locally or run the Docker Compose stack.
2. Run migrations and seed:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_life_rpg
```

3. Rerun backend verification:

```bash
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
```

4. Keep frontend verification green:

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

5. After the database is green, decide whether the next product step is
   ActivityWatch stage 2 or RPG/UI stabilization.
