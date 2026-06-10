# Life RPG Tracker - Agent Guidelines

Use this repository to build a local Django Life RPG Tracker according to `docs/life-rpg-tracker-mvp-spec.md`.

## MUST Rules

1. **MUST follow the MVP spec** — treat `docs/life-rpg-tracker-mvp-spec.md` as the source of truth for scope, models, stages, and acceptance criteria.
2. **MUST keep the app local-first** — optimize for one local user, PostgreSQL, and simple Django workflows before adding external integrations.
3. **MUST use React for the app frontend** — use React, TypeScript, Vite, Tailwind CSS, and Chart.js for the dashboard/product UI.
4. **MUST NOT add DRF or Celery for MVP unless the spec changes** — use standard Django JSON views, models, admin, forms, and management commands for the backend API.
5. **MUST keep domain logic explicit** — prefer model methods or service functions over hidden Django signals for XP calculation.
6. **MUST add tests for domain behavior** — cover level calculation, `XpEvent` totals, multi-skill activity XP calculation, empty dashboard, and dashboard with sample data.
7. **MUST preserve simple architecture** — add abstractions only when they remove real duplication or clarify ownership.
8. **MUST use Django 6.0.6** — keep dependency and documentation changes aligned with the project version.
9. **MUST use PostgreSQL for MVP** — replace the generated SQLite settings with `.env` or environment-based PostgreSQL configuration during implementation.

## Task Router

| When you need | Work in |
|---|---|
| Skill data, XP ledger, XP totals, level formulas | `skills/` |
| Activity definitions, activity rewards, source rules, activity entries, XP calculation services | `activities/` |
| Life statuses such as Rested, Fed, Hydrated, Entertainment | `statuses/` |
| Future AI-generated quests and quest completion | `rpg/` |
| Dashboard API, aggregates, React shell, chart payloads | `dashboard/` |
| React app, UI components, client-side dashboard state | `frontend/` |
| Project URLs, settings, template/static configuration | `config/` |
| Product requirements and implementation stages | `docs/life-rpg-tracker-mvp-spec.md` |
| Phase 1 implementation details | `docs/phase-1-local-mvp-spec.md` |
| Future finance module notes | `docs/finance-module-notes.md` |

## Implementation Order

1. Register `skills`, `activities`, `statuses`, and `dashboard` in `INSTALLED_APPS`.
2. Configure PostgreSQL through `.env` or environment variables.
3. Create `LifeArea`, `Skill`, `XpEvent`, `ActivityDefinition`, `ActivityReward`, `ActivityRule`, `ActivityEntry`, `StatusDefinition`, and `StatusEntry` models.
4. Generate and apply migrations against PostgreSQL.
5. Register all models in Django Admin.
6. Add explicit XP calculation through `XpEvent` model methods or service functions.
7. Add a `seed_life_rpg` management command for sample data.
8. Add the dashboard manual activity form with explicit `ActivityDefinition` selection.
9. Expose dashboard data through standard Django JSON views.
10. Add a minimal Django template only as the React mount shell if needed.
11. Scaffold the React frontend with Vite, TypeScript, Tailwind CSS, and Chart.js.
12. Connect the React dashboard to the Django JSON endpoints.
13. Run backend and frontend checks before calling a phase complete.

## Data Model Constraints

- **LifeArea** — user-editable category. MUST group skills and activity definitions without hardcoded category choices.
- **Skill** — user growth area. MUST have a non-empty unique `name`, optional `life_area`, `created_at`, and level/progress helpers. MUST remain user-editable data, not an enum or Django `choices`.
- **XpEvent** — XP ledger entry. MUST be the source of truth for skill XP across activities, quests, and future manual corrections.
- **ActivityDefinition** — user-editable activity type. MUST be able to award XP to multiple skills through `ActivityReward`.
- **ActivityReward** — per-skill reward for an activity definition. MUST have required `activity_definition`, required `skill`, and `xp_per_minute > 0`.
- **ActivityRule** — source-to-activity mapping. MUST have a non-empty `pattern` and required `activity_definition`; MUST NOT point directly to a skill.
- **ActivityEntry** — recorded activity. MUST have required `activity_definition`, `source`, `minutes > 0`, `started_at`, and `created_at`.
- **StatusDefinition** — user-editable life status such as Rested, Fed, Hydrated, or Entertainment. MUST NOT be treated as a skill.
- **StatusEntry** — status measurement. MUST have required `status_definition`, `value` in `0..100`, and `recorded_at`.
- **Global level** — derived value. MUST be calculated from `XpEvent` totals in MVP, not stored in a separate table.

## XP Rules

1. Calculate activity XP per rewarded skill as `minutes * activity_reward.xp_per_minute`.
2. Calculate skill level with `floor(sqrt(xp / 100)) + 1`.
3. Clamp the displayed minimum level to `1`.
4. Create one `XpEvent` per `ActivityReward` when an activity awards XP.
5. Create an `XpEvent` when a future quest completion awards XP.
6. Do not treat `ActivityEntry` as the only source of XP.
7. Do not let AI directly mutate XP; AI may generate quest proposals, and completed quests award XP through `XpEvent`.
8. Do not award XP to `Entertainment`; keep it as a status.

## Dashboard Rules

1. Show total XP, global level, today's activity count, today's time, and today's XP.
2. Show every skill with name, level, XP, and progress to next level.
3. Show current status values.
4. Provide a manual activity form where the user selects `ActivityDefinition`.
5. Default the dashboard range to today; also support current week, current month, and custom date range.
6. Sort skills by highest XP first unless the spec changes.
7. Render empty states without JavaScript errors.
8. Keep Chart.js payloads JSON-safe and expose them through dashboard API responses.

## Admin Rules

1. Register `LifeArea`, `Skill`, `XpEvent`, `ActivityDefinition`, `ActivityReward`, `ActivityRule`, `ActivityEntry`, `StatusDefinition`, and `StatusEntry`.
2. Add list displays for high-signal fields only.
3. Add filters for skill and date fields where useful.
4. Add search for `LifeArea.name`, `Skill.name`, `ActivityDefinition.name`, `ActivityRule.pattern`, `ActivityEntry.source`, and `StatusDefinition.name`.
5. Keep admin behavior predictable; do not hide important XP mutations in signals.

## Commands

Use these commands for normal development:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

After the React frontend is scaffolded, use the package-manager commands documented in `frontend/package.json` for frontend development and builds.

Use this command after the seed task exists:

```bash
python manage.py seed_life_rpg
```

## Quality Checklist

1. Run `python manage.py test` after model, service, or dashboard changes.
2. Run `python manage.py makemigrations --check --dry-run` when model changes should not create new migrations.
3. Keep type hints on service functions and non-trivial model helpers.
4. Keep views thin; move reusable aggregation or XP logic out of templates.
5. Keep React components presentational where possible; keep XP and aggregation rules in Django services.
6. Update `docs/life-rpg-tracker-mvp-spec.md` when scope or behavior changes.

## Structure

```text
.
  AGENTS.md
  docs/
    life-rpg-tracker-mvp-spec.md
    phase-1-local-mvp-spec.md
    finance-module-notes.md
  manage.py
  config/
  skills/
  activities/
  statuses/
  dashboard/
  frontend/
```
