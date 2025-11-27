import os
import pygame

from config import CELL_SIZE
from core.engine.types import PieceType, Side
from core.settings_manager import Settings
from data.localisation import PIECE_BODY_THEMES, PIECE_SYMBOL_SETS
from data.themes import default_piece_theme

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
AVATAR_DIR = os.path.join(ASSETS_DIR, "avatars")
BOARD_IMAGE_DIR = os.path.join(ASSETS_DIR, "boards")
LOSS_BADGE_FILE = "loss_badge.png"

_board_image_cache = {}
_board_border_cache = {}


BUILTIN_AVATARS = [
    "player1.png",
    "player2.png",
    "player3.png",
]

AVATAR_BOARD_SIZE = int(CELL_SIZE * 0.8)

_avatar_cache = {}
_loss_badge_cache = {}

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


def _grayscale_surface(src):
    """Return a cached-size grayscale copy of the given surface."""
    gray = src.copy()
    w, h = gray.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = gray.get_at((x, y))
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            gray.set_at((x, y), (lum, lum, lum, a))
    return gray


def _surface_has_color(surf, sample_steps=8):
    """Return True if the surface contains any non-grayscale colored pixel.

    The function samples the surface at a coarse grid (controlled by
    `sample_steps`) to avoid expensive per-pixel scans for large images.
    Fully transparent pixels are ignored.
    """
    try:
        w, h = surf.get_size()
    except Exception:
        return False
    if w == 0 or h == 0:
        return False

    step_x = max(1, w // sample_steps)
    step_y = max(1, h // sample_steps)

    for y in range(0, h, step_y):
        for x in range(0, w, step_x):
            px = surf.get_at((x, y))
            # px is (r,g,b,a) for surfaces with alpha
            if len(px) >= 4 and px[3] == 0:
                # ignore fully transparent pixels
                continue
            r, g, b = px[0], px[1], px[2]
            if r != g or r != b:
                return True
    return False


def _surface_average_luminance(surf, sample_steps=8):
    """Estimate the average luminance of non-transparent pixels on the surface."""
    try:
        w, h = surf.get_size()
    except Exception:
        return 0
    if w == 0 or h == 0:
        return 0

    total = 0
    count = 0
    step_x = max(1, w // sample_steps)
    step_y = max(1, h // sample_steps)

    for y in range(0, h, step_y):
        for x in range(0, w, step_x):
            px = surf.get_at((x, y))
            if len(px) >= 4 and px[3] == 0:
                continue
            r, g, b = px[0], px[1], px[2]
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            total += lum
            count += 1
    if count == 0:
        return 0
    return total // count


def load_avatar_image(path: str, size: int, grayscale: bool = False):
    if not path:
        return None
    full_path = resolve_avatar_path(path)
    key = (full_path, size, grayscale)
    if key in _avatar_cache:
        return _avatar_cache[key]
    if grayscale:
        base = load_avatar_image(path, size, grayscale=False)
        if base is None:
            return None
        gray = _grayscale_surface(base)
        _avatar_cache[key] = gray
        return gray
    if not os.path.exists(full_path):
        return None
    try:
        img = pygame.image.load(full_path).convert_alpha()
    except Exception:
        return None
    img = pygame.transform.smoothscale(img, (size, size))
    _avatar_cache[key] = img
    return img


def load_loss_badge(size: int):
    key = size
    if key in _loss_badge_cache:
        return _loss_badge_cache[key]
    path = os.path.join(AVATAR_DIR, LOSS_BADGE_FILE)
    badge = None
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            badge = pygame.transform.smoothscale(img, (size, size))
        except Exception:
            badge = None
    if badge is None:
        badge = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)
        radius = max(6, size // 2 - 2)
        pygame.draw.circle(badge, (200, 45, 45), center, radius)
        pygame.draw.circle(badge, (255, 255, 255), center, radius, 2)
        offset = int(radius * 0.6)
        width = max(2, size // 10)
        pygame.draw.line(
            badge,
            (255, 255, 255),
            (center[0] - offset, center[1] - offset),
            (center[0] + offset, center[1] + offset),
            width,
        )
        pygame.draw.line(
            badge,
            (255, 255, 255),
            (center[0] - offset, center[1] + offset),
            (center[0] + offset, center[1] - offset),
            width,
        )
    _loss_badge_cache[key] = badge
    return badge


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
    # Build candidate path. If the expected filename doesn't exist, fall back
    # to common defaults used in the assets tree (e.g. 'red.png' / 'black.png')
    if folder:
        path = os.path.join(PIECE_BODIES_DIR, folder, filename)
    else:
        path = os.path.join(PIECE_BODIES_DIR, filename)
    key = (theme_index, side, size)
    if key in _piece_body_cache:
        return _piece_body_cache[key]
    if not os.path.exists(path):
        # Fallbacks: try standard names inside the folder (red.png / black.png)
        fallback_name = "red.png" if side == Side.RED else "black.png"
        if folder:
            alt_path = os.path.join(PIECE_BODIES_DIR, folder, fallback_name)
        else:
            alt_path = os.path.join(PIECE_BODIES_DIR, fallback_name)
        if os.path.exists(alt_path):
            path = alt_path
        else:
            # Try any file in the folder that contains 'red' or 'black' in name
            if folder:
                try:
                    for fn in os.listdir(os.path.join(PIECE_BODIES_DIR, folder)):
                        low = fn.lower()
                        if (side == Side.RED and "red" in low) or (side != Side.RED and "black" in low):
                            candidate = os.path.join(PIECE_BODIES_DIR, folder, fn)
                            if os.path.exists(candidate):
                                path = candidate
                                break
                except Exception:
                    pass
            # If still not found, give up
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
    theme = default_piece_theme()
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

    # Colourize symbol only when the symbol image is monochrome. If the
    # symbol PNG already contains colors, preserve the original color.
    # For some symbol sets (e.g. modern) the black-side images may be
    # white-on-transparent glyphs. In that case we should keep the white
    # appearance instead of recolouring them to the theme's black colour.
    symbol_colored = symbol_img.copy()
    try:
        if not _surface_has_color(symbol_colored):
            symbol_colored.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    except Exception:
        # On any failure, fall back to attempting to colourize — this keeps
        # behavior compatible with older themes.
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


def process_and_save_avatar(source_path: str, target_size: int = 256) -> str:
    """Load an image from an arbitrary path, center-crop to square, resize to
    `target_size` and save as a JPEG into the avatars folder. Returns the
    relative filename (not absolute) on success or an empty string on failure.
    """
    try:
        if not os.path.exists(source_path):
            return ""
        # Load with pygame to preserve compatibility with rest of the app
        img = pygame.image.load(source_path).convert_alpha()
        w, h = img.get_size()
        # center-crop to square
        if w > h:
            x = (w - h) // 2
            y = 0
            side = h
        else:
            x = 0
            y = (h - w) // 2
            side = w
        cropped = pygame.Surface((side, side), pygame.SRCALPHA)
        cropped.blit(img, (-(x), -(y)))
        # Resize to target_size
        resized = pygame.transform.smoothscale(cropped, (target_size, target_size))

        # Convert to RGB surface (no alpha) for JPEG saving
        rgb = pygame.Surface((target_size, target_size))
        rgb.fill((255, 255, 255))
        rgb.blit(resized, (0, 0))

        # Ensure avatars directory exists
        os.makedirs(AVATAR_DIR, exist_ok=True)
        # Unique filename
        import time

        fname = f"user_avatar_{int(time.time())}.jpg"
        out_path = os.path.join(AVATAR_DIR, fname)
        try:
            pygame.image.save(rgb, out_path)
            return fname
        except Exception:
            return ""
    except Exception:
        return ""


def delete_avatar_file(rel_path: str) -> bool:
    """Delete an avatar file inside the avatars folder if it exists and is
    not one of the builtin avatar names. Returns True on successful removal.
    """
    try:
        if not rel_path:
            return False
        if rel_path in BUILTIN_AVATARS:
            return False
        full = resolve_avatar_path(rel_path)
        # Ensure the target is inside the AVATAR_DIR for safety
        full_norm = os.path.normpath(full)
        dir_norm = os.path.normpath(AVATAR_DIR)
        if not full_norm.startswith(dir_norm):
            return False
        if os.path.exists(full_norm):
            os.remove(full_norm)
            # remove cached variants if present
            keys = [k for k in list(_avatar_cache.keys()) if k[0] == full_norm]
            for k in keys:
                del _avatar_cache[k]
            return True
    except Exception:
        pass
    return False

def load_board_border_image(theme):
    path_rel = theme.get("border_image")
    if not path_rel:
        return None
    key = path_rel
    if key in _board_border_cache:
        return _board_border_cache[key]
    full_path = os.path.join(BOARD_IMAGE_DIR, path_rel)
    if not os.path.exists(full_path):
        return None
    try:
        img = pygame.image.load(full_path).convert_alpha()
    except Exception:
        return None
    _board_border_cache[key] = img
    return img
