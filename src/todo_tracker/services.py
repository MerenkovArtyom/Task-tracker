from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from todo_tracker.models import Note, NotePriority, NoteStatus
from todo_tracker.repositories import TaskRepository


class TaskNotFoundError(Exception):
    pass


UNSET = object()


class TaskService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: TaskRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository or TaskRepository()

    def create_note(
        self,
        title: str,
        content: str,
        priority: NotePriority | str,
        due_date: datetime | None = None,
        status: NoteStatus = NoteStatus.IN_PROGRESS,
    ) -> Note:
        with self._session_factory() as session:
            note = Note(
                title=title,
                content=content,
                priority=priority,
                due_date=due_date,
                status=status,
            )
            return self._repository.add(session, note)

    def list_active_notes(self) -> list[Note]:
        with self._session_factory() as session:
            return self._repository.list_notes(session, active_only=True)

    def list_notes(self) -> list[Note]:
        with self._session_factory() as session:
            return self._repository.list_notes(session, active_only=False)

    def list_notes_for_gui(self) -> list[Note]:
        return self.list_notes()

    def update_note_by_number(
        self,
        number: int,
        *,
        title: str | None = None,
        content: str | None = None,
        priority: NotePriority | str | None = None,
        due_date: datetime | None | object = UNSET,
    ) -> Note:
        with self._session_factory() as session:
            note = self._repository.get_by_number(session, number, active_only=True)
            if note is None:
                raise TaskNotFoundError(f"Task number {number} was not found")
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content
            if priority is not None:
                note.priority = priority
            if due_date is not UNSET:
                note.due_date = due_date
            return self._repository.save(session, note)

    def update_note_by_id(
        self,
        note_id: int,
        *,
        title: str | None = None,
        content: str | None = None,
        priority: NotePriority | str | None = None,
        due_date: datetime | None | object = UNSET,
    ) -> Note:
        with self._session_factory() as session:
            note = self._repository.get_by_id(session, note_id)
            if note is None:
                raise TaskNotFoundError(f"Task id {note_id} was not found")
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content
            if priority is not None:
                note.priority = priority
            if due_date is not UNSET:
                note.due_date = due_date
            return self._repository.save(session, note)

    def mark_done_by_number(self, number: int) -> Note:
        with self._session_factory() as session:
            note = self._repository.get_by_number(session, number, active_only=True)
            if note is None:
                raise TaskNotFoundError(f"Task number {number} was not found")
            note.status = NoteStatus.DONE
            return self._repository.save(session, note)

    def mark_done_by_id(self, note_id: int) -> Note:
        with self._session_factory() as session:
            note = self._repository.get_by_id(session, note_id)
            if note is None:
                raise TaskNotFoundError(f"Task id {note_id} was not found")
            note.status = NoteStatus.DONE
            return self._repository.save(session, note)

    def delete_note_by_id(self, note_id: int) -> bool:
        with self._session_factory() as session:
            deleted = self._repository.delete_by_id(session, note_id)
            if not deleted:
                raise TaskNotFoundError(f"Task id {note_id} was not found")
            return True

    def delete_done_notes(self) -> int:
        with self._session_factory() as session:
            return self._repository.delete_done(session)
