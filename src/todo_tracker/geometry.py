from __future__ import annotations


POPUP_WIDTH = 560
TARGET_POPUP_HEIGHT = 450
WINDOW_GAP = 12


def compute_popup_frame(
    *,
    status_x: float,
    status_y: float,
    status_width: float,
    screen_min_x: float,
    screen_max_x: float,
    screen_height: float,
    content_height: float,
) -> dict[str, float]:
    available_height = max(int(screen_height) - (WINDOW_GAP * 2), 0)
    height = min(available_height, TARGET_POPUP_HEIGHT)
    x = status_x + (status_width / 2) - (POPUP_WIDTH / 2)
    x = max(screen_min_x + 8, min(x, screen_max_x - POPUP_WIDTH - 8))
    y = status_y - height - WINDOW_GAP
    return {"x": x, "y": y, "width": POPUP_WIDTH, "height": height}


def status_item_screen_frame(status_button) -> object:
    button_window = status_button.window()
    return button_window.convertRectToScreen_(status_button.frame())
