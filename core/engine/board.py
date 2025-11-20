from config import BOARD_COLS, BOARD_ROWS
from .types import Side, PieceType, Piece

class Board:
    def __init__(self, red_on_bottom: bool = True):
        self.red_on_bottom = red_on_bottom
        self.grid = []
        self.setup_initial()

    def _is_bottom_side(self, side: Side) -> bool:
        return (side == Side.RED and self.red_on_bottom) or (side == Side.BLACK and not self.red_on_bottom)

    def _palace_rows(self, side: Side):
        # Bottom palace rows are 7-9, top are 0-2.
        return (7, 9) if self._is_bottom_side(side) else (0, 2)

    def _soldier_forward(self, side: Side) -> int:
        # Bottom side moves up (negative row), top side moves down (positive row).
        return -1 if self._is_bottom_side(side) else 1

    def _soldier_crossed_river(self, side: Side, row: int) -> bool:
        # River is between rows 4 and 5.
        if self._is_bottom_side(side):
            return row <= 4
        return row >= 5

    def _elephant_stays_home(self, side: Side, row: int) -> bool:
        # Elephants cannot cross the river.
        if self._is_bottom_side(side):
            return row >= 5
        return row <= 4

    def setup_initial(self):
        self.grid = [[None for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]

        def set_piece(row, col, side, ptype):
            self.grid[row][col] = Piece(side, ptype)

        def place_army(side: Side, is_bottom: bool):
            back_row = BOARD_ROWS - 1 if is_bottom else 0
            cannon_row = BOARD_ROWS - 3 if is_bottom else 2
            soldier_row = BOARD_ROWS - 4 if is_bottom else 3

            set_piece(back_row, 0, side, PieceType.ROOK)
            set_piece(back_row, 1, side, PieceType.HORSE)
            set_piece(back_row, 2, side, PieceType.ELEPHANT)
            set_piece(back_row, 3, side, PieceType.ADVISOR)
            set_piece(back_row, 4, side, PieceType.GENERAL)
            set_piece(back_row, 5, side, PieceType.ADVISOR)
            set_piece(back_row, 6, side, PieceType.ELEPHANT)
            set_piece(back_row, 7, side, PieceType.HORSE)
            set_piece(back_row, 8, side, PieceType.ROOK)

            set_piece(cannon_row, 1, side, PieceType.CANNON)
            set_piece(cannon_row, 7, side, PieceType.CANNON)

            for c in [0, 2, 4, 6, 8]:
                set_piece(soldier_row, c, side, PieceType.SOLDIER)

        bottom_side = Side.RED if self.red_on_bottom else Side.BLACK
        top_side = Side.BLACK if self.red_on_bottom else Side.RED

        place_army(top_side, is_bottom=False)
        place_army(bottom_side, is_bottom=True)

    def inside_board(self, col, row):
        return 0 <= col < BOARD_COLS and 0 <= row < BOARD_ROWS

    def get_piece(self, col, row):
        if not self.inside_board(col, row):
            return None
        return self.grid[row][col]

    def move_piece(self, move):
        from_c, from_r = move.from_pos
        to_c, to_r = move.to_pos
        self.grid[from_r][from_c] = None
        self.grid[to_r][to_c] = move.piece

    def undo_move(self, move):
        from_c, from_r = move.from_pos
        to_c, to_r = move.to_pos
        self.grid[from_r][from_c] = move.piece
        self.grid[to_r][to_c] = move.captured

    def _apply_temp_move(self, from_c, from_r, to_c, to_r):
        piece = self.get_piece(from_c, from_r)
        captured = self.get_piece(to_c, to_r)
        self.grid[from_r][from_c] = None
        self.grid[to_r][to_c] = piece
        return captured

    def _undo_temp_move(self, from_c, from_r, to_c, to_r, captured):
        piece = self.get_piece(to_c, to_r)
        self.grid[to_r][to_c] = captured
        self.grid[from_r][from_c] = piece

    def find_general(self, side: Side):
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                p = self.grid[r][c]
                if p is not None and p.side == side and p.ptype == PieceType.GENERAL:
                    return c, r
        return None

    def is_in_check(self, side: Side) -> bool:
        gen_pos = self.find_general(side)
        if gen_pos is None:
            return False
        gx, gy = gen_pos

        enemy = Side.RED if side == Side.BLACK else Side.BLACK

        enemy_gen_pos = self.find_general(enemy)
        if enemy_gen_pos is not None:
            ex, ey = enemy_gen_pos
            if ex == gx:
                step = 1 if gy < ey else -1
                blocked = False
                for r in range(gy + step, ey, step):
                    if self.get_piece(gx, r) is not None:
                        blocked = True
                        break
                if not blocked:
                    return True

        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                p = self.grid[r][c]
                if p is None or p.side != enemy:
                    continue
                if p.ptype == PieceType.GENERAL:
                    continue
                moves = self.generate_moves_for_square(c, r)
                if (gx, gy) in moves:
                    return True
        return False

    def generate_moves_for_square(self, col, row):
        piece = self.get_piece(col, row)
        if piece is None:
            return []

        if piece.ptype == PieceType.GENERAL:
            return self._gen_general_moves(col, row, piece)
        if piece.ptype == PieceType.ADVISOR:
            return self._gen_advisor_moves(col, row, piece)
        if piece.ptype == PieceType.ELEPHANT:
            return self._gen_elephant_moves(col, row, piece)
        if piece.ptype == PieceType.HORSE:
            return self._gen_horse_moves(col, row, piece)
        if piece.ptype == PieceType.ROOK:
            return self._gen_rook_moves(col, row, piece)
        if piece.ptype == PieceType.CANNON:
            return self._gen_cannon_moves(col, row, piece)
        if piece.ptype == PieceType.SOLDIER:
            return self._gen_soldier_moves(col, row, piece)
        return []

    def generate_legal_moves(self, col, row, side: Side):
        piece = self.get_piece(col, row)
        if piece is None or piece.side != side:
            return []

        raw_moves = self.generate_moves_for_square(col, row)
        legal = []
        for nc, nr in raw_moves:
            captured = self._apply_temp_move(col, row, nc, nr)
            if not self.is_in_check(side):
                legal.append((nc, nr))
            self._undo_temp_move(col, row, nc, nr, captured)
        return legal

    def has_any_legal_move(self, side: Side) -> bool:
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                p = self.grid[r][c]
                if p is None or p.side != side:
                    continue
                moves = self.generate_legal_moves(c, r, side)
                if moves:
                    return True
        return False

    def _gen_general_moves(self, col, row, piece):
        moves = []
        min_row, max_row = self._palace_rows(piece.side)
        min_col, max_col = 3, 5

        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dc, dr in directions:
            nc, nr = col + dc, row + dr
            if not self.inside_board(nc, nr):
                continue
            if not (min_col <= nc <= max_col and min_row <= nr <= max_row):
                continue
            target = self.get_piece(nc, nr)
            if target is None or target.side != piece.side:
                moves.append((nc, nr))
        return moves

    def _gen_advisor_moves(self, col, row, piece):
        moves = []
        min_row, max_row = self._palace_rows(piece.side)
        min_col, max_col = 3, 5

        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dc, dr in directions:
            nc, nr = col + dc, row + dr
            if not self.inside_board(nc, nr):
                continue
            if not (min_col <= nc <= max_col and min_row <= nr <= max_row):
                continue
            target = self.get_piece(nc, nr)
            if target is None or target.side != piece.side:
                moves.append((nc, nr))
        return moves

    def _gen_elephant_moves(self, col, row, piece):
        moves = []
        directions = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
        for dc, dr in directions:
            nc, nr = col + dc, row + dr
            mc, mr = col + dc // 2, row + dr // 2
            if not self.inside_board(nc, nr):
                continue
            if not self._elephant_stays_home(piece.side, nr):
                continue
            if self.get_piece(mc, mr) is not None:
                continue
            target = self.get_piece(nc, nr)
            if target is None or target.side != piece.side:
                moves.append((nc, nr))
        return moves

    def _gen_horse_moves(self, col, row, piece):
        moves = []
        candidates = [
            (col + 1, row + 2, col, row + 1),
            (col - 1, row + 2, col, row + 1),
            (col + 1, row - 2, col, row - 1),
            (col - 1, row - 2, col, row - 1),
            (col + 2, row + 1, col + 1, row),
            (col + 2, row - 1, col + 1, row),
            (col - 2, row + 1, col - 1, row),
            (col - 2, row - 1, col - 1, row),
        ]
        for nc, nr, bc, br in candidates:
            if not self.inside_board(nc, nr):
                continue
            if self.get_piece(bc, br) is not None:
                continue
            target = self.get_piece(nc, nr)
            if target is None or target.side != piece.side:
                moves.append((nc, nr))
        return moves

    def _gen_rook_moves(self, col, row, piece):
        moves = []
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dc, dr in directions:
            nc, nr = col + dc, row + dr
            while self.inside_board(nc, nr):
                target = self.get_piece(nc, nr)
                if target is None:
                    moves.append((nc, nr))
                else:
                    if target.side != piece.side:
                        moves.append((nc, nr))
                    break
                nc += dc
                nr += dr
        return moves

    def _gen_cannon_moves(self, col, row, piece):
        moves = []
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dc, dr in directions:
            nc, nr = col + dc, row + dr
            jumped = False
            while self.inside_board(nc, nr):
                target = self.get_piece(nc, nr)
                if not jumped:
                    if target is None:
                        moves.append((nc, nr))
                    else:
                        jumped = True
                else:
                    if target is not None:
                        if target.side != piece.side:
                            moves.append((nc, nr))
                        break
                nc += dc
                nr += dr
        return moves

    def _gen_soldier_moves(self, col, row, piece):
        moves = []
        forward = self._soldier_forward(piece.side)

        nc, nr = col, row + forward
        if self.inside_board(nc, nr):
            target = self.get_piece(nc, nr)
            if target is None or target.side != piece.side:
                moves.append((nc, nr))

        if self._soldier_crossed_river(piece.side, row):
            for dc in [-1, 1]:
                nc, nr = col + dc, row
                if self.inside_board(nc, nr):
                    target = self.get_piece(nc, nr)
                    if target is None or target.side != piece.side:
                        moves.append((nc, nr))
        return moves
    def reset(self, red_on_bottom: bool = True):
        self.red_on_bottom = red_on_bottom
        self.setup_initial()
