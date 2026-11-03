import pygame

class BackgroundThumbnail:

    def __init__(self, rect, image, action, art):

        self.rect = pygame.Rect(rect)
        self.image = image
        self.action = action
        self.art = art
        self.hovered = False
        self.selected = False
        self._scaled = None

    def update(self, mouse_pos):

        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        rect = self.rect.move(0, -4) if self.hovered else self.rect

        image = self.image
        if image.get_size() != rect.size:  # layout may have shrunk the slot
            if self._scaled is None or self._scaled[0] is not image or self._scaled[1] != rect.size:
                self._scaled = (image, rect.size, pygame.transform.smoothscale(image, rect.size))
            image = self._scaled[2]

        frame = self.art.frame(rect.w, rect.h, self.hovered)
        screen.blit(frame, (rect.x - 20, rect.y - 20))
        screen.blit(image, rect)

        if self.selected:
            pygame.draw.rect(screen, (226, 52, 44), rect.inflate(10, 10), 4)
            seal = self.art.seal(38, True)
            screen.blit(seal, (rect.right - 44, rect.top + 6))
