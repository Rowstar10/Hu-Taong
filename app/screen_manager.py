class Screen_Manager:
    def __init__(self, root):
        self.root = root
        self.current = None

    def set(self, screen):
        if self.current:
            self.current.hide()
        self.current = screen
        self.current.show()
