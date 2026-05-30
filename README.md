# todo-tracker

Python task tracker for macOS with local `SQLite` storage, SQLAlchemy models, and a small CLI for testing the core task operations before wiring them into a menu bar UI.

## Stack

- Python 3.11+
- `uv` for dependency management
- `SQLAlchemy` for the data model and persistence
- `Typer` for the CLI
- `SQLite` as the local database

## Setup

Install dependencies:

```bash
uv sync --dev
```

## Run The CLI

By default, the app uses a local database at `~/.todo_tracker.db`.

Show active tasks:

```bash
uv run todo-tracker list
```

Use a custom database path:

```bash
uv run todo-tracker --db-url sqlite:///tasks.db list
```

## Commands

Create a task:

```bash
uv run todo-tracker add --title "Buy milk" --content "2 bottles" --priority 1
```

Create a task with a due date:

```bash
uv run todo-tracker add --title "Submit report" --content "PDF export" --priority 2 --due-date "2026-06-01T18:30:00"
```

List active tasks:

```bash
uv run todo-tracker list
```

Update a task by its human-visible number from the current `list` output:

```bash
uv run todo-tracker update 1 --title "Buy bread" --content "Rye bread" --priority 3
```

Mark a task as done:

```bash
uv run todo-tracker done 1
```

Delete all tasks with status `done`:

```bash
uv run todo-tracker delete
```

## CLI Rules

- Task numbering starts from `1`, not `0`.
- `update <num>` and `done <num>` work with the current `list` output, not with database `id`.
- `list` shows only `in_progress` tasks by default.
- Tasks are sorted by `priority`, then `due_date`, then `created_at`.
- `delete` removes all tasks with status `done`.

## Statuses

The model supports these statuses:

- `in_progress`
- `done`
- `archived`

At the moment, the CLI does not have a dedicated command to display `done` or `archived` tasks. If you need to inspect them directly, you can query the SQLite database:

```bash
sqlite3 ~/.todo_tracker.db "select id, title, status, priority, due_date, created_at from notes where status in ('done', 'archived') order by priority, due_date, created_at;"
```

## Tests

Run all tests:

```bash
uv run pytest -q
```
