import os
import math
import pygame

from config import (
    BOARD_COLS,
    BOARD_ROWS,
    CELL_SIZE,
    MARGIN_X,
    MARGIN_Y,
    BOARD_OFFSET_Y,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)
from core.engine.board import Board
from core.engine.types import Side, Move, PieceType

from data.localisation import TEXT, PIECE_BODY_THEMES, PIECE_SYMBOL_SETS, t, FONT_BY_LANGUAGE
from data.themes import BOARD_THEMES
from data.backgrounds import BACKGROUNDS
from data.side_panel_backgrounds import SIDE_PANEL_BACKGROUNDS
from core.settings_manager import Settings, load_settings, save_settings
from data.avatar_assets import (
    ASSETS_DIR,
    BUILTIN_AVATARS,
    get_piece_sprite,
    select_avatar_file_dialog,
    AVATAR_BOARD_SIZE,
    process_and_save_avatar,
    delete_avatar_file,
)
from core.profiles_manager import DEFAULT_ELO, load_profiles, save_profiles, find_player, apply_game_result_to_profiles
from core.engine.constants import AI_SIDE, HUMAN_SIDE
from core.engine.ai_engine import AI_LEVELS, choose_ai_move
from core.ui_components import Button
from core.engine.draw_helpers import (
    draw_board,
    draw_selection,
    draw_move_hints,
    draw_move_origin,
    draw_piece_preview,
    draw_side_avatars_on_board,
    draw_profile_avatar,
    draw_ai_avatar,
    get_bottom_avatar_rect,
    get_top_avatar_rect,
    board_to_screen,
    screen_to_board,
)



