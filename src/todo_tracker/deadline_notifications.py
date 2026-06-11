from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from Foundation import NSDate, NSMutableDictionary, NSUserNotification

from todo_tracker.models import Note, NoteStatus


NOTIFICATION_SOURCE_KEY = "todo_tracker_source"
NOTIFICATION_SOURCE_VALUE = "todo-tracker"
NOTIFICATION_NOTE_ID_KEY = "todo_tracker_note_id"


def datetime_to_nsdate(value: datetime) -> NSDate:
    return NSDate.dateWithTimeIntervalSince1970_(value.timestamp())


def build_notification_user_info(note: Note) -> NSMutableDictionary:
    user_info = NSMutableDictionary.alloc().init()
    user_info.setObject_forKey_(NOTIFICATION_SOURCE_VALUE, NOTIFICATION_SOURCE_KEY)
    user_info.setObject_forKey_(str(note.id), NOTIFICATION_NOTE_ID_KEY)
    return user_info


def notification_belongs_to_app(notification: Any) -> bool:
    user_info = notification.userInfo()
    if user_info is None:
        return False

    if hasattr(user_info, "objectForKey_"):
        source = user_info.objectForKey_(NOTIFICATION_SOURCE_KEY)
    else:
        source = user_info.get(NOTIFICATION_SOURCE_KEY)
    return str(source) == NOTIFICATION_SOURCE_VALUE


def should_schedule_deadline_notification(note: Note, *, now: datetime) -> bool:
    return (
        note.status == NoteStatus.IN_PROGRESS
        and note.due_date is not None
        and note.due_date >= now
    )


def build_deadline_notification(note: Note, notification_cls: type = NSUserNotification) -> Any:
    notification = notification_cls.alloc().init()
    notification.setTitle_(note.title)
    message = note.content.strip()
    if message:
        notification.setInformativeText_(message)
    notification.setUserInfo_(build_notification_user_info(note))
    notification.setDeliveryDate_(datetime_to_nsdate(note.due_date))
    return notification


def reschedule_deadline_notifications(
    center: Any,
    notes: Iterable[Note],
    *,
    now: datetime | None = None,
    notification_cls: type = NSUserNotification,
) -> None:
    if center is None:
        return

    for notification in list(center.scheduledNotifications() or []):
        if notification_belongs_to_app(notification):
            center.removeScheduledNotification_(notification)

    current_time = now or datetime.now()
    for note in notes:
        if should_schedule_deadline_notification(note, now=current_time):
            center.scheduleNotification_(build_deadline_notification(note, notification_cls=notification_cls))
