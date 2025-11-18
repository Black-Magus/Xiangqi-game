# ui/desktop/ai_engine.py

import math
import random

from config import BOARD_COLS, BOARD_ROWS
from core.engine.board import Board
from core.engine.types import Side, PieceType, Move

from core.engine.constants import AI_SIDE

PIECE_VALUES = {
    PieceType.GENERAL: 10000,
    PieceType.ROOK: 500,
    PieceType.CANNON: 275,
    PieceType.HORSE: 275,
    PieceType.ELEPHANT: 125,
    PieceType.ADVISOR: 125,
    PieceType.SOLDIER: 60,
}

AI_LEVELS = [
    {
        "name": "Noob Bot",
        "avatar_char": "N",
        "color": (120, 170, 255),
        "depth": 1,
        "randomness": 0.9,
        "avatar_path": "ai_casual.jpg",
        "elo": 900,
    },
    {
        "name": "Pro Bot",
        "avatar_char": "P",
        "color": (120, 220, 120),
        "depth": 1,
        "randomness": 0.2,
        "avatar_path": "ai_soldier.jpg",
        "elo": 1200,
    },
    {
        "name": "Hacker Bot",
        "avatar_char": "H",
        "color": (220, 120, 120),
        "depth": 2,
        "randomness": 0.0,
        "avatar_path": "ai_general.jpg",
        "elo": 1500,
    },
]


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
