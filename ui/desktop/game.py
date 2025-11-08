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
from engine.board import Board
from engine.types import Side, PieceType, Move

# UI Colours
RED_COLOR = (220, 50, 50)
BLACK_COLOR = (30, 30, 30)
BG_COLOR = (230, 200, 150)
BOARD_LINE_COLOR = (80, 40, 10)
SELECT_COLOR = (255, 215, 0)
HINT_COLOR = (0, 150, 0)


def board_to_screen(col, row):
    x = MARGIN_X + col * CELL_SIZE
    y = MARGIN_Y + row * CELL_SIZE
    return x, y


def screen_to_board(x, y):
    col = (x - MARGIN_X) // CELL_SIZE
    row = (y - MARGIN_Y) // CELL_SIZE
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


def run_game():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Xiangqi - PvP with checkmate")

    clock = pygame.time.Clock()
    font_piece = pygame.font.SysFont("SimHei", 28)
    font_text = pygame.font.SysFont("Consolas", 18)

    board = Board()
    current_side = Side.RED
    selected = None
    valid_moves = []
    move_history = []
    in_check_side = None
    game_over = False
    winner = None

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_over:
                    continue

                mx, my = event.pos
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

                                    current_side = (
                                        Side.BLACK
                                        if current_side == Side.RED
                                        else Side.RED
                                    )

                                    if board.is_in_check(current_side):
                                        in_check_side = current_side
                                        if not board.has_any_legal_move(current_side):
                                            game_over = True
                                            winner = (
                                                Side.RED
                                                if current_side == Side.BLACK
                                                else Side.BLACK
                                            )
                                    else:
                                        in_check_side = None
                                selected = None
                                valid_moves = []

        draw_board(screen)

        if selected is not None:
            draw_selection(screen, *selected)
            draw_move_hints(screen, valid_moves)

        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                piece = board.get_piece(c, r)
                if piece is not None:
                    draw_piece(screen, piece, c, r, font_piece)

        panel_x = MARGIN_X + BOARD_COLS * CELL_SIZE + 20
        turn_text = f"Turn: {'RED' if current_side == Side.RED else 'BLACK'}"
        tt_surf = font_text.render(turn_text, True, (0, 0, 0))
        screen.blit(tt_surf, (panel_x, MARGIN_Y))

        if in_check_side is not None and not game_over:
            msg = "CHECK on RED" if in_check_side == Side.RED else "CHECK on BLACK"
            ck_surf = font_text.render(msg, True, (200, 0, 0))
            screen.blit(ck_surf, (panel_x, MARGIN_Y + 25))

        if game_over and winner is not None:
            msg = (
                "RED wins by checkmate"
                if winner == Side.RED
                else "BLACK wins by checkmate"
            )
            win_surf = font_text.render(msg, True, (0, 0, 200))
            screen.blit(win_surf, (panel_x, MARGIN_Y + 50))

        y_log = MARGIN_Y + 90
        for i, mv in enumerate(move_history[-10:]):
            text = f"{len(move_history) - 10 + i + 1}. {mv}"
            mv_surf = font_text.render(text, True, (0, 0, 0))
            screen.blit(mv_surf, (panel_x, y_log))
            y_log += 20

        pygame.display.flip()

    pygame.quit()
