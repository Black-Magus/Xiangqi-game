import pygame

from config import BOARD_COLS, BOARD_ROWS, CELL_SIZE, MARGIN_X, MARGIN_Y, BOARD_OFFSET_Y
from core.engine.types import Side, PieceType

from data.themes import BOARD_THEMES, PIECE_THEMES
from data.avatar_assets import (
    AVATAR_BOARD_SIZE,
    get_piece_sprite,
    load_avatar_image,
    load_board_image,
    load_board_border_image,
    load_loss_badge,
)
from core.profiles_manager import DEFAULT_ELO, find_player
from core.engine.ai_engine import AI_LEVELS
from core.settings_manager import Settings

BOARD_TOP = MARGIN_Y + BOARD_OFFSET_Y
LOSS_BADGE_SIZE = int(AVATAR_BOARD_SIZE * 1.3)
LOSS_BADGE_GAP = 6

def board_to_screen(col, row):
    x = MARGIN_X + col * CELL_SIZE
    y = BOARD_TOP + row * CELL_SIZE
    return x, y


def screen_to_board(x, y):
    col = (x - MARGIN_X + CELL_SIZE // 2) // CELL_SIZE
    row = (y - BOARD_TOP + CELL_SIZE // 2) // CELL_SIZE
    if 0 <= col < BOARD_COLS and 0 <= row < BOARD_ROWS:
        return int(col), int(row)
    return None, None


def draw_board(surface, settings: Settings):
    theme = BOARD_THEMES[settings.board_theme_index]

    bg_color = theme.get("bg_color", (30, 30, 30))
    surface.fill(bg_color)

    board_w = (BOARD_COLS - 1) * CELL_SIZE
    board_h = (BOARD_ROWS - 1) * CELL_SIZE

    border_img = load_board_border_image(theme)
    img = load_board_image(theme)
    if border_img is not None:
        border_surface = border_img
        src_w, src_h = border_img.get_size()

        inner_rect = theme.get("border_inner_rect")
        if inner_rect is not None:
            ix, iy, inner_w, inner_h = inner_rect
        else:
            # fallback: dùng size của board image như cũ
            inner_size = theme.get("border_inner_size")
            if inner_size is None and img is not None:
                inner_size = img.get_size()
            inner_w, inner_h = inner_size if inner_size else (board_w, board_h)
            ix = iy = 0

        # scale border sao cho vùng inner vừa đúng với board_w, board_h
        scale_x = board_w / float(inner_w)
        scale_y = board_h / float(inner_h)
        target_w = int(round(src_w * scale_x))
        target_h = int(round(src_h * scale_y))

        if (target_w, target_h) != (src_w, src_h):
            border_surface = pygame.transform.smoothscale(border_img, (target_w, target_h))

        # Căn border sao cho góc trái trên của inner rect trùng MARGIN_X, BOARD_TOP
        border_x = int(round(MARGIN_X - ix * scale_x))
        border_y = int(round(BOARD_TOP - iy * scale_y))

        surface.blit(border_surface, (border_x, border_y))

    # Draw the board after the border so the grid/artwork always sits on top of any opaque border center.
    if img is not None:
        scaled = pygame.transform.smoothscale(img, (board_w, board_h))
        surface.blit(scaled, (MARGIN_X, BOARD_TOP))
    else:
        # Fall back to sensible defaults when theme colors are missing
        line_color = theme.get("line_color", (40, 40, 40))
        river_color = theme.get("river_color", (210, 220, 230))

        for c in range(BOARD_COLS):
            x = MARGIN_X + c * CELL_SIZE
            y1 = BOARD_TOP
            y2 = BOARD_TOP + (BOARD_ROWS - 1) * CELL_SIZE
            pygame.draw.line(surface, line_color, (x, y1), (x, y2), 2)

        for r in range(BOARD_ROWS):
            y = BOARD_TOP + r * CELL_SIZE
            x1 = MARGIN_X
            x2 = MARGIN_X + (BOARD_COLS - 1) * CELL_SIZE
            pygame.draw.line(surface, line_color, (x1, y), (x2, y), 2)

        river_y_top = BOARD_TOP + 4 * CELL_SIZE
        river_rect = pygame.Rect(
            MARGIN_X,
            river_y_top,
            (BOARD_COLS - 1) * CELL_SIZE,
            CELL_SIZE,
        )
        pygame.draw.rect(surface, river_color, river_rect)


def draw_piece(surface, piece, col, row, font, settings: Settings, highlight_color=None):
    x, y = board_to_screen(col, row)
    size = int(CELL_SIZE * 0.9)
    if highlight_color:
        max_radius = CELL_SIZE // 2 + 8
        glow_surf = pygame.Surface((max_radius * 2, max_radius * 2), pygame.SRCALPHA)
        center = (max_radius, max_radius)
        layers = 4
        for i in range(layers):
            radius = max_radius - i * 3
            blend = i / (layers - 1) if layers > 1 else 1.0
            alpha = int(40 + (160 - 40) * blend)
            pygame.draw.circle(glow_surf, (*highlight_color, alpha), center, radius)
        glow_rect = glow_surf.get_rect(center=(x, y))
        surface.blit(glow_surf, glow_rect)

    # Draw piece sprite
    sprite = get_piece_sprite(piece, settings, size)
    if sprite is not None:
        rect = sprite.get_rect(center=(x, y))
        surface.blit(sprite, rect)
        return

    # Fallback text
    cx = x
    cy = y
    radius = CELL_SIZE // 2 - 4
    theme = PIECE_THEMES[settings.piece_theme_index]
    color = theme["red_color"] if piece.side == Side.RED else theme["black_color"]

    pygame.draw.circle(surface, (245, 230, 200), (cx, cy), radius)
    pygame.draw.circle(surface, color, (cx, cy), radius, 2)
    
    if piece.ptype == PieceType.GENERAL:
        text = "帥" if piece.side == Side.RED else "將"
    elif piece.ptype == PieceType.ADVISOR:
        text = "仕" if piece.side == Side.RED else "士"
    elif piece.ptype == PieceType.ELEPHANT:
        text = "相" if piece.side == Side.RED else "象"
    elif piece.ptype == PieceType.HORSE:
        text = "傌" if piece.side == Side.RED else "馬"
    elif piece.ptype == PieceType.ROOK:
        text = "俥" if piece.side == Side.RED else "車"
    elif piece.ptype == PieceType.CANNON:
        text = "炮" if piece.side == Side.RED else "砲"
    else:
        text = "兵" if piece.side == Side.RED else "卒"

    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=(cx, cy))
    surface.blit(text_surf, text_rect)


def draw_selection(surface, col, row):
    x, y = board_to_screen(col, row)
    radius = CELL_SIZE // 2 - 2
    pygame.draw.circle(surface, (255, 215, 0), (x, y), radius, 3)


def draw_move_hints(surface, moves):
    for c, r in moves:
        x, y = board_to_screen(c, r)
        pygame.draw.circle(surface, (0, 150, 0), (x, y), 6)


def draw_move_origin(surface, col, row, color):
    x, y = board_to_screen(col, row)
    pygame.draw.circle(surface, color, (x, y), 9)


def draw_piece_preview(surface, piece, col, row, font, settings: Settings, alpha=120):
    x, y = board_to_screen(col, row)
    size = int(CELL_SIZE * 0.9)
    sprite = get_piece_sprite(piece, settings, size)
    if sprite is not None:
        preview = sprite.copy()
        preview.set_alpha(alpha)
        rect = preview.get_rect(center=(x, y))
        surface.blit(preview, rect)
        return

    theme = PIECE_THEMES[settings.piece_theme_index]
    color = theme["red_color"] if piece.side == Side.RED else theme["black_color"]
    bg_color = (245, 230, 200, alpha)
    outline_color = (*color, alpha)

    surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
    radius = CELL_SIZE // 2 - 4
    center = (CELL_SIZE // 2, CELL_SIZE // 2)
    pygame.draw.circle(surf, bg_color, center, radius)
    pygame.draw.circle(surf, outline_color, center, radius, 2)

    if piece.ptype == PieceType.GENERAL:
        text = "帥" if piece.side == Side.RED else "將"
    elif piece.ptype == PieceType.ADVISOR:
        text = "仕" if piece.side == Side.RED else "士"
    elif piece.ptype == PieceType.ELEPHANT:
        text = "相" if piece.side == Side.RED else "象"
    elif piece.ptype == PieceType.HORSE:
        text = "傌" if piece.side == Side.RED else "馬"
    elif piece.ptype == PieceType.ROOK:
        text = "俥" if piece.side == Side.RED else "車"
    elif piece.ptype == PieceType.CANNON:
        text = "炮" if piece.side == Side.RED else "砲"
    else:
        text = "兵" if piece.side == Side.RED else "卒"

    text_surf = font.render(text, True, color)
    text_surf.set_alpha(alpha)
    text_rect = text_surf.get_rect(center=center)
    surf.blit(text_surf, text_rect)

    rect = surf.get_rect(center=(x, y))
    surface.blit(surf, rect)


def draw_profile_avatar(surface, profile, center, size, font_avatar):
    avatar = profile.get("avatar", {})
    path = avatar.get("path")
    img = load_avatar_image(path, size)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if img is not None:
        surface.blit(img, rect)
    else:
        color = tuple(avatar.get("color", [180, 180, 180]))
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, 2)
        initials = avatar.get("symbol") or profile.get("display_name", "?")[:2]
        text = font_avatar.render(str(initials), True, (0, 0, 0))
        text_rect = text.get_rect(center=rect.center)
        surface.blit(text, text_rect)


def draw_ai_avatar(surface, ai_level_cfg, center, size, font_avatar):
    path = ai_level_cfg.get("avatar_path")
    img = load_avatar_image(path, size)
    rect = pygame.Rect(0, 0, size, size)
    rect.center = center
    if img is not None:
        surface.blit(img, rect)
    else:
        color = ai_level_cfg.get("color", (120, 120, 120))
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, (0, 0, 0), rect, 2)
        symbol = ai_level_cfg.get("avatar_char", "?")
        text = font_avatar.render(str(symbol), True, (0, 0, 0))
        text_rect = text.get_rect(center=rect.center)
        surface.blit(text, text_rect)


