from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from todo_tracker.db import Base
from todo_tracker.models import Note, NotePriority, NoteStatus
from todo_tracker.services import TaskNotFoundError, TaskService


@pytest.fixture
def service() -> TaskService:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return TaskService(session_factory)


def test_create_note_persists_task(service: TaskService) -> None:
    note = service.create_note(
        title="Buy milk",
        content="2 bottles",
        priority=NotePriority.MEDIUM,
        due_date=datetime(2026, 6, 2, 9, 0),
    )

    assert note.id is not None
    assert note.status == NoteStatus.IN_PROGRESS
    assert note.created_at is not None


def test_list_notes_for_gui_sorts_active_before_done_then_priority_due_date_and_created_at(
    service: TaskService,
) -> None:
    done = service.create_note("Done", "done", priority=NotePriority.HIGH, status=NoteStatus.DONE)
    later = service.create_note(
        "Later",
        "third",
        priority=NotePriority.LOW,
        due_date=datetime(2026, 6, 3, 10, 0),
    )
    first = service.create_note(
        "First",
        "first",
        priority=NotePriority.HIGH,
        due_date=datetime(2026, 6, 2, 10, 0),
    )
    second = service.create_note(
        "Second",
        "second",
        priority=NotePriority.HIGH,
        due_date=datetime(2026, 6, 2, 10, 0),
    )

    notes = service.list_notes_for_gui()

    assert [note.title for note in notes] == [first.title, second.title, later.title, done.title]


def test_list_active_notes_excludes_done_and_archived(service: TaskService) -> None:
    service.create_note("Active", "todo", priority=NotePriority.LOW)
    service.create_note("Done", "done", priority=NotePriority.LOW, status=NoteStatus.DONE)
    service.create_note("Archived", "archived", priority=NotePriority.LOW, status=NoteStatus.ARCHIVED)

    notes = service.list_active_notes()

    assert [note.title for note in notes] == ["Active"]


def test_update_note_by_id_updates_expected_task(service: TaskService) -> None:
    first = service.create_note("A", "first", priority=NotePriority.LOW)
    service.create_note("B", "second", priority=NotePriority.MEDIUM)

    note = service.update_note_by_id(
        first.id,
        title="Updated A",
        content="updated",
        priority=NotePriority.HIGH,
        due_date=datetime(2026, 6, 4, 18, 0),
    )

    assert note.title == "Updated A"
    assert note.content == "updated"
    assert note.priority == NotePriority.HIGH
    assert note.due_date == datetime(2026, 6, 4, 18, 0)


def test_update_note_by_number_updates_expected_task(service: TaskService) -> None:
    service.create_note("A", "first", priority=NotePriority.LOW)
    service.create_note("B", "second", priority=NotePriority.MEDIUM)

    note = service.update_note_by_number(
        1,
        title="Updated A",
        content="updated",
        priority=NotePriority.HIGH,
        due_date=datetime(2026, 6, 4, 18, 0),
    )

    assert note.title == "Updated A"
    assert note.content == "updated"
    assert note.priority == NotePriority.HIGH
    assert note.due_date == datetime(2026, 6, 4, 18, 0)


def test_mark_done_by_id_updates_expected_task_and_moves_it_below_active(service: TaskService) -> None:
    first = service.create_note("A", "first", priority=NotePriority.HIGH)
    second = service.create_note("B", "second", priority=NotePriority.MEDIUM)

    note = service.mark_done_by_id(first.id)

    assert note.title == "A"
    assert note.status == NoteStatus.DONE
    assert [visible.title for visible in service.list_notes_for_gui()] == [second.title, first.title]


def test_mark_done_by_number_updates_expected_task(service: TaskService) -> None:
    service.create_note("A", "first", priority=NotePriority.HIGH)
    service.create_note("B", "second", priority=NotePriority.MEDIUM)

    note = service.mark_done_by_number(1)

    assert note.title == "A"
    assert note.status == NoteStatus.DONE
    assert [active.title for active in service.list_active_notes()] == ["B"]


def test_delete_done_notes_removes_only_done_tasks(service: TaskService) -> None:
    service.create_note("Active", "todo", priority=NotePriority.LOW)
    service.create_note("Done 1", "done", priority=NotePriority.MEDIUM, status=NoteStatus.DONE)
    service.create_note("Done 2", "done", priority=NotePriority.HIGH, status=NoteStatus.DONE)

    deleted_count = service.delete_done_notes()

    assert deleted_count == 2
    assert [note.title for note in service.list_active_notes()] == ["Active"]


def test_update_note_by_number_rejects_out_of_range(service: TaskService) -> None:
    service.create_note("Only", "task", priority=NotePriority.LOW)

    with pytest.raises(TaskNotFoundError):
        service.update_note_by_number(2, title="Missing")


def test_service_can_list_all_notes_for_cli_secondary_views(service: TaskService) -> None:
    service.create_note("Active", "todo", priority=NotePriority.LOW)
    service.create_note("Done", "done", priority=NotePriority.MEDIUM, status=NoteStatus.DONE)

    notes = service.list_notes()

    assert [note.title for note in notes] == ["Active", "Done"]


def test_update_note_by_id_can_clear_deadline(service: TaskService) -> None:
    note = service.create_note(
        "With deadline",
        "todo",
        priority=NotePriority.MEDIUM,
        due_date=datetime(2026, 6, 5, 9, 0),
    )

    updated = service.update_note_by_id(note.id, due_date=None)

    assert updated.due_date is None


def test_delete_note_by_id_removes_only_targeted_note(service: TaskService) -> None:
    first = service.create_note("First", "todo", priority=NotePriority.LOW)
    second = service.create_note("Second", "todo", priority=NotePriority.HIGH)

    deleted = service.delete_note_by_id(first.id)

    assert deleted is True
    assert [note.title for note in service.list_notes_for_gui()] == [second.title]


def test_id_based_methods_reject_missing_note(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError):
        service.update_note_by_id(999, title="Missing")

    with pytest.raises(TaskNotFoundError):
        service.mark_done_by_id(999)

    with pytest.raises(TaskNotFoundError):
        service.delete_note_by_id(999)
