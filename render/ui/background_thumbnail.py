import pygame

class BackgroundThumbnail:

    def __init__(self, rect, image, action):

        self.rect = pygame.Rect(rect)
        self.image = image
        self.action = action
        self.hovered = False
        
    def update(self, mouse_pos):

        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        screen.blit(self.image, self.rect)

        color = (255,255,0) if self.hovered else (200,200,200)

        pygame.draw.rect(screen, color, self.rect, 3)
