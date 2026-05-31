from __future__ import annotations

from sqlalchemy import case, delete, select
from sqlalchemy.orm import Session

from todo_tracker.models import Note, NotePriority, NoteStatus


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
        else:
            stmt = stmt.where(Note.status != NoteStatus.ARCHIVED)

        status_order = case(
            (Note.status == NoteStatus.IN_PROGRESS, 0),
            (Note.status == NoteStatus.DONE, 1),
            else_=2,
        )
        priority_order = case(
            (Note.priority == NotePriority.HIGH, 0),
            (Note.priority == NotePriority.MEDIUM, 1),
            (Note.priority == NotePriority.LOW, 2),
            else_=3,
        )
        stmt = stmt.order_by(
            status_order,
            priority_order,
            Note.due_date.asc().nullslast(),
            Note.created_at.asc(),
        )
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

    def get_by_id(self, session: Session, note_id: int) -> Note | None:
        return session.get(Note, note_id)

    def delete_by_id(self, session: Session, note_id: int) -> bool:
        note = self.get_by_id(session, note_id)
        if note is None:
            return False
        session.delete(note)
        session.commit()
        return True

    def delete_done(self, session: Session) -> int:
        stmt = delete(Note).where(Note.status == NoteStatus.DONE)
        result = session.execute(stmt)
        session.commit()
        return int(result.rowcount or 0)
