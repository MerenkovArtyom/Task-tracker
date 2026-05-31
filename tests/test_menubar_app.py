from pathlib import Path
from unittest.mock import patch

from todo_tracker.geometry import POPUP_WIDTH, compute_popup_frame, status_item_screen_frame
from todo_tracker.menubar import resolve_status_icon_path


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


def test_compute_popup_frame_uses_fixed_width_and_half_screen_height_cap() -> None:
    frame = compute_popup_frame(
        status_x=900,
        status_y=1000,
        status_width=24,
        screen_min_x=0,
        screen_max_x=1440,
        screen_height=900,
        content_height=700,
    )

    assert frame["width"] == POPUP_WIDTH
    assert frame["height"] == 450
    assert frame["y"] == 538


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
