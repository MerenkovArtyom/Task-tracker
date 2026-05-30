from __future__ import annotations

from datetime import datetime
from typing import Annotated

import typer

from todo_tracker.db import init_db
from todo_tracker.models import Note
from todo_tracker.services import UNSET, TaskNotFoundError, TaskService


app = typer.Typer(help="Task tracker CLI.")


def parse_due_date(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def get_service(ctx: typer.Context) -> TaskService:
    return ctx.obj["service"]


def format_note(index: int, note: Note) -> str:
    due = f" due={note.due_date.isoformat(sep=' ', timespec='minutes')}" if note.due_date else ""
    return f"{index}. [{note.status.value}] {note.title} (priority={note.priority}){due}"


@app.callback()
def main(
    ctx: typer.Context,
    db_url: Annotated[str, typer.Option("--db-url", help="SQLite database URL.")] = "",
) -> None:
    session_factory = init_db(db_url) if db_url else init_db()
    ctx.obj = {"service": TaskService(session_factory)}


@app.command()
def add(
    ctx: typer.Context,
    title: Annotated[str, typer.Option("--title")],
    content: Annotated[str, typer.Option("--content")],
    priority: Annotated[int, typer.Option("--priority")],
    due_date: Annotated[str | None, typer.Option("--due-date")] = None,
) -> None:
    service = get_service(ctx)
    note = service.create_note(
        title=title,
        content=content,
        priority=priority,
        due_date=parse_due_date(due_date),
    )
    typer.echo(f"Created task {note.id}: {note.title}")


@app.command("list")
def list_tasks(ctx: typer.Context) -> None:
    service = get_service(ctx)
    notes = service.list_active_notes()
    if not notes:
        typer.echo("No active tasks.")
        return

    for index, note in enumerate(notes, start=1):
        typer.echo(format_note(index, note))


@app.command()
def update(
    ctx: typer.Context,
    number: int,
    title: Annotated[str | None, typer.Option("--title")] = None,
    content: Annotated[str | None, typer.Option("--content")] = None,
    priority: Annotated[int | None, typer.Option("--priority")] = None,
    due_date: Annotated[str | None, typer.Option("--due-date")] = None,
) -> None:
    service = get_service(ctx)
    try:
        note = service.update_note_by_number(
            number,
            title=title,
            content=content,
            priority=priority,
            due_date=parse_due_date(due_date) if due_date is not None else UNSET,
        )
    except TaskNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    typer.echo(f"Updated task {number}: {note.title}")


@app.command()
def done(ctx: typer.Context, number: int) -> None:
    service = get_service(ctx)
    try:
        note = service.mark_done_by_number(number)
    except TaskNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    typer.echo(f"Marked task {number} as done: {note.title}")


@app.command()
def delete(ctx: typer.Context) -> None:
    service = get_service(ctx)
    deleted_count = service.delete_done_notes()
    suffix = "" if deleted_count == 1 else "s"
    typer.echo(f"Deleted {deleted_count} done task{suffix}")


if __name__ == "__main__":
    app()
