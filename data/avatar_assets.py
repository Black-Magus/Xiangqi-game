import os
import pygame

from config import CELL_SIZE
from core.engine.types import PieceType, Side
from core.settings_manager import Settings
from data.localisation import PIECE_BODY_THEMES, PIECE_SYMBOL_SETS
from data.themes import PIECE_THEMES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
AVATAR_DIR = os.path.join(ASSETS_DIR, "avatars")
BOARD_IMAGE_DIR = os.path.join(ASSETS_DIR, "boards")

_board_image_cache = {}


BUILTIN_AVATARS = [
    "player1.png",
    "player2.png",
    "player3.png",
]

AVATAR_BOARD_SIZE = int(CELL_SIZE * 0.8)

_avatar_cache = {}

# Piece PNG assets
PIECES_DIR = os.path.join(ASSETS_DIR, "pieces")
PIECE_BODIES_DIR = os.path.join(PIECES_DIR, "bodies")
PIECE_SYMBOLS_DIR = os.path.join(PIECES_DIR, "symbols")

_piece_body_cache = {}
_piece_symbol_cache = {}
_piece_sprite_cache = {}

# map PieceType -> string key symbol 
PIECE_TYPE_KEY = {
    PieceType.GENERAL: "general",
    PieceType.ADVISOR: "advisor",
    PieceType.ELEPHANT: "elephant",
    PieceType.HORSE: "horse",
    PieceType.ROOK: "rook",
    PieceType.CANNON: "cannon",
    PieceType.SOLDIER: "soldier",
}


def resolve_avatar_path(path: str) -> str:
    if not path:
        return ""
    if os.path.isabs(path):
        return path
    return os.path.join(AVATAR_DIR, path)


def load_avatar_image(path: str, size: int):
    if not path:
        return None
    full_path = resolve_avatar_path(path)
    key = (full_path, size)
    if key in _avatar_cache:
        return _avatar_cache[key]
    if not os.path.exists(full_path):
        return None
    try:
        img = pygame.image.load(full_path).convert_alpha()
    except Exception:
        return None
    img = pygame.transform.smoothscale(img, (size, size))
    _avatar_cache[key] = img
    return img


def select_avatar_file_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filetypes = [
            ("Image files", "*.png;*.jpg;*.jpeg;*.bmp"),
            ("All files", "*.*"),
        ]
        filename = filedialog.askopenfilename(
            title="Select avatar image",
            filetypes=filetypes,
        )
        root.destroy()
        if filename:
            return filename
    except Exception:
        return None

def load_piece_body_image(theme_index, side, size):
    if not PIECE_BODY_THEMES:
        return None
    theme_index = theme_index % len(PIECE_BODY_THEMES)
    theme = PIECE_BODY_THEMES[theme_index]
    filename = theme["red_file"] if side == Side.RED else theme["black_file"]
    if not filename:
        return None
    folder = theme.get("folder")
    if folder:
        path = os.path.join(PIECE_BODIES_DIR, folder, filename)
    else:
        path = os.path.join(PIECE_BODIES_DIR, filename)
    key = (theme_index, side, size)
    if key in _piece_body_cache:
        return _piece_body_cache[key]
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
    except Exception:
        return None
    img = pygame.transform.smoothscale(img, (size, size))
    _piece_body_cache[key] = img
    return img


def load_piece_symbol_image(symbol_index, piece_key, side, size):
    if not PIECE_SYMBOL_SETS:
        return None
    symbol_index = symbol_index % len(PIECE_SYMBOL_SETS)
    theme = PIECE_SYMBOL_SETS[symbol_index]

    side_key = "red" if side == Side.RED else "black"
    side_map = theme["files"].get(side_key, {})
    filename = side_map.get(piece_key)
    if not filename:
        return None

    folder = theme.get("folder")
    if folder:
        path = os.path.join(PIECE_SYMBOLS_DIR, folder, filename)
    else:
        path = os.path.join(PIECE_SYMBOLS_DIR, filename)
    key = (symbol_index, side_key, piece_key, size)
    if key in _piece_symbol_cache:
        return _piece_symbol_cache[key]
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
    except Exception:
        return None
    img = pygame.transform.smoothscale(img, (size, size))
    _piece_symbol_cache[key] = img
    return img


def get_symbol_color_for_side(settings: Settings, side: Side):
    theme = PIECE_THEMES[settings.piece_theme_index]
    return theme["red_color"] if side == Side.RED else theme["black_color"]


def get_piece_sprite(piece, settings: Settings, size: int):
    piece_key = PIECE_TYPE_KEY.get(piece.ptype)
    if piece_key is None:
        return None

    if not PIECE_BODY_THEMES or not PIECE_SYMBOL_SETS:
        return None

    body_theme_index = settings.piece_body_theme_index % len(PIECE_BODY_THEMES)
    symbol_theme_index = settings.piece_symbol_set_index % len(PIECE_SYMBOL_SETS)
    color = get_symbol_color_for_side(settings, piece.side)
    color_key = (color[0], color[1], color[2])

    cache_key = (body_theme_index, symbol_theme_index, piece.side, piece_key, color_key, size)
    if cache_key in _piece_sprite_cache:
        return _piece_sprite_cache[cache_key]

    body_img = load_piece_body_image(body_theme_index, piece.side, size)
    symbol_img = load_piece_symbol_image(symbol_theme_index, piece_key, piece.side, size)
    if body_img is None or symbol_img is None:
        return None

    # Colourize symbol
    symbol_colored = symbol_img.copy()
    symbol_colored.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.blit(body_img, (0, 0))
    surf.blit(symbol_colored, (0, 0))

    _piece_sprite_cache[cache_key] = surf
    return surf

def load_board_image(theme):
    path_rel = theme.get("image")
    if not path_rel:
        return None
    key = path_rel
    if key in _board_image_cache:
        return _board_image_cache[key]
    full_path = os.path.join(BOARD_IMAGE_DIR, path_rel)
    if not os.path.exists(full_path):
        return None
    try:
        img = pygame.image.load(full_path).convert_alpha()
    except Exception:
        return None
    _board_image_cache[key] = img
    return img

