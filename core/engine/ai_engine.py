import math
import random

from config import BOARD_COLS, BOARD_ROWS
from core.engine.board import Board
from core.engine.types import Side, PieceType, Move
from core.engine.constants import AI_SIDE
from core.engine.evaluation import (
    evaluate_board,
    evaluate_piece_positional,  # exported for potential future move ordering tweaks
    PIECE_VALUES,
)

AI_LEVELS = [
    {
        "name": "Level 1 - Angry Man",
        "avatar_char": "1",
        "color": (160, 160, 160),
        "depth": 1,
        "randomness": 0.9,    
        "eval_noise": 80,       
        "avatar_path": "ai1.jpg",
        "elo": 800,
    },
    {
        "name": "Level 2 - Lỗ Tấn",
        "avatar_char": "2",
        "color": (120, 170, 255),
        "depth": 1,
        "randomness": 0.5,
        "eval_noise": 50,
        "avatar_path": "ai2.jpg",
        "elo": 1000,
    },
    {
        "name": "Level 3 - Bạch My Lão Tổ",
        "avatar_char": "3",
        "color": (120, 220, 120),
        "depth": 2,
        "randomness": 0.25,
        "eval_noise": 30,
        "avatar_path": "ai3.jpg",
        "elo": 1200,
    },
    {
        "name": "Level 4 - Tào Mạnh Đức",
        "avatar_char": "4",
        "color": (220, 180, 120),
        "depth": 3,
        "randomness": 0.1,
        "eval_noise": 15,
        "avatar_path": "ai4.jpg",
        "elo": 1400,
    },
    {
        "name": "Level 5 - Doanh Chính",
        "avatar_char": "5",
        "color": (220, 120, 120),
        "depth": 3,
        "randomness": 0.0,
        "eval_noise": 5,
        "avatar_path": "ai5.jpg",
        "elo": 1650,
    },
    {
        "name": "Level 6 - Quân Sư của Lưu Bị",
        "avatar_char": "6",
        "color": (255, 80, 80),
        "depth": 4,             
        "randomness": 0.0,
        "eval_noise": 0,
        "avatar_path": "ai6.jpg",
        "elo": 1850,
    },
]
"""AI engine: search, move generation, and level configuration.

Refactored to delegate board evaluation to `evaluation.py` to reduce
monolithic responsibilities and enable future improvements (e.g. phased
evaluation, caching) without touching search code.
"""


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


def _move_sort_key(mv: Move, ai_side: Side) -> int:
    score = 0

    if mv.captured is not None:
        cap_val = PIECE_VALUES.get(mv.captured.ptype, 0)
        own_val = PIECE_VALUES.get(mv.piece.ptype, 0)
        score += 10 * cap_val - own_val

    from_c, from_r = mv.from_pos
    to_c, to_r = mv.to_pos

    if mv.piece.ptype == PieceType.SOLDIER:
        if mv.piece.side == Side.RED:
            if to_r < from_r:
                score += 8
        else:
            if to_r > from_r:
                score += 8

    if mv.piece.ptype in (PieceType.ROOK, PieceType.CANNON, PieceType.HORSE):
        score += max(0, 6 - abs(4 - to_c))

    if mv.piece.side == ai_side:
        score += 3

    return score


def minimax_search(board: Board,
                   depth: int,
                   ai_side: Side,
                   current_side: Side,
                   alpha: float,
                   beta: float) -> float:
    if depth == 0:
        return evaluate_board(board, ai_side)

    moves = generate_all_legal_moves(board, current_side)
    if not moves:
        if board.is_in_check(current_side):
            return -100000 if current_side == ai_side else 100000
        else:
            return 0

    moves.sort(key=lambda mv: _move_sort_key(mv, ai_side), reverse=True)

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
            if score > alpha:
                alpha = score
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
            if score < beta:
                beta = score
            if beta <= alpha:
                break
        return best


def choose_ai_move(board: Board, level_cfg, side: Side):
    """
    Chọn nước đi cho AI với cấu hình level_cfg.
    - depth: độ sâu tìm kiếm minimax
    - randomness: xác suất chơi hẳn một nước random
    - eval_noise: thêm nhiễu vào đánh giá để level thấp chơi ngu hơn
    """
    moves = generate_all_legal_moves(board, side)
    if not moves:
        return None

    moves.sort(key=lambda mv: _move_sort_key(mv, side), reverse=True)

    depth = level_cfg["depth"]
    randomness = level_cfg["randomness"]
    eval_noise = level_cfg.get("eval_noise", 0.0)

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

        if eval_noise > 0:
            score += random.uniform(-eval_noise, eval_noise)

        if score > best_score + 1e-6:
            best_score = score
            best_moves = [mv]
        elif abs(score - best_score) <= 1e-6:
            best_moves.append(mv)

    return random.choice(best_moves) if best_moves else random.choice(moves)