def _draw_text_with_shadow(surface, font, text, color, pos):
    shadow = font.render(text, True, (0, 0, 0))
    surface.blit(shadow, (pos[0] + 1, pos[1] + 1))
    surf = font.render(text, True, color)
    surface.blit(surf, pos)
    rect = surf.get_rect(topleft=pos)
    return rect


def _compute_caption_layout(rect, font_avatar, name_text, elo_text, align_left):
    name_w, name_h = font_avatar.size(name_text)
    elo_w, elo_h = font_avatar.size(elo_text)
    pad = 10
    gap = 12
    total_w = name_w + gap + elo_w
    base_x = rect.left - total_w - pad if align_left else rect.right + pad
    base_y = rect.centery - max(name_h, elo_h) // 2
    return base_x, base_y, gap


def _draw_avatar_caption(surface, rect, name, elo_value, name_color, font_avatar, align_left=False):
    if not name:
        return None
    name_text = str(name)
    elo_text = f"ELO: {int(round(elo_value))}"

    base_x, base_y, gap = _compute_caption_layout(rect, font_avatar, name_text, elo_text, align_left)

    name_rect = _draw_text_with_shadow(surface, font_avatar, name_text, name_color, (base_x, base_y))
    elo_pos = (name_rect.right + gap, base_y)
    elo_rect = _draw_text_with_shadow(surface, font_avatar, elo_text, (50, 50, 50), elo_pos)
    return {"name_rect": name_rect, "elo_rect": elo_rect, "align_left": align_left}


