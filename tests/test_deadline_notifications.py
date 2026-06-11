from __future__ import annotations

from datetime import datetime, timedelta

from todo_tracker.deadline_notifications import (
    NOTIFICATION_NOTE_ID_KEY,
    NOTIFICATION_SOURCE_KEY,
    NOTIFICATION_SOURCE_VALUE,
    build_deadline_notification,
    notification_belongs_to_app,
    reschedule_deadline_notifications,
    should_schedule_deadline_notification,
)
from todo_tracker.models import Note, NotePriority, NoteStatus


class FakeNotification:
    def __init__(self) -> None:
        self.title = None
        self.subtitle = None
        self.message = None
        self.delivery_date = None
        self.user_info = None

    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self

    def setTitle_(self, value):
        self.title = value

    def setSubtitle_(self, value):
        self.subtitle = value

    def setInformativeText_(self, value):
        self.message = value

    def setUserInfo_(self, value):
        self.user_info = value

    def setDeliveryDate_(self, value):
        self.delivery_date = value

    def userInfo(self):
        return self.user_info


class FakeCenter:
    def __init__(self, scheduled=None) -> None:
        self._scheduled = list(scheduled or [])
        self.removed = []
        self.added = []

    def scheduledNotifications(self):
        return list(self._scheduled)

    def removeScheduledNotification_(self, notification):
        self.removed.append(notification)
        self._scheduled = [item for item in self._scheduled if item is not notification]

    def scheduleNotification_(self, notification):
        self.added.append(notification)


def build_note(
    note_id: int,
    *,
    status: NoteStatus = NoteStatus.IN_PROGRESS,
    due_date: datetime | None = None,
    content: str = "Body",
) -> Note:
    note = Note(
        title=f"Task {note_id}",
        content=content,
        priority=NotePriority.MEDIUM,
        status=status,
        due_date=due_date,
    )
    note.id = note_id
    return note


def test_should_schedule_deadline_notification_accepts_future_in_progress_note() -> None:
    now = datetime(2026, 6, 11, 12, 0)
    note = build_note(1, due_date=now + timedelta(minutes=1))

    assert should_schedule_deadline_notification(note, now=now) is True


def test_should_schedule_deadline_notification_rejects_done_note() -> None:
    now = datetime(2026, 6, 11, 12, 0)
    note = build_note(1, status=NoteStatus.DONE, due_date=now + timedelta(minutes=1))

    assert should_schedule_deadline_notification(note, now=now) is False


def test_should_schedule_deadline_notification_rejects_archived_note() -> None:
    now = datetime(2026, 6, 11, 12, 0)
    note = build_note(1, status=NoteStatus.ARCHIVED, due_date=now + timedelta(minutes=1))

    assert should_schedule_deadline_notification(note, now=now) is False


def test_should_schedule_deadline_notification_rejects_note_without_due_date() -> None:
    now = datetime(2026, 6, 11, 12, 0)
    note = build_note(1, due_date=None)

    assert should_schedule_deadline_notification(note, now=now) is False


def test_should_schedule_deadline_notification_rejects_past_due_date() -> None:
    now = datetime(2026, 6, 11, 12, 0)
    note = build_note(1, due_date=now - timedelta(minutes=1))

    assert should_schedule_deadline_notification(note, now=now) is False


def test_build_deadline_notification_uses_stable_payload() -> None:
    due_date = datetime(2026, 6, 11, 12, 30)
    note = build_note(7, due_date=due_date, content="Call client")

    notification = build_deadline_notification(note, notification_cls=FakeNotification)

    assert notification.title == "Task 7"
    assert notification.subtitle is None
    assert notification.message == "Call client"
    assert str(notification.userInfo().objectForKey_(NOTIFICATION_SOURCE_KEY)) == NOTIFICATION_SOURCE_VALUE
    assert str(notification.userInfo().objectForKey_(NOTIFICATION_NOTE_ID_KEY)) == "7"
    assert notification.delivery_date is not None


def test_build_deadline_notification_leaves_message_empty_without_note_content() -> None:
    due_date = datetime(2026, 6, 11, 12, 30)
    note = build_note(8, due_date=due_date, content="   ")

    notification = build_deadline_notification(note, notification_cls=FakeNotification)

    assert notification.title == "Task 8"
    assert notification.subtitle is None
    assert notification.message is None


def test_reschedule_deadline_notifications_replaces_only_app_owned_notifications() -> None:
    owned = FakeNotification()
    owned.setUserInfo_({NOTIFICATION_SOURCE_KEY: NOTIFICATION_SOURCE_VALUE})
    foreign = FakeNotification()
    foreign.setUserInfo_({"source": "other-app"})
    center = FakeCenter([owned, foreign])
    now = datetime(2026, 6, 11, 12, 0)
    notes = [
        build_note(1, due_date=now + timedelta(minutes=5)),
        build_note(2, status=NoteStatus.DONE, due_date=now + timedelta(minutes=10)),
    ]

    reschedule_deadline_notifications(center, notes, now=now, notification_cls=FakeNotification)

    assert center.removed == [owned]
    assert center.added[0].title == "Task 1"
    assert center.added[0].subtitle is None
    assert len(center.added) == 1
    assert foreign in center.scheduledNotifications()


def test_notification_belongs_to_app_rejects_notification_without_matching_user_info() -> None:
    notification = FakeNotification()
    notification.setUserInfo_({"source": "other-app"})

    assert notification_belongs_to_app(notification) is False
