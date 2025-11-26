import math
import random

from config import BOARD_COLS, BOARD_ROWS
from core.engine.board import Board
from core.engine.types import Side, PieceType, Move

from core.engine.constants import AI_SIDE

PIECE_VALUES = {
    PieceType.GENERAL: 10000,
    PieceType.ROOK: 600,
    PieceType.CANNON: 300,
    PieceType.HORSE: 300,
    PieceType.ELEPHANT: 150,
    PieceType.ADVISOR: 150,
    PieceType.SOLDIER: 70,
}

AI_LEVELS = [
    {
        "name": "Level 1 - Beginner",
        "avatar_char": "1",
        "color": (160, 160, 160),
        "depth": 1,
        "randomness": 0.9,    
        "eval_noise": 80,       
        "avatar_path": "ai_casual.jpg",
        "elo": 800,
    },
    {
        "name": "Level 2 - Casual",
        "avatar_char": "2",
        "color": (120, 170, 255),
        "depth": 1,
        "randomness": 0.5,
        "eval_noise": 50,
        "avatar_path": "ai_casual.jpg",
        "elo": 1000,
    },
    {
        "name": "Level 3 - Student",
        "avatar_char": "3",
        "color": (120, 220, 120),
        "depth": 2,
        "randomness": 0.25,
        "eval_noise": 30,
        "avatar_path": "ai_soldier.jpg",
        "elo": 1200,
    },
    {
        "name": "Level 4 - Strong",
        "avatar_char": "4",
        "color": (220, 180, 120),
        "depth": 3,
        "randomness": 0.1,
        "eval_noise": 15,
        "avatar_path": "ai_soldier.jpg",
        "elo": 1400,
    },
    {
        "name": "Level 5 - Master",
        "avatar_char": "5",
        "color": (220, 120, 120),
        "depth": 3,
        "randomness": 0.0,
        "eval_noise": 5,
        "avatar_path": "ai_general.jpg",
        "elo": 1650,
    },
    {
        "name": "Level 6 - Grandmaster",
        "avatar_char": "6",
        "color": (255, 80, 80),
        "depth": 4,             
        "randomness": 0.0,
        "eval_noise": 0,
        "avatar_path": "ai_general.jpg",
        "elo": 1850,
    },
]


def _evaluate_piece_positional(p, c, r) -> int:
    bonus = 0

    if p.ptype == PieceType.SOLDIER:
        if p.side == Side.RED:
            forward = 9 - r         
            crossed_river = r <= 4
        else:
            forward = r
            crossed_river = r >= 5

        bonus += forward * 2
        if crossed_river:
            bonus += 25

        if 3 <= c <= 5:
            bonus += 6

    elif p.ptype == PieceType.HORSE:
        if 2 <= c <= 6:
            bonus += 6
        if 3 <= r <= 6:
            bonus += 4

    elif p.ptype == PieceType.ROOK:
        bonus += max(0, 8 - 2 * abs(4 - c))

    elif p.ptype == PieceType.CANNON:
        if 2 <= c <= 6 and 2 <= r <= 7:
            bonus += 8

    elif p.ptype == PieceType.GENERAL:
        if c == 4:
            bonus += 10
        if (p.side == Side.RED and r >= 7) or (p.side == Side.BLACK and r <= 2):
            bonus += 6

    elif p.ptype == PieceType.ELEPHANT:
        if (p.side == Side.RED and r >= 5) or (p.side == Side.BLACK and r <= 4):
            bonus += 6
        if 2 <= c <= 6:
            bonus += 4

    elif p.ptype == PieceType.ADVISOR:
        if c == 4 and ((p.side == Side.RED and r >= 8) or (p.side == Side.BLACK and r <= 1)):
            bonus += 8

    return bonus


def evaluate_board(board: Board, ai_side: Side) -> int:
    score = 0

    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            p = board.get_piece(c, r)
            if p is None:
                continue

            base = PIECE_VALUES.get(p.ptype, 0)
            pos_bonus = _evaluate_piece_positional(p, c, r)
            piece_score = base + pos_bonus

            if p.side == ai_side:
                score += piece_score
            else:
                score -= piece_score

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
