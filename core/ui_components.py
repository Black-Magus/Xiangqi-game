import pygame
from typing import Optional


class Button:
    def __init__(self, rect: pygame.Rect, label: str = "", style: Optional[dict] = None):
        self.rect = rect
        self.label = label
        self.style = style or {}
        self.hovered = False

    def _create_vertical_gradient(self, size, top_color, bottom_color):
        width, height = size
        gradient = pygame.Surface((width, height), pygame.SRCALPHA)
        if height <= 1:
            gradient.fill(top_color)
            return gradient
        for y in range(height):
            t = y / (height - 1)
            color = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
            pygame.draw.line(gradient, color, (0, y), (width, y))
        return gradient

    def _draw_gradient(self, surface, font, enabled: bool):
        rect = self.rect
        style = self.style
        top_color, bottom_color = style.get("colors_enabled", ((200, 200, 200), (160, 160, 160)))
        if not enabled:
            top_color, bottom_color = style.get("colors_disabled", ((170, 170, 170), (120, 120, 120)))

        border_radius = style.get("border_radius", 8)
        border_color = style.get("border_color", (60, 60, 60))
        text_color = style.get("text_color_enabled", (0, 0, 0)) if enabled else style.get(
            "text_color_disabled", (70, 70, 70)
        )

        shadow_color = style.get("shadow_color")
        shadow_offset = style.get("shadow_offset", (0, 0))
        if style.get("shadow") and shadow_color:
            shadow_rect = rect.move(*shadow_offset)
            shadow_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(shadow_surface, shadow_color, shadow_surface.get_rect(), border_radius=border_radius)
            surface.blit(shadow_surface, shadow_rect.topleft)

        gradient = self._create_vertical_gradient(rect.size, top_color, bottom_color)
        if border_radius > 0:
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=border_radius)
            gradient.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(gradient, rect.topleft)

        if style.get("gloss"):
            gloss_height = max(6, rect.height // 2)
            gloss_rect = pygame.Rect(rect.x + 3, rect.y + 3, rect.width - 6, gloss_height)
            gloss_surface = pygame.Surface((gloss_rect.width, gloss_rect.height), pygame.SRCALPHA)
            gloss_color = style.get("gloss_color", (255, 255, 255, 70))
            pygame.draw.rect(
                gloss_surface,
                gloss_color,
                gloss_surface.get_rect(),
                border_radius=max(2, border_radius - 2),
            )
            surface.blit(gloss_surface, gloss_rect.topleft)

        pygame.draw.rect(surface, border_color, rect, 2, border_radius=border_radius)

        # Render label; support temporary bold toggling via style['bold']
        bold = style.get("bold", False)
        prev_bold = False
        if hasattr(font, "get_bold"):
            try:
                prev_bold = font.get_bold()
            except Exception:
                prev_bold = False
        if bold and hasattr(font, "set_bold"):
            try:
                font.set_bold(True)
            except Exception:
                pass
        text_surf = font.render(self.label, True, text_color)
        # restore bold state
        if hasattr(font, "set_bold"):
            try:
                font.set_bold(prev_bold)
            except Exception:
                pass
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def _draw_image_circle(self, surface, font, enabled: bool):
        rect = self.rect
        diameter = min(rect.width, rect.height)
        style = self.style
        bg_enabled = style.get("bg_enabled", (235, 235, 235))
        bg_disabled = style.get("bg_disabled", (180, 180, 180))
        border_color = style.get("border_color", (60, 60, 60))
        disabled_alpha = style.get("disabled_alpha", 170)
        angle = style.get("image_angle", 0)

        circle_surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        center = (diameter // 2, diameter // 2)

        img = style.get("image_surface")
        if img is not None:
            iw, ih = img.get_size()
            if iw > 0 and ih > 0:
                scale = max(diameter / iw, diameter / ih)
                target_size = (max(1, int(iw * scale)), max(1, int(ih * scale)))
                img_scaled = pygame.transform.smoothscale(img, target_size)
                draw_img = img_scaled
                if angle:
                    rotated = pygame.transform.rotozoom(draw_img, angle, 1.0)
                    rw, rh = rotated.get_size()
                    if rw > 0 and rh > 0:
                        fit_scale = min(diameter / rw, diameter / rh, 1.0)
                        if fit_scale != 1.0:
                            rotated = pygame.transform.smoothscale(
                                rotated,
                                (max(1, int(rw * fit_scale)), max(1, int(rh * fit_scale))),
                            )
                    draw_img = rotated
                img_rect = draw_img.get_rect(center=center)
                circle_surface.blit(draw_img, img_rect)
                mask = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
                pygame.draw.circle(mask, (255, 255, 255, 255), center, diameter // 2)
                circle_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            else:
                pygame.draw.circle(circle_surface, bg_enabled, center, diameter // 2)
        else:
            bg = bg_enabled if enabled else bg_disabled
            pygame.draw.circle(circle_surface, bg, center, diameter // 2)

        pygame.draw.circle(circle_surface, border_color, center, diameter // 2, 2)
        if not enabled:
            circle_surface.set_alpha(disabled_alpha)
        surface.blit(circle_surface, rect.topleft)

    def draw(self, surface, font, enabled: bool = True):
        # If hovered, we may apply a subtle overlay/highlight. The caller
        # should update `self.hovered` each frame based on mouse position.
        if self.style.get("variant") == "gradient":
            # Slightly brighten gradient when hovered
            if self.hovered:
                # Temporarily tweak colors in style without mutating original
                s = dict(self.style)
                ce = s.get("colors_enabled")
                if ce and isinstance(ce, tuple) and len(ce) >= 2:
                    def brighten(c, amount=14):
                        return tuple(min(255, max(0, x + amount)) for x in c)

                    s["colors_enabled"] = (brighten(ce[0]), brighten(ce[1]))
                # use _draw_gradient with modified style by temporarily swapping
                old_style = self.style
                try:
                    self.style = s
                    self._draw_gradient(surface, font, enabled)
                finally:
                    self.style = old_style
            else:
                self._draw_gradient(surface, font, enabled)
            return
        if self.style.get("variant") == "image_circle":
            self._draw_image_circle(surface, font, enabled)
            return

        bg = (200, 200, 200) if enabled else (160, 160, 160)
        border = (80, 80, 80)
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)
        if self.hovered:
            try:
                overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                overlay.fill((255, 255, 255, 28))
                surface.blit(overlay, self.rect.topleft)
                # also draw a subtle outer glow
                glow_color = self.style.get("hover_glow_color", (255, 255, 255))
                pygame.draw.rect(surface, glow_color, self.rect.inflate(6, 6), 2, border_radius=8)
            except Exception:
                pass
        text_color = (0, 0, 0)
        # Render label; support temporary bold toggling via style['bold']
        style = self.style
        bold = style.get("bold", False)
        prev_bold = False
        if hasattr(font, "get_bold"):
            try:
                prev_bold = font.get_bold()
            except Exception:
                prev_bold = False
        if bold and hasattr(font, "set_bold"):
            try:
                font.set_bold(True)
            except Exception:
                pass
        text_surf = font.render(self.label, True, text_color)
        if hasattr(font, "set_bold"):
            try:
                font.set_bold(prev_bold)
            except Exception:
                pass
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, pos) -> bool:
        return self.rect.collidepoint(pos)
