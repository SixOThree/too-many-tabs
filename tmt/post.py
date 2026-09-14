"""Per-frame pixel effects on BGRx uint8 arrays shaped (H, W, 4)."""
import io
import math

import numpy as np
from numba import njit
from PIL import Image, ImageEnhance


@njit(cache=True)
def _hash(x, y, s):
    h = (x * 374761393 + y * 668265263 + s * 2147483647) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


@njit(cache=True)
def vhs(arr, shift_r, shift_b, scan_h, scan_amt, noise_amt, seed, wobble_amp, wobble_phase, track_y, track_h):
    H, W = arr.shape[0], arr.shape[1]
    src = arr.copy()
    for y in range(H):
        wob = int(wobble_amp * math.sin(y * 0.013 + wobble_phase) + wobble_amp * 0.5 * math.sin(y * 0.041 + wobble_phase * 1.7))
        in_track = track_h > 0 and y >= track_y and y < track_y + track_h
        if in_track:
            wob += int(12 * _hash(0, y // 3, seed) * (1 if seed % 2 == 0 else -1)) * max(1, W // 1920)
        sl = 1.0
        if scan_h > 0 and (y // scan_h) % 2 == 1:
            sl = 1.0 - scan_amt
        for x in range(W):
            xr = x - shift_r - wob
            xg = x - wob
            xb = x + shift_b - wob
            if xr < 0:
                xr = 0
            elif xr >= W:
                xr = W - 1
            if xg < 0:
                xg = 0
            elif xg >= W:
                xg = W - 1
            if xb < 0:
                xb = 0
            elif xb >= W:
                xb = W - 1
            n = 0.0
            if noise_amt > 0:
                n = (_hash(x // max(1, W // 1920 * 2), y // max(1, W // 1920 * 2), seed) - 0.5) * noise_amt
            if in_track:
                n += (_hash(x // 4, y, seed + 7) - 0.4) * 55
            r = src[y, xr, 2] * sl + n
            g = src[y, xg, 1] * sl + n
            b = src[y, xb, 0] * sl + n
            arr[y, x, 2] = 255 if r > 255 else (0 if r < 0 else int(r))
            arr[y, x, 1] = 255 if g > 255 else (0 if g < 0 else int(g))
            arr[y, x, 0] = 255 if b > 255 else (0 if b < 0 else int(b))


@njit(cache=True)
def flash(arr, amt, cr, cg, cb):
    H, W = arr.shape[0], arr.shape[1]
    for y in range(H):
        for x in range(W):
            arr[y, x, 2] = int(arr[y, x, 2] + (cr - arr[y, x, 2]) * amt)
            arr[y, x, 1] = int(arr[y, x, 1] + (cg - arr[y, x, 1]) * amt)
            arr[y, x, 0] = int(arr[y, x, 0] + (cb - arr[y, x, 0]) * amt)


@njit(cache=True)
def hue_rotate(arr, ang):
    c = math.cos(ang)
    s = math.sin(ang)
    k = 1.0 / 3.0
    sq = math.sqrt(k)
    m00 = c + (1 - c) * k
    m01 = k * (1 - c) - sq * s
    m02 = k * (1 - c) + sq * s
    m10 = k * (1 - c) + sq * s
    m11 = c + k * (1 - c)
    m12 = k * (1 - c) - sq * s
    m20 = k * (1 - c) - sq * s
    m21 = k * (1 - c) + sq * s
    m22 = c + k * (1 - c)
    H, W = arr.shape[0], arr.shape[1]
    for y in range(H):
        for x in range(W):
            r = arr[y, x, 2]
            g = arr[y, x, 1]
            b = arr[y, x, 0]
            nr = r * m00 + g * m01 + b * m02
            ng = r * m10 + g * m11 + b * m12
            nb = r * m20 + g * m21 + b * m22
            arr[y, x, 2] = 255 if nr > 255 else (0 if nr < 0 else int(nr))
            arr[y, x, 1] = 255 if ng > 255 else (0 if ng < 0 else int(ng))
            arr[y, x, 0] = 255 if nb > 255 else (0 if nb < 0 else int(nb))


@njit(cache=True)
def grade(arr, sat, contrast, bright, tr, tg, tb, tint):
    H, W = arr.shape[0], arr.shape[1]
    for y in range(H):
        for x in range(W):
            r = arr[y, x, 2] / 255.0
            g = arr[y, x, 1] / 255.0
            b = arr[y, x, 0] / 255.0
            l = 0.3 * r + 0.59 * g + 0.11 * b
            r = l + (r - l) * sat
            g = l + (g - l) * sat
            b = l + (b - l) * sat
            r = (r - 0.5) * contrast + 0.5 + bright
            g = (g - 0.5) * contrast + 0.5 + bright
            b = (b - 0.5) * contrast + 0.5 + bright
            if tint > 0:
                r = r * (1 - tint) + l * tr * tint
                g = g * (1 - tint) + l * tg * tint
                b = b * (1 - tint) + l * tb * tint
            r *= 255
            g *= 255
            b *= 255
            arr[y, x, 2] = 255 if r > 255 else (0 if r < 0 else int(r))
            arr[y, x, 1] = 255 if g > 255 else (0 if g < 0 else int(g))
            arr[y, x, 0] = 255 if b > 255 else (0 if b < 0 else int(b))


@njit(cache=True)
def melt(arr, amount, seed, t):
    H, W = arr.shape[0], arr.shape[1]
    src = arr.copy()
    block = max(1, W // 160)
    for x in range(W):
        col = x // block
        d = int(amount * H * (_hash(col, 0, seed) ** 2) * (0.6 + 0.4 * math.sin(t * 3 + col * 0.3)))
        for y in range(H):
            sy = y - d
            if sy < 0:
                arr[y, x, 0] = src[0, x, 0] // 2
                arr[y, x, 1] = src[0, x, 1] // 3
                arr[y, x, 2] = min(255, src[0, x, 2] + 40)
            else:
                arr[y, x, 0] = src[sy, x, 0]
                arr[y, x, 1] = src[sy, x, 1]
                arr[y, x, 2] = src[sy, x, 2]


@njit(cache=True)
def slices(arr, seed, count, maxshift):
    H, W = arr.shape[0], arr.shape[1]
    src = arr.copy()
    for k in range(count):
        y0 = int(_hash(k, 1, seed) * H)
        h = int(4 + _hash(k, 2, seed) * H * 0.06)
        dx = int((_hash(k, 3, seed) - 0.5) * 2 * maxshift)
        for y in range(y0, min(H, y0 + h)):
            for x in range(W):
                sx = (x - dx) % W
                arr[y, x, 0] = src[y, sx, 0]
                arr[y, x, 1] = src[y, sx, 1]
                arr[y, x, 2] = src[y, sx, 2]


def invert(arr):
    np.bitwise_not(arr[..., :3], out=arr[..., :3])


def mirror(arr):
    W = arr.shape[1]
    h = W // 2
    arr[:, W - h:] = arr[:, :h][:, ::-1]


def kaleido(arr):
    mirror(arr)
    H = arr.shape[0]
    h = H // 2
    arr[H - h:] = arr[:h][::-1]


def fry(arr, q=8):
    H, W = arr.shape[0], arr.shape[1]
    im = Image.frombuffer('RGBX', (W, H), arr.tobytes(), 'raw', 'BGRX').convert('RGB')
    im = ImageEnhance.Color(im).enhance(3.2)
    im = ImageEnhance.Contrast(im).enhance(1.7)
    im = ImageEnhance.Sharpness(im).enhance(6.0)
    small = im.resize((W // 3, H // 3), Image.BILINEAR)
    buf = io.BytesIO()
    small.save(buf, 'JPEG', quality=q)
    buf.seek(0)
    im = Image.open(buf).convert('RGB').resize((W, H), Image.NEAREST)
    a = np.asarray(im)
    arr[..., 2] = a[..., 0]
    arr[..., 1] = a[..., 1]
    arr[..., 0] = a[..., 2]


def posterize(arr, bits=3):
    sh = 8 - bits
    arr[..., :3] = (arr[..., :3] >> sh) << sh
