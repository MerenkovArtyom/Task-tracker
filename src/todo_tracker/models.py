from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from todo_tracker.db import Base


class NoteStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NoteStatus] = mapped_column(
        SqlEnum(
            NoteStatus,
            name="note_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @validates("status")
    def validate_status(self, _: str, value: NoteStatus | str) -> NoteStatus:
        if isinstance(value, NoteStatus):
            return value
        return NoteStatus(value)
