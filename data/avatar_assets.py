import os
import pygame

from config import CELL_SIZE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "..", "..", "assets")
AVATAR_DIR = os.path.join(ASSETS_DIR, "avatars")

BUILTIN_AVATARS = [
    "player1.png",
    "player2.png",
    "player3.png",
]

AVATAR_BOARD_SIZE = int(CELL_SIZE * 2.4)

_avatar_cache = {}


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
