import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
PIECES_ASSETS_DIR = os.path.join(ASSETS_DIR, "pieces")
PIECE_BODIES_DIR = os.path.join(PIECES_ASSETS_DIR, "bodies")
PIECE_SYMBOLS_DIR = os.path.join(PIECES_ASSETS_DIR, "symbols")


def _safe_listdir(path):
    try:
        return [p for p in os.listdir(path) if not p.startswith(".")]
    except Exception:
        return []


def discover_body_themes():
    """Discover piece body themes from `assets/pieces/bodies`.

    Returns a list of theme dicts matching the shape expected by the codebase:
    {"key": <folder>, "name": {"en": <folder>, "vi": <folder>}, "folder": <folder>, "red_file": <file>, "black_file": <file>}
    """
    themes = []
    for folder in _safe_listdir(PIECE_BODIES_DIR):
        folder_path = os.path.join(PIECE_BODIES_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        files = _safe_listdir(folder_path)
        red_file = None
        black_file = None
        for fn in files:
            low = fn.lower()
            if "red" in low and red_file is None:
                red_file = fn
            if "black" in low and black_file is None:
                black_file = fn
        # try exact fallbacks
        if red_file is None and "red.png" in [f.lower() for f in files]:
            for f in files:
                if f.lower() == "red.png":
                    red_file = f
                    break
        if black_file is None and "black.png" in [f.lower() for f in files]:
            for f in files:
                if f.lower() == "black.png":
                    black_file = f
                    break
        # if we have both files, register the theme
        if red_file and black_file:
            themes.append(
                {
                    "key": folder,
                    "name": {"en": folder, "vi": folder},
                    "folder": folder,
                    "red_file": red_file,
                    "black_file": black_file,
                }
            )
    return themes


_PIECE_KEYS = [
    "general",
    "advisor",
    "elephant",
    "horse",
    "rook",
    "cannon",
    "soldier",
]


def discover_symbol_sets():
    """Discover piece symbol sets from `assets/pieces/symbols`.

    Returns a list of symbol set dicts matching the expected shape:
    {"key": <folder>, "name": {...}, "folder": <folder>, "files": {"red": {...}, "black": {...}}}
    """
    sets = []
    for folder in _safe_listdir(PIECE_SYMBOLS_DIR):
        folder_path = os.path.join(PIECE_SYMBOLS_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        files = _safe_listdir(folder_path)
        red_map = {}
        black_map = {}
        for fn in files:
            low = fn.lower()
            side = None
            if "red" in low:
                side = "red"
            elif "black" in low:
                side = "black"
            if side is None:
                continue
            for key in _PIECE_KEYS:
                if key in low:
                    if side == "red":
                        red_map[key] = fn
                    else:
                        black_map[key] = fn
                    break
        # Only include sets that have at least one mapping
        if red_map or black_map:
            sets.append(
                {
                    "key": folder,
                    "name": {"en": folder, "vi": folder},
                    "folder": folder,
                    "files": {"red": red_map, "black": black_map},
                }
            )
    return sets