def run_game():
    pygame.init()

    settings = load_settings()
    profiles_data = load_profiles()

    base_width = WINDOW_WIDTH
    base_height = WINDOW_HEIGHT
    base_ratio = base_width / base_height
    resolution_ratios = {
        "fit": base_ratio,
        "wide": 16 / 9,
    }

    def ratio_value(key: str) -> float:
        return resolution_ratios.get(key, resolution_ratios["fit"])

    target_ratio = ratio_value(settings.resolution_ratio)
    screen_info = pygame.display.Info()
    max_screen_w, max_screen_h = screen_info.current_w, screen_info.current_h

    def compute_logical_width():
        return max(base_width, int(round(base_height * target_ratio)))

    logical_width = compute_logical_width()

    def lock_size_to_ratio(width, height):
        width = min(max_screen_w, width)
        height = min(max_screen_h, height)
        width_based_height = int(round(width / target_ratio))
        height_based_width = int(round(height * target_ratio))
        if abs(width_based_height - height) <= abs(height_based_width - width):
            result_w, result_h = width, width_based_height
        else:
            result_w, result_h = height_based_width, height
        result_w = min(max_screen_w, max(400, result_w))
        result_h = min(max_screen_h, max(400, result_h))
        return result_w, result_h

    def initial_window_size():
        width = int(round(base_height * target_ratio))
        height = base_height
        width = min(max_screen_w, max(400, width))
        height = min(max_screen_h, max(400, height))
        return width, height

    window_mode_size = initial_window_size()
    window_flags = 0

    if settings.display_mode == "fullscreen":
        window_flags = pygame.FULLSCREEN | pygame.DOUBLEBUF
        window_surface = pygame.display.set_mode((0, 0), window_flags)
    elif settings.display_mode == "window_fullscreen":
        info = pygame.display.Info()
        window_mode_size = (info.current_w, info.current_h)
        window_flags = pygame.NOFRAME | pygame.DOUBLEBUF
        window_surface = pygame.display.set_mode(window_mode_size, window_flags)
    else:
        window_flags = pygame.RESIZABLE | pygame.DOUBLEBUF
        window_mode_size = lock_size_to_ratio(*window_mode_size)
        window_surface = pygame.display.set_mode(window_mode_size, window_flags)

    # Attempt to set a window icon if an icon file is provided.
    # Prefer a top-level `icon.ico` in the project root, fall back to bundled assets.
    try:
        icon_candidates = [
            os.path.join(os.getcwd(), "icon.ico"),
            os.path.join(os.getcwd(), "icon.png"),
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons", "icon.png"),
            os.path.join(ASSETS_DIR, "icons", "icon.png"),
        ]
        for p in icon_candidates:
            p = os.path.normpath(p)
            if os.path.exists(p):
                try:
                    icon_surf = pygame.image.load(p)
                    pygame.display.set_icon(icon_surf)
                    break
                except Exception:
                    # ignore and try the next candidate
                    continue
    except Exception:
        pass

    pygame.display.set_caption("Xiangqi - Cờ Tướng")

    screen = pygame.Surface((base_width, base_height), pygame.SRCALPHA).convert_alpha()

    render_scale = 1.0
    render_size = (base_width, base_height)
    render_offset = (0, 0)
    frame_surface = pygame.Surface((logical_width, base_height), pygame.SRCALPHA).convert_alpha()

    # Avatar overlay button state
    avatar_buttons_open = False
    avatar_buttons_side = None  # 'bottom' or 'top'
    avatar_button_rects = {}
    # Active piece move animations
    # Each entry: {"piece": Piece, "from": (c,r), "to": (c,r), "start": ticks, "duration": seconds, "sprite": Surface}
    animations = []
    # Load component icons
    try:
        upload_img = pygame.image.load(os.path.join(ASSETS_DIR, "components", "upload.png")).convert_alpha()
    except Exception:
        upload_img = None
    try:
        delete_img = pygame.image.load(os.path.join(ASSETS_DIR, "components", "delete.png")).convert_alpha()
    except Exception:
        delete_img = None

    def refresh_render_targets():
        nonlocal frame_surface
        frame_surface = pygame.Surface((logical_width, base_height), pygame.SRCALPHA).convert_alpha()
        recompute_render_scale()

    def recompute_render_scale():
        nonlocal render_scale, render_size, render_offset
        win_w, win_h = window_surface.get_size()
        render_scale = min(win_w / logical_width, win_h / base_height)
        render_size = (
            max(1, int(logical_width * render_scale)),
            max(1, int(base_height * render_scale)),
        )
        render_offset = (
            (win_w - render_size[0]) // 2,
            (win_h - render_size[1]) // 2,
        )

    recompute_render_scale()

    clock = pygame.time.Clock()
    def _normalize_lang(code: str) -> str:
        if not code:
            return "en"
        c = code.replace('-', '_').lower()
        # common Chinese variants
        if c.startswith("zh"):
            if "hk" in c or "hant_hk" in c:
                return "hk"
            if "tw" in c or "hant" in c:
                return "tw"
            # default to traditional (tw) if explicitly traditional requested
            return "tw" if "traditional" in c or "hant" in c else "en"
        # direct mappings
        if c.startswith("ja"):
            return "ja"
        if c.startswith("ko"):
            return "ko"
        if c.startswith("vi"):
            return "vi"
        if c.startswith("en"):
            return "en"
        # fallback to provided code if matches mapping keys
        return c

    def load_font_for_language(lang_code: str, size: int, fallback_name: str = "Consolas"):
        try:
            key = _normalize_lang(lang_code)
            mapping = FONT_BY_LANGUAGE.get(key)
            # If we have an explicit mapping, try that first
            if mapping:
                font_path = os.path.join(ASSETS_DIR, "fonts", mapping["folder"], mapping["file"])
                if os.path.exists(font_path):
                    return pygame.font.Font(font_path, size)
                # if mapped file not present, try any font under the folder
                folder_path = os.path.join(ASSETS_DIR, "fonts", mapping["folder"])
                if os.path.isdir(folder_path):
                    for fname in os.listdir(folder_path):
                        if fname.lower().endswith((".ttf", ".otf")):
                            candidate = os.path.join(folder_path, fname)
                            try:
                                return pygame.font.Font(candidate, size)
                            except Exception:
                                continue
            # Try generic folder matching normalized key
            alt_folder = os.path.join(ASSETS_DIR, "fonts", key)
            if os.path.isdir(alt_folder):
                for fname in os.listdir(alt_folder):
                    if fname.lower().endswith((".ttf", ".otf")):
                        candidate = os.path.join(alt_folder, fname)
                        try:
                            return pygame.font.Font(candidate, size)
                        except Exception:
                            continue
        except Exception:
            pass
        # As a last resort, try a platform/system font likely to contain CJK glyphs
        try:
            if key in ("ja",):
                return pygame.font.SysFont("MS Gothic", size) or pygame.font.SysFont(fallback_name, size)
            if key in ("ko",):
                return pygame.font.SysFont("Malgun Gothic", size) or pygame.font.SysFont(fallback_name, size)
            if key in ("hk", "tw"):
                return pygame.font.SysFont("Microsoft JhengHei", size) or pygame.font.SysFont(fallback_name, size)
            return pygame.font.SysFont(fallback_name, size)
        except Exception:
            return pygame.font.Font(None, size)

    # Load fonts according to selected language (bundled where available)
    # use already-loaded settings variable and normalize variants like 'zh_HK' -> 'hk'
    lang_code = getattr(settings, "language", "en")
    font_piece = load_font_for_language(lang_code, 28, fallback_name="SimHei")
    font_text = load_font_for_language(lang_code, 18, fallback_name="Consolas")
    font_button = load_font_for_language(lang_code, 16, fallback_name="Consolas")
    font_title = load_font_for_language(lang_code, 40, fallback_name="SimHei")
    font_avatar = load_font_for_language(lang_code, 16, fallback_name="Consolas")
    font_timer = load_font_for_language(lang_code, 24, fallback_name="Consolas")

    TIMER_CHOICES = [
        {"label": "1:00", "seconds": 60, "asset": os.path.join("components", "1m.jpg")},
        {"label": "5:00", "seconds": 300, "asset": os.path.join("components", "5m.jpg")},
        {"label": "10:00", "seconds": 600, "asset": os.path.join("components", "10m.jpg")},
        {"label": "∞", "seconds": None, "asset": os.path.join("components", "infinite.jpg")},
    ]

    board = Board()
    human_side = HUMAN_SIDE
    ai_side = AI_SIDE
    current_side = Side.RED
    selected = None
    valid_moves = []
    move_history = []
    redo_stack = []
    in_check_side = None
    game_over = False
    winner = None
    hovered_move = None
    result_recorded = False
    replay_index = None
    paused = False 

    # Log (replay/tabs)
    log_active_tab = "moves"   # Moves or Captured
    move_log_offset = 0        # index of first move currently displayed in log
    log_box_rect_current = None  # rect of the log box for handling mouse scroll
    log_follow_latest = True
    loss_badge_anim_start = None
    loss_badge_side = None
    slash_image = None
    slash_anim_start = None
    slash_anim_side = None
    slash_anim_pos = None
    switch_anim_start = None
    switch_angle_from = 0 if board.red_on_bottom else SWITCH_ROTATION_STEP
    switch_angle_to = switch_angle_from
    switch_cooldown_until = 0

    state = "menu"
    mode = None
    ai_level_index = 1
    ai_match_started = False
    pvp_match_started = False
    settings_return_state = "menu"
    settings_page = "main"
    settings_category = "general"

    timer_option_index = len(TIMER_CHOICES) - 1  # default unlimited
    time_remaining = {
        Side.RED: TIMER_CHOICES[timer_option_index]["seconds"],
        Side.BLACK: TIMER_CHOICES[timer_option_index]["seconds"],
    }
    timer_rects_current = {}
    timer_modal_open = False
    timer_thumbnail_cache = {}
    BACKGROUND_DIR = os.path.join(ASSETS_DIR, "bg")
    background_modal_open = False
    background_image_cache = {}
    background_scaled_cache = {}
    background_thumb_cache = {}
    MENU_BACKGROUND_PATH = os.path.join(ASSETS_DIR, "menu", "main_menu.jpg")
    menu_background_image_cache = {}
    menu_background_scaled_cache = {}
    MENU_CORNER_RADIUS = 18
    # Pause menu image (animated uncrop)
    PAUSE_MENU_PATH = os.path.join(ASSETS_DIR, "menu", "pause_menu.png")
    pause_menu_image_cache = {}
    pause_menu_scaled_cache = {}
    # animation state
    pause_anim_start = None
    PAUSE_ANIM_DURATION = 0.25
    PAUSE_ANIM_INITIAL_CROP_BOTTOM = 66
    PAUSE_MENU_FADE = 0.4
    PAUSE_BUTTON_FADE = 1.5
    # Pause menu title (displayed above buttons)
    PAUSE_MENU_TITLE_PATH = os.path.join(ASSETS_DIR, "menu", "pause_menu_title.png")
    pause_menu_title_image_cache = {}
    pause_menu_title_scaled_cache = {}
    # Side panel backgrounds
    SIDE_PANEL_DIR = os.path.join(ASSETS_DIR, "menu", "sidemenu")
    SIDE_PANEL_IMAGE_CACHE = {}
    SIDE_PANEL_SCALED_CACHE = {}
    SIDE_PANEL_THUMB_CACHE = {}
    side_panel_modal_open = False

    # Flags assets
    FLAGS_DIR = os.path.join(ASSETS_DIR, "menu", "flags")
    FLAG_CACHE = {}
    LANG_FLAG_FILES = {
        "vi": "vietnam.jpg",
        "en": "usuk.jpg",
        "ja": "japan.jpg",
        "hk": "hongkong.jpg",
        "tw": "taiwan.jpg",
        "ko": "korea.jpg",
    }

    def load_flag_for_language(lang_code: str, size):
        """Load and cache a flag image for a language code scaled to `size`.
        `size` is a (w, h) tuple. Returns a pygame.Surface or None."""
        try:
            key = _normalize_lang(lang_code)
        except Exception:
            key = (lang_code or "").lower()
        fname = LANG_FLAG_FILES.get(key)
        if not fname:
            return None
        cache_key = (fname, size)
        if cache_key in FLAG_CACHE:
            return FLAG_CACHE[cache_key]
        full_path = os.path.join(FLAGS_DIR, fname)
        surf = None
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path)
                img = img.convert_alpha() if img.get_alpha() is not None else img.convert()
                surf = pygame.transform.smoothscale(img, size)
            except Exception:
                surf = None
        FLAG_CACHE[cache_key] = surf
        return surf

    panel_x = MARGIN_X + BOARD_COLS * CELL_SIZE + 20
    board_right = MARGIN_X + (BOARD_COLS - 1) * CELL_SIZE
    board_top = MARGIN_Y + BOARD_OFFSET_Y

    PANEL_MIN_LOG_TOP = MARGIN_Y + 160
    LOG_BOX_WIDTH = 321
    LOG_BOX_HEIGHT = 260
    START_BUTTON_HEIGHT = 48
    START_BUTTON_WIDTH = LOG_BOX_WIDTH
    START_BUTTON_OFFSET_X = 30  # nudge to the right of center
    SWITCH_BUTTON_SIZE = 44
    SWITCH_BUTTON_SPACING = 12
    SWITCH_ROTATION_STEP = 180
    SWITCH_ROTATION_DURATION = 0.5

    # Panel width used by side-panel buttons
    PANEL_WIDTH = LOG_BOX_WIDTH
    RESIGN_BUTTON_GAP = 20

    switch_image_path = os.path.join(ASSETS_DIR, "components", "switch.png")
    switch_image = None
    try:
        switch_image = pygame.image.load(switch_image_path).convert_alpha()
    except Exception:
        switch_image = None

    start_button_style = {
        "variant": "gradient",
        "colors_enabled": ((150, 255, 150), (0, 190, 0)),
        "colors_disabled": ((180, 180, 180), (130, 130, 130)),
        "border_radius": 14,
        "border_color": (0, 110, 0),
        "text_color_enabled": (255, 255, 255),
        "text_color_disabled": (235, 235, 235),
        "gloss": True,
        "gloss_color": (255, 255, 255, 70),
        "shadow": True,
        "shadow_color": (0, 0, 0, 90),
        "shadow_offset": (0, 4),
        "bold": True,
    }
    resign_button_style = {
        "variant": "gradient",
        "colors_enabled": ((255, 150, 150), (200, 0, 0)),
        "colors_disabled": ((200, 170, 170), (150, 80, 80)),
        "border_radius": 10,
        "border_color": (140, 0, 0),
        "text_color_enabled": (255, 255, 255),
        "text_color_disabled": (235, 235, 235),
        "gloss": True,
        "gloss_color": (255, 255, 255, 70),
        "bold": True,
    }
    new_game_button_style = {
        "variant": "gradient",
        "colors_enabled": ((160, 210, 255), (0, 90, 200)),
        "colors_disabled": ((180, 190, 210), (80, 110, 150)),
        "border_radius": 10,
        "border_color": (0, 70, 140),
        "text_color_enabled": (255, 255, 255),
        "text_color_disabled": (235, 235, 235),
        "gloss": True,
        "gloss_color": (255, 255, 255, 70),
        "bold": True,
    }
    switch_button_style = {
        "variant": "image_circle",
        "image_surface": switch_image,
        "bg_enabled": (245, 245, 245),
        "bg_disabled": (190, 190, 190),
        "border_color": (40, 40, 40),
        "image_inset": 6,
        "disabled_alpha": 150,
    }
    # Takeback button style (golden)
    takeback_button_style = {
        "variant": "gradient",
        "colors_enabled": ((255, 255, 90), (200, 140, 0)),
        "colors_disabled": ((200, 180, 140), (150, 120, 80)),
        "border_radius": 10,
        "border_color": (120, 80, 0),
        "text_color_enabled": (0, 0, 0),
        "text_color_disabled": (60, 60, 60),
        "gloss": True,
        "gloss_color": (255, 255, 255, 70),
    }
    # Tab button style (black with white text)
    tab_button_style = {
        "variant": "gradient",
        "colors_enabled": ((40, 40, 40), (0, 0, 0)),
        "colors_disabled": ((100, 100, 100), (80, 80, 80)),
        "border_radius": 8,
        "border_color": (20, 20, 20),
        "text_color_enabled": (255, 255, 255),
        "text_color_disabled": (200, 200, 200),
        "bold": True,
    }
    # AI change button style (white bg, red text)
    ai_change_button_style = {
        "variant": "gradient",
        "colors_enabled": ((255, 255, 255), (240, 240, 240)),
        "colors_disabled": ((230, 230, 230), (200, 200, 200)),
        "border_radius": 10,
        "border_color": (160, 40, 40),
        "text_color_enabled": (200, 30, 30),
        "text_color_disabled": (150, 150, 150),
        "bold": True,
    }

    btn_in_game_settings = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 153, PANEL_WIDTH, 30))
    btn_takeback = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 120, PANEL_WIDTH, 30))
    # Split the bottom row into two buttons (Resign / New game) that expand to fill the panel
    half_w = (PANEL_WIDTH - RESIGN_BUTTON_GAP) // 2
    btn_resign = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 80, half_w, 30), style=resign_button_style)
    btn_new_game = Button(pygame.Rect(panel_x + half_w + RESIGN_BUTTON_GAP, WINDOW_HEIGHT - 80, PANEL_WIDTH - half_w - RESIGN_BUTTON_GAP, 30), style=new_game_button_style)
    btn_ai_level = Button(pygame.Rect(panel_x + 30, MARGIN_Y + 95, 160, 28))
    btn_start_match = Button(
        pygame.Rect(panel_x, MARGIN_Y - START_BUTTON_HEIGHT - 20, START_BUTTON_WIDTH, START_BUTTON_HEIGHT),
        style=start_button_style,
    )
    btn_replay_prev = Button(pygame.Rect(panel_x, MARGIN_Y + 140, 40, 28))       # "<"
    btn_replay_next = Button(pygame.Rect(panel_x + 50, MARGIN_Y + 140, 40, 28))  # ">"
    btn_change_side = Button(
        pygame.Rect(panel_x - SWITCH_BUTTON_SIZE - SWITCH_BUTTON_SPACING, MARGIN_Y - SWITCH_BUTTON_SIZE - 12, SWITCH_BUTTON_SIZE, SWITCH_BUTTON_SIZE),
        label="",
        style=switch_button_style,
    )

    center_x = WINDOW_WIDTH // 2
    start_y = WINDOW_HEIGHT // 2 - 140
    menu_gap = 52
    btn_menu_pvp = Button(pygame.Rect(center_x - 110, start_y, 220, 42))
    btn_menu_ai = Button(pygame.Rect(center_x - 110, start_y + menu_gap, 220, 42))
    btn_menu_stats = Button(pygame.Rect(center_x - 110, start_y + menu_gap * 2, 220, 42))
    btn_menu_settings = Button(pygame.Rect(center_x - 110, start_y + menu_gap * 3, 220, 42))
    btn_menu_credits = Button(pygame.Rect(center_x - 110, start_y + menu_gap * 4, 220, 42))
    btn_menu_exit = Button(pygame.Rect(center_x - 110, start_y + menu_gap * 5, 220, 42))
    btn_credits_back = Button(pygame.Rect(center_x - 100, WINDOW_HEIGHT - 110, 200, 40))

    btn_log_tab_moves = Button(pygame.Rect(panel_x, PANEL_MIN_LOG_TOP, 100, 24))
    btn_log_tab_captured = Button(pygame.Rect(panel_x + 110, PANEL_MIN_LOG_TOP, 100, 24))

    # Apply styles to takeback and log tab buttons
    btn_takeback.style = takeback_button_style
    btn_log_tab_moves.style = tab_button_style
    btn_log_tab_captured.style = tab_button_style
    btn_ai_level.style = ai_change_button_style
    # Make in-panel controls use bold labels
    try:
        btn_in_game_settings.style["bold"] = True
    except Exception:
        btn_in_game_settings.style = {"bold": True}
    try:
        btn_replay_prev.style["bold"] = True
    except Exception:
        btn_replay_prev.style = {"bold": True}
    try:
        btn_replay_next.style["bold"] = True
    except Exception:
        btn_replay_next.style = {"bold": True}


    # Pause modal
    pause_center_x = WINDOW_WIDTH // 2
    pause_start_y = WINDOW_HEIGHT // 2 - 70
    btn_pause_resume = Button(pygame.Rect(pause_center_x - 100, pause_start_y, 200, 40))
    btn_pause_settings = Button(pygame.Rect(pause_center_x - 100, pause_start_y + 55, 200, 40))
    btn_pause_player_stats = Button(pygame.Rect(pause_center_x - 100, pause_start_y + 110, 200, 40))
    btn_pause_to_menu = Button(pygame.Rect(pause_center_x - 100, pause_start_y + 165, 200, 40))

    settings_center_x = WINDOW_WIDTH // 2
    settings_open_dropdown = None
    btn_settings_back = Button(pygame.Rect(settings_center_x - 110, WINDOW_HEIGHT - 65, 220, 36))

    # Central list of buttons used for hover handling
    try:
        all_buttons = [
            btn_in_game_settings,
            btn_takeback,
            btn_resign,
            btn_new_game,
            btn_ai_level,
            btn_start_match,
            btn_replay_prev,
            btn_replay_next,
            btn_change_side,
            btn_menu_pvp,
            btn_menu_ai,
            btn_menu_stats,
            btn_menu_settings,
            btn_menu_credits,
            btn_menu_exit,
            btn_credits_back,
            btn_log_tab_moves,
            btn_log_tab_captured,
            btn_pause_resume,
            btn_pause_settings,
            btn_pause_player_stats,
            btn_pause_to_menu,
            btn_settings_back,
        ]
    except Exception:
        all_buttons = []

    def apply_display_mode():
        nonlocal window_surface, window_mode_size, window_flags
        if settings.display_mode == "fullscreen":
            window_flags = pygame.FULLSCREEN | pygame.DOUBLEBUF
            window_surface = pygame.display.set_mode((0, 0), window_flags)
        elif settings.display_mode == "window_fullscreen":
            info = pygame.display.Info()
            window_mode_size = (info.current_w, info.current_h)
            window_flags = pygame.NOFRAME | pygame.DOUBLEBUF
            window_surface = pygame.display.set_mode(window_mode_size, window_flags)
        else:
            window_flags = pygame.RESIZABLE | pygame.DOUBLEBUF
            window_mode_size = lock_size_to_ratio(*window_mode_size)
            window_surface = pygame.display.set_mode(window_mode_size, window_flags)
        recompute_render_scale()

    def build_settings_items():
        lang = settings.language

        def make_theme_options(entries):
            # Some theme/name entries only provide a subset of languages (eg. 'en'/'vi').
            # Use fallback to English or any available name when the requested language is missing.
            opts = []
            for idx, entry in enumerate(entries):
                names = entry.get("name", {})
                text = names.get(lang) or names.get("en") or (next(iter(names.values())) if names else "")
                opts.append({"value": idx, "text": text})
            return opts

        board_options = make_theme_options(BOARD_THEMES)
        background_options = make_theme_options(BACKGROUNDS)
        body_options = make_theme_options(PIECE_BODY_THEMES)
        symbol_options = make_theme_options(PIECE_SYMBOL_SETS)

        display_modes = [
            {"value": "window", "text": t(settings, "display_window")},
            {"value": "window_fullscreen", "text": t(settings, "display_window_fullscreen")},
            {"value": "fullscreen", "text": t(settings, "display_fullscreen")},
        ]
        ratio_options = [
            {"value": "fit", "text": t(settings, "ratio_fit")},
            {"value": "wide", "text": t(settings, "ratio_wide")},
        ]
        language_options = [
            {"value": "vi", "text": t(settings, "settings_option_vietnamese")},
            {"value": "en", "text": t(settings, "settings_option_english")},
            {"value": "ja", "text": t(settings, "settings_option_japanese")},
            {"value": "hk", "text": t(settings, "settings_option_cantonese")},
            {"value": "tw", "text": t(settings, "settings_option_chinese_traditional")},
            {"value": "ko", "text": t(settings, "settings_option_korean")},
        ]

        def current_label(options, value):
            for opt in options:
                if opt["value"] == value:
                    return opt["text"]
            return t(settings, "settings_option_not_available")

        items = {
            "board_theme": {
                "label": t(settings, "settings_label_board_theme"),
                "value": settings.board_theme_index % len(BOARD_THEMES) if BOARD_THEMES else 0,
                "options": board_options,
                "enabled": bool(board_options),
            },
            "background": {
                "label": t(settings, "settings_label_background"),
                "value": settings.background_index % len(BACKGROUNDS) if BACKGROUNDS else 0,
                "options": background_options,
                "enabled": bool(background_options),
                "kind": "modal",
            },
            "side_panel_background": {
                "label": t(settings, "settings_label_side_panel_background"),
                "value": settings.side_panel_background_index % len(SIDE_PANEL_BACKGROUNDS) if SIDE_PANEL_BACKGROUNDS else 0,
                "options": make_theme_options(SIDE_PANEL_BACKGROUNDS) if SIDE_PANEL_BACKGROUNDS else [],
                "enabled": bool(SIDE_PANEL_BACKGROUNDS),
                "kind": "modal",
            },
            "log_box_transparency": {
                "label": t(settings, "settings_label_log_transparency"),
                "value": settings.log_box_transparency,
                "options": [],
                "enabled": True,
                "kind": "slider",
                "selected_label": f"{int(settings.log_box_transparency / 255 * 100)}%",
            },
            "piece_body": {
                "label": t(settings, "settings_label_piece_body"),
                "value": settings.piece_body_theme_index % len(PIECE_BODY_THEMES) if PIECE_BODY_THEMES else 0,
                "options": body_options,
                "enabled": bool(body_options),
            },
            "piece_symbols": {
                "label": t(settings, "settings_label_piece_icons"),
                "value": settings.piece_symbol_set_index % len(PIECE_SYMBOL_SETS) if PIECE_SYMBOL_SETS else 0,
                "options": symbol_options,
                "enabled": bool(symbol_options),
            },
            "display_mode": {
                "label": t(settings, "settings_label_display_mode"),
                "value": settings.display_mode,
                "options": display_modes,
                "enabled": True,
            },
            "resolution": {
                "label": t(settings, "settings_label_resolution"),
                "value": settings.resolution_ratio,
                "options": ratio_options,
                "enabled": True,
            },
            "language": {
                "label": t(settings, "settings_label_language"),
                "value": settings.language,
                "options": language_options,
                "enabled": True,
            },
        }

        for key, item in items.items():
            if item.get("kind") == "slider":
                # keep selected_label already set for slider
                continue
            item["selected_label"] = current_label(item["options"], item["value"]) if item.get("options") else str(item.get("value"))

        return items

    def get_settings_panel_rect():
        return pygame.Rect(60, 80, WINDOW_WIDTH - 120, WINDOW_HEIGHT - 160)

    def settings_tab_entries():
        return [
            {"key": "general", "label": t(settings, "settings_section_general")},
            {"key": "gameplay", "label": t(settings, "settings_section_gameplay")},
            {"key": "appearance", "label": t(settings, "settings_section_appearance")},
            {"key": "display", "label": t(settings, "settings_section_display")},
            {"key": "audio", "label": t(settings, "settings_section_audio")},
        ]

    def build_settings_tabs(panel_rect):
        entries = settings_tab_entries()
        tab_width = 150
        tab_height = 34
        gap = 12
        total_w = len(entries) * tab_width + (len(entries) - 1) * gap
        start_x = panel_rect.centerx - total_w // 2
        y = panel_rect.top + 70
        tabs = []
        for i, entry in enumerate(entries):
            rect = pygame.Rect(start_x + i * (tab_width + gap), y, tab_width, tab_height)
            tabs.append({**entry, "rect": rect})
        content_top = y + tab_height + 24
        return {"tabs": tabs, "content_top": content_top}

    def build_settings_layout(category, content_top=150):
        items = build_settings_items()
        row_width = 520
        dropdown_width = 230
        start_x = (WINDOW_WIDTH - row_width) // 2
        row_height = 40
        gap_y = 8
        section_gap = 10
        headers = []
        rows = []
        options = []

        section_map = {
            "general": [("general", t(settings, "settings_section_general"), ["language"])],
            "gameplay": [("gameplay", t(settings, "settings_section_gameplay"), [])],
            "appearance": [
                ("appearance", t(settings, "settings_section_appearance"), ["side_panel_background", "log_box_transparency", "background", "board_theme", "piece_body", "piece_symbols"])
            ],
            "display": [("display", t(settings, "settings_section_display"), ["display_mode", "resolution"])],
            "audio": [("audio", t(settings, "settings_section_audio"), [])],
        }

        sections = section_map.get(category, section_map["general"])

        y = content_top
        for _, title, keys in sections:
            headers.append({"title": title, "pos": (start_x, y)})
            y += 28
            for key in keys:
                if key not in items:
                    continue
                item = items[key]
                kind = item.get("kind", "dropdown")
                row_rect = pygame.Rect(start_x, y, row_width, row_height)
                value_rect = pygame.Rect(row_rect.right - dropdown_width - 12, row_rect.y + 5, dropdown_width, row_rect.height - 10)
                rows.append(
                    {
                        "key": key,
                        "rect": row_rect,
                        "value_rect": value_rect,
                        "label": item["label"],
                        "value_text": item["selected_label"],
                        "enabled": item["enabled"],
                        "options": item["options"],
                        "value": item["value"],
                        "kind": kind,
                    }
                )

                if kind == "dropdown" and settings_open_dropdown == key and item["enabled"]:
                    option_height = 30
                    for idx, opt in enumerate(item["options"]):
                        opt_rect = pygame.Rect(
                            value_rect.x,
                            value_rect.bottom + 4 + idx * (option_height + 4),
                            value_rect.width,
                            option_height,
                        )
                        options.append(
                            {
                                "key": key,
                                "rect": opt_rect,
                                "value": opt["value"],
                                "text": opt["text"],
                                "selected": opt["value"] == item["value"],
                            }
                        )

                y += row_height + gap_y
            y += section_gap

        return {"headers": headers, "rows": rows, "options": options, "content_bottom": y}

    def apply_setting_selection(key, value):
        nonlocal window_surface, window_mode_size, window_flags, logical_width, target_ratio

        if key == "board_theme":
            settings.board_theme_index = int(value) % len(BOARD_THEMES)
        elif key == "background" and BACKGROUNDS:
            settings.background_index = int(value) % len(BACKGROUNDS)
        elif key == "piece_body" and PIECE_BODY_THEMES:
            settings.piece_body_theme_index = int(value) % len(PIECE_BODY_THEMES)
        elif key == "piece_symbols" and PIECE_SYMBOL_SETS:
            settings.piece_symbol_set_index = int(value) % len(PIECE_SYMBOL_SETS)
        elif key == "side_panel_background" and SIDE_PANEL_BACKGROUNDS:
            settings.side_panel_background_index = int(value) % len(SIDE_PANEL_BACKGROUNDS)
        elif key == "display_mode":
            settings.display_mode = value
            apply_display_mode()
        elif key == "resolution":
            settings.resolution_ratio = value
            target_ratio = ratio_value(settings.resolution_ratio)
            logical_width = compute_logical_width()
            window_mode_size = lock_size_to_ratio(*window_mode_size)
            if settings.display_mode == "window":
                window_surface = pygame.display.set_mode(window_mode_size, window_flags)
            refresh_render_targets()
        elif key == "language":
            # Normalize language codes when user changes language
            settings.language = _normalize_lang(value)

        save_settings(settings)

    def timer_seconds_for_index(idx: int):
        if not TIMER_CHOICES:
            return None
        idx = idx % len(TIMER_CHOICES)
        return TIMER_CHOICES[idx]["seconds"]

    def reset_timers_to_full():
        nonlocal time_remaining
        sec = timer_seconds_for_index(timer_option_index)
        time_remaining = {Side.RED: sec, Side.BLACK: sec}

    def current_match_started():
        if state == "ai":
            return ai_match_started
        if state == "pvp":
            return pvp_match_started
        if mode == "ai":
            return ai_match_started
        if mode == "pvp":
            return pvp_match_started
        return False

    def start_current_match():
        nonlocal ai_match_started, pvp_match_started
        if state == "ai":
            ai_match_started = True
        elif state == "pvp":
            pvp_match_started = True

    def can_change_side_now():
        if state not in ("pvp", "ai"):
            return False
        if game_over:
            return False
        if replay_index is not None:
            return False
        if move_history:
            return False
        if current_match_started():
            return False
        return True

    def format_time_value(seconds):
        if seconds is None:
            return "∞"
        if seconds < 0:
            seconds = 0
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes}:{secs:02d}"

    def timer_labels_dict():
        return {
            "red": format_time_value(time_remaining.get(Side.RED)),
            "black": format_time_value(time_remaining.get(Side.BLACK)),
        }

    def can_change_timer():
        if state not in ("pvp", "ai"):
            return False
        if game_over:
            return False
        if current_match_started():
            return False
        if state == "ai":
            return True
        return len(move_history) == 0

    def set_timer_option(idx: int):
        nonlocal timer_option_index
        timer_option_index = idx % len(TIMER_CHOICES)
        reset_timers_to_full()

    def cycle_timer_option():
        set_timer_option(timer_option_index + 1)

    def load_timer_thumbnail(asset_rel, size):
        key = (asset_rel, size)
        if key in timer_thumbnail_cache:
            return timer_thumbnail_cache[key]
        full_path = os.path.join(ASSETS_DIR, asset_rel)
        surf = None
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path)
                if img.get_alpha() is not None:
                    img = img.convert_alpha()
                else:
                    img = img.convert()
                surf = pygame.transform.smoothscale(img, size)
            except Exception:
                surf = None
        if surf is None:
            surf = pygame.Surface(size)
            surf.fill((80, 80, 80))
            pygame.draw.rect(surf, (30, 30, 30), surf.get_rect(), 2)
        timer_thumbnail_cache[key] = surf
        return surf

    def build_timer_modal_layout():
        modal_width = 520
        modal_height = 360
        modal_rect = pygame.Rect(0, 0, modal_width, modal_height)
        modal_rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

        padding = 20
        header_height = 90
        cols = 2
        card_w = (modal_width - (cols + 1) * padding) // cols
        card_h = 120
        options = []
        for idx, choice in enumerate(TIMER_CHOICES):
            row = idx // cols
            col = idx % cols
            x = modal_rect.x + padding + col * (card_w + padding)
            y = modal_rect.y + header_height + row * (card_h + padding)
            rect = pygame.Rect(x, y, card_w, card_h)
            thumb_rect = pygame.Rect(rect.x + 10, rect.y + 10, rect.width - 20, 70)
            options.append(
                {
                    "index": idx,
                    "choice": choice,
                    "rect": rect,
                    "thumb_rect": thumb_rect,
                }
            )

        close_rect = pygame.Rect(modal_rect.right - 78, modal_rect.top + 16, 60, 26)
        return {"modal_rect": modal_rect, "options": options, "close_rect": close_rect}

    def get_background_entry(idx=None):
        if not BACKGROUNDS:
            return None
        if idx is None:
            idx = settings.background_index
        idx = idx % len(BACKGROUNDS)
        return BACKGROUNDS[idx]

    def _cover_scale_image(img, target_size):
        tw, th = target_size
        if tw <= 0 or th <= 0:
            return None
        iw, ih = img.get_size()
        if iw <= 0 or ih <= 0:
            return None
        scale = max(tw / iw, th / ih)
        new_size = (max(1, int(round(iw * scale))), max(1, int(round(ih * scale))))
        scaled = pygame.transform.smoothscale(img, new_size)
        offset_x = max(0, (new_size[0] - tw) // 2)
        offset_y = max(0, (new_size[1] - th) // 2)
        rect = pygame.Rect(offset_x, offset_y, tw, th)
        return scaled.subsurface(rect).copy()

    def _apply_round_corners(surf, radius):
        if surf is None:
            return None
        w, h = surf.get_size()
        if w <= 0 or h <= 0:
            return surf
        rounded = surf.convert_alpha()
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        rounded.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return rounded

    def load_background_image(file_name):
        if not file_name:
            return None
        key = file_name
        if key in background_image_cache:
            return background_image_cache[key]
        full_path = os.path.join(BACKGROUND_DIR, file_name)
        img = None
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path)
                img = img.convert_alpha() if img.get_alpha() is not None else img.convert()
            except Exception:
                img = None
        background_image_cache[key] = img
        return img

    def load_background_surface(size):
        entry = get_background_entry()
        if entry is None:
            return None
        file_name = entry.get("file")
        if not file_name:
            return None
        key = (file_name, size)
        if key in background_scaled_cache:
            return background_scaled_cache[key]
        img = load_background_image(file_name)
        surf = _cover_scale_image(img, size) if img is not None else None
        background_scaled_cache[key] = surf
        return surf

    def load_background_thumbnail(idx, size):
        entry = get_background_entry(idx)
        if entry is None:
            return None
        file_name = entry.get("file")
        if not file_name:
            return None
        key = (file_name, size)
        if key in background_thumb_cache:
            return background_thumb_cache[key]
        img = load_background_image(file_name)
        thumb = _cover_scale_image(img, size) if img is not None else None
        if thumb is None:
            thumb = pygame.Surface(size)
            thumb.fill((70, 70, 70))
            pygame.draw.rect(thumb, (20, 20, 20), thumb.get_rect(), 2)
        background_thumb_cache[key] = thumb
        return thumb

    def load_menu_background_image():
        key = MENU_BACKGROUND_PATH
        if key in menu_background_image_cache:
            return menu_background_image_cache[key]
        img = None
        if os.path.exists(key):
            try:
                img = pygame.image.load(key)
                img = img.convert_alpha() if img.get_alpha() is not None else img.convert()
            except Exception:
                img = None
        menu_background_image_cache[key] = img
        return img

    def load_menu_background_surface(size):
        if size in menu_background_scaled_cache:
            return menu_background_scaled_cache[size]
        img = load_menu_background_image()
        surf = _cover_scale_image(img, size) if img is not None else None
        if surf is not None:
            surf = _apply_round_corners(surf, MENU_CORNER_RADIUS)
        menu_background_scaled_cache[size] = surf
        return surf

    def load_pause_menu_image():
        key = PAUSE_MENU_PATH
        if key in pause_menu_image_cache:
            return pause_menu_image_cache[key]
        img = None
        if os.path.exists(key):
            try:
                img = pygame.image.load(key)
                img = img.convert_alpha() if img.get_alpha() is not None else img.convert()
            except Exception:
                img = None
        pause_menu_image_cache[key] = img
        return img

    def load_pause_menu_surface(size):
        if size in pause_menu_scaled_cache:
            return pause_menu_scaled_cache[size]
        img = load_pause_menu_image()
        surf = pygame.transform.smoothscale(img, size) if img is not None else None
        pause_menu_scaled_cache[size] = surf
        return surf

    def load_pause_menu_title_image():
        key = PAUSE_MENU_TITLE_PATH
        if key in pause_menu_title_image_cache:
            return pause_menu_title_image_cache[key]
        img = None
        if os.path.exists(key):
            try:
                img = pygame.image.load(key)
                img = img.convert_alpha() if img.get_alpha() is not None else img.convert()
            except Exception:
                img = None
        pause_menu_title_image_cache[key] = img
        return img

    def load_pause_menu_title_surface(size=None):
        """Return a scaled title surface that is NOT cropped.
        If `size` is provided it will attempt to fit within that box preserving aspect ratio.
        Otherwise it returns the title at half its original size (no crop)."""
        key = size
        if key in pause_menu_title_scaled_cache:
            return pause_menu_title_scaled_cache[key]
        img = load_pause_menu_title_image()
        surf = None
        if img is not None:
            iw, ih = img.get_size()
            if size is None:
                # default: half the original image size
                new_w = max(1, iw // 2)
                new_h = max(1, ih // 2)
            else:
                tw, th = size
                if tw <= 0 or th <= 0:
                    new_w, new_h = max(1, iw // 2), max(1, ih // 2)
                else:
                    # fit the image into the target box without cropping
                    scale = min(tw / iw, th / ih)
                    new_w = max(1, int(round(iw * scale)))
                    new_h = max(1, int(round(ih * scale)))
            try:
                surf = pygame.transform.smoothscale(img, (new_w, new_h))
            except Exception:
                surf = img
        pause_menu_title_scaled_cache[key] = surf
        return surf

    def draw_menu_background(surface, dim_alpha=0):
        size = surface.get_size()
        bg = load_menu_background_surface(size)
        if bg is None:
            surface.fill((40, 40, 60))
        else:
            surface.blit(bg, (0, 0))
            if dim_alpha > 0:
                overlay = pygame.Surface(size, pygame.SRCALPHA)
                overlay.fill((0, 0, 0, dim_alpha))
                surface.blit(overlay, (0, 0))

    def background_label(idx=None):
        entry = get_background_entry(idx)
        if entry is None:
            return TEXT[settings.language]["settings_option_not_available"]
        name_map = entry.get("name", {})
        lang = settings.language
        return name_map.get(lang) or name_map.get("en") or entry.get("key", "Background")

    def draw_background_layer(surface, dim_alpha=90):
        size = surface.get_size()
        bg = load_background_surface(size)
        if bg is None:
            surface.fill((40, 40, 60))
        else:
            surface.blit(bg, (0, 0))
            if dim_alpha > 0:
                overlay = pygame.Surface(size, pygame.SRCALPHA)
                overlay.fill((0, 0, 0, dim_alpha))
                surface.blit(overlay, (0, 0))

    def set_background_index(idx):
        if not BACKGROUNDS:
            return
        settings.background_index = idx % len(BACKGROUNDS)
        save_settings(settings)

    def build_background_modal_layout():
        cols = max(1, min(3, len(BACKGROUNDS) if BACKGROUNDS else 1))
        padding = 20
        header_height = 90
        thumb_size = 120
        card_w = thumb_size + 28
        card_h = thumb_size + 70

        modal_width = padding + cols * (card_w + padding)
        modal_width = min(WINDOW_WIDTH - 40, max(400, modal_width))
        rows = max(1, (len(BACKGROUNDS) + cols - 1) // cols if BACKGROUNDS else 1)
        modal_height = header_height + rows * (card_h + padding) + padding
        modal_height = min(WINDOW_HEIGHT - 40, max(340, modal_height))

        modal_rect = pygame.Rect(0, 0, modal_width, modal_height)
        modal_rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

        options = []
        for idx, bg in enumerate(BACKGROUNDS):
            row = idx // cols
            col = idx % cols
            x = modal_rect.x + padding + col * (card_w + padding)
            y = modal_rect.y + header_height + row * (card_h + padding)
            rect = pygame.Rect(x, y, card_w, card_h)
            thumb_x = rect.x + (rect.width - thumb_size) // 2
            thumb_rect = pygame.Rect(thumb_x, rect.y + 12, thumb_size, thumb_size)
            options.append(
                {
                    "index": idx,
                    "rect": rect,
                    "thumb_rect": thumb_rect,
                }
            )

        close_rect = pygame.Rect(modal_rect.right - 78, modal_rect.top + 16, 60, 26)
        return {
            "modal_rect": modal_rect,
            "options": options,
            "close_rect": close_rect,
            "thumb_size": thumb_size,
        }

    # --- Side panel background helpers ---
    def get_side_panel_entry(idx=None):
        if not SIDE_PANEL_BACKGROUNDS:
            return None
        if idx is None:
            idx = settings.side_panel_background_index
        idx = idx % len(SIDE_PANEL_BACKGROUNDS)
        return SIDE_PANEL_BACKGROUNDS[idx]

    def load_side_panel_image(file_name):
        if not file_name:
            return None
        key = file_name
        if key in SIDE_PANEL_IMAGE_CACHE:
            return SIDE_PANEL_IMAGE_CACHE[key]
        full_path = os.path.join(SIDE_PANEL_DIR, file_name)
        img = None
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path)
                img = img.convert_alpha() if img.get_alpha() is not None else img.convert()
            except Exception:
                img = None
        SIDE_PANEL_IMAGE_CACHE[key] = img
        return img

    def load_side_panel_surface(size):
        entry = get_side_panel_entry()
        if entry is None:
            return None
        file_name = entry.get("file")
        if not file_name:
            return None
        key = (file_name, size)
        if key in SIDE_PANEL_SCALED_CACHE:
            return SIDE_PANEL_SCALED_CACHE[key]
        img = load_side_panel_image(file_name)
        surf = _cover_scale_image(img, size) if img is not None else None
        SIDE_PANEL_SCALED_CACHE[key] = surf
        return surf

    def load_side_panel_thumbnail(idx, size):
        entry = get_side_panel_entry(idx)
        if entry is None:
            return None
        file_name = entry.get("file")
        if not file_name:
            return None
        key = (file_name, size)
        if key in SIDE_PANEL_THUMB_CACHE:
            return SIDE_PANEL_THUMB_CACHE[key]
        img = load_side_panel_image(file_name)
        thumb = _cover_scale_image(img, size) if img is not None else None
        if thumb is None:
            thumb = pygame.Surface(size)
            thumb.fill((70, 70, 70))
            pygame.draw.rect(thumb, (20, 20, 20), thumb.get_rect(), 2)
        SIDE_PANEL_THUMB_CACHE[key] = thumb
        return thumb

    def side_panel_label(idx=None):
        entry = get_side_panel_entry(idx)
        if entry is None:
            return TEXT[settings.language]["settings_option_not_available"]
        name_map = entry.get("name", {})
        lang = settings.language
        return name_map.get(lang) or name_map.get("en") or entry.get("key", "Side Panel")

    def build_side_panel_modal_layout():
        cols = max(1, min(3, len(SIDE_PANEL_BACKGROUNDS) if SIDE_PANEL_BACKGROUNDS else 1))
        padding = 20
        header_height = 90
        thumb_size = 120
        card_w = thumb_size + 28
        card_h = thumb_size + 70

        modal_width = padding + cols * (card_w + padding)
        modal_width = min(WINDOW_WIDTH - 40, max(400, modal_width))
        rows = max(1, (len(SIDE_PANEL_BACKGROUNDS) + cols - 1) // cols if SIDE_PANEL_BACKGROUNDS else 1)
        modal_height = header_height + rows * (card_h + padding) + padding
        modal_height = min(WINDOW_HEIGHT - 40, max(340, modal_height))

        modal_rect = pygame.Rect(0, 0, modal_width, modal_height)
        modal_rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

        options = []
        for idx, bg in enumerate(SIDE_PANEL_BACKGROUNDS):
            row = idx // cols
            col = idx % cols
            x = modal_rect.x + padding + col * (card_w + padding)
            y = modal_rect.y + header_height + row * (card_h + padding)
            rect = pygame.Rect(x, y, card_w, card_h)
            thumb_x = rect.x + (rect.width - thumb_size) // 2
            thumb_rect = pygame.Rect(thumb_x, rect.y + 12, thumb_size, thumb_size)
            options.append(
                {
                    "index": idx,
                    "rect": rect,
                    "thumb_rect": thumb_rect,
                }
            )

        close_rect = pygame.Rect(modal_rect.right - 78, modal_rect.top + 16, 60, 26)
        return {
            "modal_rect": modal_rect,
            "options": options,
            "close_rect": close_rect,
            "thumb_size": thumb_size,
        }

    def to_game_coords(pos):
        if render_scale <= 0:
            return 0, 0, False
        lx = (pos[0] - render_offset[0]) / render_scale
        ly = (pos[1] - render_offset[1]) / render_scale
        logical_pad_x = (logical_width - base_width) / 2
        gx = lx - logical_pad_x
        inside = 0 <= gx <= base_width and 0 <= ly <= base_height
        return int(gx), int(ly), inside

    def reset_game(red_on_bottom=None):
        nonlocal current_side, selected, valid_moves, move_history, redo_stack, hovered_move
        nonlocal in_check_side, game_over, winner, result_recorded, replay_index, paused, ai_match_started, pvp_match_started, timer_modal_open, background_modal_open, side_panel_modal_open
        nonlocal slash_anim_start, slash_anim_side, slash_anim_pos, human_side, ai_side, log_follow_latest, loss_badge_anim_start, loss_badge_side
        nonlocal switch_anim_start, switch_cooldown_until, switch_angle_from, switch_angle_to
        if red_on_bottom is None:
            red_on_bottom = board.red_on_bottom
        board.reset(red_on_bottom=red_on_bottom)
        human_side = Side.RED if board.red_on_bottom else Side.BLACK
        ai_side = Side.BLACK if board.red_on_bottom else Side.RED
        current_side = Side.RED
        selected = None
        valid_moves = []
        move_history = []
        redo_stack = []
        in_check_side = None
        game_over = False
        winner = None
        hovered_move = None
        result_recorded = False
        replay_index = None
        paused = False
        ai_match_started = False
        pvp_match_started = False
        timer_modal_open = False
        background_modal_open = False
        side_panel_modal_open = False
        loss_badge_anim_start = None
        loss_badge_side = None
        slash_anim_start = None
        slash_anim_side = None
        slash_anim_pos = None
        log_follow_latest = True
        switch_anim_start = None
        switch_cooldown_until = 0
        base_switch_angle = 0 if board.red_on_bottom else SWITCH_ROTATION_STEP
        switch_angle_from = base_switch_angle
        switch_angle_to = base_switch_angle
        reset_timers_to_full()

    def change_side_by_swapping_pieces():
        nonlocal move_log_offset
        if state not in ("pvp", "ai"):
            return
        move_log_offset = 0
        if state == "pvp":
            last_sel = profiles_data.setdefault("last_selected", {}).setdefault("pvp", {})
            red_id = last_sel.get("red_player_id", "p1")
            black_id = last_sel.get("black_player_id", "p2")
            last_sel["red_player_id"], last_sel["black_player_id"] = black_id, red_id
            save_profiles(profiles_data)
        reset_game(red_on_bottom=not board.red_on_bottom)

    def update_hover_preview(mx, my, inside):
        nonlocal hovered_move
        # Update button hovered states regardless of game state so menus
        # and pause panels receive hover feedback.
        try:
            for b in all_buttons:
                try:
                    b.hovered = b.rect.collidepoint(mx, my) if inside else False
                except Exception:
                    pass
        except Exception:
            pass

        if not inside:
            hovered_move = None
            return

        # Hover preview for piece moves only active during gameplay when
        # not paused and not game over.
        if state not in ("pvp", "ai") or paused or game_over:
            hovered_move = None
            return

        if selected is None or not valid_moves:
            hovered_move = None
            return
        col, row = screen_to_board(mx, my)
        if col is None:
            hovered_move = None
            return
        hovered_move = (col, row) if (col, row) in valid_moves else None

    def register_result_if_needed(winner_side, is_draw=False):
        nonlocal result_recorded, human_side
        if result_recorded:
            return
        if mode not in ("pvp", "ai"):
            return
        apply_game_result_to_profiles(profiles_data, mode, winner_side, is_draw, ai_level_index, human_side)
        result_recorded = True

    def load_slash_image():
        nonlocal slash_image
        if slash_image is not None:
            return slash_image
        path = os.path.join(ASSETS_DIR, "pieces", "movement", "slash.png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path)
                img = img.convert_alpha() if img.get_alpha() is not None else img.convert()
                max_w = int(CELL_SIZE * 1.4)
                max_h = int(CELL_SIZE * 1.8)
                iw, ih = img.get_size()
                base_scale = min(1.0, max_w / max(1, iw), max_h / max(1, ih))
                scale = base_scale * 1.2 
                if scale < 1.0:
                    new_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
                    img = pygame.transform.smoothscale(img, new_size)
                slash_image = img
            except Exception:
                slash_image = None
        return slash_image

    def start_slash_animation(loser_side, last_move=None):
        nonlocal slash_anim_start, slash_anim_side, slash_anim_pos
        if loser_side not in (Side.RED, Side.BLACK):
            return
        pos = board.find_general(loser_side)
        if pos is None and last_move is not None:
            captured = getattr(last_move, "captured", None)
            if captured is not None and captured.ptype == PieceType.GENERAL and captured.side == loser_side:
                pos = last_move.to_pos
        if pos is None:
            return
        slash_anim_side = loser_side
        slash_anim_start = pygame.time.get_ticks()
        slash_anim_pos = pos

    def slash_progress_for(loser_side):
        if loser_side not in (Side.RED, Side.BLACK):
            return 0.0
        if slash_anim_start is None or slash_anim_side != loser_side:
            return 0.0
        elapsed = (pygame.time.get_ticks() - slash_anim_start) / 1000.0
        duration = 0.25
        if elapsed <= 0:
            return 0.0
        if elapsed >= duration:
            return 1.0
        return min(1.0, elapsed / duration)

    def start_loss_badge_animation(loser_side, last_move=None):
        nonlocal loss_badge_anim_start, loss_badge_side
        if loser_side not in (Side.RED, Side.BLACK):
            return
        loss_badge_side = loser_side
        loss_badge_anim_start = pygame.time.get_ticks()
        start_slash_animation(loser_side, last_move)

    def loss_badge_scale_for(loser_side):
        if loser_side not in (Side.RED, Side.BLACK):
            return 1.0
        if loss_badge_anim_start is None or loss_badge_side != loser_side:
            return 1.0
        elapsed = (pygame.time.get_ticks() - loss_badge_anim_start) / 1000.0
        duration = 0.3
        start_scale = 9
        if elapsed <= 0:
            return start_scale
        if elapsed >= duration:
            return 1.0
        progress = min(1.0, elapsed / duration)
        falloff = (1.0 - progress) * (1.0 - progress)
        return 1.0 + (start_scale - 1.0) * falloff

    def avatar_shake_dx(side):
        if side not in (Side.RED, Side.BLACK):
            return 0
        if loss_badge_anim_start is None or loss_badge_side != side:
            return 0
        elapsed = (pygame.time.get_ticks() - loss_badge_anim_start) / 1000.0
        duration = 0.3
        if elapsed < 0 or elapsed > duration:
            return 0
        progress = elapsed / duration
        amplitude = 8 * (1.0 - progress)
        shakes = 10
        return int(round(math.sin(progress * shakes * math.pi) * amplitude))

    def switch_rotation_angle():
        nonlocal switch_anim_start, switch_angle_from, switch_angle_to
        if switch_anim_start is None:
            return switch_angle_to
        elapsed = (pygame.time.get_ticks() - switch_anim_start) / 1000.0
        duration = SWITCH_ROTATION_DURATION
        if elapsed <= 0:
            return switch_angle_from
        if elapsed >= duration:
            switch_anim_start = None
            switch_angle_from = switch_angle_to % 360
            switch_angle_to = switch_angle_from
            return switch_angle_to
        progress = min(1.0, elapsed / duration)
        return switch_angle_from + (switch_angle_to - switch_angle_from) * progress

    def clamp_replay_index():
        nonlocal replay_index
        if replay_index is None:
            return
        if replay_index < 0:
            replay_index = 0
        elif replay_index > len(move_history):
            replay_index = len(move_history)

    def rebuild_position_from_replay_index():
        nonlocal current_side, in_check_side, replay_index
        if replay_index is None:
            return

        clamp_replay_index()

        board.reset(red_on_bottom=board.red_on_bottom)
        current_side = Side.RED
        in_check_side = None

        for i in range(replay_index):
            mv = move_history[i]
            board.move_piece(mv)
            current_side = Side.BLACK if current_side == Side.RED else Side.RED

        if board.is_in_check(current_side):
            in_check_side = current_side
        else:
            in_check_side = None


    def update_game_state_after_side_change():
        nonlocal in_check_side, game_over, winner, result_recorded, replay_index
        if board.is_in_check(current_side):
            in_check_side = current_side
            if not board.has_any_legal_move(current_side):
                if not game_over:
                    game_over = True
                    winner_side = Side.RED if current_side == Side.BLACK else Side.BLACK
                    winner = winner_side
                    start_loss_badge_animation(current_side, last_move=move_history[-1] if move_history else None)
                    register_result_if_needed(winner_side, False)
                    replay_index = len(move_history)
            else:
                in_check_side = None
                if not result_recorded:
                    game_over = False
                    winner = None

    def switch_to_menu():
        nonlocal state, selected, valid_moves, in_check_side, game_over, winner, result_recorded, ai_match_started, pvp_match_started, hovered_move, background_modal_open, side_panel_modal_open
        state = "menu"
        selected = None
        valid_moves = []
        hovered_move = None
        in_check_side = None
        game_over = False
        winner = None
        result_recorded = False
        ai_match_started = False
        pvp_match_started = False
        background_modal_open = False
        side_panel_modal_open = False

    def timers_are_running():
        if state not in ("pvp", "ai"):
            return False
        if paused or game_over:
            return False
        if timer_modal_open:
            return False
        if replay_index is not None:
            return False
        if state == "ai":
            return ai_match_started
        if state == "pvp":
            return pvp_match_started and len(move_history) > 0
        return False

    def handle_timeout(side: Side):
        nonlocal game_over, winner, selected, valid_moves, in_check_side, replay_index, hovered_move
        if game_over:
            return
        game_over = True
        winner_side = Side.BLACK if side == Side.RED else Side.RED
        winner = winner_side
        in_check_side = None
        selected = None
        valid_moves = []
        hovered_move = None
        start_loss_badge_animation(side, last_move=move_history[-1] if move_history else None)
        register_result_if_needed(winner_side, False)
        replay_index = len(move_history)

    def ai_make_move():
        nonlocal current_side, move_history, redo_stack, game_over, winner
        nonlocal in_check_side, selected, valid_moves, hovered_move
        nonlocal log_follow_latest, human_side, ai_side
        if game_over or current_side != ai_side or not ai_match_started:
            return
        level_cfg = AI_LEVELS[ai_level_index]
        mv = choose_ai_move(board, level_cfg, ai_side)
        if mv is None:
            if board.is_in_check(ai_side):
                game_over = True
                winner = human_side
                start_loss_badge_animation(ai_side, last_move=move_history[-1] if move_history else None)
                register_result_if_needed(human_side, False)
                replay_index = len(move_history)
            else:
                game_over = True
                winner = None
                register_result_if_needed(None, True)
                replay_index = len(move_history)
            in_check_side = None
            return

        move_piece_with_animation(mv)
        move_history.append(mv)
        redo_stack.clear()
        log_follow_latest = True
        selected = None
        valid_moves = []
        hovered_move = None

        current_side = human_side
        update_game_state_after_side_change()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # ESC key logic
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Close any open modal first. If none are open, handle
                    # state transitions (credits/settings) or toggle pause in
                    # gameplay states.
                    if timer_modal_open:
                        timer_modal_open = False
                    elif background_modal_open:
                        background_modal_open = False
                    elif side_panel_modal_open:
                        side_panel_modal_open = False
                    else:
                        if state == "credits":
                            state = "menu"
                        elif state == "settings":
                            settings_open_dropdown = None
                            if settings_page == "stats":
                                if settings_return_state:
                                    state = settings_return_state
                                settings_page = "main"
                            else:
                                state = settings_return_state
                        elif state in ("pvp", "ai"):
                            paused = not paused
            elif event.type == pygame.VIDEORESIZE and settings.display_mode == "window":
                # Avoid recreating the window surface on every resize step to reduce flicker.
                window_mode_size = (event.w, event.h)
                window_surface = pygame.display.get_surface()
                recompute_render_scale()
            elif event.type == pygame.MOUSEMOTION:
                mx, my, inside_game = to_game_coords(event.pos)
                update_hover_preview(mx, my, inside_game)
            # Choose avatar logic
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my, inside_game = to_game_coords(event.pos)
                btn = event.button

                if side_panel_modal_open:
                    layout = build_side_panel_modal_layout()
                    if btn == 1:
                        if not layout["modal_rect"].collidepoint(mx, my):
                            side_panel_modal_open = False
                            continue
                        if layout["close_rect"].collidepoint(mx, my):
                            side_panel_modal_open = False
                            continue
                        clicked_idx = None
                        for opt in layout["options"]:
                            if opt["rect"].collidepoint(mx, my) or opt["thumb_rect"].collidepoint(mx, my):
                                clicked_idx = opt["index"]
                                break
                        if clicked_idx is not None:
                            settings.side_panel_background_index = clicked_idx % len(SIDE_PANEL_BACKGROUNDS)
                            save_settings(settings)
                            side_panel_modal_open = False
                            continue
                        continue
                    else:
                        continue

                if background_modal_open:
                    layout = build_background_modal_layout()
                    if btn == 1:
                        if not layout["modal_rect"].collidepoint(mx, my):
                            background_modal_open = False
                            continue
                        if layout["close_rect"].collidepoint(mx, my):
                            background_modal_open = False
                            continue
                        clicked_background = None
                        for opt in layout["options"]:
                            if opt["rect"].collidepoint(mx, my) or opt["thumb_rect"].collidepoint(mx, my):
                                clicked_background = opt["index"]
                                break
                        if clicked_background is not None:
                            set_background_index(clicked_background)
                            background_modal_open = False
                            continue
                        continue
                    else:
                        continue

                if timer_modal_open:
                    layout = build_timer_modal_layout()
                    if not can_change_timer():
                        timer_modal_open = False
                        continue
                    if btn == 1:
                        if not layout["modal_rect"].collidepoint(mx, my):
                            timer_modal_open = False
                            continue
                        if layout["close_rect"].collidepoint(mx, my):
                            timer_modal_open = False
                            continue
                        clicked_option = None
                        for opt in layout["options"]:
                            if opt["rect"].collidepoint(mx, my) or opt["thumb_rect"].collidepoint(mx, my):
                                clicked_option = opt["index"]
                                break
                        if clicked_option is not None:
                            set_timer_option(clicked_option)
                            timer_modal_open = False
                            continue
                        continue
                    else:
                        continue

                if not inside_game:
                    continue

                # Scroll log with wheel: moves or captured tab
                if btn in (4, 5) and state in ("pvp", "ai") and log_box_rect_current is not None:
                    if log_box_rect_current.collidepoint(mx, my):
                        # moves tab scroll
                        if log_active_tab == "moves":
                            try:
                                vi = replay_index if replay_index is not None else len(move_history)
                            except NameError:
                                vi = len(move_history)

                            box_lines = max(1, log_box_rect_current.height // 20)
                            max_offset = max(0, vi - box_lines)

                            if btn == 4:  # scroll up
                                log_follow_latest = False
                                move_log_offset = max(0, move_log_offset - 1)
                            elif btn == 5:  # scroll down
                                log_follow_latest = False
                                move_log_offset = min(max_offset, move_log_offset + 1)

                        # do not scroll captured tab; icons will be auto-scaled to fit
                    continue

                if state in ("pvp", "ai"):
                    bottom_rect = get_bottom_avatar_rect()
                    top_rect = get_top_avatar_rect()
                    clicked_avatar = False

                    # If avatar overlay is open, check clicks on the overlay buttons first
                    if avatar_buttons_open and btn == 1:
                        # check upload
                        ur = avatar_button_rects.get("upload")
                        dr = avatar_button_rects.get("delete")
                        if ur and ur.collidepoint(mx, my):
                            # choose and process file
                            filename = select_avatar_file_dialog()
                            if filename:
                                saved = process_and_save_avatar(filename)
                                if saved:
                                    # determine player object for current overlay side
                                    if avatar_buttons_side == "bottom":
                                        if mode == "pvp":
                                            red_id = profiles_data.get("last_selected", {}).get("pvp", {}).get("red_player_id", "p1")
                                            player = find_player(profiles_data, red_id)
                                        else:
                                            human_id = profiles_data.get("last_selected", {}).get("ai", {}).get("human_player_id", "p1")
                                            player = find_player(profiles_data, human_id)
                                    else:
                                        # top
                                        black_id = profiles_data.get("last_selected", {}).get("pvp", {}).get("black_player_id", "p2")
                                        player = find_player(profiles_data, black_id)
                                    if player is not None:
                                        avatar = player.setdefault("avatar", {})
                                        avatar["type"] = "image"
                                        avatar["path"] = saved
                                        save_profiles(profiles_data)
                            avatar_buttons_open = False
                            avatar_buttons_side = None
                            avatar_button_rects = {}
                            continue
                        if dr and dr.collidepoint(mx, my):
                            # delete avatar for the overlay side
                            if avatar_buttons_side == "bottom":
                                if mode == "pvp":
                                    red_id = profiles_data.get("last_selected", {}).get("pvp", {}).get("red_player_id", "p1")
                                    player = find_player(profiles_data, red_id)
                                else:
                                    human_id = profiles_data.get("last_selected", {}).get("ai", {}).get("human_player_id", "p1")
                                    player = find_player(profiles_data, human_id)
                            else:
                                player = find_player(profiles_data, profiles_data.get("last_selected", {}).get("pvp", {}).get("black_player_id", "p2"))
                            if player is not None:
                                avatar = player.get("avatar", {})
                                path = avatar.get("path")
                                if path:
                                    try:
                                        delete_avatar_file(path)
                                    except Exception:
                                        pass
                                # reset avatar
                                player["avatar"] = {}
                                save_profiles(profiles_data)
                            avatar_buttons_open = False
                            avatar_buttons_side = None
                            avatar_button_rects = {}
                            continue
                
                    if bottom_rect.collidepoint(mx, my):
                        clicked_avatar = True
                        if mode == "pvp":
                            red_id = profiles_data.get("last_selected", {}).get("pvp", {}).get("red_player_id", "p1")
                            player = find_player(profiles_data, red_id)
                        else:
                            human_id = profiles_data.get("last_selected", {}).get("ai", {}).get("human_player_id", "p1")
                            player = find_player(profiles_data, human_id)

                        if player is not None:
                            avatar = player.setdefault("avatar", {})
                            if btn == 1:
                                # Open avatar action overlay for this avatar (upload / delete)
                                avatar_buttons_open = True
                                avatar_buttons_side = "bottom"
                                # compute button positions around avatar
                                ar = get_bottom_avatar_rect()
                                dx = avatar_shake_dx(Side.RED) if 'avatar_shake_dx' in globals() else 0
                                ar = ar.move(dx, 0)
                                btn_size = max(20, int(AVATAR_BOARD_SIZE * 0.4))
                                gap = 6
                                # For bottom player, place both buttons to the LEFT of avatar
                                upload_rect = pygame.Rect(0, 0, btn_size, btn_size)
                                delete_rect = pygame.Rect(0, 0, btn_size, btn_size)
                                left_x = ar.left - gap - btn_size // 2
                                upload_rect.center = (left_x, ar.centery - btn_size // 2 - gap)
                                delete_rect.center = (left_x, ar.centery + btn_size // 2 + gap)
                                avatar_button_rects = {"upload": upload_rect, "delete": delete_rect}
                            elif btn == 3:
                                filename = select_avatar_file_dialog()
                                if filename:
                                    avatar["type"] = "image"
                                    avatar["path"] = filename
                                    save_profiles(profiles_data)
                            elif btn == 3:
                                filename = select_avatar_file_dialog()
                                if filename:
                                    avatar["type"] = "image"
                                    avatar["path"] = filename
                                    save_profiles(profiles_data)

                    elif top_rect.collidepoint(mx, my) and mode == "pvp":
                        clicked_avatar = True
                        black_id = profiles_data.get("last_selected", {}).get("pvp", {}).get("black_player_id", "p2")
                        player = find_player(profiles_data, black_id)
                        if player is not None:
                            avatar = player.setdefault("avatar", {})
                            if btn == 1:
                                avatar_buttons_open = True
                                avatar_buttons_side = "top"
                                ar = get_top_avatar_rect()
                                dx = avatar_shake_dx(Side.BLACK) if 'avatar_shake_dx' in globals() else 0
                                ar = ar.move(dx, 0)
                                btn_size = max(20, int(AVATAR_BOARD_SIZE * 0.4))
                                gap = 6
                                # For top player, place both buttons to the RIGHT of avatar
                                upload_rect = pygame.Rect(0, 0, btn_size, btn_size)
                                delete_rect = pygame.Rect(0, 0, btn_size, btn_size)
                                right_x = ar.right + gap + btn_size // 2
                                upload_rect.center = (right_x, ar.centery - btn_size // 2 - gap)
                                delete_rect.center = (right_x, ar.centery + btn_size // 2 + gap)
                                avatar_button_rects = {"upload": upload_rect, "delete": delete_rect}
                            elif btn == 3:
                                filename = select_avatar_file_dialog()
                                if filename:
                                    avatar["type"] = "image"
                                    avatar["path"] = filename
                                    save_profiles(profiles_data)

                    if clicked_avatar:
                        continue

                    if btn == 1 and timer_rects_current and can_change_timer():
                        if timer_rects_current.get("red", pygame.Rect(0, 0, 0, 0)).collidepoint(mx, my) or \
                           timer_rects_current.get("black", pygame.Rect(0, 0, 0, 0)).collidepoint(mx, my):
                            timer_modal_open = True
                            continue

                if btn != 1:
                    if btn == 3 and state in ("pvp", "ai") and selected is not None:
                        selected = None
                        valid_moves = []
                        hovered_move = None
                    continue

                lang = settings.language
                lang_text = TEXT[lang]

                if state == "menu":
                    if btn_menu_pvp.is_clicked((mx, my)):
                        reset_game()
                        mode = "pvp"
                        state = "pvp"
                        continue
                    if btn_menu_ai.is_clicked((mx, my)):
                        reset_game()
                        mode = "ai"
                        state = "ai"
                        continue
                    if btn_menu_settings.is_clicked((mx, my)):
                        settings_return_state = "menu"
                        settings_page = "main"
                        settings_open_dropdown = None
                        state = "settings"
                        continue
                    if btn_menu_stats.is_clicked((mx, my)):
                        settings_return_state = "menu"
                        settings_page = "stats"
                        settings_open_dropdown = None
                        state = "settings"
                        continue
                    if btn_menu_credits.is_clicked((mx, my)):
                        state = "credits"
                        continue
                    if btn_menu_exit.is_clicked((mx, my)):
                        running = False
                        continue

                elif state == "credits":
                    if btn_credits_back.is_clicked((mx, my)):
                        state = "menu"
                        continue

                elif state == "settings":
                    if settings_page == "main":
                        settings_panel_rect = get_settings_panel_rect()
                        tabs_layout = build_settings_tabs(settings_panel_rect)

                        tab_clicked = False
                        for tab in tabs_layout["tabs"]:
                            if tab["rect"].collidepoint(mx, my):
                                settings_category = tab["key"]
                                settings_open_dropdown = None
                                tab_clicked = True
                                break
                        if tab_clicked:
                            continue

                        layout = build_settings_layout(settings_category, content_top=tabs_layout["content_top"])

                        option_clicked = False
                        for opt in layout["options"]:
                            if opt["rect"].collidepoint(mx, my):
                                apply_setting_selection(opt["key"], opt["value"])
                                settings_open_dropdown = None
                                option_clicked = True
                                break
                        if option_clicked:
                            continue

                        if btn_settings_back.is_clicked((mx, my)):
                            state = settings_return_state
                            settings_page = "main"
                            settings_open_dropdown = None
                            continue

                        row_clicked = False
                        for row in layout["rows"]:
                            if not row["enabled"]:
                                continue
                            if row["rect"].collidepoint(mx, my) or row["value_rect"].collidepoint(mx, my):
                                # Special handling for slider-type row (log box transparency)
                                if row.get("kind") == "slider" and row.get("key") == "log_box_transparency":
                                    value_rect = row["value_rect"]
                                    slider_area = pygame.Rect(value_rect.x + 6, value_rect.y + 8, max(1, value_rect.width - 46), max(1, value_rect.height - 16))
                                    checkbox_rect = pygame.Rect(value_rect.right - 28, value_rect.centery - 8, 18, 18)
                                    # Click on checkbox toggles enabling
                                    if checkbox_rect.collidepoint(mx, my):
                                        settings.log_box_transparency_enabled = not settings.log_box_transparency_enabled
                                        save_settings(settings)
                                    else:
                                        # Click on slider area sets value (only if enabled)
                                        if settings.log_box_transparency_enabled and slider_area.collidepoint(mx, my):
                                            rel = (mx - slider_area.x) / float(max(1, slider_area.width))
                                            v = int(max(0, min(1.0, rel)) * 255)
                                            settings.log_box_transparency = v
                                            save_settings(settings)
                                    row_clicked = True
                                    break

                                if row.get("kind") == "modal":
                                    key = row.get("key")
                                    if key == "background":
                                        background_modal_open = True
                                    elif key == "side_panel_background":
                                        side_panel_modal_open = True
                                    settings_open_dropdown = None
                                else:
                                    settings_open_dropdown = None if settings_open_dropdown == row["key"] else row["key"]
                                row_clicked = True
                                break
                        if row_clicked:
                            continue

                        if settings_open_dropdown is not None:
                            settings_open_dropdown = None
                            continue
                    else:
                        if btn_settings_back.is_clicked((mx, my)):
                            if settings_return_state:
                                state = settings_return_state
                            settings_page = "main"
                            settings_open_dropdown = None
                            continue
                # In-game state         
                elif state in ("pvp", "ai"):
                    # Pause modal
                    if paused:
                        lang = settings.language
                        lang_text = TEXT[lang]

                        if btn_pause_resume.is_clicked((mx, my)):
                            paused = False
                            continue

                        if btn_pause_settings.is_clicked((mx, my)):
                            settings_return_state = state
                            settings_page = "main"
                            paused = False
                            settings_open_dropdown = None
                            state = "settings"
                            continue

                        if btn_pause_player_stats.is_clicked((mx, my)):
                            settings_return_state = state
                            settings_page = "stats"
                            settings_open_dropdown = None
                            paused = False
                            state = "settings"
                            continue

                        if btn_pause_to_menu.is_clicked((mx, my)):
                            reset_game()
                            switch_to_menu()
                            paused = False
                            continue
                        continue

                    match_started = current_match_started()
                    match_pending = not match_started

                    if btn_log_tab_moves.is_clicked((mx, my)):
                        log_active_tab = "moves"
                        continue
                    if btn_log_tab_captured.is_clicked((mx, my)):
                        log_active_tab = "captured"
                        continue
                    if btn_change_side.is_clicked((mx, my)) and can_change_side_now():
                        now_ms = pygame.time.get_ticks()
                        if now_ms >= switch_cooldown_until:
                            prev_angle = switch_rotation_angle()
                            change_side_by_swapping_pieces()
                            switch_angle_from = prev_angle
                            switch_angle_to = prev_angle + SWITCH_ROTATION_STEP
                            switch_anim_start = now_ms
                            switch_cooldown_until = now_ms + 700
                        continue

                    # Setting button clicked
                    if btn_in_game_settings.is_clicked((mx, my)):
                        settings_return_state = state
                        settings_page = "main"
                        settings_open_dropdown = None
                        state = "settings"
                        continue
                    # Replay
                    if game_over and move_history:
                        if btn_replay_prev.is_clicked((mx, my)):
                            if replay_index is None:
                                replay_index = len(move_history)
                            if replay_index > 0:
                                replay_index -= 1
                                rebuild_position_from_replay_index()
                            continue

                        if btn_replay_next.is_clicked((mx, my)):
                            if replay_index is None:
                                replay_index = len(move_history)
                            if replay_index < len(move_history):
                                replay_index += 1
                                rebuild_position_from_replay_index()
                            continue
                    # Start match
                    if match_pending and btn_start_match.is_clicked((mx, my)):
                        start_current_match()
                        continue
                    # AI level change
                    if state == "ai" and match_pending and btn_ai_level.is_clicked((mx, my)):
                        ai_level_index = (ai_level_index + 1) % len(AI_LEVELS)
                        continue
                    # Takeback clicked
                    if not game_over and btn_takeback.is_clicked((mx, my)):
                        if match_pending:
                            continue
                        if move_history:
                            steps = min(2, len(move_history))
                            for _ in range(steps):
                                last_move = move_history.pop()
                                board.undo_move(last_move)
                                redo_stack.append(last_move)
                                current_side = Side.RED if current_side == Side.BLACK else Side.BLACK
                                log_follow_latest = True
                            update_game_state_after_side_change()
                            clamp_replay_index()
                        continue
                    # Resign clicked
                    if btn_resign.is_clicked((mx, my)):
                        if match_pending:
                            continue
                        if not game_over:
                            game_over = True
                            winner_side = Side.RED if current_side == Side.BLACK else Side.BLACK
                            winner = winner_side
                            in_check_side = None
                            selected = None
                            valid_moves = []
                            start_loss_badge_animation(current_side, last_move=move_history[-1] if move_history else None)
                            register_result_if_needed(winner_side, False)
                            replay_index = len(move_history)
                        continue
                    # New game clicked
                    if btn_new_game.is_clicked((mx, my)):
                        reset_game()
                        continue

                    if match_pending:
                        continue

                    if game_over:
                        continue
                    
                    # AI move turn
                    if state == "ai" and current_side == ai_side:
                        continue

                    col, row = screen_to_board(mx, my)
                    if col is not None:
                        piece = board.get_piece(col, row)
                        if selected is None:
                            if piece is not None and piece.side == current_side:
                                selected = (col, row)
                                valid_moves = board.generate_legal_moves(col, row, current_side)
                            else:
                                selected = None
                                valid_moves = []
                            hovered_move = None
                        else:
                            sel_c, sel_r = selected
                            if col == sel_c and row == sel_r:
                                selected = None
                                valid_moves = []
                                hovered_move = None
                            else:
                                if piece is not None and piece.side == current_side:
                                    selected = (col, row)
                                    valid_moves = board.generate_legal_moves(col, row, current_side)
                                    update_hover_preview(mx, my, True)
                                else:
                                    if (col, row) in valid_moves:
                                        moving_piece = board.get_piece(sel_c, sel_r)
                                        captured = board.get_piece(col, row)
                                        mv = Move((sel_c, sel_r), (col, row), moving_piece, captured)
                                        board.move_piece(mv)
                                        move_history.append(mv)
                                        redo_stack.clear()
                                        log_follow_latest = True

                                        current_side = Side.BLACK if current_side == Side.RED else Side.RED
                                        update_game_state_after_side_change()
                                    selected = None
                                    valid_moves = []
                                    hovered_move = None

        if state == "ai" and ai_match_started and not game_over and not paused and current_side == ai_side:
            ai_make_move()

        if timers_are_running():
            current_remaining = time_remaining.get(current_side)
            if current_remaining is not None:
                current_remaining -= dt
                time_remaining[current_side] = current_remaining
                if current_remaining <= 0:
                    time_remaining[current_side] = 0
                    handle_timeout(current_side)

        lang = settings.language
        lang_text = TEXT[lang]

        if state == "menu":
            draw_background_layer(screen, dim_alpha=110)
        elif state == "credits":
            draw_background_layer(screen, dim_alpha=110)
        elif state in ("pvp", "ai"):
            draw_background_layer(screen, dim_alpha=130)
        elif state == "settings":
            draw_background_layer(screen, dim_alpha=110)
        else:
            screen.fill((40, 40, 60))

        # MENU SCREEN
        if state == "menu":
            band_height = menu_gap * 6 + 200
            band_rect = pygame.Rect(center_x - 230, start_y - 200, 460, band_height + 170)
            band_radius = MENU_CORNER_RADIUS
            band_image = load_menu_background_surface(band_rect.size)
            if band_image is not None:
                screen.blit(band_image, band_rect.topleft)
                overlay = pygame.Surface(band_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(overlay, (255, 255, 255, 80), overlay.get_rect(), border_radius=band_radius)
                screen.blit(overlay, band_rect.topleft)
            else:
                band_surface = pygame.Surface(band_rect.size, pygame.SRCALPHA)
                pygame.draw.rect(
                    band_surface,
                    (248, 244, 232, 190),
                    band_surface.get_rect(),
                    border_radius=band_radius,
                )
                screen.blit(band_surface, band_rect.topleft)
            pygame.draw.rect(screen, (80, 60, 40), band_rect, 2, border_radius=band_radius)

            title_surf = font_title.render(lang_text["title"], True, (40, 30, 25))
            title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, start_y - 80))
            screen.blit(title_surf, title_rect)

            sub_surf = font_text.render(lang_text["subtitle"], True, (60, 50, 45))
            sub_rect = sub_surf.get_rect(center=(WINDOW_WIDTH // 2, start_y - 52))
            screen.blit(sub_surf, sub_rect)

            btn_menu_pvp.label = lang_text["menu_pvp"]
            btn_menu_ai.label = lang_text["menu_ai"]
            btn_menu_stats.label = t(settings, "settings_player_stats")
            btn_menu_settings.label = lang_text["menu_settings"]
            btn_menu_credits.label = lang_text["menu_credits"]
            btn_menu_exit.label = lang_text["menu_exit"]

            btn_menu_pvp.draw(screen, font_button, enabled=True)
            btn_menu_ai.draw(screen, font_button, enabled=True)
            btn_menu_stats.draw(screen, font_button, enabled=True)
            btn_menu_settings.draw(screen, font_button, enabled=True)
            btn_menu_credits.draw(screen, font_button, enabled=True)
            btn_menu_exit.draw(screen, font_button, enabled=True)

        elif state == "credits":
            panel_rect = pygame.Rect(center_x - 230, start_y - 80, 460, 360)
            panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
            panel.fill((248, 244, 232, 235))
            screen.blit(panel, panel_rect.topleft)
            pygame.draw.rect(screen, (80, 60, 40), panel_rect, 2, border_radius=14)

            title_surf = font_title.render(lang_text["credits_title"], True, (50, 35, 20))
            title_rect = title_surf.get_rect(center=(panel_rect.centerx, panel_rect.top + 40))
            screen.blit(title_surf, title_rect)

            credits_lines = [
                lang_text["credits_line_1"],
                lang_text["credits_line_2"],
                lang_text["credits_line_3"],
            ]
            line_y = title_rect.bottom + 20
            for line in credits_lines:
                line_surf = font_text.render(line, True, (70, 60, 50))
                line_rect = line_surf.get_rect(center=(panel_rect.centerx, line_y))
                screen.blit(line_surf, line_rect)
                line_y += 26

            btn_credits_back.rect.center = (panel_rect.centerx, panel_rect.bottom - 40)
            btn_credits_back.label = lang_text["btn_back"]
            btn_credits_back.draw(screen, font_button, enabled=True)

        elif state in ("pvp", "ai"):
            board_area = pygame.Rect(MARGIN_X - 16, board_top - 16, (BOARD_COLS - 1) * CELL_SIZE + 32, (BOARD_ROWS - 1) * CELL_SIZE + 32)
            board_back = pygame.Surface(board_area.size, pygame.SRCALPHA)
            board_back.fill((15, 15, 15, 140))
            screen.blit(board_back, board_area.topleft)

            panel_rect = pygame.Rect(panel_x - 20, MARGIN_Y - 30, WINDOW_WIDTH - panel_x - 20, WINDOW_HEIGHT - (MARGIN_Y - 30) - 40)
            panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
            # Try to draw selected side-panel background; fallback to plain fill
            side_bg = None
            try:
                side_bg = load_side_panel_surface(panel_rect.size)
            except Exception:
                side_bg = None
            if side_bg is not None:
                panel_surf.blit(side_bg, (0, 0))
            else:
                panel_surf.fill((245, 245, 245, 215))
            screen.blit(panel_surf, panel_rect.topleft)
            pygame.draw.rect(screen, (50, 50, 50), panel_rect, 2, border_radius=10)

            start_btn_margin = 12
            start_btn_center = (panel_rect.centerx + START_BUTTON_OFFSET_X, panel_rect.top - start_btn_margin)
            switch_btn_midbottom_x = start_btn_center[0] - START_BUTTON_WIDTH // 2 - SWITCH_BUTTON_SPACING - SWITCH_BUTTON_SIZE // 2
            btn_change_side.rect.size = (SWITCH_BUTTON_SIZE, SWITCH_BUTTON_SIZE)
            btn_change_side.rect.midbottom = (switch_btn_midbottom_x, start_btn_center[1])
            btn_change_side.style["image_angle"] = switch_rotation_angle()

            draw_board(screen, settings, clear_surface=False)
            match_started = current_match_started()
            match_not_started = not match_started
            loser_side = None
            if mode is not None:
                badge_scale = 1.0
                if game_over and winner in (Side.RED, Side.BLACK):
                    loser_side = Side.BLACK if winner == Side.RED else Side.RED
                    if loss_badge_anim_start is None or loss_badge_side != loser_side:
                        start_loss_badge_animation(loser_side, last_move=move_history[-1] if move_history else None)
                    badge_scale = loss_badge_scale_for(loser_side)
                timer_rects_current = draw_side_avatars_on_board(
                    screen,
                    profiles_data,
                    mode,
                    ai_level_index,
                    font_avatar,
                    font_timer,
                    timer_labels=timer_labels_dict(),
                    loser_side=loser_side,
                    loss_badge_scale=badge_scale,
                    red_on_bottom=board.red_on_bottom,
                    active_side=current_side if mode in ("pvp", "ai") else None,
                    match_started=match_started,
                    shake_dx_fn=avatar_shake_dx,
                )

            # Draw avatar overlay buttons if open
            if avatar_buttons_open:
                try:
                    for key, rect in avatar_button_rects.items():
                        # draw white circular background with subtle border
                        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
                        radius = rect.width // 2
                        pygame.draw.circle(bg, (255, 255, 255, 240), (radius, radius), radius)
                        # light border
                        pygame.draw.circle(bg, (200, 200, 200, 255), (radius, radius), radius, 1)
                        screen.blit(bg, rect.topleft)
                        img = upload_img if key == "upload" else delete_img
                        if img is not None:
                            try:
                                img_s = pygame.transform.smoothscale(img, (rect.width - 6, rect.height - 6))
                                img_rect = img_s.get_rect(center=rect.center)
                                screen.blit(img_s, img_rect.topleft)
                            except Exception:
                                pass
                except Exception:
                    pass


            if can_change_side_now():
                btn_change_side.draw(screen, font_button, enabled=True)

            if selected is not None:
                draw_selection(screen, *selected)
                draw_move_hints(screen, valid_moves)

            last_highlight = None
            last_origin = None
            capturable_targets = set()
            if move_history:
                clamp_replay_index()
                idx = replay_index - 1 if replay_index is not None else len(move_history) - 1
                if 0 <= idx < len(move_history):
                    last_mv = move_history[idx]
                    hl_color = (0, 180, 0) if last_mv.piece.side == Side.RED else (200, 0, 0)
                    last_highlight = {"pos": last_mv.to_pos, "color": hl_color}
                    origin_color = (0, 180, 0) if last_mv.piece.side == Side.RED else (200, 0, 0)
                    last_origin = {"pos": last_mv.from_pos, "color": origin_color}

            if selected and valid_moves:
                sel_piece = board.get_piece(*selected)
                if sel_piece is not None:
                    for mv in valid_moves:
                        dest_piece = board.get_piece(*mv)
                        if dest_piece is not None and dest_piece.side != sel_piece.side:
                            capturable_targets.add(mv)

            if last_origin:
                c_from, r_from = last_origin["pos"]
                draw_move_origin(screen, c_from, r_from, last_origin["color"])

            for r in range(BOARD_ROWS):
                for c in range(BOARD_COLS):
                    piece = board.get_piece(c, r)
                    if piece is not None:
                        from core.engine.draw_helpers import draw_piece  
                        highlight_color = None
                        if last_highlight and last_highlight["pos"] == (c, r):
                            highlight_color = last_highlight["color"]
                        if (c, r) in capturable_targets:
                            highlight_color = (255, 215, 0)
                        draw_piece(screen, piece, c, r, font_piece, settings, highlight_color=highlight_color)

            if hovered_move and selected is not None:
                sel_piece = board.get_piece(*selected)
                if sel_piece is not None:
                    draw_piece_preview(
                        screen,
                        sel_piece,
                        hovered_move[0],
                        hovered_move[1],
                        font_piece,
                        settings,
                        alpha=130,
                    )

            # Animate sword slash overlay on the defeated General (reveals from top to bottom).
            if game_over and slash_anim_pos is not None and slash_anim_side is not None:
                img = load_slash_image()
                progress = slash_progress_for(slash_anim_side)
                if img is not None and progress > 0:
                    full_w, full_h = img.get_size()
                    draw_h = max(1, int(full_h * progress))
                    src_rect = pygame.Rect(0, 0, full_w, draw_h)
                    sx, sy = board_to_screen(*slash_anim_pos)
                    dest_pos = (sx - full_w // 2, sy - full_h // 2)
                    screen.blit(img, dest_pos, area=src_rect)

            # removed mode and turn display per user request
            y_info = MARGIN_Y + 10
            if in_check_side is not None and not game_over:
                msg = lang_text["check_on_red"] if in_check_side == Side.RED else lang_text["check_on_black"]
                ck_surf = font_text.render(msg, True, (200, 0, 0))
                screen.blit(ck_surf, (panel_x, y_info))
                y_info += 25

            if game_over and winner is not None:
                if winner == Side.RED:
                    msg = lang_text["red_wins"]
                    color = (200, 0, 0)
                elif winner == Side.BLACK:
                    msg = lang_text["black_wins"]
                    color = (0, 0, 200)
                else:
                    msg = lang_text["game_over"]
                    color = (0, 0, 0)

                # Render the win message centered at the top of the side panel,
                # bigger, bold and uppercase per request.
                try:
                    panel_center_x = panel_rect.centerx
                except Exception:
                    panel_center_x = panel_x + LOG_BOX_WIDTH // 2

                win_text = msg.upper()
                win_surf = font_title.render(win_text, True, color)
                win_rect = win_surf.get_rect(center=(panel_center_x, MARGIN_Y + 18))
                screen.blit(win_surf, win_rect)
                y_info = win_rect.bottom + 8

            if match_not_started:
                pending_surf = font_text.render(lang_text["match_not_started"], True, (60, 60, 60))
                screen.blit(pending_surf, (panel_x, y_info))
                y_info += 22

            last_sel = profiles_data.get("last_selected", {})
            pvp_info = last_sel.get("pvp", {})
            ai_info = last_sel.get("ai", {})

            y_players = y_info + 10
            small_size = 24

            if mode == "pvp":
                red_id = pvp_info.get("red_player_id", "p1")
                black_id = pvp_info.get("black_player_id", "p2")
                red_player = find_player(profiles_data, red_id)
                black_player = find_player(profiles_data, black_id)

                if red_player:
                    center = (
                        panel_x + small_size // 2 + 4 + avatar_shake_dx(Side.RED),
                        y_players + small_size // 2,
                    )
                    draw_profile_avatar(
                        screen,
                        red_player,
                        center,
                        small_size,
                        font_avatar,
                        grayscale=loser_side == Side.RED,
                    )
                    label = t(settings, "label_red_player").format(name=red_player.get("display_name", "Player 1"))
                    color = (200, 0, 0) if current_side == Side.RED else (0, 0, 0)
                    txt = font_text.render(label, True, color)
                    screen.blit(txt, (panel_x + small_size + 8, y_players))
                    y_players += small_size + 6

                if black_player:
                    center = (
                        panel_x + small_size // 2 + 4 + avatar_shake_dx(Side.BLACK),
                        y_players + small_size // 2,
                    )
                    draw_profile_avatar(
                        screen,
                        black_player,
                        center,
                        small_size,
                        font_avatar,
                        grayscale=loser_side == Side.BLACK,
                    )
                    label = t(settings, "label_black_player").format(name=black_player.get("display_name", "Player 2"))
                    color = (0, 0, 200) if current_side == Side.BLACK else (0, 0, 0)
                    txt = font_text.render(label, True, color)
                    screen.blit(txt, (panel_x + small_size + 8, y_players))
                    y_players += small_size + 6

            else:
                human_id = ai_info.get("human_player_id", "p1")
                human_player = find_player(profiles_data, human_id)
                if human_player:
                    center = (
                        panel_x + small_size // 2 + 4 + avatar_shake_dx(human_side),
                        y_players + small_size // 2,
                    )
                    draw_profile_avatar(
                        screen,
                        human_player,
                        center,
                        small_size,
                        font_avatar,
                        grayscale=loser_side == human_side,
                    )
                    label = t(settings, "label_red_player").format(
                        name=human_player.get("display_name", "Player 1")
                    )
                    color = (200, 0, 0) if current_side == Side.RED else (0, 0, 0)
                    txt = font_text.render(label, True, color)
                    screen.blit(txt, (panel_x + small_size + 8, y_players))
                    y_players += small_size + 6

                ai_cfg = AI_LEVELS[ai_level_index]
                center = (
                    panel_x + small_size // 2 + 4 + avatar_shake_dx(ai_side),
                    y_players + small_size // 2,
                )
                draw_ai_avatar(
                    screen,
                    ai_cfg,
                    center,
                    small_size,
                    font_avatar,
                    grayscale=loser_side == ai_side,
                )
                label = t(settings, "label_ai_player").format(name=ai_cfg["name"])
                color = (0, 0, 200) if current_side == Side.BLACK else (0, 0, 0)
                txt = font_text.render(label, True, color)
                screen.blit(txt, (panel_x + small_size + 8, y_players))
                y_players += small_size + 6

            panel_log_top = max(PANEL_MIN_LOG_TOP, y_players + 10)

            # AI controls
            if state == "ai":
                # Show a centered "Change AI" button before the match starts
                level_cfg = AI_LEVELS[ai_level_index]
                btn_ai_level.label = "Change AI"
                # keep button size, center horizontally in the side panel
                try:
                    btn_ai_level.rect.centerx = panel_rect.centerx
                except Exception:
                    btn_ai_level.rect.x = panel_x + 30
                btn_ai_level.rect.y = panel_log_top
                if match_not_started:
                    btn_ai_level.draw(screen, font_button, enabled=True)
                panel_log_top += 35

            if match_not_started:
                btn_start_match.label = lang_text["btn_start_match"]
                btn_start_match.rect.size = (START_BUTTON_WIDTH, START_BUTTON_HEIGHT)
                btn_start_match.rect.midbottom = start_btn_center
                btn_start_match.draw(screen, font_button, enabled=True)

            btn_replay_prev.label = "<"
            btn_replay_next.label = ">"
            if game_over and move_history:
                current_idx = len(move_history) if replay_index is None else replay_index
                enabled_prev = current_idx > 0
                enabled_next = current_idx < len(move_history)
            else:
                enabled_prev = False
                enabled_next = False

            # Show replay controls only after the match is over
            if game_over and move_history:
                btn_replay_prev.draw(screen, font_button, enabled=enabled_prev)
                btn_replay_next.draw(screen, font_button, enabled=enabled_next)

            # Make the log box expand vertically up to near the in-game settings button
            log_top = panel_log_top + 30
            try:
                settings_btn_top = btn_in_game_settings.rect.top
            except Exception:
                settings_btn_top = WINDOW_HEIGHT - 153
            desired_bottom = settings_btn_top - 12
            computed_height = max(80, desired_bottom - log_top)
            if computed_height <= 0:
                computed_height = LOG_BOX_HEIGHT
            log_box_rect = pygame.Rect(panel_x, log_top, LOG_BOX_WIDTH, computed_height)
            log_box_rect_current = log_box_rect

            # Make the two tabs sized relative to the log box and centered above it
            tab_gap = 12
            tab_height = 24
            tab_width = max(60, (log_box_rect.width - tab_gap) // 2)
            total_tabs_w = tab_width * 2 + tab_gap
            start_x = log_box_rect.x + max(0, (log_box_rect.width - total_tabs_w) // 2)
            tab_y = log_box_rect.y - 26
            btn_log_tab_moves.rect = pygame.Rect(start_x, tab_y, tab_width, tab_height)
            btn_log_tab_captured.rect = pygame.Rect(start_x + tab_width + tab_gap, tab_y, tab_width, tab_height)

            # Position replay buttons centered below the log box and a bit lower
            try:
                prev_w, prev_h = btn_replay_prev.rect.size
            except Exception:
                prev_w, prev_h = 40, 28
            gap = 12
            total_w = prev_w * 2 + gap
            start_rx = log_box_rect.centerx - total_w // 2
            # Replay buttons pos
            replay_y = log_box_rect.bottom - 35
            btn_replay_prev.rect.topleft = (start_rx, replay_y)
            btn_replay_next.rect.topleft = (start_rx + prev_w + gap, replay_y)

            # Label tabs
            btn_log_tab_moves.label = t(settings, "tab_moves")
            btn_log_tab_captured.label = t(settings, "tab_captured")

            btn_log_tab_moves.draw(screen, font_button, enabled=(log_active_tab == "moves"))
            btn_log_tab_captured.draw(screen, font_button, enabled=(log_active_tab == "captured"))

            # Draw log box background with configurable transparency
            alpha = settings.log_box_transparency if getattr(settings, "log_box_transparency_enabled", True) else 255
            bg_surf = pygame.Surface((log_box_rect.width, log_box_rect.height), pygame.SRCALPHA)
            bg_surf.fill((235, 235, 235, int(alpha)))
            screen.blit(bg_surf, log_box_rect.topleft)
            pygame.draw.rect(screen, (80, 80, 80), log_box_rect, 2)

            inner_margin_x = 8
            inner_margin_y = 8
            line_height = 20
            max_lines = max(1, (log_box_rect.height - inner_margin_y * 2) // line_height)

            try:
                view_index = replay_index if replay_index is not None else len(move_history)
            except NameError:
                view_index = len(move_history)

            if view_index < 0:
                view_index = 0
            if view_index > len(move_history):
                view_index = len(move_history)

            max_offset = max(0, view_index - max_lines)

            if log_active_tab == "moves":
                if log_follow_latest:
                    move_log_offset = max_offset
                else:
                    if move_log_offset > max_offset:
                        move_log_offset = max_offset
                    if move_log_offset < 0:
                        move_log_offset = 0
            else:
                if move_log_offset > max_offset:
                    move_log_offset = max_offset
                if move_log_offset < 0:
                    move_log_offset = 0

            if log_active_tab == "moves":
                start_idx = move_log_offset
                end_idx = min(view_index, start_idx + max_lines)

                y_text = log_box_rect.y + inner_margin_y
                for i in range(start_idx, end_idx):
                    mv = move_history[i]
                    # number
                    num_text = f"{i + 1}."
                    side_color = (200, 0, 0) if getattr(mv.piece, "side", None) == Side.RED else (0, 0, 200)
                    num_surf = font_text.render(num_text, True, side_color)
                    x = log_box_rect.x + inner_margin_x
                    screen.blit(num_surf, (x, y_text))
                    x += num_surf.get_width() + 6

                    # piece name without R-/B- prefix
                    piece_name = "?"
                    try:
                        piece_name = mv.piece.ptype.value.capitalize()
                    except Exception:
                        piece_name = str(mv.piece)
                    piece_surf = font_text.render(piece_name, True, side_color)
                    screen.blit(piece_surf, (x, y_text))
                    x += piece_surf.get_width() + 6

                    # from -> to
                    try:
                        pos_text = f"{mv.from_pos} -> {mv.to_pos}"
                    except Exception:
                        pos_text = ""
                    pos_surf = font_text.render(pos_text, True, (0, 0, 0))
                    screen.blit(pos_surf, (x, y_text))
                    y_text += line_height

                if view_index == 0:
                    empty_txt = "(no moves)" if settings.language == "en" else "(chưa có nước đi)"
                    et_surf = font_text.render(empty_txt, True, (120, 120, 120))
                    et_rect = et_surf.get_rect(center=log_box_rect.center)
                    screen.blit(et_surf, et_rect)

            else:
                # Tab Captured: show captured pieces in two vertical columns
                captured_by_red_counts = {}  # RED captured pieces (i.e. RED captured BLACK)
                captured_by_black_counts = {}  # BLACK captured pieces (i.e. BLACK captured RED)

                for mv in move_history[:view_index]:
                    if mv.captured is not None:
                        mover_side = mv.piece.side
                        pt = mv.captured.ptype
                        if mover_side == Side.RED:
                            captured_by_red_counts[pt] = captured_by_red_counts.get(pt, 0) + 1
                        else:
                            captured_by_black_counts[pt] = captured_by_black_counts.get(pt, 0) + 1

                piece_order = [
                    PieceType.GENERAL,
                    PieceType.ROOK,
                    PieceType.CANNON,
                    PieceType.HORSE,
                    PieceType.ELEPHANT,
                    PieceType.ADVISOR,
                    PieceType.SOLDIER,
                ]

                class _DummyPiece:
                    def __init__(self, side, ptype):
                        self.side = side
                        self.ptype = ptype

                # Larger icons for captured pieces
                captured_icon_size = 48
                gap_y = 8

                # Column positions: left for RED's captured (icons of BLACK pieces), right for BLACK's captured
                left_x = log_box_rect.x + inner_margin_x
                right_x = log_box_rect.x + log_box_rect.width - inner_margin_x - captured_icon_size - 28

                y_start = log_box_rect.y + inner_margin_y

                # Compute how many rows (visible types) there are and auto-scale icons to fit
                available_height = log_box_rect.height - (inner_margin_y * 2)
                visible_types = [pt for pt in piece_order if (captured_by_red_counts.get(pt, 0) > 0 or captured_by_black_counts.get(pt, 0) > 0)]
                total_visible = len(visible_types)

                if total_visible == 0:
                    empty_txt = "(no captured pieces)" if settings.language == "en" else "(chưa ăn được quân nào)"
                    et_surf = font_text.render(empty_txt, True, (120, 120, 120))
                    et_rect = et_surf.get_rect(center=log_box_rect.center)
                    screen.blit(et_surf, et_rect)
                else:
                    # Compute a dynamic icon size so all visible rows fit vertically
                    min_icon = 20
                    max_icon = 48
                    # space for gaps between rows
                    total_gap = gap_y * (total_visible - 1)
                    tentative_icon = max(min_icon, (available_height - total_gap) // total_visible)
                    icon_size = max(min_icon, min(max_icon, tentative_icon))

                    # Recompute column x positions based on icon_size
                    left_x = log_box_rect.x + inner_margin_x
                    right_x = log_box_rect.x + log_box_rect.width - inner_margin_x - icon_size - 28

                    row_height = icon_size + gap_y
                    y = y_start
                    for pt in visible_types:
                        # Left column: pieces RED captured (icons of BLACK pieces)
                        left_count = captured_by_red_counts.get(pt, 0)
                        if left_count > 0:
                            dummy_piece = _DummyPiece(Side.BLACK, pt)
                            icon = get_piece_sprite(dummy_piece, settings, icon_size)
                            if icon is None:
                                icon = font_text.render("?", True, (0, 0, 0))
                            icon_rect = icon.get_rect(topleft=(left_x, y))
                            screen.blit(icon, icon_rect.topleft)
                            cnt_txt = f"x{left_count}"
                            cnt_surf = font_text.render(cnt_txt, True, (0, 0, 0))
                            cnt_rect = cnt_surf.get_rect(midleft=(left_x + icon_rect.width + 8, y + icon_rect.height / 2 - 2))
                            screen.blit(cnt_surf, cnt_rect.topleft)

                        # Right column: pieces BLACK captured (icons of RED pieces)
                        right_count = captured_by_black_counts.get(pt, 0)
                        if right_count > 0:
                            dummy_piece = _DummyPiece(Side.RED, pt)
                            icon = get_piece_sprite(dummy_piece, settings, icon_size)
                            if icon is None:
                                icon = font_text.render("?", True, (0, 0, 0))
                            icon_rect = icon.get_rect(topleft=(right_x, y))
                            screen.blit(icon, icon_rect.topleft)
                            cnt_txt = f"x{right_count}"
                            cnt_surf = font_text.render(cnt_txt, True, (0, 0, 0))
                            cnt_rect = cnt_surf.get_rect(midleft=(right_x + icon_rect.width + 8, y + icon_rect.height / 2 - 2))
                            screen.blit(cnt_surf, cnt_rect.topleft)

                        y += row_height

                def piece_char_for_display(ptype, side):
                    if ptype == PieceType.GENERAL:
                        return "帥" if side == Side.RED else "將"
                    elif ptype == PieceType.ADVISOR:
                        return "仕" if side == Side.RED else "士"
                    elif ptype == PieceType.ELEPHANT:
                        return "相" if side == Side.RED else "象"
                    elif ptype == PieceType.HORSE:
                        return "傌" if side == Side.RED else "馬"
                    elif ptype == PieceType.ROOK:
                        return "俥" if side == Side.RED else "車"
                    elif ptype == PieceType.CANNON:
                        return "炮" if side == Side.RED else "砲"
                    else:
                        return "兵" if side == Side.RED else "卒"

                # Duplicate character-based rendering removed; icons and counts are
                # already drawn above in two vertical columns without text labels.


            btn_in_game_settings.label = lang_text["btn_settings_in_game"]
            btn_takeback.label = lang_text["btn_takeback"]
            btn_resign.label = lang_text["btn_resign"]
            btn_new_game.label = lang_text["btn_new_game"]

            btn_in_game_settings.draw(screen, font_button, enabled=True)
            btn_takeback.draw(screen, font_button, enabled=bool(move_history) and not game_over)
            btn_resign.draw(screen, font_button, enabled=not game_over)
            btn_new_game.draw(screen, font_button, enabled=True)
            # Draw replay buttons only when the match is over
            if game_over and move_history:
                btn_replay_prev.draw(screen, font_button, enabled=enabled_prev)
                btn_replay_next.draw(screen, font_button, enabled=enabled_next)
        # SETTING MENU 
        elif state == "settings":
            settings_panel_rect = get_settings_panel_rect()
            settings_panel = pygame.Surface(settings_panel_rect.size, pygame.SRCALPHA)
            settings_panel.fill((18, 18, 24, 185))
            screen.blit(settings_panel, settings_panel_rect.topleft)
            pygame.draw.rect(screen, (60, 60, 60), settings_panel_rect, 2, border_radius=12)

            if settings_page == "main":
                tabs_layout = build_settings_tabs(settings_panel_rect)
                layout = build_settings_layout(settings_category, content_top=tabs_layout["content_top"])

                title_surf = font_title.render(t(settings, "settings_title"), True, (240, 240, 240))
                title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 120))
                screen.blit(title_surf, title_rect)

                for tab in tabs_layout["tabs"]:
                    is_selected = tab["key"] == settings_category
                    base_color = (220, 220, 220) if is_selected else (180, 180, 180)
                    border_color = (40, 40, 40)
                    pygame.draw.rect(screen, base_color, tab["rect"], border_radius=8)
                    pygame.draw.rect(screen, border_color, tab["rect"], 2, border_radius=8)
                    label_color = (20, 20, 20) if is_selected else (40, 40, 40)
                    tab_surf = font_button.render(tab["label"], True, label_color)
                    tab_rect = tab_surf.get_rect(center=tab["rect"].center)
                    screen.blit(tab_surf, tab_rect)

                header_color = (215, 205, 205)
                for header in layout["headers"]:
                    header_surf = font_button.render(header["title"], True, header_color)
                    screen.blit(header_surf, header["pos"])

                if not layout["rows"]:
                    info_surf = font_text.render(t(settings, "settings_no_options"), True, (225, 225, 225))
                    info_y = layout["content_bottom"] + 10
                    info_rect = info_surf.get_rect(center=(WINDOW_WIDTH // 2, info_y))
                    screen.blit(info_surf, info_rect)

                for row in layout["rows"]:
                    base_color = (90, 80, 80) if row["enabled"] else (70, 70, 70)
                    border_color = (40, 40, 40)
                    pygame.draw.rect(screen, base_color, row["rect"], border_radius=8)
                    pygame.draw.rect(screen, border_color, row["rect"], 2, border_radius=8)

                    label_surf = font_text.render(row["label"], True, (235, 235, 235))
                    label_rect = label_surf.get_rect(midleft=(row["rect"].x + 14, row["rect"].centery))
                    screen.blit(label_surf, label_rect)

                    value_rect = row["value_rect"]
                    # Special rendering for the log box transparency slider + checkbox
                    if row.get("kind") == "slider" and row.get("key") == "log_box_transparency":
                        enabled = settings.log_box_transparency_enabled
                        slider_area = pygame.Rect(value_rect.x + 6, value_rect.y + 8, max(1, value_rect.width - 46), max(1, value_rect.height - 16))
                        checkbox_rect = pygame.Rect(value_rect.right - 28, value_rect.centery - 8, 18, 18)

                        # Slider background
                        bg_col = (245, 245, 245) if enabled else (180, 180, 180)
                        pygame.draw.rect(screen, bg_col, slider_area, border_radius=6)
                        pygame.draw.rect(screen, border_color, slider_area, 2, border_radius=6)

                        # Filled portion
                        fill_w = int((settings.log_box_transparency / 255.0) * slider_area.width)
                        fill_rect = pygame.Rect(slider_area.x, slider_area.y, fill_w, slider_area.height)
                        fill_col = (0, 110, 200) if enabled else (120, 120, 120)
                        pygame.draw.rect(screen, fill_col, fill_rect, border_radius=6)

                        # Knob
                        knob_x = slider_area.x + max(4, min(slider_area.width - 4, fill_w))
                        knob_center = (knob_x, slider_area.centery)
                        knob_color = (255, 255, 255) if enabled else (220, 220, 220)
                        pygame.draw.circle(screen, knob_color, knob_center, 7)
                        pygame.draw.circle(screen, border_color, knob_center, 7, 2)

                        # Percentage text
                        pct = int(settings.log_box_transparency / 255.0 * 100)
                        pct_surf = font_button.render(f"{pct}%", True, (0, 0, 0) if enabled else (90, 90, 90))
                        pct_rect = pct_surf.get_rect(midleft=(slider_area.right + 6, slider_area.centery))
                        screen.blit(pct_surf, pct_rect)

                        # Checkbox to enable/disable
                        pygame.draw.rect(screen, (255, 255, 255), checkbox_rect, border_radius=4)
                        pygame.draw.rect(screen, border_color, checkbox_rect, 2, border_radius=4)
                        if enabled:
                            # draw check mark
                            cx = checkbox_rect.centerx
                            cy = checkbox_rect.centery
                            pygame.draw.line(screen, (20, 120, 20), (checkbox_rect.left + 4, cy), (cx - 1, checkbox_rect.bottom - 5), 3)
                            pygame.draw.line(screen, (20, 120, 20), (cx - 1, checkbox_rect.bottom - 5), (checkbox_rect.right - 4, checkbox_rect.top + 4), 3)

                    else:
                        value_color = (230, 230, 230) if row["enabled"] else (150, 150, 150)
                        pygame.draw.rect(screen, value_color, value_rect, border_radius=6)
                        pygame.draw.rect(screen, border_color, value_rect, 2, border_radius=6)

                        # Draw flag icon for language row, if available
                        text_x = value_rect.x + 10
                        if row.get("key") == "language":
                            # choose a sensible flag size based on row height
                            fh = max(12, value_rect.height - 12)
                            fw = int(round(fh * 1.6))
                            flag_surf = load_flag_for_language(row.get("value"), (fw, fh))
                            if flag_surf:
                                flag_rect = flag_surf.get_rect()
                                flag_rect.midleft = (value_rect.x + 8 + flag_rect.width // 2, value_rect.centery)
                                screen.blit(flag_surf, (value_rect.x + 8, value_rect.centery - flag_rect.height // 2))
                                text_x = value_rect.x + 8 + flag_rect.width + 8

                        value_surf = font_button.render(row["value_text"], True, (0, 0, 0))
                        value_surf_rect = value_surf.get_rect(midleft=(text_x, value_rect.centery))
                        screen.blit(value_surf, value_surf_rect)

                        arrow_x = value_rect.right - 16
                        arrow_y = value_rect.centery
                        if row.get("kind") == "modal":
                            arrow_pts = [(arrow_x - 6, arrow_y - 6), (arrow_x + 6, arrow_y), (arrow_x - 6, arrow_y + 6)]
                        elif settings_open_dropdown == row["key"]:
                            arrow_pts = [(arrow_x - 6, arrow_y + 3), (arrow_x + 6, arrow_y + 3), (arrow_x, arrow_y - 5)]
                        else:
                            arrow_pts = [(arrow_x - 6, arrow_y - 3), (arrow_x + 6, arrow_y - 3), (arrow_x, arrow_y + 5)]
                        pygame.draw.polygon(screen, (0, 0, 0), arrow_pts)

                for opt in layout["options"]:
                    bg = (225, 225, 225)
                    if opt["selected"]:
                        bg = (200, 220, 255)
                    pygame.draw.rect(screen, bg, opt["rect"], border_radius=6)
                    pygame.draw.rect(screen, (60, 60, 60), opt["rect"], 1, border_radius=6)
                    # Draw flag for language options when available
                    opt_text_x = opt["rect"].x + 10
                    if opt.get("key") == "language":
                        ofh = max(12, opt["rect"].height - 8)
                        ofw = int(round(ofh * 1.6))
                        opt_flag = load_flag_for_language(opt.get("value"), (ofw, ofh))
                        if opt_flag:
                            screen.blit(opt_flag, (opt["rect"].x + 6, opt["rect"].centery - opt_flag.get_height() // 2))
                            opt_text_x = opt["rect"].x + 6 + opt_flag.get_width() + 8

                    opt_surf = font_button.render(opt["text"], True, (0, 0, 0))
                    opt_rect = opt_surf.get_rect(midleft=(opt_text_x, opt["rect"].centery))
                    screen.blit(opt_surf, opt_rect)

                dropdown_bottom = layout["content_bottom"]
                if layout["options"]:
                    dropdown_bottom = max(dropdown_bottom, max(opt["rect"].bottom for opt in layout["options"]))

                footer_top = max(dropdown_bottom + 30, WINDOW_HEIGHT - 120)
                footer_top = min(footer_top, WINDOW_HEIGHT - 70)

                btn_settings_back.rect.center = (settings_center_x, footer_top)
                btn_settings_back.label = t(settings, "btn_back")

                btn_settings_back.draw(screen, font_button, enabled=True)

            else:
                title_surf = font_title.render(t(settings, "stats_title"), True, (240, 240, 240))
                title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 120))
                screen.blit(title_surf, title_rect)

                games_label = t(settings, "stats_games")
                wins_label = t(settings, "stats_wins")
                losses_label = t(settings, "stats_losses")
                draws_label = t(settings, "stats_draws")
                winrate_label = t(settings, "stats_winrate")
                overall_label = t(settings, "stats_overall")
                vs_ai_label = t(settings, "stats_vs_ai")
                vs_human_label = t(settings, "stats_vs_human")

                start_x = settings_center_x - 260
                y = 180

                for p in profiles_data.get("players", []):
                    avatar_center = (start_x + 20, y + 15)
                    draw_profile_avatar(screen, p, avatar_center, 30, font_avatar)

                    name = p.get("display_name", "Player")
                    name_surf = font_text.render(name, True, (240, 240, 240))
                    screen.blit(name_surf, (start_x + 40, y))

                    elo_value = int(p.get("elo", DEFAULT_ELO))
                    elo_label = t(settings, "label_elo").format(elo=elo_value)
                    elo_surf = font_text.render(elo_label, True, (210, 210, 210))
                    screen.blit(elo_surf, (start_x + 40, y + 18))

                    stats = p.get("stats", {})
                    ov = stats.get("overall", {"games": 0, "wins": 0, "losses": 0, "draws": 0})
                    ai_stats = stats.get("vs_ai", {"games": 0, "wins": 0, "losses": 0, "draws": 0})
                    hv = stats.get("vs_human", {"games": 0, "wins": 0, "losses": 0, "draws": 0})

                    def fmt_block(label_txt, s):
                        g = s.get("games", 0)
                        w = s.get("wins", 0)
                        l = s.get("losses", 0)
                        d = s.get("draws", 0)
                        wr = (w / g * 100) if g > 0 else 0.0
                        line1 = f"{label_txt}: {games_label} {g}, {wins_label} {w}, {losses_label} {l}, {draws_label} {d}"
                        line2 = f"{winrate_label}: {wr:.1f}%"
                        return line1, line2

                    ov_l1, ov_l2 = fmt_block(overall_label, ov)
                    ai_l1, ai_l2 = fmt_block(vs_ai_label, ai_stats)
                    hv_l1, hv_l2 = fmt_block(vs_human_label, hv)

                    y_line = y + 36
                    for line in [ov_l1, ov_l2, ai_l1, ai_l2, hv_l1, hv_l2]:
                        ls = font_text.render(line, True, (220, 220, 220))
                        screen.blit(ls, (start_x + 40, y_line))
                        y_line += 18

                    y = y_line + 10

                btn_settings_back.label = t(settings, "btn_back")
                btn_settings_back.rect.center = (settings_center_x, WINDOW_HEIGHT - 70)
                btn_settings_back.draw(screen, font_button, enabled=True)
        # Background modal rendering
        if background_modal_open and BACKGROUNDS:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            layout = build_background_modal_layout()
            modal_rect = layout["modal_rect"]

            pygame.draw.rect(screen, (245, 245, 245), modal_rect, border_radius=12)
            pygame.draw.rect(screen, (60, 60, 60), modal_rect, 2, border_radius=12)

            title_text = t(settings, "background_modal_title")
            subtitle_text = t(settings, "background_modal_subtitle")

            title_surf = font_title.render(title_text, True, (25, 25, 25))
            title_rect = title_surf.get_rect(midtop=(modal_rect.centerx, modal_rect.top + 16))
            screen.blit(title_surf, title_rect)

            subtitle_surf = font_text.render(subtitle_text, True, (60, 60, 60))
            subtitle_rect = subtitle_surf.get_rect(midtop=(modal_rect.centerx, title_rect.bottom + 6))
            screen.blit(subtitle_surf, subtitle_rect)

            close_rect = layout["close_rect"]
            pygame.draw.rect(screen, (225, 225, 225), close_rect, border_radius=6)
            pygame.draw.rect(screen, (90, 90, 90), close_rect, 1, border_radius=6)
            close_label = lang_text.get("btn_back", "Back")
            close_surf = font_button.render(close_label, True, (20, 20, 20))
            close_surf_rect = close_surf.get_rect(center=close_rect.center)
            screen.blit(close_surf, close_surf_rect)

            selected_idx = settings.background_index % len(BACKGROUNDS) if BACKGROUNDS else -1
            for opt in layout["options"]:
                rect = opt["rect"]
                thumb_rect = opt["thumb_rect"]
                is_selected = opt["index"] == selected_idx
                bg = (235, 235, 235) if is_selected else (220, 220, 220)
                border_color = (190, 60, 60) if is_selected else (90, 90, 90)
                pygame.draw.rect(screen, bg, rect, border_radius=10)
                pygame.draw.rect(screen, border_color, rect, 2, border_radius=10)

                thumb = load_background_thumbnail(opt["index"], (thumb_rect.width, thumb_rect.height))
                if thumb is not None:
                    screen.blit(thumb, thumb_rect)

                name_text = background_label(opt["index"])
                name_surf = font_button.render(name_text, True, (25, 25, 25))
                name_rect = name_surf.get_rect(midtop=(rect.centerx, thumb_rect.bottom + 8))
                screen.blit(name_surf, name_rect)
        # Side panel modal rendering
        if side_panel_modal_open and SIDE_PANEL_BACKGROUNDS:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            layout = build_side_panel_modal_layout()
            modal_rect = layout["modal_rect"]

            pygame.draw.rect(screen, (245, 245, 245), modal_rect, border_radius=12)
            pygame.draw.rect(screen, (60, 60, 60), modal_rect, 2, border_radius=12)

            title_text = t(settings, "side_panel_modal_title")
            subtitle_text = t(settings, "side_panel_modal_subtitle")

            title_surf = font_title.render(title_text, True, (25, 25, 25))
            title_rect = title_surf.get_rect(midtop=(modal_rect.centerx, modal_rect.top + 16))
            screen.blit(title_surf, title_rect)

            subtitle_surf = font_text.render(subtitle_text, True, (60, 60, 60))
            subtitle_rect = subtitle_surf.get_rect(midtop=(modal_rect.centerx, title_rect.bottom + 6))
            screen.blit(subtitle_surf, subtitle_rect)

            close_rect = layout["close_rect"]
            pygame.draw.rect(screen, (225, 225, 225), close_rect, border_radius=6)
            pygame.draw.rect(screen, (90, 90, 90), close_rect, 1, border_radius=6)
            close_label = lang_text.get("btn_back", "Back")
            close_surf = font_button.render(close_label, True, (20, 20, 20))
            close_surf_rect = close_surf.get_rect(center=close_rect.center)
            screen.blit(close_surf, close_surf_rect)

            selected_idx = settings.side_panel_background_index % len(SIDE_PANEL_BACKGROUNDS) if SIDE_PANEL_BACKGROUNDS else -1
            for opt in layout["options"]:
                rect = opt["rect"]
                thumb_rect = opt["thumb_rect"]
                is_selected = opt["index"] == selected_idx
                bg = (235, 235, 235) if is_selected else (220, 220, 220)
                border_color = (190, 60, 60) if is_selected else (90, 90, 90)
                pygame.draw.rect(screen, bg, rect, border_radius=10)
                pygame.draw.rect(screen, border_color, rect, 2, border_radius=10)

                thumb = load_side_panel_thumbnail(opt["index"], (thumb_rect.width, thumb_rect.height))
                if thumb is not None:
                    screen.blit(thumb, thumb_rect)

                name_text = side_panel_label(opt["index"])
                name_surf = font_button.render(name_text, True, (25, 25, 25))
                name_rect = name_surf.get_rect(midtop=(rect.centerx, thumb_rect.bottom + 8))
                screen.blit(name_surf, name_rect)
        # Timer modal rendering
        if timer_modal_open and can_change_timer():
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            layout = build_timer_modal_layout()
            modal_rect = layout["modal_rect"]

            pygame.draw.rect(screen, (245, 245, 245), modal_rect, border_radius=12)
            pygame.draw.rect(screen, (60, 60, 60), modal_rect, 2, border_radius=12)

            title_text = lang_text.get("timer_modal_title", "Match timer")
            subtitle_text = lang_text.get("timer_modal_subtitle", "Choose how much time each side gets")

            title_surf = font_title.render(title_text, True, (25, 25, 25))
            title_rect = title_surf.get_rect(midtop=(modal_rect.centerx, modal_rect.top + 16))
            screen.blit(title_surf, title_rect)

            subtitle_surf = font_text.render(subtitle_text, True, (60, 60, 60))
            subtitle_rect = subtitle_surf.get_rect(midtop=(modal_rect.centerx, title_rect.bottom + 6))
            screen.blit(subtitle_surf, subtitle_rect)

            close_rect = layout["close_rect"]
            pygame.draw.rect(screen, (225, 225, 225), close_rect, border_radius=6)
            pygame.draw.rect(screen, (90, 90, 90), close_rect, 1, border_radius=6)
            close_label = lang_text.get("btn_back", "Back")
            close_surf = font_button.render(close_label, True, (20, 20, 20))
            close_surf_rect = close_surf.get_rect(center=close_rect.center)
            screen.blit(close_surf, close_surf_rect)

            for opt in layout["options"]:
                rect = opt["rect"]
                thumb_rect = opt["thumb_rect"]
                choice = opt["choice"]
                is_selected = opt["index"] == timer_option_index
                bg = (235, 235, 235) if is_selected else (220, 220, 220)
                border_color = (190, 60, 60) if is_selected else (90, 90, 90)
                pygame.draw.rect(screen, bg, rect, border_radius=10)
                pygame.draw.rect(screen, border_color, rect, 2, border_radius=10)

                thumb = load_timer_thumbnail(choice["asset"], (thumb_rect.width, thumb_rect.height))
                if thumb is not None:
                    screen.blit(thumb, thumb_rect)

                label_surf = font_timer.render(choice["label"], True, (25, 25, 25))
                label_rect = label_surf.get_rect(midtop=(rect.centerx, thumb_rect.bottom + 6))
                screen.blit(label_surf, label_rect)
        # Paused modal rendering
        if paused:
            # Overlay
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            # Modal (animated pause menu image)
            modal_width = int(360 * 1.5)
            modal_height = int(220 * 3)  # increased height x2 as requested
            modal_rect = pygame.Rect(0, 0, modal_width, modal_height)
            modal_rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

            # load and scale pause menu image
            pause_img = load_pause_menu_surface((modal_width, modal_height))
            now = pygame.time.get_ticks() / 1000.0
            if pause_anim_start is None:
                pause_anim_start = now
            elapsed = max(0.0, now - pause_anim_start)
            progress = min(1.0, elapsed / PAUSE_ANIM_DURATION) if PAUSE_ANIM_DURATION > 0 else 1.0
            # scale initial crop proportionally to modal height (original reference 220)
            initial_crop = int(PAUSE_ANIM_INITIAL_CROP_BOTTOM * (modal_height / 220))
            crop_bottom = int(initial_crop * (1.0 - progress))

            if pause_img is not None:
                w, h = pause_img.get_size()
                crop_rect = pygame.Rect(0, 0, w, max(1, h - max(0, crop_bottom)))
                try:
                    visible = pause_img.subsurface(crop_rect)
                except Exception:
                    visible = pause_img
                # compute menu fade alpha
                menu_alpha = min(1.0, elapsed / PAUSE_MENU_FADE) if PAUSE_MENU_FADE > 0 else 1.0
                try:
                    visible_copy = visible.copy()
                    visible_copy.set_alpha(int(menu_alpha * 255))
                    screen.blit(visible_copy, (modal_rect.left, modal_rect.top + crop_bottom))
                except Exception:
                    screen.blit(visible, (modal_rect.left, modal_rect.top + crop_bottom))
            else:
                pygame.draw.rect(screen, (240, 240, 240), modal_rect, border_radius=8)
                pygame.draw.rect(screen, (60, 60, 60), modal_rect, 2, border_radius=8)

            title_text = lang_text["paused"]
            resume_text = lang_text["resume"]
            to_menu_text = lang_text["main_menu"]

            # Pause buttons label (include player stats)
            lang_text = TEXT[settings.language]
            btn_pause_resume.label = resume_text
            btn_pause_settings.label = lang_text["menu_settings"]
            btn_pause_player_stats.label = t(settings, "settings_player_stats") if "settings_player_stats" in TEXT.get(settings.language, {}) else lang_text.get("menu_stats", "Player Stats")
            btn_pause_to_menu.label = to_menu_text

            # center all four buttons vertically in the modal and double the gap between them
            buttons = (btn_pause_resume, btn_pause_settings, btn_pause_player_stats, btn_pause_to_menu)
            btn_count = len(buttons)
            spacing = 90  # doubled from ~45
            group_span = (btn_count - 1) * spacing
            # move buttons slightly lower so title sits above them comfortably
            first_center_y = modal_rect.centery - (group_span // 2) + 30
            for i, btn in enumerate(buttons):
                btn.rect.center = (modal_rect.centerx, int(first_center_y + i * spacing))

            # draw buttons and the optional title onto a temporary surface and fade them in
            btn_alpha = min(1.0, elapsed / PAUSE_BUTTON_FADE) if PAUSE_BUTTON_FADE > 0 else 1.0
            buttons_surf = pygame.Surface((modal_rect.width, modal_rect.height), pygame.SRCALPHA)

            # draw pause title (if available) above the buttons. Use uncropped half-size image by default.
            title_img = load_pause_menu_title_image()
            title_surf = None
            if title_img is not None:
                # prefer to show the title at half its original size (no cropping)
                title_surf = load_pause_menu_title_surface(None)
            if title_surf is not None:
                title_rect = title_surf.get_rect()
                # position title above the first button (half spacing above)
                title_center_y_local = int(first_center_y - (spacing // 2) - modal_rect.top - 30)
                title_rect.center = (modal_rect.width // 2, title_center_y_local)
                try:
                    buttons_surf.blit(title_surf, title_rect)
                except Exception:
                    pass

            # draw each button shifted to modal-local coords
            for btn in buttons:
                old_rect = btn.rect.copy()
                try:
                    btn.rect = btn.rect.move(-modal_rect.left, -modal_rect.top)
                    btn.draw(buttons_surf, font_button, enabled=True)
                finally:
                    btn.rect = old_rect

            try:
                buttons_surf.set_alpha(int(btn_alpha * 255))
            except Exception:
                pass
            screen.blit(buttons_surf, modal_rect.topleft)
        else:
            # reset animation when not paused
            pause_anim_start = None

        bg_frame = load_background_surface((logical_width, base_height))
        fill_color = (0, 0, 0)
        if bg_frame is not None:
            frame_surface.blit(bg_frame, (0, 0))
            try:
                fill_color = bg_frame.get_at((0, 0))[:3]
            except Exception:
                fill_color = (0, 0, 0)
        else:
            if not screen.get_locked():
                try:
                    fill_color = screen.get_at((0, 0))[:3]
                except Exception:
                    fill_color = (0, 0, 0)
            frame_surface.fill(fill_color)
        pad_x = (logical_width - base_width) // 2
        frame_surface.blit(screen, (pad_x, 0))
        win_w, win_h = window_surface.get_size()
        bg_window = load_background_surface((win_w, win_h))
        if bg_window is not None:
            window_surface.blit(bg_window, (0, 0))
            dim_overlay = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
            dim_overlay.fill((0, 0, 0, 120))
            window_surface.blit(dim_overlay, (0, 0))
        else:
            window_surface.fill(fill_color)
        scaled_surface = pygame.transform.smoothscale(frame_surface, render_size)
        window_surface.blit(scaled_surface, render_offset)
        pygame.display.flip()

    save_settings(settings)
    save_profiles(profiles_data)
    pygame.quit()
