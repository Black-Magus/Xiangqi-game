import pygame
import math
import random

from config import (
    BOARD_COLS,
    BOARD_ROWS,
    CELL_SIZE,
    MARGIN_X,
    MARGIN_Y,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)
from engine.board import Board
from engine.types import Side, PieceType, Move

# UI Colours
RED_COLOR = (220, 50, 50)
BLACK_COLOR = (30, 30, 30)
BG_COLOR = (230, 200, 150)
BOARD_LINE_COLOR = (80, 40, 10)
SELECT_COLOR = (255, 215, 0)
HINT_COLOR = (0, 150, 0)

# Sides
AI_SIDE = Side.BLACK
HUMAN_SIDE = Side.RED

# AI Levels
AI_LEVELS = [
    {"name": "Noob Bot", "avatar_char": "N", "color": (120, 170, 255), "depth": 1, "randomness": 0.9},
    {"name": "Pro Bot", "avatar_char": "P", "color": (120, 220, 120), "depth": 1, "randomness": 0.2},
    {"name": "Hacker Bot", "avatar_char": "H", "color": (220, 120, 120), "depth": 2, "randomness": 0.0},
]

class Button:
    def __init__(self, rect, label):
        self.rect = rect
        self.label = label

    def draw(self, surface, font, enabled=True):
        bg = (200, 200, 200) if enabled else (160, 160, 160)
        border = (80, 80, 80)
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)
        text_color = (0, 0, 0)
        text_surf = font.render(self.label, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


def board_to_screen(col, row):
    x = MARGIN_X + col * CELL_SIZE
    y = MARGIN_Y + row * CELL_SIZE
    return x, y


def screen_to_board(x, y):
    col = (x - MARGIN_X + CELL_SIZE // 2) // CELL_SIZE
    row = (y - MARGIN_Y + CELL_SIZE // 2) // CELL_SIZE
    if 0 <= col < BOARD_COLS and 0 <= row < BOARD_ROWS:
        return int(col), int(row)
    return None, None


def draw_board(surface):
    surface.fill(BG_COLOR)

    for c in range(BOARD_COLS):
        x = MARGIN_X + c * CELL_SIZE
        y1 = MARGIN_Y
        y2 = MARGIN_Y + (BOARD_ROWS - 1) * CELL_SIZE
        pygame.draw.line(surface, BOARD_LINE_COLOR, (x, y1), (x, y2), 2)

    for r in range(BOARD_ROWS):
        y = MARGIN_Y + r * CELL_SIZE
        x1 = MARGIN_X
        x2 = MARGIN_X + (BOARD_COLS - 1) * CELL_SIZE
        pygame.draw.line(surface, BOARD_LINE_COLOR, (x1, y), (x2, y), 2)

    river_y_top = MARGIN_Y + 4 * CELL_SIZE
    river_rect = pygame.Rect(
        MARGIN_X,
        river_y_top,
        (BOARD_COLS - 1) * CELL_SIZE,
        CELL_SIZE,
    )
    pygame.draw.rect(surface, (220, 210, 170), river_rect)


def draw_piece(surface, piece, col, row, font):
    x, y = board_to_screen(col, row)
    cx = x
    cy = y
    radius = CELL_SIZE // 2 - 4
    color = RED_COLOR if piece.side == Side.RED else BLACK_COLOR
    pygame.draw.circle(surface, (245, 230, 200), (cx, cy), radius)
    pygame.draw.circle(surface, color, (cx, cy), radius, 2)

    if piece.ptype == PieceType.GENERAL:
        text = "帥" if piece.side == Side.RED else "將"
    elif piece.ptype == PieceType.ADVISOR:
        text = "仕" if piece.side == Side.RED else "士"
    elif piece.ptype == PieceType.ELEPHANT:
        text = "相" if piece.side == Side.RED else "象"
    elif piece.ptype == PieceType.HORSE:
        text = "傌" if piece.side == Side.RED else "馬"
    elif piece.ptype == PieceType.ROOK:
        text = "俥" if piece.side == Side.RED else "車"
    elif piece.ptype == PieceType.CANNON:
        text = "炮" if piece.side == Side.RED else "砲"
    else:
        text = "兵" if piece.side == Side.RED else "卒"

    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=(cx, cy))
    surface.blit(text_surf, text_rect)


def draw_selection(surface, col, row):
    x, y = board_to_screen(col, row)
    radius = CELL_SIZE // 2 - 2
    pygame.draw.circle(surface, SELECT_COLOR, (x, y), radius, 3)


def draw_move_hints(surface, moves):
    for c, r in moves:
        x, y = board_to_screen(c, r)
        pygame.draw.circle(surface, HINT_COLOR, (x, y), 6)

# ===========================
# AI helper
# ===========================

PIECE_VALUES = {
    PieceType.GENERAL: 10000,
    PieceType.ROOK: 500,
    PieceType.CANNON: 275,
    PieceType.HORSE: 275,
    PieceType.ELEPHANT: 125,
    PieceType.ADVISOR: 125,
    PieceType.SOLDIER: 60,
}


def evaluate_board(board: Board, ai_side: Side) -> int:
    score = 0
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            p = board.get_piece(c, r)
            if p is None:
                continue
            val = PIECE_VALUES.get(p.ptype, 0)
            if p.side == ai_side:
                score += val
            else:
                score -= val
    return score


def generate_all_legal_moves(board: Board, side: Side):
    moves = []
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            p = board.get_piece(c, r)
            if p is None or p.side != side:
                continue
            legal = board.generate_legal_moves(c, r, side)
            for nc, nr in legal:
                captured = board.get_piece(nc, nr)
                mv = Move((c, r), (nc, nr), p, captured)
                moves.append(mv)
    return moves


def minimax_search(board: Board, depth: int, ai_side: Side, current_side: Side, alpha: float, beta: float) -> float:
    if depth == 0:
        return evaluate_board(board, ai_side)

    moves = generate_all_legal_moves(board, current_side)
    if not moves:
        if board.is_in_check(current_side):
            return -100000 if current_side == ai_side else 100000
        else:
            return 0

    if current_side == ai_side:
        best = -math.inf
        for mv in moves:
            from_c, from_r = mv.from_pos
            to_c, to_r = mv.to_pos
            captured = board._apply_temp_move(from_c, from_r, to_c, to_r)
            next_side = Side.RED if current_side == Side.BLACK else Side.BLACK
            score = minimax_search(board, depth - 1, ai_side, next_side, alpha, beta)
            board._undo_temp_move(from_c, from_r, to_c, to_r, captured)

            if score > best:
                best = score
            alpha = max(alpha, score)
            if beta <= alpha:
                break
        return best
    else:
        best = math.inf
        for mv in moves:
            from_c, from_r = mv.from_pos
            to_c, to_r = mv.to_pos
            captured = board._apply_temp_move(from_c, from_r, to_c, to_r)
            next_side = Side.RED if current_side == Side.BLACK else Side.BLACK
            score = minimax_search(board, depth - 1, ai_side, next_side, alpha, beta)
            board._undo_temp_move(from_c, from_r, to_c, to_r, captured)

            if score < best:
                best = score
            beta = min(beta, score)
            if beta <= alpha:
                break
        return best


def choose_ai_move(board: Board, level_cfg, side: Side):
    moves = generate_all_legal_moves(board, side)
    if not moves:
        return None

    depth = level_cfg["depth"]
    randomness = level_cfg["randomness"]

    if randomness > 0 and random.random() < randomness:
        return random.choice(moves)

    best_score = -math.inf
    best_moves = []

    for mv in moves:
        from_c, from_r = mv.from_pos
        to_c, to_r = mv.to_pos
        captured = board._apply_temp_move(from_c, from_r, to_c, to_r)

        if depth <= 1:
            score = evaluate_board(board, side)
        else:
            next_side = Side.RED if side == Side.BLACK else Side.BLACK
            score = minimax_search(board, depth - 1, side, next_side, -math.inf, math.inf)

        board._undo_temp_move(from_c, from_r, to_c, to_r, captured)

        if score > best_score + 1e-6:
            best_score = score
            best_moves = [mv]
        elif abs(score - best_score) <= 1e-6:
            best_moves.append(mv)

    return random.choice(best_moves) if best_moves else random.choice(moves)

# ===========================
# Main Application 
# ===========================

def run_game():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
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

    state = "menu"
    mode = None
    ai_level_index = 1

    panel_x = MARGIN_X + BOARD_COLS * CELL_SIZE + 20

    # Game buttons
    btn_takeback = Button(
        pygame.Rect(panel_x, WINDOW_HEIGHT - 80, 190, 30),
        "Takeback",
    )

    btn_resign = Button(
        pygame.Rect(panel_x, WINDOW_HEIGHT - 120, 90, 30),
        "Resign",
    )
    btn_new_game = Button(
        pygame.Rect(panel_x + 100, WINDOW_HEIGHT - 120, 90, 30),
        "New game",
    )
    btn_ai_level = Button(
        pygame.Rect(panel_x + 30, MARGIN_Y + 70, 160, 28),
        "AI: Soldier Bot",
    )

    # Main menu
    center_x = WINDOW_WIDTH // 2
    start_y = WINDOW_HEIGHT // 2 - 80
    btn_menu_pvp = Button(
        pygame.Rect(center_x - 100, start_y, 200, 40),
        "Play PvP (local)",
    )
    btn_menu_ai = Button(
        pygame.Rect(center_x - 100, start_y + 50, 200, 40),
        "Play vs AI",
    )
    btn_menu_settings = Button(
        pygame.Rect(center_x - 100, start_y + 100, 200, 40),
        "Settings",
    )
    btn_menu_exit = Button(
        pygame.Rect(center_x - 100, start_y + 150, 200, 40),
        "Exit",
    )

    # Settings button 
    btn_settings_back = Button(
        pygame.Rect(center_x - 60, WINDOW_HEIGHT - 100, 120, 35),
        "Back",
    )


    def reset_game():
        nonlocal current_side, selected, valid_moves, move_history, redo_stack
        nonlocal in_check_side, game_over, winner
        board.reset()
        current_side = Side.RED
        selected = None
        valid_moves = []
        move_history = []
        redo_stack = []
        in_check_side = None
        game_over = False
        winner = None

    def update_game_state_after_side_change():
        nonlocal in_check_side, game_over, winner
        if board.is_in_check(current_side):
            in_check_side = current_side
            if not board.has_any_legal_move(current_side):
                game_over = True
                winner = Side.RED if current_side == Side.BLACK else Side.BLACK
            else:
                game_over = False
                winner = None
        else:
            in_check_side = None
            game_over = False
            winner = None

    def switch_to_menu():
        nonlocal state, selected, valid_moves, in_check_side, game_over, winner
        state = "menu"
        selected = None
        valid_moves = []
        in_check_side = None
        game_over = False
        winner = None

    def ai_make_move():
        nonlocal current_side, move_history, redo_stack, game_over, winner, in_check_side, selected, valid_moves
        if game_over:
            return
        if current_side != AI_SIDE:
            return

        level_cfg = AI_LEVELS[ai_level_index]
        mv = choose_ai_move(board, level_cfg, AI_SIDE)
        if mv is None:
            if board.is_in_check(AI_SIDE):
                game_over = True
                winner = HUMAN_SIDE
            else:
                game_over = True
                winner = None
            in_check_side = None
            return

        board.move_piece(mv)
        move_history.append(mv)
        redo_stack.clear()
        selected = None
        valid_moves = []

        # Change turn to player
        current_side = HUMAN_SIDE
        update_game_state_after_side_change()


    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and state != "menu":
                    # Return to main menu ESC
                    switch_to_menu()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # --------- STATE: MENU ----------
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
                        state = "settings"
                        continue
                    if btn_menu_exit.is_clicked((mx, my)):
                        running = False
                        continue

                # --------- STATE: SETTINGS ----------
                elif state == "settings":
                    if btn_settings_back.is_clicked((mx, my)):
                        switch_to_menu()
                        continue

                # --------- STATE: GAME (PVP / AI) ----------
                elif state in ("pvp", "ai"):
                    if state == "ai" and btn_ai_level.is_clicked((mx, my)):
                        ai_level_index = (ai_level_index + 1) % len(AI_LEVELS)
                        continue
                    
                    if btn_takeback.is_clicked((mx, my)):
                        if move_history:
                            steps = min(2, len(move_history))
                            for _ in range(steps):
                                last_move = move_history.pop()
                                board.undo_move(last_move)
                                redo_stack.append(last_move)
                                current_side = (
                                    Side.RED
                                    if current_side == Side.BLACK
                                    else Side.BLACK
                                )
                            update_game_state_after_side_change()
                        continue

                    if btn_resign.is_clicked((mx, my)):
                        if not game_over:
                            game_over = True
                            winner = (
                                Side.RED
                                if current_side == Side.BLACK
                                else Side.BLACK
                            )
                            in_check_side = None
                            selected = None
                            valid_moves = []
                        continue

                    if btn_new_game.is_clicked((mx, my)):
                        reset_game()
                        continue

                    if game_over:
                        continue
                    if state == "ai" and current_side == AI_SIDE:
                        continue

                    # Handle click on the board
                    col, row = screen_to_board(mx, my)
                    if col is not None:
                        piece = board.get_piece(col, row)
                        if selected is None:
                            if piece is not None and piece.side == current_side:
                                selected = (col, row)
                                valid_moves = board.generate_legal_moves(
                                    col,
                                    row,
                                    current_side,
                                )
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
                                    valid_moves = board.generate_legal_moves(
                                        col,
                                        row,
                                        current_side,
                                    )
                                else:
                                    if (col, row) in valid_moves:
                                        moving_piece = board.get_piece(sel_c, sel_r)
                                        captured = board.get_piece(col, row)
                                        move = Move(
                                            (sel_c, sel_r),
                                            (col, row),
                                            moving_piece,
                                            captured,
                                        )
                                        board.move_piece(move)
                                        move_history.append(move)
                                        redo_stack.clear()

                                        current_side = (
                                            Side.BLACK
                                            if current_side == Side.RED
                                            else Side.RED
                                        )
                                        update_game_state_after_side_change()
                                    selected = None
                                    valid_moves = []
        if state == "ai" and not game_over and current_side == AI_SIDE:
            ai_make_move()

        # ================== DRAW ==================
        if state == "menu":
            screen.fill((40, 40, 60))
            title_surf = font_title.render("Xiangqi", True, (250, 250, 250))
            title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 140))
            screen.blit(title_surf, title_rect)

            subtitle = "Press Esc in game to return here"
            sub_surf = font_text.render(subtitle, True, (220, 220, 220))
            sub_rect = sub_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 110))
            screen.blit(sub_surf, sub_rect)

            btn_menu_pvp.draw(screen, font_button, enabled=True)
            btn_menu_ai.draw(screen, font_button, enabled=True)
            btn_menu_settings.draw(screen, font_button, enabled=True)
            btn_menu_exit.draw(screen, font_button, enabled=True)

        elif state in ("pvp", "ai"):
            draw_board(screen)

            if selected is not None:
                draw_selection(screen, *selected)
                draw_move_hints(screen, valid_moves)

            for r in range(BOARD_ROWS):
                for c in range(BOARD_COLS):
                    piece = board.get_piece(c, r)
                    if piece is not None:
                        draw_piece(screen, piece, c, r, font_piece)

            # Panel
            panel_x = MARGIN_X + BOARD_COLS * CELL_SIZE + 20
            mode_text = "Mode: PvP" if mode == "pvp" else "Mode: vs AI (placeholder)"
            mt_surf = font_text.render(mode_text, True, (0, 0, 0))
            screen.blit(mt_surf, (panel_x, MARGIN_Y))

            turn_text = f"Turn: {'RED' if current_side == Side.RED else 'BLACK'}"
            tt_surf = font_text.render(turn_text, True, (0, 0, 0))
            screen.blit(tt_surf, (panel_x, MARGIN_Y + 20))

            if in_check_side is not None and not game_over:
                msg = "CHECK on RED" if in_check_side == Side.RED else "CHECK on BLACK"
                ck_surf = font_text.render(msg, True, (200, 0, 0))
                screen.blit(ck_surf, (panel_x, MARGIN_Y + 45))

            if game_over and winner is not None:
                if winner == Side.RED:
                    msg = "RED wins"
                elif winner == Side.BLACK:
                    msg = "BLACK wins"
                else:
                    msg = "Game over"
                win_surf = font_text.render(msg, True, (0, 0, 200))
                screen.blit(win_surf, (panel_x, MARGIN_Y + 70))
            # nếu đang ở chế độ AI, hiển thị avatar + nút level
            if state == "ai":
                level_cfg = AI_LEVELS[ai_level_index]
                btn_ai_level.label = f"AI: {level_cfg['name']}"

                # avatar tròn màu ở bên trái nút
                avatar_center = (panel_x + 16, MARGIN_Y + 109)
                pygame.draw.circle(screen, level_cfg["color"], avatar_center, 12)
                pygame.draw.circle(screen, (0, 0, 0), avatar_center, 12, 2)
                avatar_text = font_avatar.render(level_cfg["avatar_char"], True, (0, 0, 0))
                avatar_rect = avatar_text.get_rect(center=avatar_center)
                screen.blit(avatar_text, avatar_rect)

                btn_ai_level.draw(screen, font_button, enabled=True)

                y_log_start = MARGIN_Y + 140
            else:
                y_log_start = MARGIN_Y + 110
                
            # log moves
            y_log = MARGIN_Y + 110
            for i, mv in enumerate(move_history[-10:]):
                text = f"{len(move_history) - 10 + i + 1}. {mv}"
                mv_surf = font_text.render(text, True, (0, 0, 0))
                screen.blit(mv_surf, (panel_x, y_log))
                y_log += 20

            # Draw buttons
            btn_takeback.draw(screen, font_button, enabled=bool(move_history))
            btn_resign.draw(screen, font_button, enabled=not game_over)
            btn_new_game.draw(screen, font_button, enabled=True)

        elif state == "settings":
            screen.fill((50, 40, 40))
            title_surf = font_title.render("Settings", True, (240, 240, 240))
            title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 120))
            screen.blit(title_surf, title_rect)

            lines = [
                "Settings placeholder",
                "- Avatar, player name",
                "- Light/Dark mode",
                "- Sound, animation",
                "",
                "Press Esc or Back to return to menu",
            ]
            y = 180
            for line in lines:
                line_surf = font_text.render(line, True, (230, 230, 230))
                line_rect = line_surf.get_rect(center=(WINDOW_WIDTH // 2, y))
                screen.blit(line_surf, line_rect)
                y += 30

            btn_settings_back.draw(screen, font_button, enabled=True)

        pygame.display.flip()

    pygame.quit()