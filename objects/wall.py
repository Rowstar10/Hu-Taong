from objects.game_object import GameObject
from config import STATIC

class Wall(GameObject):
    body_type = STATIC
    is_wall = True

    def __init__(self, game, x0, y0, x1, y1, is_goal = False, is_separator = False):
        width = x1 - x0
        height = y1 - y0
        super().__init__(game, width, height, x0, y0,
                         inv_mass = 0, restitution = 0.8)
        
        self.id = None
        self.is_goal = is_goal
        self.is_separator = is_separator
