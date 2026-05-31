from __future__ import annotations

import math
from datetime import datetime

import objc
from AppKit import (
    NSApp,
    NSAttributedString,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSBox,
    NSButton,
    NSColor,
    NSDatePicker,
    NSDatePickerElementFlagHourMinute,
    NSDatePickerElementFlagYearMonthDay,
    NSFloatingWindowLevel,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSMakeRect,
    NSMakeSize,
    NSPanel,
    NSPopUpButton,
    NSRoundedBezelStyle,
    NSScrollView,
    NSStatusWindowLevel,
    NSStringDrawingUsesLineFragmentOrigin,
    NSStrikethroughStyleAttributeName,
    NSTrackingActiveAlways,
    NSTrackingArea,
    NSTrackingInVisibleRect,
    NSTrackingMouseEnteredAndExited,
    NSTextField,
    NSTextView,
    NSView,
    NSViewHeightSizable,
    NSViewWidthSizable,
    NSWindowStyleMaskFullSizeContentView,
    NSWindowStyleMaskTitled,
)
from Foundation import NSDate, NSObject

from todo_tracker.debugging import debug_log, debug_log_exception
from todo_tracker.geometry import WINDOW_GAP, compute_popup_frame, status_item_screen_frame
from todo_tracker.models import Note, NotePriority
from todo_tracker.services import TaskNotFoundError, TaskService


ROW_HORIZONTAL_PADDING = 14
ROW_HEADER_HEIGHT = 34
ROW_BOTTOM_PADDING = 10
ROW_CONTENT_SPACING = 6
ROW_ACTION_WIDTH = 28
ROW_CONTROL_GAP = 8
FOOTER_HEIGHT = 52
EDITOR_HEIGHT = 246
MIN_PANEL_HEIGHT = 180


def datetime_to_nsdate(value: datetime) -> NSDate:
    return NSDate.dateWithTimeIntervalSince1970_(value.timestamp())


def nsdate_to_datetime(value: NSDate) -> datetime:
    return datetime.fromtimestamp(value.timeIntervalSince1970())


def priority_title(priority: NotePriority) -> str:
    return priority.value.capitalize()


def priority_from_title(title: str) -> NotePriority:
    return NotePriority(title.lower())


def measure_text_height(text: str, width: float, font) -> float:
    if not text.strip():
        return 0
    attributed = NSAttributedString.alloc().initWithString_attributes_(
        text,
        {NSFontAttributeName: font},
    )
    rect = attributed.boundingRectWithSize_options_(
        NSMakeSize(max(width, 10), 10_000),
        NSStringDrawingUsesLineFragmentOrigin,
    )
    return math.ceil(rect.size.height)


