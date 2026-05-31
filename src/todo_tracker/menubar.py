from __future__ import annotations

from pathlib import Path
import sys

import objc
import rumps
from AppKit import NSApplication
from rumps.rumps import AppHelper, NSApp, clicked, debug_mode, events, notifications, timer

from todo_tracker.debugging import debug_log, debug_log_exception
from todo_tracker.db import init_db
from todo_tracker.geometry import POPUP_WIDTH, compute_popup_frame, status_item_screen_frame
from todo_tracker.popup import PopupController
from todo_tracker.services import TaskService


def resolve_status_icon_path() -> Path:
    bundled_icon = Path(__file__).resolve().with_name("icon.png")
    if bundled_icon.exists():
        return bundled_icon

    if getattr(sys, "frozen", None) == "macosx_app":
        resource_path = Path.cwd() / "icon.png"
        if resource_path.exists():
            return resource_path

    return Path(__file__).resolve().parents[2] / "assets" / "icon.png"


class StatusButtonTarget(objc.lookUpClass("NSObject")):
    def initWithApp_(self, app: "MenuBarTodoApp"):
        self = objc.super(StatusButtonTarget, self).init()
        if self is None:
            return None
        self.app = app
        return self

    def handleStatusItemClick_(self, _sender):
        debug_log("StatusButtonTarget.handleStatusItemClick_ invoked")
        try:
            self.app.handle_status_click()
        except Exception:
            debug_log_exception("StatusButtonTarget.handleStatusItemClick_ failed")
            raise


class MenuBarTodoApp(rumps.App):
    def __init__(self, db_url: str | None = None) -> None:
        super().__init__(
            "Todo Tracker",
            title=None,
            icon=str(resolve_status_icon_path()),
            template=True,
            menu=[],
            quit_button=None,
        )
        session_factory = init_db(db_url) if db_url else init_db()
        self.service = TaskService(session_factory)
        self.popup_controller = PopupController.alloc().initWithService_(self.service)
        self._status_target = StatusButtonTarget.alloc().initWithApp_(self)
        debug_log("MenuBarTodoApp initialized")

    def run(self, **options):
        dont_change = object()
        debug = options.get("debug", dont_change)
        if debug is not dont_change:
            debug_mode(debug)

        nsapplication = NSApplication.sharedApplication()
        nsapplication.activateIgnoringOtherApps_(True)
        self._nsapp = NSApp.alloc().init()
        self._nsapp._app = self.__dict__
        nsapplication.setDelegate_(self._nsapp)
        notifications._init_nsapp(self._nsapp)

        setattr(rumps.App, "*app_instance", self)
        for current_timer in getattr(timer, "*timers", []):
            current_timer.start()
        for callback in getattr(clicked, "*buttons", []):
            callback(self)

        self._nsapp.initializeStatusBar()
        status_button = self._nsapp.nsstatusitem.button()
        self._nsapp.nsstatusitem.setMenu_(None)
        status_button.setTarget_(self._status_target)
        status_button.setAction_("handleStatusItemClick:")
        debug_log("Status item initialized and action wired")

        AppHelper.installMachInterrupt()
        events.before_start.emit()
        AppHelper.runEventLoop()

    def handle_status_click(self) -> None:
        debug_log("MenuBarTodoApp.handle_status_click called")
        self.popup_controller.toggle_from_status_button(self._nsapp.nsstatusitem.button())


def create_status_app(db_url: str | None = None) -> MenuBarTodoApp:
    return MenuBarTodoApp(db_url=db_url)


def main() -> None:
    create_status_app().run()


if __name__ == "__main__":
    main()
