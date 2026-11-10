"""Courts: the stones a match starts with, picked on the Match Setup screen.

Every court is mirror-symmetric, so neither side has an advantage, keeps the serve spot in the
middle clear, and leaves no pocket a ball could rattle around in.  Each piece is
(centre x, centre y, width, height, patrol speed, style); a piece with a speed drifts up and down.
"""
import random
from dataclasses import dataclass

from config import BASE_W, BASE_H

MID_X, MID_Y = BASE_W / 2, BASE_H / 2


@dataclass(frozen=True)
class Court:
    name: str
    glyph: str
    about: str
    pieces: tuple


COURTS = (
    Court("Classic", "空", "The open court: nothing but you, the ball and the walls.", ()),
    Court("Twin Stones", "双", "Two tombstones on the centre line, above and below the serve.",
          ((MID_X, 270, 80, 170, 0, "tomb"), (MID_X, BASE_H - 270, 80, 170, 0, "tomb"))),
    Court("Graveyard", "墓", "Four small headstones, two in each half: angles off them are hard to read.",
          ((BASE_W * 0.34, 250, 66, 120, 0, "tomb"), (BASE_W * 0.34, BASE_H - 250, 66, 120, 0, "tomb"),
           (BASE_W * 0.66, 250, 66, 120, 0, "tomb"), (BASE_W * 0.66, BASE_H - 250, 66, 120, 0, "tomb"))),
    Court("Ferry Gates", "门", "Two lacquer pillars drift up and down in opposite directions mid-court.",
          ((BASE_W * 0.42, 300, 56, 200, 210, "pillar"), (BASE_W * 0.58, BASE_H - 300, 56, 200, -210, "pillar"))),
    Court("Narrow Pass", "隘", "Long stone walls close the middle from above and below; play through the gap.",
          ((MID_X, 165, 60, 330, 0, "pillar"), (MID_X, BASE_H - 165, 60, 330, 0, "pillar"))),
)
RANDOM = len(COURTS)                      # the last option: a different court each match
NAMES = [court.name for court in COURTS] + ["Random"]


def pick(index):
    """The court for a match: the one chosen, or any but Classic for Random."""
    if index >= len(COURTS):
        return random.choice(COURTS[1:])
    return COURTS[index]


def build(game, court):
    """Put the court's stones on the field; they stand for the whole match."""
    from objects.obstacle import Obstacle
    stones = []
    for cx, cy, w, h, speed, style in court.pieces:
        lo, hi = 110 + h / 2, BASE_H - 110 - h / 2
        stones.append(Obstacle(game, cx - w / 2, cy - h / 2, w, h, speed = speed, lo = lo, hi = hi, style = style))
    return stones
