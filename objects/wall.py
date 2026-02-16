from objects.game_object import GameObject
from config import STATIC

class Wall(GameObject):
    body_type = STATIC
    is_wall = True

    def __init__(self, game, x0, y0, x1, y1, color = "White", is_goal = False, is_separator = False):
        width = x1 - x0
        height = y1 - y0
        super().__init__(game, width, height, x0, y0,
                         inv_mass = 0, restitution = 1)
        
        self.id = None
        self.is_goal = is_goal
        self.is_separator = is_separator

        if is_goal:
            self.id = self.canvas.create_rectangle(self.x0, self.y0,
                                                        self.x1, self.y1,
                                                        fill = color)
        if is_separator:
            self.id = self.canvas.create_line(self.x0, self.y0,
                                                        self.x1, self.y1,
                                                        fill = color,
                                                        dash = (5, 1))
