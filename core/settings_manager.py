import json
import os
from typing import Dict, Any

from data.themes import BOARD_THEMES
from data.localisation import PIECE_BODY_THEMES, PIECE_SYMBOL_SETS, FONT_BY_LANGUAGE
from data.backgrounds import BACKGROUNDS



class Settings:
    def __init__(self):
        self.board_theme_index = 0
        self.display_mode = "window"  # "window", "window_fullscreen", or "fullscreen"
        self.language = "vi"          # "vi" or "en"
        self.piece_body_theme_index = 0
        self.piece_symbol_set_index = 0
        self.resolution_ratio = "fit"  # "fit" or "wide"
        self.background_index = 0
        self.side_panel_background_index = 0
        # Enable piece movement animation during gameplay
        self.piece_animation = True
        # log box transparency settings (0..255). If disabled, the log box is opaque.
        self.log_box_transparency_enabled = True
        self.log_box_transparency = 200



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR)) 
DATA_DIR = os.path.join(ROOT_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

SETTINGS_FILE = "data/settings.json"


def settings_to_dict(settings: Settings) -> Dict[str, Any]:
    return {
        "board_theme_index": settings.board_theme_index,
        "display_mode": settings.display_mode,
        "language": settings.language,
        "piece_body_theme_index": settings.piece_body_theme_index,
        "piece_symbol_set_index": settings.piece_symbol_set_index,
        "piece_animation": settings.piece_animation,
        "resolution_ratio": settings.resolution_ratio,
        "background_index": settings.background_index,
        "side_panel_background_index": settings.side_panel_background_index,
        "log_box_transparency_enabled": settings.log_box_transparency_enabled,
        "log_box_transparency": settings.log_box_transparency,
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
        if data.get("display_mode") in ("window", "window_fullscreen", "fullscreen"):
            s.display_mode = data["display_mode"]
        # Accept any supported language codes from FONT_BY_LANGUAGE and
        # normalize common variants (eg. zh_HK, zh-TW) to our keys.
        lang_val = data.get("language")
        if isinstance(lang_val, str):
            lv = lang_val.replace('-', '_').lower()
            chosen = None
            if lv in FONT_BY_LANGUAGE:
                chosen = lv
            elif lv.startswith("zh"):
                if "hk" in lv or "hant_hk" in lv:
                    chosen = "hk"
                elif "tw" in lv or "hant" in lv:
                    chosen = "tw"
            elif lv.startswith("ja"):
                chosen = "ja"
            elif lv.startswith("ko"):
                chosen = "ko"
            elif lv.startswith("vi"):
                chosen = "vi"
            elif lv.startswith("en"):
                chosen = "en"

            if chosen and chosen in FONT_BY_LANGUAGE:
                s.language = chosen
        if "piece_body_theme_index" in data and PIECE_BODY_THEMES:
            s.piece_body_theme_index = int(data["piece_body_theme_index"]) % len(PIECE_BODY_THEMES)
        if "piece_symbol_set_index" in data and PIECE_SYMBOL_SETS:
            s.piece_symbol_set_index = int(data["piece_symbol_set_index"]) % len(PIECE_SYMBOL_SETS)
        if "piece_animation" in data:
            try:
                s.piece_animation = bool(data.get("piece_animation", True))
            except Exception:
                s.piece_animation = True
        if data.get("resolution_ratio") in ("fit", "wide"):
            s.resolution_ratio = data["resolution_ratio"]
        if "background_index" in data and BACKGROUNDS:
            s.background_index = int(data["background_index"]) % len(BACKGROUNDS)
        # side panel backgrounds may be defined separately
        try:
            from data.side_panel_backgrounds import SIDE_PANEL_BACKGROUNDS
        except Exception:
            SIDE_PANEL_BACKGROUNDS = None
        if "side_panel_background_index" in data and SIDE_PANEL_BACKGROUNDS:
            s.side_panel_background_index = int(data["side_panel_background_index"]) % len(SIDE_PANEL_BACKGROUNDS)
        if "log_box_transparency_enabled" in data:
            try:
                s.log_box_transparency_enabled = bool(data["log_box_transparency_enabled"])
            except Exception:
                s.log_box_transparency_enabled = True
        if "log_box_transparency" in data:
            try:
                v = int(data["log_box_transparency"]) if data["log_box_transparency"] is not None else 200
                s.log_box_transparency = max(0, min(255, v))
            except Exception:
                s.log_box_transparency = 200

    return s


def save_settings(settings: Settings) -> None:
    data = settings_to_dict(settings)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
