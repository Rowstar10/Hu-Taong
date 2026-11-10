"""The replay library: every match, clip and highlight you've saved, newest first."""
import pygame

from core.states.base_state import State
from game import replay


class ReplaysState(State):
    NAME = "replays"
    is_menu = True
    PER_PAGE = 7

    def __init__(self, app):
        super().__init__(app)
        self.page = 0
        self.refresh()

    def refresh(self):
        self.items = replay.saved_replays()
        most = max(0, (len(self.items) - 1) // self.PER_PAGE)
        self.page = min(self.page, most)
        self._laid = None                      # lay the screen out again for the new list

    def enter(self, **kwargs):
        super().enter(**kwargs)
        self.refresh()

    def shown(self):
        first = self.page * self.PER_PAGE
        return self.items[first:first + self.PER_PAGE]

    def draw(self, screen):
        super().draw(screen)
        self.app.renderer.draw_replays_menu(self, screen)

    def watch(self, path):
        clip = replay.Clip.load(path)
        if clip is None or not clip.frames:
            self.app.renderer.show_toast(f"{path.name} couldn't be read")
            return
        self.push_state("replay", clip = clip, mode = "viewer", saved = path)

    def delete(self, path):
        def action():
            try:
                path.unlink()
            except OSError as e:
                self.app.renderer.show_toast(f"Couldn't delete it: {e.strerror or e}")
            self.pop_state(mute = True)
            self.refresh()
        self.push_state("confirm_choice", action = action, header = "Delete this replay?", mute = True)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pop_state()
        if event.type == pygame.MOUSEWHEEL:
            self.turn(-event.y)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            key = self.hit_test(self.app.window_to_base(event.pos))
            shown = self.shown()
            if key and key.startswith("watch_"):
                index = int(key[6:])
                if index < len(shown):
                    self.watch(shown[index][0])
            elif key and key.startswith("delete_"):
                index = int(key[7:])
                if index < len(shown):
                    self.delete(shown[index][0])
            elif key == "page_left":
                self.turn(-1)
            elif key == "page_right":
                self.turn(1)
            elif key == "open_folder":
                self.open_folder()
            elif key == "back":
                self.pop_state()

    def turn(self, step):
        pages = max(1, (len(self.items) + self.PER_PAGE - 1) // self.PER_PAGE)
        page = max(0, min(pages - 1, self.page + step))
        if page != self.page:
            self.page = page
            self._laid = None

    def open_folder(self):
        folder = replay.replays_folder()
        folder.mkdir(parents = True, exist_ok = True)
        try:
            import os
            os.startfile(str(folder))
        except (OSError, AttributeError):
            self.app.renderer.show_toast(str(folder))
