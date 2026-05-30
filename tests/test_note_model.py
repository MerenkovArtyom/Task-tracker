from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from todo_tracker.db import Base
from todo_tracker.models import Note, NoteStatus


def test_model_imports() -> None:
    assert Note is not None
    assert NoteStatus.IN_PROGRESS.value == "in_progress"


def test_schema_creates_notes_table() -> None:
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("notes")}
    assert columns == {"id", "title", "content", "status", "priority", "due_date"}


def test_note_persists_due_date_and_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    due_date = datetime(2026, 6, 1, 9, 30)

    with Session(engine) as session:
        note = Note(
            title="Ship MVP",
            content="Prepare first release",
            status=NoteStatus.IN_PROGRESS,
            priority=2,
            due_date=due_date,
        )
        session.add(note)
        session.commit()
        session.refresh(note)

        assert note.id is not None
        assert note.status == NoteStatus.IN_PROGRESS
        assert note.due_date == due_date


def test_note_allows_null_due_date() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        note = Note(
            title="Inbox",
            content="No deadline yet",
            status=NoteStatus.DONE,
            priority=1,
            due_date=None,
        )
        session.add(note)
        session.commit()
        session.refresh(note)

        assert note.due_date is None


def test_note_rejects_invalid_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        with pytest.raises(ValueError):
            note = Note(
                title="Invalid",
                content="Bad status",
                status="pending",
                priority=3,
                due_date=None,
            )
            session.add(note)
