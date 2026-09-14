import math

PI = math.pi
TAU = 2 * math.pi


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def inv_lerp(a, b, x):
    return clamp((x - a) / (b - a)) if b != a else 0.0


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t ** 3


def ease_in_out(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t, s=1.70158):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_elastic(t):
    t = clamp(t)
    if t in (0.0, 1.0):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (TAU / 3)) + 1


def bounce(t):
    t = clamp(t)
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def hrand(*args):
    """Deterministic hash -> [0,1)."""
    h = 0x345678
    for a in args:
        v = int(a * 1000003) if isinstance(a, float) else int(a)
        h = (h ^ (v & 0xFFFFFFFF)) * 0x01000193 & 0xFFFFFFFF
        h ^= h >> 13
        h = h * 0x5BD1E995 & 0xFFFFFFFF
        h ^= h >> 15
    return (h & 0xFFFFFF) / float(0x1000000)


def hsign(*args):
    return hrand(*args) * 2 - 1


def pulse(t, center, width):
    """Triangle-ish bump around center with half-width."""
    d = abs(t - center) / width
    return clamp(1 - d)


def decay(t, t0, rate=8.0):
    """Exponential envelope starting at t0."""
    if t < t0:
        return 0.0
    return math.exp(-(t - t0) * rate)


def wobble(t, freq=1.0, seed=0):
    return (math.sin(t * freq * TAU + seed * 1.7) * 0.6 + math.sin(t * freq * 2.3 * TAU + seed * 3.1) * 0.4)
