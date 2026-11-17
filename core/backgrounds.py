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
        self.dim_jobs = OrderedDict()   # (name, dim) -> Future of a dimmed picture, baked on the worker
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

    def _dim(self, picture, dim):
        """The picture with `dim` baked in, exactly as get() bakes it (its own shade: this runs on
        the worker, while get()'s may be in use on the main thread)."""
        surf = picture.result().copy()
        shade = pygame.Surface(self.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, int(255 * dim)))
        surf.blit(shade, (0, 0))
        return surf

    # ---------- Asking for pictures (main thread) ----------

    def request(self, name, dim = None):
        """Start loading a picture without waiting for it, and, given the dim it will be shown at,
        baking that in too, so showing it later costs the main thread nothing."""
        if name not in self.pictures:
            self.pictures[name] = self.worker.submit(self._picture, name)
            self.trim()
        if dim and (name, dim) not in self.dim_jobs and not self.baked(name, dim):
            self.dim_jobs[(name, dim)] = self.worker.submit(self._dim, self.pictures[name], dim)
            while len(self.dim_jobs) > self.KEEP:
                self.dim_jobs.popitem(last = False)[1].cancel()

    def baked(self, name, dim):
        cached = self.dimmed.get(name)
        return cached is not None and cached[0] == dim

    def ready(self, name, dim = None):
        """Is the picture loaded (and, given a dim, baked at it)?"""
        future = self.pictures.get(name)
        if future is None or not future.done():
            return False
        if not dim or self.baked(name, dim):
            return True
        job = self.dim_jobs.get((name, dim))
        return job is not None and job.done()

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
            job = self.dim_jobs.pop((name, dim), None)
            if job is not None and job.done() and not job.cancelled() and job.exception() is None:
                surf = job.result()                        # baked on the worker already
            else:
                if job is not None:
                    job.cancel()
                surf = self.picture(name)
                if dim > 0:
                    surf = self._shade_main(surf, dim)
            cached = self.dimmed[name] = (dim, surf)
        self.dimmed.move_to_end(name)
        while len(self.dimmed) > self.KEEP:
            self.dimmed.popitem(last = False)
        return cached[1]

    def _shade_main(self, surf, dim):
        """Bake `dim` in on the main thread (when the worker hasn't), exactly as _dim does."""
        surf = surf.copy()
        if self.shade is None:
            self.shade = pygame.Surface(self.size, pygame.SRCALPHA)
        self.shade.fill((0, 0, 0, int(255 * dim)))
        surf.blit(self.shade, (0, 0))
        return surf

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
