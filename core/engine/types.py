from enum import Enum

class Side(Enum):
    RED = "red"
    BLACK = "black"


class PieceType(Enum):
    GENERAL = "general"
    ADVISOR = "advisor"
    ELEPHANT = "elephant"
    HORSE = "horse"
    ROOK = "rook"
    CANNON = "cannon"
    SOLDIER = "soldier"


class Piece:
    def __init__(self, side: Side, ptype: PieceType):
        self.side = side
        self.ptype = ptype

    def __repr__(self):
        return f"{self.side.value[0].upper()}-{self.ptype.value}"


class Move:
    def __init__(self, from_pos, to_pos, piece, captured=None):
        self.from_pos = from_pos  # (col,row)
        self.to_pos = to_pos
        self.piece = piece
        self.captured = captured

    def __repr__(self):
        return f"{self.piece} {self.from_pos} -> {self.to_pos}"
