# AGENTS.md

## Project overview

This repository contains `todo-tracker`, a native macOS menu bar task tracker written in Python.

The app runs from the macOS menu bar, stores tasks in a local SQLite database, provides a Typer-based CLI, and includes a custom AppKit/PyObjC popup UI for viewing, editing, completing, and deleting tasks.

## Tech stack

* Python 3.11+
* `uv` for dependency management and command execution
* `rumps` + PyObjC/AppKit for the macOS menu bar UI
* SQLAlchemy 2.x for persistence
* SQLite as the local database
* Typer for the CLI
* pytest for tests
* py2app for building a `.app` bundle

## Repository structure

Important paths:

* `src/todo_tracker/cli.py` — Typer CLI entrypoint.
* `src/todo_tracker/menubar.py` — menu bar app entrypoint.
* `src/todo_tracker/popup.py` — popup UI and controller.
* `src/todo_tracker/geometry.py` — popup positioning logic.
* `src/todo_tracker/models.py` — SQLAlchemy models and enums.
* `src/todo_tracker/repositories.py` — database query and persistence layer.
* `src/todo_tracker/services.py` — business logic layer.
* `app_bundle/setup.py` — py2app bundle configuration.
* `tests/` — pytest test suite.

## Environment setup

Install dependencies with dev tools:

```bash
uv sync --dev
```

Use `uv run` for project commands instead of invoking global Python tools directly.

## Common commands

Run all tests:

```bash
uv run pytest -q
```

Run the CLI:

```bash
uv run todo-tracker list
```

Run the menu bar app from source:

```bash
PYTHONPATH=src .venv/bin/python -m todo_tracker.menubar
```

Build the macOS `.app` bundle:

```bash
cd app_bundle
../.venv/bin/python setup.py py2app
```

The built bundle is expected at:

```bash
app_bundle/dist/TodoTracker.app
```

## Local database

By default, the app uses:

```bash
~/.todo_tracker.db
```

For tests or manual checks, prefer passing a temporary SQLite database URL through the CLI `--db-url` option instead of touching the user’s real local database.

Example:

```bash
uv run todo-tracker --db-url sqlite:///tmp/todo-tracker-test.db list
```

## Domain model rules

Task statuses are:

* `in_progress`
* `done`
* `archived`

Task priorities are:

* `high`
* `medium`
* `low`

The SQLAlchemy `Note` model is the source of truth for these values. Do not introduce new status or priority string values unless the model, CLI, UI, tests, and README are updated together.

## Sorting rules

Task ordering must stay consistent across the repository:

1. `in_progress` tasks first.
2. `done` tasks after active tasks.
3. Priority order inside each status group:

   * `high`
   * `medium`
   * `low`
4. Earlier due dates first.
5. Earlier creation dates first.

The repository layer owns this ordering. Avoid duplicating sort logic in the CLI or UI unless there is a strong reason.

## CLI behavior

The CLI exposes these main commands:

```bash
uv run todo-tracker add --title "Task title" --content "Task body" --priority low
uv run todo-tracker add --title "Task title" --content "Task body" --priority high --due-date "2026-06-01T18:30:00"
uv run todo-tracker list
uv run todo-tracker update 1 --title "New title" --content "New body" --priority medium
uv run todo-tracker done 1
uv run todo-tracker delete
```

Important: `update <number>` and `done <number>` operate on the task number from the current `list` output, not on the database row `id`.

Do not change that behavior casually. If it changes, update the README, tests, and user-facing CLI messages.

## Architecture guidelines

Keep the current layering:

* CLI and UI code should call `TaskService`.
* `TaskService` should contain business operations and transaction boundaries.
* `TaskRepository` should contain SQLAlchemy queries and persistence details.
* SQLAlchemy model definitions and enum validation belong in `models.py`.

Avoid putting raw SQLAlchemy query logic directly into UI or CLI code when it can live in the repository layer.

## UI guidelines

The menu bar app is macOS-specific. Be careful with changes involving:

* `rumps`
* `AppKit`
* window positioning
* hover behavior
* popup sizing
* date picker behavior
* Dock/menu bar app behavior

When editing UI code, preserve the existing user experience unless the task explicitly asks for a UI change:

* popup has fixed width and bounded height
* long lists scroll
* completed tasks move below active tasks
* completed tasks are visually struck through
* edit/delete controls are shown only on hover
* task content can be expanded/collapsed
* priority and optional due date can be edited in the form

## Testing expectations

Before finishing changes, run:

