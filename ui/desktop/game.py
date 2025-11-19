import os
import pygame

from config import (
    BOARD_COLS,
    BOARD_ROWS,
    CELL_SIZE,
    MARGIN_X,
    MARGIN_Y,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)
from core.engine.board import Board
from core.engine.types import Side, Move, PieceType

from data.localisation import TEXT, PIECE_BODY_THEMES, PIECE_SYMBOL_SETS, t
from data.themes import BOARD_THEMES, PIECE_THEMES
from core.settings_manager import Settings, load_settings, save_settings
from data.avatar_assets import ASSETS_DIR, BUILTIN_AVATARS, get_piece_sprite
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
    screen_to_board,
)
from data.avatar_assets import select_avatar_file_dialog


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
    pygame.display.set_caption("Xiangqi - Cờ Tướng")

    screen = pygame.Surface((base_width, base_height), pygame.SRCALPHA).convert_alpha()

    render_scale = 1.0
    render_size = (base_width, base_height)
    render_offset = (0, 0)
    frame_surface = pygame.Surface((logical_width, base_height), pygame.SRCALPHA).convert_alpha()

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
    font_piece = pygame.font.SysFont("SimHei", 28)
    font_text = pygame.font.SysFont("Consolas", 18)
    font_button = pygame.font.SysFont("Consolas", 16)
    font_title = pygame.font.SysFont("SimHei", 40, bold=True)
    font_avatar = pygame.font.SysFont("Consolas", 16, bold=True)
    font_timer = pygame.font.SysFont("Consolas", 24, bold=True)

    TIMER_CHOICES = [
        {"label": "1:00", "seconds": 60, "asset": os.path.join("avatars", "ai_soldier.jpg")},
        {"label": "5:00", "seconds": 300, "asset": os.path.join("avatars", "ai_casual.jpg")},
        {"label": "10:00", "seconds": 600, "asset": os.path.join("avatars", "ai_general.jpg")},
        {"label": "∞", "seconds": None, "asset": os.path.join("boards", "classic.png")},
    ]

    board = Board()
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

    state = "menu"
    mode = None
    ai_level_index = 1
    ai_match_started = False
    settings_return_state = "menu"
    settings_page = "main"

    timer_option_index = len(TIMER_CHOICES) - 1  # default unlimited
    time_remaining = {
        Side.RED: TIMER_CHOICES[timer_option_index]["seconds"],
        Side.BLACK: TIMER_CHOICES[timer_option_index]["seconds"],
    }
    timer_rects_current = {}
    timer_modal_open = False
    timer_thumbnail_cache = {}

    panel_x = MARGIN_X + BOARD_COLS * CELL_SIZE + 20

    btn_in_game_settings = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 153, 190, 30))
    btn_takeback = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 120, 190, 30))
    btn_resign = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 80, 90, 30))
    btn_new_game = Button(pygame.Rect(panel_x + 100, WINDOW_HEIGHT - 80, 90, 30))
    btn_ai_level = Button(pygame.Rect(panel_x + 30, MARGIN_Y + 95, 160, 28))
    btn_start_match = Button(pygame.Rect(panel_x + 30, MARGIN_Y + 130, 160, 28))
    btn_replay_prev = Button(pygame.Rect(panel_x, MARGIN_Y + 140, 40, 28))       # "<"
    btn_replay_next = Button(pygame.Rect(panel_x + 50, MARGIN_Y + 140, 40, 28))  # ">"

    center_x = WINDOW_WIDTH // 2
    start_y = WINDOW_HEIGHT // 2 - 80
    btn_menu_pvp = Button(pygame.Rect(center_x - 100, start_y, 200, 40))
    btn_menu_ai = Button(pygame.Rect(center_x - 100, start_y + 50, 200, 40))
    btn_menu_settings = Button(pygame.Rect(center_x - 100, start_y + 100, 200, 40))
    btn_menu_exit = Button(pygame.Rect(center_x - 100, start_y + 150, 200, 40))

    # log / captured box
    PANEL_MIN_LOG_TOP = MARGIN_Y + 160
    LOG_BOX_WIDTH = 220
    LOG_BOX_HEIGHT = 260

    btn_log_tab_moves = Button(pygame.Rect(panel_x, PANEL_MIN_LOG_TOP, 100, 24))
    btn_log_tab_captured = Button(pygame.Rect(panel_x + 110, PANEL_MIN_LOG_TOP, 100, 24))


    # Pause modal
    pause_center_x = WINDOW_WIDTH // 2
    pause_start_y = WINDOW_HEIGHT // 2 - 70
    btn_pause_resume = Button(pygame.Rect(pause_center_x - 100, pause_start_y, 200, 40))
    btn_pause_settings = Button(pygame.Rect(pause_center_x - 100, pause_start_y + 55, 200, 40))
    btn_pause_to_menu = Button(pygame.Rect(pause_center_x - 100, pause_start_y + 110, 200, 40))

    settings_center_x = WINDOW_WIDTH // 2
    settings_open_dropdown = None
    btn_settings_player_stats = Button(pygame.Rect(settings_center_x - 110, WINDOW_HEIGHT - 110, 220, 36))
    btn_settings_back = Button(pygame.Rect(settings_center_x - 110, WINDOW_HEIGHT - 65, 220, 36))

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
            return [{"value": idx, "text": entry["name"][lang]} for idx, entry in enumerate(entries)]

        board_options = make_theme_options(BOARD_THEMES)
        body_options = make_theme_options(PIECE_BODY_THEMES)
        symbol_options = make_theme_options(PIECE_SYMBOL_SETS)
        color_options = make_theme_options(PIECE_THEMES)

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
            "piece_symbol_color": {
                "label": t(settings, "settings_label_piece_symbol_color"),
                "value": settings.piece_theme_index % len(PIECE_THEMES) if PIECE_THEMES else 0,
                "options": color_options,
                "enabled": bool(color_options),
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

        for item in items.values():
            item["selected_label"] = current_label(item["options"], item["value"])

        return items

    def build_settings_layout():
        items = build_settings_items()
        row_width = 520
        dropdown_width = 230
        start_x = (WINDOW_WIDTH - row_width) // 2
        start_y = 130
        row_height = 40
        gap_y = 8
        section_gap = 10
        headers = []
        rows = []
        options = []

        sections = [
            ("appearance", t(settings, "settings_section_appearance"), ["board_theme", "piece_body", "piece_symbols", "piece_symbol_color"]),
            ("display", t(settings, "settings_section_display"), ["display_mode", "resolution"]),
            ("general", t(settings, "settings_section_general"), ["language"]),
        ]

        y = start_y
        for _, title, keys in sections:
            headers.append({"title": title, "pos": (start_x, y)})
            y += 28
            for key in keys:
                item = items[key]
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
                    }
                )

                if settings_open_dropdown == key and item["enabled"]:
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
        elif key == "piece_body" and PIECE_BODY_THEMES:
            settings.piece_body_theme_index = int(value) % len(PIECE_BODY_THEMES)
        elif key == "piece_symbols" and PIECE_SYMBOL_SETS:
            settings.piece_symbol_set_index = int(value) % len(PIECE_SYMBOL_SETS)
        elif key == "piece_symbol_color":
            settings.piece_theme_index = int(value) % len(PIECE_THEMES)
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
            settings.language = value

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
        if state == "ai":
            return not ai_match_started
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

    def to_game_coords(pos):
        if render_scale <= 0:
            return 0, 0, False
        lx = (pos[0] - render_offset[0]) / render_scale
        ly = (pos[1] - render_offset[1]) / render_scale
        logical_pad_x = (logical_width - base_width) / 2
        gx = lx - logical_pad_x
        inside = 0 <= gx <= base_width and 0 <= ly <= base_height
        return int(gx), int(ly), inside

    def reset_game():
        nonlocal current_side, selected, valid_moves, move_history, redo_stack, hovered_move
        nonlocal in_check_side, game_over, winner, result_recorded, replay_index, paused, ai_match_started, timer_modal_open
        board.reset()
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
        timer_modal_open = False
        loss_badge_anim_start = None
        loss_badge_side = None
        reset_timers_to_full()

    def update_hover_preview(mx, my, inside):
        nonlocal hovered_move
        if not inside:
            hovered_move = None
            return
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
        nonlocal result_recorded
        if result_recorded:
            return
        if mode not in ("pvp", "ai"):
            return
        apply_game_result_to_profiles(profiles_data, mode, winner_side, is_draw, ai_level_index)
        result_recorded = True

    def start_loss_badge_animation(loser_side):
        nonlocal loss_badge_anim_start, loss_badge_side
        if loser_side not in (Side.RED, Side.BLACK):
            return
        loss_badge_side = loser_side
        loss_badge_anim_start = pygame.time.get_ticks()

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

        board.reset()
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
                    start_loss_badge_animation(current_side)
                    register_result_if_needed(winner_side, False)
                    replay_index = len(move_history)
            else:
                in_check_side = None
                if not result_recorded:
                    game_over = False
                    winner = None

    def switch_to_menu():
        nonlocal state, selected, valid_moves, in_check_side, game_over, winner, result_recorded, ai_match_started, hovered_move
        state = "menu"
        selected = None
        valid_moves = []
        hovered_move = None
        in_check_side = None
        game_over = False
        winner = None
        result_recorded = False
        ai_match_started = False

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
        return len(move_history) > 0

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
        start_loss_badge_animation(side)
        register_result_if_needed(winner_side, False)
        replay_index = len(move_history)

    def ai_make_move():
        nonlocal current_side, move_history, redo_stack, game_over, winner
        nonlocal in_check_side, selected, valid_moves, hovered_move
        nonlocal log_follow_latest
        if game_over or current_side != AI_SIDE or not ai_match_started:
            return
        level_cfg = AI_LEVELS[ai_level_index]
        mv = choose_ai_move(board, level_cfg, AI_SIDE)
        if mv is None:
            if board.is_in_check(AI_SIDE):
                game_over = True
                winner = HUMAN_SIDE
                start_loss_badge_animation(AI_SIDE)
                register_result_if_needed(HUMAN_SIDE, False)
                replay_index = len(move_history)
            else:
                game_over = True
                winner = None
                register_result_if_needed(None, True)
                replay_index = len(move_history)
            in_check_side = None
            return

        board.move_piece(mv)
        move_history.append(mv)
        redo_stack.clear()
        log_follow_latest = True
        selected = None
        valid_moves = []
        hovered_move = None

        current_side = HUMAN_SIDE
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
                    if timer_modal_open:
                        timer_modal_open = False
                    elif state == "settings":
                        settings_open_dropdown = None
                        if settings_page == "stats":
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

                # Scroll move log with wheel
                if btn in (4, 5) and state in ("pvp", "ai") and log_active_tab == "moves" and log_box_rect_current is not None:
                    if log_box_rect_current.collidepoint(mx, my):
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
                    continue

                if state in ("pvp", "ai"):
                    bottom_rect = get_bottom_avatar_rect()
                    top_rect = get_top_avatar_rect()
                    clicked_avatar = False
                
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
                                current = avatar.get("path")
                                if current in BUILTIN_AVATARS:
                                    idx = BUILTIN_AVATARS.index(current)
                                    idx = (idx + 1) % len(BUILTIN_AVATARS)
                                else:
                                    idx = 0
                                avatar["type"] = "image"
                                avatar["path"] = BUILTIN_AVATARS[idx]
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
                                current = avatar.get("path")
                                if current in BUILTIN_AVATARS:
                                    idx = BUILTIN_AVATARS.index(current)
                                    idx = (idx + 1) % len(BUILTIN_AVATARS)
                                else:
                                    idx = 0
                                avatar["type"] = "image"
                                avatar["path"] = BUILTIN_AVATARS[idx]
                                save_profiles(profiles_data)
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
                        settings_open_dropdown = None
                        state = "settings"
                        continue
                    if btn_menu_exit.is_clicked((mx, my)):
                        running = False
                        continue
                
                elif state == "settings":
                    if settings_page == "main":
                        layout = build_settings_layout()

                        option_clicked = False
                        for opt in layout["options"]:
                            if opt["rect"].collidepoint(mx, my):
                                apply_setting_selection(opt["key"], opt["value"])
                                settings_open_dropdown = None
                                option_clicked = True
                                break
                        if option_clicked:
                            continue

                        if btn_settings_player_stats.is_clicked((mx, my)):
                            settings_page = "stats"
                            settings_open_dropdown = None
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

                        if btn_pause_to_menu.is_clicked((mx, my)):
                            reset_game()
                            switch_to_menu()
                            paused = False
                            continue
                        continue

                    ai_input_locked = state == "ai" and not ai_match_started

                    if btn_log_tab_moves.is_clicked((mx, my)):
                        log_active_tab = "moves"
                        continue
                    if btn_log_tab_captured.is_clicked((mx, my)):
                        log_active_tab = "captured"
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
                    # Start match (AI only)
                    if state == "ai" and not ai_match_started and btn_start_match.is_clicked((mx, my)):
                        ai_match_started = True
                        continue
                    # AI level change
                    if state == "ai" and not ai_match_started and btn_ai_level.is_clicked((mx, my)):
                        ai_level_index = (ai_level_index + 1) % len(AI_LEVELS)
                        continue
                    # Takeback clicked
                    if btn_takeback.is_clicked((mx, my)):
                        if ai_input_locked:
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
                        if ai_input_locked:
                            continue
                        if not game_over:
                            game_over = True
                            winner_side = Side.RED if current_side == Side.BLACK else Side.BLACK
                            winner = winner_side
                            in_check_side = None
                            selected = None
                            valid_moves = []
                            start_loss_badge_animation(current_side)
                            register_result_if_needed(winner_side, False)
                            replay_index = len(move_history)
                        continue
                    # New game clicked
                    if btn_new_game.is_clicked((mx, my)):
                        reset_game()
                        continue

                    if state == "ai" and not ai_match_started:
                        continue
                    
                    if game_over:
                        continue
                    
                    # AI move turn
                    if state == "ai" and current_side == AI_SIDE:
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

        if state == "ai" and ai_match_started and not game_over and not paused and current_side == AI_SIDE:
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
        

        # MENU SCREEN
        if state == "menu":
            screen.fill((40, 40, 60))
            title_surf = font_title.render(lang_text["title"], True, (250, 250, 250))
            title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 140))
            screen.blit(title_surf, title_rect)

            sub_surf = font_text.render(lang_text["subtitle"], True, (220, 220, 220))
            sub_rect = sub_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 110))
            screen.blit(sub_surf, sub_rect)

            btn_menu_pvp.label = lang_text["menu_pvp"]
            btn_menu_ai.label = lang_text["menu_ai"]
            btn_menu_settings.label = lang_text["menu_settings"]
            btn_menu_exit.label = lang_text["menu_exit"]

            btn_menu_pvp.draw(screen, font_button, enabled=True)
            btn_menu_ai.draw(screen, font_button, enabled=True)
            btn_menu_settings.draw(screen, font_button, enabled=True)
            btn_menu_exit.draw(screen, font_button, enabled=True)

        elif state in ("pvp", "ai"):
            draw_board(screen, settings)
            if mode is not None:
                loser_side = None
                badge_scale = 1.0
                if game_over and winner in (Side.RED, Side.BLACK):
                    loser_side = Side.BLACK if winner == Side.RED else Side.RED
                    if loss_badge_anim_start is None or loss_badge_side != loser_side:
                        start_loss_badge_animation(loser_side)
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
                )

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

            mode_text = lang_text["mode_pvp"] if mode == "pvp" else lang_text["mode_ai"]
            mt_surf = font_text.render(mode_text, True, (0, 0, 0))
            screen.blit(mt_surf, (panel_x, MARGIN_Y))

            turn_text = lang_text["turn_red"] if current_side == Side.RED else lang_text["turn_black"]
            tt_surf = font_text.render(turn_text, True, (0, 0, 0))
            screen.blit(tt_surf, (panel_x, MARGIN_Y + 20))

            y_info = MARGIN_Y + 45
            if in_check_side is not None and not game_over:
                msg = lang_text["check_on_red"] if in_check_side == Side.RED else lang_text["check_on_black"]
                ck_surf = font_text.render(msg, True, (200, 0, 0))
                screen.blit(ck_surf, (panel_x, y_info))
                y_info += 25

            if game_over and winner is not None:
                if winner == Side.RED:
                    msg = lang_text["red_wins"]
                elif winner == Side.BLACK:
                    msg = lang_text["black_wins"]
                else:
                    msg = lang_text["game_over"]
                win_surf = font_text.render(msg, True, (0, 0, 200))
                screen.blit(win_surf, (panel_x, y_info))
                y_info += 25

            if mode == "ai" and not ai_match_started:
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
                    center = (panel_x + small_size // 2 + 4, y_players + small_size // 2)
                    draw_profile_avatar(screen, red_player, center, small_size, font_avatar)
                    label = t(settings, "label_red_player").format(name=red_player.get("display_name", "Player 1"))
                    color = (200, 0, 0) if current_side == Side.RED else (0, 0, 0)
                    txt = font_text.render(label, True, color)
                    screen.blit(txt, (panel_x + small_size + 8, y_players))
                    y_players += small_size + 6

                if black_player:
                    center = (panel_x + small_size // 2 + 4, y_players + small_size // 2)
                    draw_profile_avatar(screen, black_player, center, small_size, font_avatar)
                    label = t(settings, "label_black_player").format(name=black_player.get("display_name", "Player 2"))
                    color = (0, 0, 200) if current_side == Side.BLACK else (0, 0, 0)
                    txt = font_text.render(label, True, color)
                    screen.blit(txt, (panel_x + small_size + 8, y_players))
                    y_players += small_size + 6

            else:
                human_id = ai_info.get("human_player_id", "p1")
                human_player = find_player(profiles_data, human_id)
                if human_player:
                    center = (panel_x + small_size // 2 + 4, y_players + small_size // 2)
                    draw_profile_avatar(screen, human_player, center, small_size, font_avatar)
                    label = t(settings, "label_red_player").format(
                        name=human_player.get("display_name", "Player 1")
                    )
                    color = (200, 0, 0) if current_side == Side.RED else (0, 0, 0)
                    txt = font_text.render(label, True, color)
                    screen.blit(txt, (panel_x + small_size + 8, y_players))
                    y_players += small_size + 6

                ai_cfg = AI_LEVELS[ai_level_index]
                center = (panel_x + small_size // 2 + 4, y_players + small_size // 2)
                draw_ai_avatar(screen, ai_cfg, center, small_size, font_avatar)
                label = t(settings, "label_ai_player").format(name=ai_cfg["name"])
                color = (0, 0, 200) if current_side == Side.BLACK else (0, 0, 0)
                txt = font_text.render(label, True, color)
                screen.blit(txt, (panel_x + small_size + 8, y_players))
                y_players += small_size + 6

            panel_log_top = max(PANEL_MIN_LOG_TOP, y_players + 10)

            # AI controls
            if state == "ai":
                level_cfg = AI_LEVELS[ai_level_index]
                btn_ai_level.label = f"AI: {level_cfg['name']}"

                btn_ai_level.rect.topleft = (panel_x + 10, panel_log_top)
                btn_ai_level.draw(screen, font_button, enabled=not ai_match_started)
                panel_log_top += 35

                btn_start_match.label = lang_text["match_started"] if ai_match_started else lang_text["btn_start_match"]
                btn_start_match.rect.topleft = (panel_x + 10, panel_log_top)
                btn_start_match.draw(screen, font_button, enabled=not ai_match_started)
                panel_log_top += 35

            btn_replay_prev.label = "<"
            btn_replay_next.label = ">"
            if game_over and move_history:
                current_idx = len(move_history) if replay_index is None else replay_index
                enabled_prev = current_idx > 0
                enabled_next = current_idx < len(move_history)
            else:
                enabled_prev = False
                enabled_next = False

            btn_replay_prev.draw(screen, font_button, enabled=enabled_prev)
            btn_replay_next.draw(screen, font_button, enabled=enabled_next)

            log_box_rect = pygame.Rect(panel_x, panel_log_top + 30, LOG_BOX_WIDTH, LOG_BOX_HEIGHT)
            log_box_rect_current = log_box_rect

            btn_log_tab_moves.rect = pygame.Rect(log_box_rect.x, log_box_rect.y - 26, 100, 24)
            btn_log_tab_captured.rect = pygame.Rect(log_box_rect.x + 110, log_box_rect.y - 26, 100, 24)

            # Label tabs
            btn_log_tab_moves.label = t(settings, "tab_moves")
            btn_log_tab_captured.label = t(settings, "tab_captured")

            btn_log_tab_moves.draw(screen, font_button, enabled=(log_active_tab == "moves"))
            btn_log_tab_captured.draw(screen, font_button, enabled=(log_active_tab == "captured"))

            pygame.draw.rect(screen, (235, 235, 235), log_box_rect)
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
                    text_line = f"{i + 1}. {mv}"
                    mv_surf = font_text.render(text_line, True, (0, 0, 0))
                    screen.blit(mv_surf, (log_box_rect.x + inner_margin_x, y_text))
                    y_text += line_height

                if view_index == 0:
                    empty_txt = "(no moves)" if settings.language == "en" else "(chưa có nước đi)"
                    et_surf = font_text.render(empty_txt, True, (120, 120, 120))
                    et_rect = et_surf.get_rect(center=log_box_rect.center)
                    screen.blit(et_surf, et_rect)

            else:
                # Tab Captured: thống kê quân bị ăn, dùng PNG icon + số lượng
                captured_by_red_counts = {} # RED ăn được quân của BLACK
                captured_by_black_counts = {} # BLACK ăn được quân của RED

                for mv in move_history[:view_index]:
                    if mv.captured is not None:
                        mover_side = mv.piece.side
                        pt = mv.captured.ptype
                        if mover_side == Side.RED:
                            captured_by_red_counts[pt] = captured_by_red_counts.get(pt, 0) + 1
                        else:
                            captured_by_black_counts[pt] = captured_by_black_counts.get(pt, 0) + 1

                if settings.language == "en":
                    red_label = "RED captured:"
                    black_label = "BLACK captured:"
                else:
                    red_label = "ĐỎ ăn được:"
                    black_label = "ĐEN ăn được:"

                piece_order = [
                    PieceType.GENERAL,
                    PieceType.ROOK,
                    PieceType.CANNON,
                    PieceType.HORSE,
                    PieceType.ELEPHANT,
                    PieceType.ADVISOR,
                    PieceType.SOLDIER,
                ]

                small_size = 26

                class _DummyPiece:
                    def __init__(self, side, ptype):
                        self.side = side
                        self.ptype = ptype

                def piece_label_text(ptype):
                    if settings.language == "en":
                        names = {
                            PieceType.GENERAL: "Gen",
                            PieceType.ROOK: "Rook",
                            PieceType.CANNON: "Cannon",
                            PieceType.HORSE: "Horse",
                            PieceType.ELEPHANT: "Elephant",
                            PieceType.ADVISOR: "Advisor",
                            PieceType.SOLDIER: "Soldier",
                        }
                    else:
                        names = {
                            PieceType.GENERAL: "Tướng",
                            PieceType.ROOK: "Xe",
                            PieceType.CANNON: "Pháo",
                            PieceType.HORSE: "Mã",
                            PieceType.ELEPHANT: "Tượng",
                            PieceType.ADVISOR: "Sĩ",
                            PieceType.SOLDIER: "Tốt",
                        }
                    return names.get(ptype, "?")

                y_text = log_box_rect.y + inner_margin_y

                # RED captured
                red_surf = font_text.render(red_label, True, (160, 0, 0))
                screen.blit(red_surf, (log_box_rect.x + inner_margin_x, y_text))
                y_text += line_height

                x_icon = log_box_rect.x + inner_margin_x
                max_x = log_box_rect.x + log_box_rect.width - inner_margin_x

                for pt in piece_order:
                    count = captured_by_red_counts.get(pt, 0)
                    if count <= 0:
                        continue

                    dummy_piece = _DummyPiece(Side.BLACK, pt)  # RED cap BLACK
                    icon = get_piece_sprite(dummy_piece, settings, small_size)
                    if icon is None:
                        icon_text = piece_label_text(pt)
                        icon = font_text.render(icon_text, True, (0, 0, 0))
                    icon_rect = icon.get_rect(topleft=(x_icon, y_text))
                    if icon_rect.right > max_x:
                        x_icon = log_box_rect.x + inner_margin_x
                        y_text += line_height
                        icon_rect.topleft = (x_icon, y_text)
                    screen.blit(icon, icon_rect.topleft)
                    x_icon = icon_rect.right + 4

                    cnt_txt = f"x{count}"
                    cnt_surf = font_text.render(cnt_txt, True, (0, 0, 0))
                    cnt_rect = cnt_surf.get_rect(midleft=(x_icon, y_text + icon_rect.height / 2 - 2))
                    if cnt_rect.right > max_x:
                        x_icon = log_box_rect.x + inner_margin_x
                        y_text += line_height
                        cnt_rect.midleft = (x_icon, y_text + icon_rect.height / 2 - 2)
                    screen.blit(cnt_surf, cnt_rect.topleft)
                    x_icon = cnt_rect.right + 8

                y_text += line_height + 6

                # BLACK captured
                black_surf = font_text.render(black_label, True, (0, 0, 160))
                screen.blit(black_surf, (log_box_rect.x + inner_margin_x, y_text))
                y_text += line_height

                x_icon = log_box_rect.x + inner_margin_x
                for pt in piece_order:
                    count = captured_by_black_counts.get(pt, 0)
                    if count <= 0:
                        continue

                    dummy_piece = _DummyPiece(Side.RED, pt)  # BLACK cap RED
                    icon = get_piece_sprite(dummy_piece, settings, small_size)
                    if icon is None:
                        icon_text = piece_label_text(pt)
                        icon = font_text.render(icon_text, True, (0, 0, 0))
                    icon_rect = icon.get_rect(topleft=(x_icon, y_text))
                    if icon_rect.right > max_x:
                        x_icon = log_box_rect.x + inner_margin_x
                        y_text += line_height
                        icon_rect.topleft = (x_icon, y_text)
                    screen.blit(icon, icon_rect.topleft)
                    x_icon = icon_rect.right + 4

                    cnt_txt = f"x{count}"
                    cnt_surf = font_text.render(cnt_txt, True, (0, 0, 0))
                    cnt_rect = cnt_surf.get_rect(midleft=(x_icon, y_text + icon_rect.height / 2 - 2))
                    if cnt_rect.right > max_x:
                        x_icon = log_box_rect.x + inner_margin_x
                        y_text += line_height
                        cnt_rect.midleft = (x_icon, y_text + icon_rect.height / 2 - 2)
                    screen.blit(cnt_surf, cnt_rect.topleft)
                    x_icon = cnt_rect.right + 8

                if not captured_by_red_counts and not captured_by_black_counts:
                    empty_txt = "(no captured pieces)" if settings.language == "en" else "(chưa ăn được quân nào)"
                    et_surf = font_text.render(empty_txt, True, (120, 120, 120))
                    et_rect = et_surf.get_rect(center=log_box_rect.center)
                    screen.blit(et_surf, et_rect)

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

                if settings.language == "en":
                    red_label = "RED captured:"
                    black_label = "BLACK captured:"
                else:
                    red_label = "ĐỎ ăn được:"
                    black_label = "ĐEN ăn được:"

                y_text = log_box_rect.y + inner_margin_y
                red_surf = font_text.render(red_label, True, (160, 0, 0))
                screen.blit(red_surf, (log_box_rect.x + inner_margin_x, y_text))
                y_text += line_height

                x_icon = log_box_rect.x + inner_margin_x
                max_x = log_box_rect.x + log_box_rect.width - inner_margin_x

                for p in captured_by_red_counts:
                    ch = piece_char_for_display(p, Side.BLACK)
                    icon_surf = font_text.render(ch, True, (0, 0, 0))
                    ir = icon_surf.get_rect(topleft=(x_icon, y_text))
                    if ir.right > max_x:
                        x_icon = log_box_rect.x + inner_margin_x
                        y_text += line_height
                        ir.topleft = (x_icon, y_text)
                    screen.blit(icon_surf, ir.topleft)
                    x_icon = ir.right + 5

                y_text += line_height + 5
                black_surf = font_text.render(black_label, True, (0, 0, 160))
                screen.blit(black_surf, (log_box_rect.x + inner_margin_x, y_text))
                y_text += line_height

                x_icon = log_box_rect.x + inner_margin_x
                for p in captured_by_black_counts:
                    ch = piece_char_for_display(p, Side.RED)
                    icon_surf = font_text.render(ch, True, (0, 0, 0))
                    ir = icon_surf.get_rect(topleft=(x_icon, y_text))
                    if ir.right > max_x:
                        x_icon = log_box_rect.x + inner_margin_x
                        y_text += line_height
                        ir.topleft = (x_icon, y_text)
                    screen.blit(icon_surf, ir.topleft)
                    x_icon = ir.right + 5

                if not captured_by_red_counts and not captured_by_black_counts:
                    empty_txt = "(no captured pieces)" if settings.language == "en" else "(chưa ăn được quân nào)"
                    et_surf = font_text.render(empty_txt, True, (120, 120, 120))
                    et_rect = et_surf.get_rect(center=log_box_rect.center)
                    screen.blit(et_surf, et_rect)


            btn_in_game_settings.label = lang_text["btn_settings_in_game"]
            btn_takeback.label = lang_text["btn_takeback"]
            btn_resign.label = lang_text["btn_resign"]
            btn_new_game.label = lang_text["btn_new_game"]

            btn_in_game_settings.draw(screen, font_button, enabled=True)
            btn_takeback.draw(screen, font_button, enabled=bool(move_history))
            btn_resign.draw(screen, font_button, enabled=not game_over)
            btn_new_game.draw(screen, font_button, enabled=True)
            btn_replay_prev.draw(screen, font_button, enabled=enabled_prev)
            btn_replay_next.draw(screen, font_button, enabled=enabled_next)
        # SETTING MENU 
        elif state == "settings":
            screen.fill((50, 40, 40))

            if settings_page == "main":
                layout = build_settings_layout()

                title_surf = font_title.render(t(settings, "settings_title"), True, (240, 240, 240))
                title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 120))
                screen.blit(title_surf, title_rect)

                header_color = (215, 205, 205)
                for header in layout["headers"]:
                    header_surf = font_button.render(header["title"], True, header_color)
                    screen.blit(header_surf, header["pos"])

                for row in layout["rows"]:
                    base_color = (90, 80, 80) if row["enabled"] else (70, 70, 70)
                    border_color = (40, 40, 40)
                    pygame.draw.rect(screen, base_color, row["rect"], border_radius=8)
                    pygame.draw.rect(screen, border_color, row["rect"], 2, border_radius=8)

                    label_surf = font_text.render(row["label"], True, (235, 235, 235))
                    label_rect = label_surf.get_rect(midleft=(row["rect"].x + 14, row["rect"].centery))
                    screen.blit(label_surf, label_rect)

                    value_rect = row["value_rect"]
                    value_color = (230, 230, 230) if row["enabled"] else (150, 150, 150)
                    pygame.draw.rect(screen, value_color, value_rect, border_radius=6)
                    pygame.draw.rect(screen, border_color, value_rect, 2, border_radius=6)

                    value_surf = font_button.render(row["value_text"], True, (0, 0, 0))
                    value_surf_rect = value_surf.get_rect(midleft=(value_rect.x + 10, value_rect.centery))
                    screen.blit(value_surf, value_surf_rect)

                    arrow_x = value_rect.right - 16
                    arrow_y = value_rect.centery
                    if settings_open_dropdown == row["key"]:
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
                    opt_surf = font_button.render(opt["text"], True, (0, 0, 0))
                    opt_rect = opt_surf.get_rect(midleft=(opt["rect"].x + 10, opt["rect"].centery))
                    screen.blit(opt_surf, opt_rect)

                dropdown_bottom = layout["content_bottom"]
                if layout["options"]:
                    dropdown_bottom = max(dropdown_bottom, max(opt["rect"].bottom for opt in layout["options"]))

                footer_top = max(dropdown_bottom + 30, WINDOW_HEIGHT - 140)
                footer_top = min(footer_top, WINDOW_HEIGHT - 70)

                btn_settings_player_stats.rect.center = (settings_center_x, footer_top)
                btn_settings_back.rect.center = (settings_center_x, footer_top + 45)

                btn_settings_player_stats.label = t(settings, "settings_player_stats")
                btn_settings_back.label = t(settings, "btn_back")

                btn_settings_player_stats.draw(screen, font_button, enabled=True)
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

            # Modal
            modal_width = 360
            modal_height = 220
            modal_rect = pygame.Rect(0, 0, modal_width, modal_height)
            modal_rect.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

            pygame.draw.rect(screen, (240, 240, 240), modal_rect, border_radius=8)
            pygame.draw.rect(screen, (60, 60, 60), modal_rect, 2, border_radius=8)

            title_text = lang_text["paused"]
            resume_text = lang_text["resume"]
            to_menu_text = lang_text["main_menu"]

            title_surf = font_title.render(title_text, True, (20, 20, 20))
            title_rect = title_surf.get_rect(center=(modal_rect.centerx, modal_rect.top + 45))
            screen.blit(title_surf, title_rect)

            # Pause buttons label
            lang_text = TEXT[settings.language]
            btn_pause_resume.label = resume_text
            btn_pause_settings.label = lang_text["menu_settings"]
            btn_pause_to_menu.label = to_menu_text

            btn_pause_resume.rect.center = (modal_rect.centerx, modal_rect.top + 95)
            btn_pause_settings.rect.center = (modal_rect.centerx, modal_rect.top + 140)
            btn_pause_to_menu.rect.center = (modal_rect.centerx, modal_rect.top + 185)

            btn_pause_resume.draw(screen, font_button, enabled=True)
            btn_pause_settings.draw(screen, font_button, enabled=True)
            btn_pause_to_menu.draw(screen, font_button, enabled=True)


        fill_color = (0, 0, 0)
        if not screen.get_locked():
            try:
                fill_color = screen.get_at((0, 0))[:3]
            except Exception:
                fill_color = (0, 0, 0)
        frame_surface.fill(fill_color)
        pad_x = (logical_width - base_width) // 2
        frame_surface.blit(screen, (pad_x, 0))
        window_surface.fill(fill_color)
        scaled_surface = pygame.transform.smoothscale(frame_surface, render_size)
        window_surface.blit(scaled_surface, render_offset)
        pygame.display.flip()

    save_settings(settings)
    save_profiles(profiles_data)
    pygame.quit()