class NoteRowView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(NoteRowView, self).initWithFrame_(frame)
        if self is None:
            return None

        self.note = None
        self.controller = None
        self.expanded = False
        self.hovered = False
        self._tracking_area = None

        self.setAutoresizingMask_(NSViewWidthSizable)
        self.setWantsLayer_(True)
        self.layer().setCornerRadius_(10.0)

        self.done_button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 24, 24))
        self.done_button.setBordered_(False)
        self.done_button.setFont_(NSFont.systemFontOfSize_(18))
        self.addSubview_(self.done_button)

        self.expand_button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 20, 20))
        self.expand_button.setBordered_(False)
        self.expand_button.setFont_(NSFont.systemFontOfSize_(12))
        self.addSubview_(self.expand_button)

        self.title_field = NSTextField.labelWithString_("")
        self.title_field.setFont_(NSFont.systemFontOfSize_weight_(13, 0.55))
        self.addSubview_(self.title_field)

        self.priority_field = NSTextField.labelWithString_("")
        self.priority_field.setFont_(NSFont.systemFontOfSize_(12))
        self.priority_field.setTextColor_(NSColor.secondaryLabelColor())
        self.addSubview_(self.priority_field)

        self.edit_button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, ROW_ACTION_WIDTH, 24))
        self.edit_button.setTitle_("✎")
        self.edit_button.setBordered_(False)
        self.edit_button.setHidden_(True)
        self.addSubview_(self.edit_button)

        self.delete_button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, ROW_ACTION_WIDTH, 24))
        self.delete_button.setTitle_("🗑")
        self.delete_button.setBordered_(False)
        self.delete_button.setHidden_(True)
        self.addSubview_(self.delete_button)

        self.content_field = NSTextField.labelWithString_("")
        self.content_field.setFont_(NSFont.systemFontOfSize_(12))
        self.content_field.setLineBreakMode_(0)
        self.content_field.setMaximumNumberOfLines_(0)
        self.content_field.setTextColor_(NSColor.secondaryLabelColor())
        self.content_field.setHidden_(True)
        self.addSubview_(self.content_field)

        return self

    @objc.python_method
    def configure(self, note: Note, controller: "PopupController", expanded: bool) -> None:
        self.note = note
        self.controller = controller
        self.expanded = expanded

        note_id = int(note.id)
        self.done_button.setTag_(note_id)
        self.done_button.setTarget_(controller)
        self.done_button.setAction_("toggleDone:")
        self.done_button.setTitle_("◉" if note.status.value == "done" else "○")

        self.expand_button.setTag_(note_id)
        self.expand_button.setTarget_(controller)
        self.expand_button.setAction_("toggleExpanded:")
        self.expand_button.setTitle_("▾" if expanded else "▸")

        self.edit_button.setTag_(note_id)
        self.edit_button.setTarget_(controller)
        self.edit_button.setAction_("editNote:")

        self.delete_button.setTag_(note_id)
        self.delete_button.setTarget_(controller)
        self.delete_button.setAction_("deleteNote:")

        self.priority_field.setStringValue_(priority_title(note.priority))
        self.content_field.setStringValue_(note.content or "")
        self.content_field.setHidden_(not expanded)
        self._update_title()
        self._update_hover()
        self.needsLayout = True

    @objc.python_method
    def _update_title(self) -> None:
        if self.note is None:
            return
        font = NSFont.systemFontOfSize_weight_(13, 0.55)
        color = NSColor.secondaryLabelColor() if self.note.status.value == "done" else NSColor.labelColor()
        attributes = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: color,
        }
        if self.note.status.value == "done":
            attributes[NSStrikethroughStyleAttributeName] = 1
        attributed = NSAttributedString.alloc().initWithString_attributes_(self.note.title, attributes)
        self.title_field.setAttributedStringValue_(attributed)

    @objc.python_method
    def preferred_height(self, width: float) -> float:
        if self.note is None:
            return ROW_HEADER_HEIGHT + ROW_BOTTOM_PADDING
        height = ROW_HEADER_HEIGHT + ROW_BOTTOM_PADDING
        if self.expanded:
            text_width = width - (ROW_HORIZONTAL_PADDING * 2) - 48
            text_height = measure_text_height(
                self.note.content or "",
                text_width,
                self.content_field.font(),
            )
            height += ROW_CONTENT_SPACING + text_height
        return max(ROW_HEADER_HEIGHT + ROW_BOTTOM_PADDING, height)

    def updateTrackingAreas(self):
        if self._tracking_area is not None:
            self.removeTrackingArea_(self._tracking_area)
        options = NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways | NSTrackingInVisibleRect
        self._tracking_area = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(),
            options,
            self,
            None,
        )
        self.addTrackingArea_(self._tracking_area)
        objc.super(NoteRowView, self).updateTrackingAreas()

    def mouseEntered_(self, _event):
        self.hovered = True
        self._update_hover()

    def mouseExited_(self, _event):
        self.hovered = False
        self._update_hover()

    @objc.python_method
    def _update_hover(self) -> None:
        hidden = not self.hovered
        self.edit_button.setHidden_(hidden)
        self.delete_button.setHidden_(hidden)
        background = (
            NSColor.controlAccentColor().colorWithAlphaComponent_(0.08)
            if self.hovered
            else NSColor.clearColor()
        )
        self.layer().setBackgroundColor_(background.CGColor())

    def layout(self):
        objc.super(NoteRowView, self).layout()
        width = self.bounds().size.width
        content_height = self.preferred_height(width)
        self.setFrameSize_(NSMakeSize(width, content_height))

        top = content_height - ROW_HEADER_HEIGHT
        x = ROW_HORIZONTAL_PADDING

        self.done_button.setFrame_(NSMakeRect(x, top + 4, 24, 24))
        x += 24 + ROW_CONTROL_GAP

        self.expand_button.setFrame_(NSMakeRect(x, top + 6, 20, 20))
        x += 20 + ROW_CONTROL_GAP

        action_x = width - ROW_HORIZONTAL_PADDING - ROW_ACTION_WIDTH
        self.delete_button.setFrame_(NSMakeRect(action_x, top + 6, ROW_ACTION_WIDTH, 20))
        self.edit_button.setFrame_(NSMakeRect(action_x - ROW_ACTION_WIDTH - 4, top + 6, ROW_ACTION_WIDTH, 20))

        priority_width = 60
        title_width = max(120, self.edit_button.frame().origin.x - x - priority_width - 8)
        self.title_field.setFrame_(NSMakeRect(x, top + 8, title_width, 18))
        self.priority_field.setFrame_(NSMakeRect(x + title_width + 8, top + 8, priority_width, 18))

        if self.expanded:
            content_y = ROW_BOTTOM_PADDING
            content_width = width - (ROW_HORIZONTAL_PADDING * 2) - 48
            self.content_field.setFrame_(NSMakeRect(x, content_y, content_width, content_height - ROW_HEADER_HEIGHT - ROW_CONTENT_SPACING - ROW_BOTTOM_PADDING))


