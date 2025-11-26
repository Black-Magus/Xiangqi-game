BOARD_THEMES = [
    {
        "key": "classic1_png",
        "name": {"en": "Classic 1", "vi": "Classic 1"},
        "bg_color": (0, 0, 0),  
        "image": "classic1/board.png",  
        "border_image": "classic1/border.png",
        "border_inner_rect": (75, 70, 986.4, 1149.2),
    },
        {
        "key": "classic2_png",
        "name": {"en": "Classic 2", "vi": "Classic 2"},
        "bg_color": (0, 0, 0),  
        "image": "classic2/board.png",  
        "border_image": "classic2/border.png",
        "border_inner_rect": (28, 26, 411, 458),
    },
]


def default_piece_theme():
    """Return the built-in piece colour theme (fixed, no user selection)."""
    if PIECE_THEMES:
        return PIECE_THEMES[0]
    return {"red_color": (220, 50, 50), "black_color": (30, 30, 30)}

PIECE_THEMES = [
    {
        "key": "red_black",
        "name": {"en": "Red vs Black", "vi": "Đỏ vs Đen"},
        "red_color": (220, 50, 50),
        "black_color": (30, 30, 30),
    },
    {
        "key": "blue_gold",
        "name": {"en": "Blue vs Gold", "vi": "Xanh vs Vàng"},
        "red_color": (40, 120, 220),
        "black_color": (200, 160, 40),
    },
    {
        "key": "crimson_gray",
        "name": {"en": "Crimson vs Gray", "vi": "Đỏ sậm vs Xám"},
        "red_color": (200, 40, 80),
        "black_color": (60, 60, 70),
    },
]
