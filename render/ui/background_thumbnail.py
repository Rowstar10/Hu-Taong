import pygame

class BackgroundThumbnail:

    def __init__(self, rect, image, action):

        self.rect = pygame.Rect(rect)
        self.image = image
        self.action = action
        self.hovered = False
        self._scaled = None
        
    def update(self, mouse_pos):

        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        image = self.image
        if image.get_size() != self.rect.size:  # layout may have shrunk the slot
            if self._scaled is None or self._scaled[0] is not image or self._scaled[1] != self.rect.size:
                self._scaled = (image, self.rect.size, pygame.transform.smoothscale(image, self.rect.size))
            image = self._scaled[2]
        screen.blit(image, self.rect)

        color = (255,255,0) if self.hovered else (200,200,200)

        pygame.draw.rect(screen, color, self.rect, 3)
