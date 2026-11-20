"""A settings page that still doesn't fit scrolls (1.9, Rowan's 1.9 plan, phase 3, step 13b).

The layout decides whether a page scrolls and how far (render/ui/layout.py, UILayout.screen_menu
with scroll=True); this works it.  The mouse wheel scrolls it, and so does a finger sliding on a
phone (core/touch.py turns that into the wheel, a notch for every WHEEL_STEP it slides, so the page
keeps up with the finger), and the controller's right stick (core/gamepad.py, the wheel again).
The scrollbar can be dragged.  The menus' highlight scrolls the page to whatever it moves to
(core/gamepad.py Navigator calls reveal()).
"""
import pygame

WHEEL_STEP = 90         # px a notch of the wheel scrolls (core/touch.py's SCROLL_STEP, so a finger is followed)
MARGIN = 24             # px kept clear round a control the highlight scrolls to
EASE = 16.0             # 1/s: how quickly the page catches up with where it's scrolled to


class Scrolling:
    """Mix into a screen's state (before State) to let its page scroll."""

    scroll = 0.0            # how far down it's scrolled, in px (eases towards scroll_target)
    scroll_target = 0.0
    scroll_at = 0           # how far it was scrolled when last drawn
    max_scroll = 0          # set by the layout as it draws: 0 when the page fits
    scroll_view = None      # the part of the panel the page scrolls in
    scroll_track = None
    scroll_handle = None
    dragging_scroll = False
    grab = 0
    ui_whole = None         # every control's hitbox as drawn, on show or not

    def update(self, dt):
        super().update(dt)
        self.scroll_target = max(0.0, min(float(self.max_scroll), self.scroll_target))
        gap = self.scroll_target - self.scroll
        self.scroll = self.scroll_target if abs(gap) < 0.5 else self.scroll + gap * min(1.0, EASE * dt)

    def scroll_by(self, px):
        self.scroll_target = max(0.0, min(float(self.max_scroll), self.scroll_target + px))

    def scroll_event(self, event):
        """Scroll for the wheel or the scrollbar.  True if `event` was taken for it."""
        if not self.max_scroll:
            return False
        kind = event.type
        if kind == pygame.MOUSEWHEEL:
            self.scroll_by(-event.y * WHEEL_STEP)
            return True
        if kind == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.app.window_to_base(event.pos)
            if self.hit_test(pos) != "scrollbar" or self.scroll_track is None:
                return False
            handle = self.scroll_handle
            self.grab = pos[1] - handle.top if handle is not None and handle.collidepoint(pos) else \
                (handle.height // 2 if handle is not None else 0)
            self.dragging_scroll = True
            self.drag_to(pos[1])
            return True
        if kind == pygame.MOUSEMOTION and self.dragging_scroll:
            self.drag_to(self.app.window_to_base(event.pos)[1])
            return True
        if kind == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_scroll:
            self.dragging_scroll = False
            return True
        return False

    def drag_to(self, y):
        """The scrollbar's handle follows the pointer (straight away, no easing)."""
        track, handle = self.scroll_track, self.scroll_handle
        handle_h = handle.height if handle is not None else 0
        room = max(1, track.height - handle_h)
        share = max(0.0, min(1.0, (y - self.grab - track.top) / room))
        self.scroll = self.scroll_target = share * self.max_scroll

    def reveal(self, key):
        """Scroll so the control `key` is on show, with a little room round it."""
        whole = (self.ui_whole or {}).get(key)
        view = self.scroll_view
        if whole is None or view is None or not self.max_scroll:
            return
        at = self.scroll_at
        if whole.top - MARGIN < view.top:
            self.scroll_target = at - (view.top - (whole.top - MARGIN))
        elif whole.bottom + MARGIN > view.bottom:
            self.scroll_target = at + (whole.bottom + MARGIN - view.bottom)
        self.scroll_target = max(0.0, min(float(self.max_scroll), self.scroll_target))
