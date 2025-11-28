"""Board evaluation logic for Xiangqi.

Separates heuristic scoring from the search implementation to keep
`ai_engine.py` focused on tree search / move selection.

Exports:
    PIECE_VALUES: Base material values.
    evaluate_piece_positional(piece, col, row): Positional bonus.
    evaluate_board(board, side): Signed evaluation from `side` perspective.
"""

from __future__ import annotations

from typing import Dict

from config import BOARD_COLS, BOARD_ROWS
from .types import Side, PieceType, Piece  # noqa: F401 (Piece used for typing clarity)


PIECE_VALUES: Dict[PieceType, int] = {
    PieceType.GENERAL: 10000,
    PieceType.ROOK: 600,
    PieceType.CANNON: 300,
    PieceType.HORSE: 300,
    PieceType.ELEPHANT: 150,
    PieceType.ADVISOR: 150,
    PieceType.SOLDIER: 70,
}


def evaluate_piece_positional(p, c: int, r: int) -> int:
    """Return a small positional bonus for piece `p` at board coords (c,r).

    These heuristics are intentionally lightweight; deeper strategic
    evaluation (e.g., connectivity, threats) is out of scope for this
    simple engine and can be layered later without modifying search code.
    """
    bonus = 0

    if p.ptype == PieceType.SOLDIER:
        if p.side == Side.RED:
            forward = 9 - r  # advancing toward enemy side decreases row index
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


def evaluate_board(board, side: Side) -> int:
    """Evaluate `board` from perspective of `side`.

    Positive values favor `side`; negative values favor the opponent.
    Combines material and positional heuristics.
    """
    score = 0
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            p = board.get_piece(c, r)
            if p is None:
                continue
            base = PIECE_VALUES.get(p.ptype, 0)
            pos_bonus = evaluate_piece_positional(p, c, r)
            piece_score = base + pos_bonus
            if p.side == side:
                score += piece_score
            else:
                score -= piece_score
    return score