```bash
uv run pytest -q
```

For changes to CLI behavior, add or update tests that exercise the CLI commands.

For changes to model, repository, or service logic, add or update tests around:

* task creation
* sorting
* status transitions
* priority handling
* due date handling
* delete behavior
* not-found behavior

For macOS UI changes, prefer extracting testable non-UI logic into small functions where practical.

## Code style

Follow the existing project style:

* Use Python type hints.
* Keep functions small and direct.
* Prefer explicit enum values over raw strings.
* Use `datetime.fromisoformat` compatibility for CLI due dates unless intentionally changing the input format.
* Keep SQLAlchemy 2.x style with `Mapped`, `mapped_column`, `select`, and sessions.
* Keep user-facing CLI output simple and stable.

## Dependency policy

Do not add dependencies unless they are necessary.

If adding a runtime dependency:

1. Add it to `pyproject.toml`.
2. Run `uv sync --dev`.
3. Make sure the app still starts from source.
4. Make sure tests pass.

If adding a dev-only dependency, put it in the dev dependency group.

## Build artifacts and generated files

Do not commit generated build artifacts or local runtime files, including:

* `.venv/`
* `__pycache__/`
* `.pytest_cache/`
* local SQLite database files
* `app_bundle/build/`
* `app_bundle/dist/`
* root-level `dist/`

Generated `.app` bundles should be built locally, not committed, unless the task explicitly asks for release artifact handling.

## Safety for local data

Be careful with operations that delete or mutate tasks.

The default database is the user’s real local task database. Tests, experiments, and examples should use a temporary database when possible.

Do not run destructive commands such as deleting completed tasks against the default database unless the user explicitly asks for it.

## Documentation updates

Update `README.md` when changing:

* setup commands
* CLI commands or options
* default database behavior
* sorting rules
* status or priority values
* app bundle build steps
* user-visible menu bar behavior

## Pull request checklist

Before submitting changes:

1. Run `uv run pytest -q`.
2. Confirm that CLI commands still work if CLI behavior was touched.
3. Confirm that the menu bar app still imports/starts if UI or app startup code was touched.
4. Update README if user-facing behavior changed.
5. Avoid committing generated files or local database files.

## UI generation and modification rules

When generating or modifying UI, treat the existing AppKit/PyObjC popup as the source of truth.

Do not redesign the interface unless the task explicitly asks for a redesign. Prefer small, focused UI changes that preserve the current menu bar workflow.

Before changing UI code:

1. Identify whether the change belongs in:
   - `src/todo_tracker/popup.py` for popup layout, controls, row rendering, hover behavior, forms, and user interactions.
   - `src/todo_tracker/geometry.py` for popup positioning and screen/menu bar geometry.
   - `src/todo_tracker/menubar.py` for menu bar app lifecycle and app entrypoint behavior.
   - `src/todo_tracker/services.py` for task operations triggered by the UI.
2. Keep business logic out of AppKit view code when possible.
3. Reuse existing service methods instead of duplicating database mutations in UI callbacks.

When adding UI elements:

- Follow the existing visual density and fixed-width popup layout.
- Keep the popup height bounded and preserve scrolling for long task lists.
- Make controls discoverable but avoid adding permanent clutter to each task row.
- Preserve hover-only edit/delete behavior unless the task asks otherwise.
- Preserve done-task styling and ordering.
- Preserve keyboard/mouse behavior expected from a small menu bar utility.
- Prefer native AppKit controls over custom-drawn controls unless necessary.
- Keep due date input compatible with the existing native date picker behavior.

When changing task row UI:

- Keep row rendering deterministic from the task model.
- Make sure completed tasks remain visually distinct.
- Make sure expanded/collapsed content state does not corrupt task data.
- Avoid using database IDs as visible row numbers in the CLI-style UI unless explicitly requested.
- Do not change sorting in UI code; task ordering should come from the repository/service layer.

When changing layout or positioning:

- Put reusable geometry calculations in `geometry.py`.
- Avoid hard-coded screen assumptions when AppKit APIs can provide screen/frame information.
- Test behavior near screen edges and menu bar boundaries.
- Keep the popup anchored to the menu bar item behavior.

When implementing UI-triggered mutations:

- Call `TaskService` methods for create, update, mark done, and delete actions.
- Refresh/re-render the popup after successful mutations.
- Handle `TaskNotFoundError` gracefully if a task disappears or becomes stale.
- Do not mutate SQLAlchemy models directly from view code unless the service layer already returned them for display.
