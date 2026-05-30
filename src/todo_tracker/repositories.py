from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from todo_tracker.models import Note, NoteStatus


class TaskRepository:
    def add(self, session: Session, note: Note) -> Note:
        session.add(note)
        session.commit()
        session.refresh(note)
        return note

    def list_notes(self, session: Session, *, active_only: bool) -> list[Note]:
        stmt = select(Note)
        if active_only:
            stmt = stmt.where(Note.status == NoteStatus.IN_PROGRESS)

        stmt = stmt.order_by(Note.priority.asc(), Note.due_date.asc().nullslast(), Note.created_at.asc())
        return list(session.scalars(stmt))

    def get_by_number(self, session: Session, number: int, *, active_only: bool) -> Note | None:
        if number < 1:
            return None

        notes = self.list_notes(session, active_only=active_only)
        if number > len(notes):
            return None
        return notes[number - 1]

    def save(self, session: Session, note: Note) -> Note:
        session.add(note)
        session.commit()
        session.refresh(note)
        return note

    def delete_done(self, session: Session) -> int:
        stmt = delete(Note).where(Note.status == NoteStatus.DONE)
        result = session.execute(stmt)
        session.commit()
        return int(result.rowcount or 0)