class NoteEditorView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(NoteEditorView, self).initWithFrame_(frame)
        if self is None:
            return None

        self.controller = None
        self.current_note_id = None
        self.deadline_enabled = False

        self.setAutoresizingMask_(NSViewWidthSizable)
        self.setHidden_(True)

        self.separator = NSBox.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 1))
        self.separator.setBoxType_(2)
        self.addSubview_(self.separator)

        self.title_field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 28))
        self.title_field.setPlaceholderString_("Title")
        self.addSubview_(self.title_field)

        self.priority_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(0, 0, 120, 28), False)
        self.priority_popup.addItemsWithTitles_(["High", "Medium", "Low"])
        self.addSubview_(self.priority_popup)

        self.deadline_button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 120, 28))
        self.deadline_button.setBezelStyle_(NSRoundedBezelStyle)
        self.deadline_button.setTarget_(self)
        self.deadline_button.setAction_("toggleDeadline:")
        self.addSubview_(self.deadline_button)

        self.date_picker = NSDatePicker.alloc().initWithFrame_(NSMakeRect(0, 0, 220, 28))
        self.date_picker.setDatePickerElements_(NSDatePickerElementFlagYearMonthDay | NSDatePickerElementFlagHourMinute)
        self.date_picker.setDateValue_(NSDate.date())
        self.date_picker.setHidden_(True)
        self.addSubview_(self.date_picker)

        self.text_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 100))
        self.text_scroll.setHasVerticalScroller_(True)
        self.text_view = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 100))
        self.text_scroll.setDocumentView_(self.text_view)
        self.addSubview_(self.text_scroll)

        self.cancel_button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 88, 30))
        self.cancel_button.setTitle_("Cancel")
        self.cancel_button.setBezelStyle_(NSRoundedBezelStyle)
        self.cancel_button.setTarget_(self)
        self.cancel_button.setAction_("cancel:")
        self.addSubview_(self.cancel_button)

        self.save_button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 30))
        self.save_button.setBezelStyle_(NSRoundedBezelStyle)
        self.save_button.setTarget_(self)
        self.save_button.setAction_("save:")
        self.addSubview_(self.save_button)

        self._update_deadline_controls()
        return self

    @objc.python_method
    def set_controller(self, controller: "PopupController") -> None:
        self.controller = controller

    @objc.python_method
    def show_for_create(self) -> None:
        self.current_note_id = None
        self.title_field.setStringValue_("")
        self.text_view.setString_("")
        self.priority_popup.selectItemWithTitle_("Medium")
        self.deadline_enabled = False
        self.date_picker.setDateValue_(NSDate.date())
        self._update_deadline_controls()
        self.save_button.setTitle_("Add note")
        self.setHidden_(False)
        self.needsLayout = True

    @objc.python_method
    def show_for_edit(self, note: Note) -> None:
        self.current_note_id = note.id
        self.title_field.setStringValue_(note.title)
        self.text_view.setString_(note.content)
        self.priority_popup.selectItemWithTitle_(priority_title(note.priority))
        self.deadline_enabled = note.due_date is not None
        if note.due_date is not None:
            self.date_picker.setDateValue_(datetime_to_nsdate(note.due_date))
        else:
            self.date_picker.setDateValue_(NSDate.date())
        self._update_deadline_controls()
        self.save_button.setTitle_("Save note")
        self.setHidden_(False)
        self.needsLayout = True

    @objc.python_method
    def hide_editor(self) -> None:
        self.current_note_id = None
        self.setHidden_(True)

    @objc.python_method
    def visible_height(self) -> float:
        return 0 if self.isHidden() else EDITOR_HEIGHT

    @objc.python_method
    def _update_deadline_controls(self) -> None:
        self.date_picker.setHidden_(not self.deadline_enabled)
        self.deadline_button.setTitle_("Remove deadline" if self.deadline_enabled else "Add deadline")

    def toggleDeadline_(self, _sender):
        self.deadline_enabled = not self.deadline_enabled
        self._update_deadline_controls()
        if self.controller is not None:
            self.controller.layoutContentViews()

    def cancel_(self, _sender):
        if self.controller is not None:
            self.controller.hideEditor()

    def save_(self, _sender):
        if self.controller is None:
            return
        title = self.title_field.stringValue().strip()
        content = self.text_view.string().strip()
        priority = priority_from_title(self.priority_popup.titleOfSelectedItem())
        due_date = nsdate_to_datetime(self.date_picker.dateValue()) if self.deadline_enabled else None
        self.controller.submit_editor(
            self.current_note_id or 0,
            title,
            content,
            priority,
            due_date,
        )

    def layout(self):
        objc.super(NoteEditorView, self).layout()
        width = self.bounds().size.width
        y = self.bounds().size.height - 1
        self.separator.setFrame_(NSMakeRect(0, y, width, 1))

        field_width = width - 24
        self.title_field.setFrame_(NSMakeRect(12, y - 38, field_width, 28))
        self.priority_popup.setFrame_(NSMakeRect(12, y - 74, 120, 28))
        self.deadline_button.setFrame_(NSMakeRect(142, y - 74, 140, 28))
        if self.deadline_enabled:
            self.date_picker.setFrame_(NSMakeRect(292, y - 74, field_width - 280, 28))
        self.text_scroll.setFrame_(NSMakeRect(12, 52, field_width, 100))
        self.cancel_button.setFrame_(NSMakeRect(width - 196, 12, 88, 30))
        self.save_button.setFrame_(NSMakeRect(width - 100, 12, 88, 30))


