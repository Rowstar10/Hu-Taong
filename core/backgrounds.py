import pygame
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor

from config import BASE_W, BASE_H, IMAGE_DIR, BG_OVERSCAN


def finished(value):
    future = Future()
    future.set_result(value)
    return future


class Backgrounds:
    """The background pictures, decoded on a worker thread when they are wanted instead of all
    at start-up.  Decoding and smooth scaling let go of Python's lock, so the game keeps running
    while a picture loads, and only the last few full-size pictures stay in memory."""

    KEEP = 4
    THUMB_SIZE = 256, 144

    def __init__(self, app, names):
        self.size = BASE_W + 2 * BG_OVERSCAN[0], BASE_H + 2 * BG_OVERSCAN[1]
        self.vignette = app.art.vignette(*self.size, strength = 120)
        self.format = pygame.Surface((1, 1)).convert()    # the window's pixel format
        self.worker = ThreadPoolExecutor(max_workers = 1, thread_name_prefix = "backgrounds")

        self.pictures = OrderedDict()   # name -> Future of the full-size picture
        self.dimmed = OrderedDict()     # name -> (dim, picture with the dim setting baked in)
        self.shade = None

        # Thumbnails for the picker are made in the background straight away
        self.thumbs = {name: self.worker.submit(self._thumb, name) for name in names}

    # ---------- Building (worker thread) ----------

    def _load(self, name):
        return pygame.image.load(str(IMAGE_DIR / name)).convert(self.format)

    def _thumb(self, name):
        return pygame.transform.smoothscale(self._load(name), self.THUMB_SIZE)

    def _picture(self, name):
        full = pygame.transform.smoothscale(self._load(name), self.size)
        full.blit(self.vignette, (0, 0))
        return full

    # ---------- Asking for pictures (main thread) ----------

    def request(self, name):
        """Start loading a picture without waiting for it."""
        if name not in self.pictures:
            self.pictures[name] = self.worker.submit(self._picture, name)
            self.trim()

    def ready(self, name):
        future = self.pictures.get(name)
        return future is not None and future.done()

    def picture(self, name):
        """The full-size picture.  If the worker hasn't got to it yet it is made right now."""
        future = self.pictures.get(name)
        if future is None or not future.done():
            if future is not None:
                future.cancel()
            future = self.pictures[name] = finished(self._picture(name))
        self.pictures.move_to_end(name)
        self.trim()
        return future.result()

    def get(self, name, dim):
        """The picture with the Dim Background setting baked in, so it costs nothing per frame."""
        cached = self.dimmed.get(name)
        if cached is None or cached[0] != dim:
            surf = self.picture(name)
            if dim > 0:
                surf = surf.copy()
                if self.shade is None:
                    self.shade = pygame.Surface(self.size, pygame.SRCALPHA)
                self.shade.fill((0, 0, 0, int(255 * dim)))
                surf.blit(self.shade, (0, 0))
            cached = self.dimmed[name] = (dim, surf)
        self.dimmed.move_to_end(name)
        while len(self.dimmed) > self.KEEP:
            self.dimmed.popitem(last = False)
        return cached[1]

    def thumb(self, name):
        future = self.thumbs.get(name)
        if future is None or (not future.done() and future.cancel()):
            future = self.thumbs[name] = finished(self._thumb(name))
        return future.result()

    def trim(self):
        while len(self.pictures) > self.KEEP:
            _, future = self.pictures.popitem(last = False)
            future.cancel()

    def close(self):
        self.worker.shutdown(wait = True, cancel_futures = True)
