from pathlib import Path
from unittest.mock import patch

from AppKit import NSBitmapImageRep
from Foundation import NSData
from todo_tracker.geometry import POPUP_WIDTH, compute_popup_frame, status_item_screen_frame
from todo_tracker.menubar import resolve_status_icon_path
from todo_tracker.popup import PopupContentView, load_button_icon, resolve_popup_asset_path


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
