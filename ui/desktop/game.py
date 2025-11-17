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
from data.avatar_assets import BUILTIN_AVATARS, get_piece_sprite
from core.profiles_manager import load_profiles, save_profiles, find_player, apply_game_result_to_profiles
from core.engine.constants import AI_SIDE, HUMAN_SIDE
from core.engine.ai_engine import AI_LEVELS, choose_ai_move
from core.ui_components import Button
from core.engine.draw_helpers import (
    draw_board,
    draw_selection,
    draw_move_hints,
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

    flags = pygame.FULLSCREEN if settings.display_mode == "fullscreen" else 0
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
    pygame.display.set_caption("Xiangqi - Cờ Tướng")

    clock = pygame.time.Clock()
    font_piece = pygame.font.SysFont("SimHei", 28)
    font_text = pygame.font.SysFont("Consolas", 18)
    font_button = pygame.font.SysFont("Consolas", 16)
    font_title = pygame.font.SysFont("SimHei", 40, bold=True)
    font_avatar = pygame.font.SysFont("Consolas", 16, bold=True)

    board = Board()
    current_side = Side.RED
    selected = None
    valid_moves = []
    move_history = []
    redo_stack = []
    in_check_side = None
    game_over = False
    winner = None
    result_recorded = False
    replay_index = None
    paused = False 

    # Log (replay/tabs)
    log_active_tab = "moves"   # Moves or Captured
    move_log_offset = 0        # index of first move currently displayed in log
    log_box_rect_current = None  # rect of the log box for handling mouse scroll
    log_follow_latest = True

    state = "menu"
    mode = None
    ai_level_index = 1
    settings_return_state = "menu"
    settings_page = "main"

    panel_x = MARGIN_X + BOARD_COLS * CELL_SIZE + 20

    btn_in_game_settings = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 153, 190, 30))
    btn_takeback = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 120, 190, 30))
    btn_resign = Button(pygame.Rect(panel_x, WINDOW_HEIGHT - 80, 90, 30))
    btn_new_game = Button(pygame.Rect(panel_x + 100, WINDOW_HEIGHT - 80, 90, 30))
    btn_ai_level = Button(pygame.Rect(panel_x + 30, MARGIN_Y + 95, 160, 28))
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
    btn_settings_board_theme = Button(pygame.Rect(settings_center_x - 160, 200, 320, 36))
    btn_settings_piece_body = Button(pygame.Rect(settings_center_x - 160, 245, 320, 36))
    btn_settings_piece_icons = Button(pygame.Rect(settings_center_x - 160, 290, 320, 36))
    btn_settings_piece_theme = Button(pygame.Rect(settings_center_x - 160, 335, 320, 36))  
    btn_settings_display = Button(pygame.Rect(settings_center_x - 160, 380, 320, 36))
    btn_settings_language = Button(pygame.Rect(settings_center_x - 160, 425, 320, 36))
    btn_settings_player_stats = Button(pygame.Rect(settings_center_x - 160, 470, 320, 36))
    btn_settings_back = Button(pygame.Rect(settings_center_x - 80, WINDOW_HEIGHT - 100, 160, 40))

    def apply_display_mode():
        nonlocal screen
        if settings.display_mode == "fullscreen":
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN)
        else:
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

    def reset_game():
        nonlocal current_side, selected, valid_moves, move_history, redo_stack
        nonlocal in_check_side, game_over, winner, result_recorded, replay_index, paused
        board.reset()
        current_side = Side.RED
        selected = None
        valid_moves = []
        move_history = []
        redo_stack = []
        in_check_side = None
        game_over = False
        winner = None
        result_recorded = False
        replay_index = None
        paused = False

    def register_result_if_needed(winner_side, is_draw=False):
        nonlocal result_recorded
        if result_recorded:
            return
        if mode not in ("pvp", "ai"):
            return
        apply_game_result_to_profiles(profiles_data, mode, winner_side, is_draw)
        result_recorded = True

    def rebuild_position_from_replay_index():
        nonlocal current_side, in_check_side
        if replay_index is None:
            return

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
                    register_result_if_needed(winner_side, False)
                    replay_index = len(move_history)
        else:
            in_check_side = None
            if not result_recorded:
                game_over = False
                winner = None

    def switch_to_menu():
        nonlocal state, selected, valid_moves, in_check_side, game_over, winner, result_recorded
        state = "menu"
        selected = None
        valid_moves = []
        in_check_side = None
        game_over = False
        winner = None
        result_recorded = False

    def ai_make_move():
        nonlocal current_side, move_history, redo_stack, game_over, winner
        nonlocal in_check_side, selected, valid_moves
        nonlocal log_follow_latest
        if game_over or current_side != AI_SIDE:
            return
        level_cfg = AI_LEVELS[ai_level_index]
        mv = choose_ai_move(board, level_cfg, AI_SIDE)
        if mv is None:
            if board.is_in_check(AI_SIDE):
                game_over = True
                winner = HUMAN_SIDE
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
                    if state == "settings":
                        if settings_page == "stats":
                            settings_page = "main"
                        else:
                            state = settings_return_state
                    elif state in ("pvp", "ai"):
                        paused = not paused
            # Choose avatar logic
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                btn = event.button

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
                        state = "settings"
                        continue
                    if btn_menu_exit.is_clicked((mx, my)):
                        running = False
                        continue
                
                elif state == "settings":
                    if settings_page == "main":
                        if btn_settings_board_theme.is_clicked((mx, my)):
                            settings.board_theme_index = (settings.board_theme_index + 1) % len(BOARD_THEMES)
                            save_settings(settings)
                            continue
                        if btn_settings_piece_body.is_clicked((mx, my)) and PIECE_BODY_THEMES:
                            settings.piece_body_theme_index = (settings.piece_body_theme_index + 1) % len(PIECE_BODY_THEMES)
                            save_settings(settings)
                            continue
                        if btn_settings_piece_icons.is_clicked((mx, my)) and PIECE_SYMBOL_SETS:
                            settings.piece_symbol_set_index = (settings.piece_symbol_set_index + 1) % len(PIECE_SYMBOL_SETS)
                            save_settings(settings)
                            continue
                        if btn_settings_piece_theme.is_clicked((mx, my)):
                            settings.piece_theme_index = (settings.piece_theme_index + 1) % len(PIECE_THEMES)
                            save_settings(settings)
                            continue
                        if btn_settings_display.is_clicked((mx, my)):
                            settings.display_mode = "fullscreen" if settings.display_mode == "window" else "window"
                            apply_display_mode()
                            save_settings(settings)
                            continue
                        if btn_settings_language.is_clicked((mx, my)):
                            settings.language = "en" if settings.language == "vi" else "vi"
                            save_settings(settings)
                            continue
                        if btn_settings_player_stats.is_clicked((mx, my)):
                            settings_page = "stats"
                            continue
                        if btn_settings_back.is_clicked((mx, my)):
                            state = settings_return_state
                            settings_page = "main"
                            continue
                    else:
                        if btn_settings_back.is_clicked((mx, my)):
                            settings_page = "main"
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
                            state = "settings"
                            continue

                        if btn_pause_to_menu.is_clicked((mx, my)):
                            reset_game()
                            switch_to_menu()
                            paused = False
                            continue
                        continue
            
                    # Setting button clicked
                    if btn_in_game_settings.is_clicked((mx, my)):
                        settings_return_state = state
                        settings_page = "main"
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
                    # AI level change
                    if state == "ai" and btn_ai_level.is_clicked((mx, my)):
                        ai_level_index = (ai_level_index + 1) % len(AI_LEVELS)
                        continue
                    # Takeback clicked
                    if btn_takeback.is_clicked((mx, my)):
                        if move_history:
                            steps = min(2, len(move_history))
                            for _ in range(steps):
                                last_move = move_history.pop()
                                board.undo_move(last_move)
                                redo_stack.append(last_move)
                                current_side = Side.RED if current_side == Side.BLACK else Side.BLACK
                                log_follow_latest = True
                            update_game_state_after_side_change()
                        continue
                    # Resign clicked
                    if btn_resign.is_clicked((mx, my)):
                        if not game_over:
                            game_over = True
                            winner_side = Side.RED if current_side == Side.BLACK else Side.BLACK
                            winner = winner_side
                            in_check_side = None
                            selected = None
                            valid_moves = []
                            register_result_if_needed(winner_side, False)
                            replay_index = len(move_history)
                        continue
                    # New game clicked
                    if btn_new_game.is_clicked((mx, my)):
                        reset_game()
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
                        else:
                            sel_c, sel_r = selected
                            if col == sel_c and row == sel_r:
                                selected = None
                                valid_moves = []
                            else:
                                if piece is not None and piece.side == current_side:
                                    selected = (col, row)
                                    valid_moves = board.generate_legal_moves(col, row, current_side)
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

        if state == "ai" and not game_over and not paused and current_side == AI_SIDE:
            ai_make_move()

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
                draw_side_avatars_on_board(screen, profiles_data, mode, ai_level_index, font_avatar)
            if btn_log_tab_moves.is_clicked((mx, my)):
                log_active_tab = "moves"
                continue
            if btn_log_tab_captured.is_clicked((mx, my)):
                log_active_tab = "captured"
                continue

            if btn_in_game_settings.is_clicked((mx, my)):
                settings_return_state = state
                settings_page = "main"
                state = "settings"
                continue


            if selected is not None:
                draw_selection(screen, *selected)
                draw_move_hints(screen, valid_moves)            
            for r in range(BOARD_ROWS):
                for c in range(BOARD_COLS):
                    piece = board.get_piece(c, r)
                    if piece is not None:
                        from core.engine.draw_helpers import draw_piece  
                        draw_piece(screen, piece, c, r, font_piece, settings)

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

            # AI level button
            if state == "ai":
                level_cfg = AI_LEVELS[ai_level_index]
                btn_ai_level.label = f"AI: {level_cfg['name']}"

                btn_ai_level.rect.topleft = (panel_x + 10, panel_log_top)
                btn_ai_level.draw(screen, font_button, enabled=True)
                panel_log_top += 35

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

                # Thứ tự hiển thị các loại quân
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

        # SETTING MENU 
        elif state == "settings":
            screen.fill((50, 40, 40))

            if settings_page == "main":
                title_surf = font_title.render(t(settings, "settings_title"), True, (240, 240, 240))
                title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 120))
                screen.blit(title_surf, title_rect)

                board_theme = BOARD_THEMES[settings.board_theme_index]
                board_name = board_theme["name"][settings.language]

                body_theme = PIECE_BODY_THEMES[settings.piece_body_theme_index % len(PIECE_BODY_THEMES)] if PIECE_BODY_THEMES else None
                symbol_set = PIECE_SYMBOL_SETS[settings.piece_symbol_set_index % len(PIECE_SYMBOL_SETS)] if PIECE_SYMBOL_SETS else None
                color_theme = PIECE_THEMES[settings.piece_theme_index]

                body_name = body_theme["name"][settings.language] if body_theme else "-"
                symbol_name = symbol_set["name"][settings.language] if symbol_set else "-"
                color_name = color_theme["name"][settings.language]

                board_label = t(settings, "settings_board_theme").format(name=board_name)
                body_label = t(settings, "settings_piece_body").format(name=body_name)
                icons_label = t(settings, "settings_piece_icons").format(name=symbol_name)
                symbol_color_label = t(settings, "settings_piece_symbol_color").format(name=color_name)


                mode_label_key = "display_window" if settings.display_mode == "window" else "display_fullscreen"
                mode_label_text = t(settings, mode_label_key)
                display_label = t(settings, "settings_display").format(mode=mode_label_text)

                if settings.language == "en":
                    lang_label = "Language: English"
                else:
                    lang_label = "Ngôn ngữ: Tiếng Việt"

                # Label buttons in settings
                btn_settings_board_theme.label = board_label
                btn_settings_piece_body.label = body_label
                btn_settings_piece_icons.label = icons_label
                btn_settings_piece_theme.label = symbol_color_label
                btn_settings_display.label = display_label
                btn_settings_language.label = lang_label
                btn_settings_player_stats.label = t(settings, "settings_player_stats")
                btn_settings_back.label = t(settings, "btn_back")

                # Draw buttons in settings
                btn_settings_board_theme.draw(screen, font_button, enabled=True)
                btn_settings_piece_body.draw(screen, font_button, enabled=True)
                btn_settings_piece_icons.draw(screen, font_button, enabled=True)
                btn_settings_piece_theme.draw(screen, font_button, enabled=True)
                btn_settings_display.draw(screen, font_button, enabled=True)
                btn_settings_language.draw(screen, font_button, enabled=True)
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

                    y_line = y + 24
                    for line in [ov_l1, ov_l2, ai_l1, ai_l2, hv_l1, hv_l2]:
                        ls = font_text.render(line, True, (220, 220, 220))
                        screen.blit(ls, (start_x + 40, y_line))
                        y_line += 18

                    y = y_line + 10

                btn_settings_back.label = t(settings, "btn_back")
                btn_settings_back.draw(screen, font_button, enabled=True)
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


        pygame.display.flip()

    save_settings(settings)
    save_profiles(profiles_data)
    pygame.quit()