def _draw_timer_for_caption(surface, font_timer, caption_info, timer_text):
    if caption_info is None or not timer_text:
        return None
    name_rect = caption_info["name_rect"]
    align_left = caption_info.get("align_left", False)

    timer_surf = font_timer.render(timer_text, True, (0, 0, 0))
    gap = 8
    box_width = 150
    box_height = 50
    if align_left:
        timer_x = get_top_avatar_rect().left - box_width * 2.9
    else:
        timer_x = get_top_avatar_rect().right - box_width
    timer_y = name_rect.y - (box_height - font_timer.get_height()) // 2

    box_rect = pygame.Rect(timer_x, timer_y, box_width, box_height)
    pygame.draw.rect(surface, (255, 255, 255), box_rect, border_radius=6)
    pygame.draw.rect(surface, (50, 50, 50), box_rect, 1, border_radius=6)

    timer_width, timer_height = timer_surf.get_size()
    text_x = box_rect.centerx - timer_width // 2
    text_y = box_rect.centery - timer_height // 2
    shadow = font_timer.render(timer_text, True, (0, 0, 0))
    surface.blit(shadow, (text_x + 1, text_y + 1))
    surface.blit(timer_surf, (text_x, text_y))
    return box_rect


def _draw_loss_badge(surface, avatar_rect, side: Side, loser_side, scale=1.0):
    if loser_side is None or side != loser_side:
        return
    target_size = max(1, int(LOSS_BADGE_SIZE * max(0.1, scale)))
    badge = load_loss_badge(target_size)
    if badge is None:
        return
    badge_rect = badge.get_rect(center=avatar_rect.center)
    surface.blit(badge, badge_rect)


