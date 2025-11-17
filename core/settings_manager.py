import json
import os
from typing import Dict, Any

from data.themes import BOARD_THEMES, PIECE_THEMES
from data.localisation import PIECE_BODY_THEMES, PIECE_SYMBOL_SETS



class Settings:
    def __init__(self):
        self.board_theme_index = 0
        self.piece_theme_index = 0
        self.display_mode = "window"  # "window", "window_fullscreen", or "fullscreen"
        self.language = "vi"          # "vi" or "en"
        self.piece_body_theme_index = 0
        self.piece_symbol_set_index = 0
        self.resolution_ratio = "fit"  # "fit" or "wide"



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
        "piece_body_theme_index": settings.piece_body_theme_index,
        "piece_symbol_set_index": settings.piece_symbol_set_index,
        "resolution_ratio": settings.resolution_ratio,
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
        if data.get("display_mode") in ("window", "window_fullscreen", "fullscreen"):
            s.display_mode = data["display_mode"]
        if data.get("language") in ("vi", "en"):
            s.language = data["language"]
        if "piece_body_theme_index" in data and PIECE_BODY_THEMES:
            s.piece_body_theme_index = int(data["piece_body_theme_index"]) % len(PIECE_BODY_THEMES)
        if "piece_symbol_set_index" in data and PIECE_SYMBOL_SETS:
            s.piece_symbol_set_index = int(data["piece_symbol_set_index"]) % len(PIECE_SYMBOL_SETS)
        if data.get("resolution_ratio") in ("fit", "wide"):
            s.resolution_ratio = data["resolution_ratio"]

    return s


def save_settings(settings: Settings) -> None:
    data = settings_to_dict(settings)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
