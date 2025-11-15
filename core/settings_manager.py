import json
import os
from typing import Dict, Any

from data.themes import BOARD_THEMES, PIECE_THEMES


class Settings:
    def __init__(self):
        self.board_theme_index = 0
        self.piece_theme_index = 0
        self.display_mode = "window"  # "window" or "fullscreen"
        self.language = "vi"          # "vi" or "en"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR)) 
DATA_DIR = os.path.join(ROOT_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

SETTINGS_FILE = "data/settings.json"


def settings_to_dict(settings: Settings) -> Dict[str, Any]:
    return {
        "board_theme_index": settings.board_theme_index,
        "piece_theme_index": settings.piece_theme_index,
        "display_mode": settings.display_mode,
        "language": settings.language,
    }


def load_settings() -> Settings:
    s = Settings()
    if not os.path.exists(SETTINGS_FILE):
        return s

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return s

    if isinstance(data, dict):
        if "board_theme_index" in data:
            s.board_theme_index = int(data["board_theme_index"]) % len(BOARD_THEMES)
        if "piece_theme_index" in data:
            s.piece_theme_index = int(data["piece_theme_index"]) % len(PIECE_THEMES)
        if data.get("display_mode") in ("window", "fullscreen"):
            s.display_mode = data["display_mode"]
        if data.get("language") in ("vi", "en"):
            s.language = data["language"]
    return s


def save_settings(settings: Settings) -> None:
    data = settings_to_dict(settings)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