def get_bottom_avatar_rect():
    rect = pygame.Rect(0, 0, AVATAR_BOARD_SIZE, AVATAR_BOARD_SIZE)
    cx = MARGIN_X - AVATAR_BOARD_SIZE // 2 + 40
    cy = BOARD_TOP + (BOARD_ROWS - 1) * CELL_SIZE + CELL_SIZE // 2 + 60
    rect.center = (cx, cy)
    return rect


def get_top_avatar_rect():
    rect = pygame.Rect(0, 0, AVATAR_BOARD_SIZE, AVATAR_BOARD_SIZE)
    cx = MARGIN_X + (BOARD_COLS - 1) * CELL_SIZE + AVATAR_BOARD_SIZE // 2 - 40
    cy = BOARD_TOP + CELL_SIZE // 2 - 115
    rect.center = (cx, cy)
    return rect


def draw_side_avatars_on_board(
    surface,
    profiles_data,
    mode,
    ai_level_index,
    font_avatar,
    font_timer,
    timer_labels=None,
    loser_side=None,
    loss_badge_scale=1.0,
):
    timer_labels = timer_labels or {}
    timer_rects = {}
    last_sel = profiles_data.get("last_selected", {})
    if mode == "pvp":
        pvp_info = last_sel.get("pvp", {})
        red_id = pvp_info.get("red_player_id", "p1")
        black_id = pvp_info.get("black_player_id", "p2")
        red_player = find_player(profiles_data, red_id)
        black_player = find_player(profiles_data, black_id)

        bottom_rect = get_bottom_avatar_rect()
        top_rect = get_top_avatar_rect()
        if red_player:
            draw_profile_avatar(surface, red_player, bottom_rect.center, AVATAR_BOARD_SIZE, font_avatar)
            _draw_loss_badge(surface, bottom_rect, Side.RED, loser_side, loss_badge_scale)
            caption = _draw_avatar_caption(
                surface,
                bottom_rect,
                red_player.get("display_name", "Player 1"),
                red_player.get("elo", DEFAULT_ELO),
                (200, 40, 40),
                font_avatar,
            )
            red_timer = _draw_timer_for_caption(surface, font_timer, caption, timer_labels.get("red"))
            if red_timer:
                timer_rects["red"] = red_timer
        if black_player:
            draw_profile_avatar(surface, black_player, top_rect.center, AVATAR_BOARD_SIZE, font_avatar)
            _draw_loss_badge(surface, top_rect, Side.BLACK, loser_side, loss_badge_scale)
            caption = _draw_avatar_caption(
                surface,
                top_rect,
                black_player.get("display_name", "Player 2"),
                black_player.get("elo", DEFAULT_ELO),
                (30, 30, 120),
                font_avatar,
                align_left=True,
            )
            black_timer = _draw_timer_for_caption(surface, font_timer, caption, timer_labels.get("black"))
            if black_timer:
                timer_rects["black"] = black_timer
    elif mode == "ai":
        ai_info = last_sel.get("ai", {})
        human_id = ai_info.get("human_player_id", "p1")
        human_player = find_player(profiles_data, human_id)
        bottom_rect = get_bottom_avatar_rect()
        top_rect = get_top_avatar_rect()
        if human_player:
            draw_profile_avatar(surface, human_player, bottom_rect.center, AVATAR_BOARD_SIZE, font_avatar)
            _draw_loss_badge(surface, bottom_rect, Side.RED, loser_side, loss_badge_scale)
            caption = _draw_avatar_caption(
                surface,
                bottom_rect,
                human_player.get("display_name", "Player 1"),
                human_player.get("elo", DEFAULT_ELO),
                (200, 40, 40),
                font_avatar,
            )
            human_timer = _draw_timer_for_caption(surface, font_timer, caption, timer_labels.get("red"))
            if human_timer:
                timer_rects["red"] = human_timer
        if AI_LEVELS:
            ai_idx = ai_level_index % len(AI_LEVELS)
            ai_cfg = AI_LEVELS[ai_idx]
            draw_ai_avatar(surface, ai_cfg, top_rect.center, AVATAR_BOARD_SIZE, font_avatar)
            _draw_loss_badge(surface, top_rect, Side.BLACK, loser_side, loss_badge_scale)
            caption = _draw_avatar_caption(
                surface,
                top_rect,
                ai_cfg.get("name", "AI"),
                ai_cfg.get("elo", DEFAULT_ELO),
                (30, 30, 120),
                font_avatar,
                align_left=True,
            )
            ai_timer = _draw_timer_for_caption(surface, font_timer, caption, timer_labels.get("black"))
            if ai_timer:
                timer_rects["black"] = ai_timer
    return timer_rects
