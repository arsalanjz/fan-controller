from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ICONS_DIR = PROJECT_ROOT / "assets" / "icons"


def get_icon_path(size: int) -> str:
    path = ICONS_DIR / f"fan-controller-icon-{size}x{size}.svg"
    return str(path)


def get_tray_icon_path() -> str:
    path = ICONS_DIR / "fan-controller-icon-tray.svg"
    return str(path)