class PopupController(NSObject):
    def initWithService_(self, service: TaskService):
        self = objc.super(PopupController, self).init()
        if self is None:
            return None

        self.service = service
        self.panel = None
        self.root_view = None
        self.scroll_view = None
        self.document_view = None
        self.editor_view = None
        self.add_button = None
        self.status_button = None
        self.notes = []
        self.expanded_note_ids = set()
        self.row_views = []
        self.last_error = None
        return self

    @objc.python_method
    def ensure_panel(self) -> None:
        if self.panel is not None:
            debug_log("PopupController.ensure_panel reused existing panel")
            return

        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 560, MIN_PANEL_HEIGHT),
            NSWindowStyleMaskTitled | NSWindowStyleMaskFullSizeContentView,
            NSBackingStoreBuffered,
            False,
        )
        panel.setTitleVisibility_(1)
        panel.setTitlebarAppearsTransparent_(True)
        panel.setMovable_(False)
        panel.setFloatingPanel_(True)
        panel.setHidesOnDeactivate_(False)
        panel.setLevel_(max(NSFloatingWindowLevel, NSStatusWindowLevel))
        panel.setDelegate_(self)

        root = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 560, MIN_PANEL_HEIGHT))
        root.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        panel.setContentView_(root)

        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, FOOTER_HEIGHT, 560, 100))
        scroll.setHasVerticalScroller_(True)
        scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        doc = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 560, 100))
        doc.setAutoresizingMask_(NSViewWidthSizable)
        scroll.setDocumentView_(doc)
        root.addSubview_(scroll)

        editor = NoteEditorView.alloc().initWithFrame_(NSMakeRect(0, FOOTER_HEIGHT, 560, EDITOR_HEIGHT))
        editor.set_controller(self)
        root.addSubview_(editor)

        add_button = NSButton.alloc().initWithFrame_(NSMakeRect(12, 10, 180, 32))
        add_button.setTitle_("Add note")
        add_button.setBezelStyle_(NSRoundedBezelStyle)
        add_button.setTarget_(self)
        add_button.setAction_("addNote:")
        root.addSubview_(add_button)

        self.panel = panel
        self.root_view = root
        self.scroll_view = scroll
        self.document_view = doc
        self.editor_view = editor
        self.add_button = add_button
        debug_log("PopupController.ensure_panel created panel")

    @objc.python_method
    def toggle_from_status_button(self, status_button) -> None:
        try:
            self.ensure_panel()
            self.status_button = status_button
            debug_log(f"PopupController.toggle_from_status_button visible_before={self.panel.isVisible()}")
            if self.panel.isVisible():
                self.panel.orderOut_(None)
                debug_log("PopupController.toggle_from_status_button hid panel")
                return

            debug_log("PopupController.toggle_from_status_button reloading notes")
            self.reload_notes()
            debug_log("PopupController.toggle_from_status_button laying out content")
            self.layoutContentViews()
            debug_log("PopupController.toggle_from_status_button positioning panel")
            self.position_panel()
            self.panel.orderFrontRegardless()
            debug_log(f"PopupController.toggle_from_status_button showed panel frame={self.panel.frame()}")
            NSApp.activateIgnoringOtherApps_(True)
        except Exception:
            debug_log_exception("PopupController.toggle_from_status_button failed")
            raise

    @objc.python_method
    def position_panel(self) -> None:
        if self.status_button is None:
            debug_log("PopupController.position_panel skipped because status_button is None")
            return
        screen = self.status_button.window().screen()
        visible_frame = screen.visibleFrame() if screen is not None else self.panel.screen().visibleFrame()
        status_frame = status_item_screen_frame(self.status_button)

        content_height = self.document_view.frame().size.height + FOOTER_HEIGHT + self.editor_view.visible_height()
        frame = compute_popup_frame(
            status_x=status_frame.origin.x,
            status_y=status_frame.origin.y + status_frame.size.height,
            status_width=status_frame.size.width,
            screen_min_x=visible_frame.origin.x,
            screen_max_x=visible_frame.origin.x + visible_frame.size.width,
            screen_height=visible_frame.size.height,
            content_height=max(content_height, MIN_PANEL_HEIGHT),
        )
        self.panel.setFrame_display_(NSMakeRect(frame["x"], frame["y"], frame["width"], frame["height"]), True)
        debug_log(
            "PopupController.position_panel "
            f"status_frame={status_frame} visible_frame={visible_frame} panel_frame={self.panel.frame()}"
        )

    @objc.python_method
    def layoutContentViews(self) -> None:
        if self.panel is None:
            return
        bounds = self.root_view.bounds()
        editor_height = self.editor_view.visible_height()
        scroll_height = max(80, bounds.size.height - FOOTER_HEIGHT - editor_height)
        self.scroll_view.setFrame_(NSMakeRect(0, FOOTER_HEIGHT + editor_height, bounds.size.width, scroll_height))
        self.editor_view.setFrame_(NSMakeRect(0, FOOTER_HEIGHT, bounds.size.width, editor_height))
        self.add_button.setFrame_(NSMakeRect(12, 10, bounds.size.width - 24, 32))
        self._layout_rows(bounds.size.width)
        self.position_panel()

    @objc.python_method
    def _layout_rows(self, width: float) -> None:
        content_width = width - 14
        y = 0
        for row_view in self.row_views:
            row_height = row_view.preferred_height(content_width)
            row_view.setFrame_(NSMakeRect(7, y, content_width, row_height))
            row_view.needsLayout = True
            y += row_height + 6
        self.document_view.setFrame_(NSMakeRect(0, 0, width, max(y, 1)))

    @objc.python_method
    def reload_notes(self) -> None:
        self.notes = self.service.list_notes_for_gui()
        for subview in list(self.document_view.subviews()):
            subview.removeFromSuperview()
        self.row_views = []
        for note in self.notes:
            row_view = NoteRowView.alloc().initWithFrame_(NSMakeRect(0, 0, 100, 44))
            row_view.configure(note, self, note.id in self.expanded_note_ids)
            self.document_view.addSubview_(row_view)
            self.row_views.append(row_view)

    @objc.python_method
    def hideEditor(self) -> None:
        self.editor_view.hide_editor()
        self.layoutContentViews()

    @objc.python_method
    def _note_by_id(self, note_id: int) -> Note | None:
        for note in self.notes:
            if int(note.id) == int(note_id):
                return note
        return None

    def addNote_(self, _sender):
        self.editor_view.show_for_create()
        self.layoutContentViews()

    def toggleExpanded_(self, sender):
        note_id = int(sender.tag())
        if note_id in self.expanded_note_ids:
            self.expanded_note_ids.remove(note_id)
        else:
            self.expanded_note_ids.add(note_id)
        self.reload_notes()
        self.layoutContentViews()

    def toggleDone_(self, sender):
        note_id = int(sender.tag())
        try:
            self.service.mark_done_by_id(note_id)
        except TaskNotFoundError as exc:
            self.last_error = str(exc)
        self.reload_notes()
        self.layoutContentViews()

    def editNote_(self, sender):
        note = self._note_by_id(int(sender.tag()))
        if note is None:
            return
        self.editor_view.show_for_edit(note)
        self.layoutContentViews()

    def deleteNote_(self, sender):
        note_id = int(sender.tag())
        try:
            self.service.delete_note_by_id(note_id)
        except TaskNotFoundError as exc:
            self.last_error = str(exc)
        self.expanded_note_ids.discard(note_id)
        self.reload_notes()
        self.layoutContentViews()

    @objc.python_method
    def submit_editor(self, note_id: int, title: str, content: str, priority: NotePriority, due_date: datetime | None) -> None:
        if not title:
            return
        if note_id:
            self.service.update_note_by_id(
                int(note_id),
                title=title,
                content=content,
                priority=priority,
                due_date=due_date,
            )
        else:
            self.service.create_note(
                title=title,
                content=content,
                priority=priority,
                due_date=due_date,
            )
        self.hideEditor()
        self.reload_notes()
        self.layoutContentViews()
