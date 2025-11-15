import pygame


class Button:
    def __init__(self, rect: pygame.Rect, label: str = ""):
        self.rect = rect
        self.label = label

    def draw(self, surface, font, enabled: bool = True):
        bg = (200, 200, 200) if enabled else (160, 160, 160)
        border = (80, 80, 80)
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)
        text_color = (0, 0, 0)
        text_surf = font.render(self.label, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, pos) -> bool:
        return self.rect.collidepoint(pos)
