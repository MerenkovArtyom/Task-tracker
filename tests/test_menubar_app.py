from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from AppKit import NSBitmapImageRep
from Foundation import NSData
from todo_tracker.geometry import POPUP_WIDTH, compute_popup_frame, status_item_screen_frame
from todo_tracker.menubar import resolve_status_icon_path
from todo_tracker.models import Note, NotePriority, NoteStatus
from todo_tracker.popup import (
    NoteRowView,
    PopupContentView,
    PopupController,
    load_button_icon,
    resolve_popup_asset_path,
)


def build_note(note_id: int, title: str = "Test note") -> Note:
    note = Note(
        title=title,
        content="Body",
        status=NoteStatus.IN_PROGRESS,
        priority=NotePriority.MEDIUM,
    )
    note.id = note_id
    return note


def build_row(note: Note, controller: PopupController) -> NoteRowView:
    row_view = NoteRowView.alloc().initWithFrame_(((0, 0), (320, 44)))
    row_view.configure(note, controller, expanded=False)
    controller.row_views.append(row_view)
    controller.notes.append(note)
    return row_view


def test_resolve_status_icon_path_points_to_assets_icon() -> None:
    icon_path = resolve_status_icon_path()

    assert icon_path.name == "icon.png"
    assert icon_path.is_absolute()
    assert icon_path.parent.name == "assets"


def test_resolve_status_icon_path_prefers_bundled_icon_when_present(tmp_path: Path) -> None:
    bundled_icon = tmp_path / "icon.png"
    bundled_icon.write_bytes(b"icon")

    with patch("todo_tracker.menubar.Path.resolve", return_value=tmp_path / "menubar.py"):
        icon_path = resolve_status_icon_path()

    assert icon_path == bundled_icon


def test_compute_popup_frame_uses_fixed_width_and_target_height_cap() -> None:
    frame = compute_popup_frame(
        status_x=900,
        status_y=1000,
        status_width=24,
        screen_min_x=0,
        screen_max_x=1440,
        screen_height=900,
        content_height=1100,
    )

    assert frame["width"] == POPUP_WIDTH
    assert frame["height"] == 450
    assert frame["y"] == 538


def test_resolve_popup_asset_path_points_to_assets_directory() -> None:
    asset_path = resolve_popup_asset_path("pencil.png")

    assert asset_path.name == "pencil.png"
    assert asset_path.is_absolute()
    assert asset_path.parent.name == "assets"


def test_resolve_popup_asset_path_prefers_bundled_asset_when_present(tmp_path: Path) -> None:
    bundled_asset = tmp_path / "trash_can.png"
    bundled_asset.write_bytes(b"icon")

    with patch("todo_tracker.popup.Path.resolve", return_value=tmp_path / "popup.py"):
        asset_path = resolve_popup_asset_path("trash_can.png")

    assert asset_path == bundled_asset


def test_popup_content_view_uses_top_down_coordinate_system() -> None:
    content_view = PopupContentView.alloc().initWithFrame_(((0, 0), (100, 100)))

    assert content_view.isFlipped() is True


def test_load_button_icon_returns_template_image_with_expected_size() -> None:
    image = load_button_icon("pencil.png")

    assert image is not None
    assert image.isTemplate() is True
    assert image.size().width == 16
    assert image.size().height == 16


def test_popup_icons_have_transparent_background() -> None:
    transparent_points = {
        "pencil.png": (20, 20),
        "trash_can.png": (20, 20),
    }
    for name, point in transparent_points.items():
        data = NSData.dataWithContentsOfFile_(str(Path("assets") / name))
        rep = NSBitmapImageRep.imageRepWithData_(data)
        pixel = rep.colorAtX_y_(*point)
        assert pixel.alphaComponent() == 0.0


def test_status_item_screen_frame_uses_button_rect_converted_to_screen() -> None:
    expected = object()

    class FakeWindow:
        def convertRectToScreen_(self, rect):
            assert rect == "button-frame"
            return expected

    class FakeButton:
        def frame(self):
            return "button-frame"

        def window(self):
            return FakeWindow()

    assert status_item_screen_frame(FakeButton()) is expected


def test_menubar_module_has_script_entrypoint_guard() -> None:
    source = Path("src/todo_tracker/menubar.py").read_text()

    assert 'if __name__ == "__main__":' in source
    assert "main()" in source


def test_delete_note_requires_confirmation_before_service_delete() -> None:
    service = Mock()
    service.list_notes_for_gui.return_value = []
    controller = PopupController.alloc().initWithService_(service)
    row_view = build_row(build_note(1), controller)

    controller.deleteNote_(row_view.delete_button)

    assert controller.active_confirm_note_id == 1
    assert row_view.confirming_delete is True
    assert row_view.delete_button.title() == "Подтвердить"
    service.delete_note_by_id.assert_not_called()


def test_delete_confirmation_expands_button_width_for_full_label() -> None:
    service = Mock()
    service.list_notes_for_gui.return_value = []
    controller = PopupController.alloc().initWithService_(service)
    row_view = build_row(build_note(1), controller)
    row_view.layout()
    initial_width = row_view.delete_button.frame().size.width

    controller.deleteNote_(row_view.delete_button)

    assert row_view.delete_button.frame().size.width > initial_width


def test_delete_note_deletes_on_second_click_after_confirmation() -> None:
    service = Mock()
    service.list_notes_for_gui.return_value = []
    controller = PopupController.alloc().initWithService_(service)
    row_view = build_row(build_note(1), controller)

    controller.deleteNote_(row_view.delete_button)
    controller.deleteNote_(row_view.delete_button)

    service.delete_note_by_id.assert_called_once_with(1)
    assert controller.active_confirm_note_id is None


def test_mouse_exit_clears_delete_confirmation() -> None:
    service = Mock()
    service.list_notes_for_gui.return_value = []
    controller = PopupController.alloc().initWithService_(service)
    row_view = build_row(build_note(1), controller)

    controller.deleteNote_(row_view.delete_button)
    row_view.mouseExited_(None)

    assert controller.active_confirm_note_id is None
    assert row_view.confirming_delete is False
    assert row_view.delete_button.title() == ""


def test_clicking_another_row_clears_delete_confirmation() -> None:
    service = Mock()
    service.list_notes_for_gui.return_value = []
    controller = PopupController.alloc().initWithService_(service)
    first_row = build_row(build_note(1, "First"), controller)
    second_row = build_row(build_note(2, "Second"), controller)

    controller.deleteNote_(first_row.delete_button)
    controller.handle_row_click(2)

    assert controller.active_confirm_note_id is None
    assert first_row.confirming_delete is False
    assert second_row.confirming_delete is False


def test_clicking_popup_background_clears_delete_confirmation() -> None:
    service = Mock()
    service.list_notes_for_gui.return_value = []
    controller = PopupController.alloc().initWithService_(service)
    row_view = build_row(build_note(1), controller)

    controller.deleteNote_(row_view.delete_button)
    controller.handle_popup_background_click()

    assert controller.active_confirm_note_id is None
    assert row_view.confirming_delete is False
