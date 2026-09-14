"""Instruments, effects and sound effects. Everything mono float32 at SR unless noted."""
import math

import numpy as np
from numba import njit
from scipy import signal

from .config import SR

_rng = np.random.default_rng(7)


def N(dur):
    return max(1, int(round(dur * SR)))


def tarr(n):
    return np.arange(n, dtype=np.float64) / SR


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def noise(n, seed=None):
    r = np.random.default_rng(seed) if seed is not None else _rng
    return r.uniform(-1, 1, n).astype(np.float32)


# ---------------------------------------------------------------- oscillators

def saw(f, n, ph0=0.0):
    f = np.broadcast_to(np.asarray(f, np.float64), (n,))
    dt = f / SR
    ph = (ph0 + np.cumsum(dt)) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    t = ph[m] / dt[m]
    y[m] -= t + t - t * t - 1
    m = ph > 1 - dt
    t = (ph[m] - 1) / dt[m]
    y[m] -= t * t + t + t + 1
    return y.astype(np.float32)


def square(f, n, duty=0.5, ph0=0.0):
    return (saw(f, n, ph0) - saw(f, n, ph0 + duty)) * 0.5


def sine(f, n, ph0=0.0):
    f = np.broadcast_to(np.asarray(f, np.float64), (n,))
    return np.sin(2 * np.pi * (ph0 + np.cumsum(f / SR))).astype(np.float32)


def tri(f, n):
    f = np.broadcast_to(np.asarray(f, np.float64), (n,))
    ph = np.cumsum(f / SR) % 1.0
    return (4 * np.abs(ph - 0.5) - 1).astype(np.float32)


# ---------------------------------------------------------------- filters

def _sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output='sos')


def lp(x, f, order=2):
    return signal.sosfilt(_sos('low', min(f, SR * 0.45), order), x).astype(np.float32)


def hp(x, f, order=2):
    return signal.sosfilt(_sos('high', f, order), x).astype(np.float32)


def bp(x, f1, f2, order=2):
    return signal.sosfilt(signal.butter(order, [f1, min(f2, SR * 0.45)], btype='band', fs=SR, output='sos'),
                          x).astype(np.float32)


@njit(cache=True)
def _svf(x, cutoff, q, mode):
    n = len(x)
    y = np.zeros(n, np.float32)
    low = 0.0
    band = 0.0
    damp = 1.0 / q
    for i in range(n):
        fc = cutoff[i]
        if fc > 16000.0:
            fc = 16000.0
        if fc < 20.0:
            fc = 20.0
        f = 2.0 * math.sin(math.pi * fc / (2.0 * 48000.0))
        for _ in range(2):  # 2x oversampled
            low = low + f * band
            high = x[i] - low - damp * band
            band = f * high + band
        if mode == 0:
            y[i] = low
        elif mode == 1:
            y[i] = band
        else:
            y[i] = high
    return y


def svf_lp(x, cutoff, q=0.9):
    c = np.broadcast_to(np.asarray(cutoff, np.float32), (len(x),)).astype(np.float32)
    return _svf(x.astype(np.float32), c, q, 0)


def svf_bp(x, cutoff, q=2.0):
    c = np.broadcast_to(np.asarray(cutoff, np.float32), (len(x),)).astype(np.float32)
    return _svf(x.astype(np.float32), c, q, 1)


def peaking(x, f0, gain_db, q=1.0):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]
    return signal.lfilter(b, a, x).astype(np.float32)


# ---------------------------------------------------------------- envelopes

def env_adsr(n, a=0.005, d=0.1, s=0.7, r=0.05, gate=None):
    gate = n / SR if gate is None else gate
    t = tarr(n)
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = np.clip(1 - (t - gate) / max(r, 1e-6), 0, 1)
    e = np.where(t > gate, e * rel, e)
    return e.astype(np.float32)


def env_exp(n, decay, attack=0.002):
    t = tarr(n)
    return (np.minimum(1, t / attack) * np.exp(-t / decay)).astype(np.float32)


# ---------------------------------------------------------------- reverb / delay

_COMBS = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
_APS = [556, 441, 341, 225]


@njit(cache=True)
def _freeverb(x, room, damp, spread):
    n = len(x)
    y = np.zeros(n, np.float32)
    combs = np.array([1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]) + spread
    combs = (combs * 48000 // 44100)
    aps = (np.array([556, 441, 341, 225]) + spread) * 48000 // 44100
    cbuf = np.zeros((8, combs.max() + 1), np.float32)
    cidx = np.zeros(8, np.int64)
    cfilt = np.zeros(8, np.float32)
    abuf = np.zeros((4, aps.max() + 1), np.float32)
    aidx = np.zeros(4, np.int64)
    fb = room * 0.28 + 0.7
    d1 = damp * 0.4
    d2 = 1 - d1
    for i in range(n):
        inp = x[i] * 0.015
        out = 0.0
        for c in range(8):
            L = combs[c]
            o = cbuf[c, cidx[c]]
            cfilt[c] = o * d2 + cfilt[c] * d1
            cbuf[c, cidx[c]] = inp + cfilt[c] * fb
            cidx[c] += 1
            if cidx[c] >= L:
                cidx[c] = 0
            out += o
        for a in range(4):
            L = aps[a]
            bo = abuf[a, aidx[a]]
            v = -out + bo
            abuf[a, aidx[a]] = out + bo * 0.5
            aidx[a] += 1
            if aidx[a] >= L:
                aidx[a] = 0
            out = v
        y[i] = out
    return y


def reverb(x, room=0.8, damp=0.5, tail=2.0):
    """Mono in -> stereo (2,n) wet only."""
    xx = np.concatenate([x.astype(np.float32), np.zeros(N(tail), np.float32)])
    l = _freeverb(xx, room, damp, 0)
    r = _freeverb(xx, room, damp, 23)
    return np.stack([l, r])


def delay(x, time, fb=0.35, n=4, mix=0.35):
    d = N(time)
    out = np.zeros(len(x) + d * n, np.float32)
    out[:len(x)] += x
    g = mix
    for k in range(1, n + 1):
        out[d * k:d * k + len(x)] += x * g
        g *= fb
    return out


# ---------------------------------------------------------------- utilities

def pan(x, p=0.0):
    """mono -> stereo with constant-power pan, p in [-1,1]."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)]).astype(np.float32)


def resample(x, ratio):
    """ratio>1 -> faster/higher."""
    n = int(len(x) / ratio)
    if n < 2:
        return np.zeros(1, np.float32)
    idx = np.arange(n) * ratio
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


def pitch(x, semis):
    return resample(x, 2 ** (semis / 12))


def softclip(x, drive=1.0):
    return (np.tanh(x * drive) / np.tanh(drive)).astype(np.float32)


def bitcrush(x, bits=6, down=4):
    q = 2 ** bits
    y = np.round(x * q) / q
    if down > 1:
        y = np.repeat(y[::down], down)[:len(x)]
    return y.astype(np.float32)


def fade(x, fin=0.005, fout=0.01):
    x = x.copy()
    a, b = min(len(x), N(fin)), min(len(x), N(fout))
    if a:
        x[..., :a] *= np.linspace(0, 1, a)
    if b:
        x[..., -b:] *= np.linspace(1, 0, b)
    return x


def tape_stop(x, dur=None):
    """Slow the signal to a halt over its length (stereo or mono)."""
    mono = x.ndim == 1
    xs = x[None] if mono else x
    n = xs.shape[-1]
    rate = np.linspace(1, 0, n) ** 1.3
    pos = np.cumsum(rate)
    pos = pos[pos < n - 1]
    out = np.stack([np.interp(pos, np.arange(n), ch) for ch in xs]).astype(np.float32)
    out = np.concatenate([out, np.zeros((out.shape[0], n - out.shape[1]), np.float32)], axis=1)
    return out[0] if mono else out


# ---------------------------------------------------------------- drums

def kick(vel=1.0):
    n = N(0.5)
    t = tarr(n)
    f = 48 + 130 * np.exp(-t / 0.035)
    y = np.sin(2 * np.pi * np.cumsum(f / SR)) * np.exp(-t / 0.3)
    y += hp(noise(n), 3000) * np.exp(-t / 0.004) * 0.5
    return softclip(y.astype(np.float32) * vel, 1.6)


def snare(vel=1.0):
    n = N(0.45)
    t = tarr(n)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.07) * 0.6 + np.sin(2 * np.pi * 320 * t) * np.exp(-t / 0.04) * 0.3
    nz = bp(noise(n), 1200, 9000) * np.exp(-t / 0.13) * 1.1
    return ((tone + nz) * vel).astype(np.float32)


def clap(vel=1.0):
    n = N(0.35)
    t = tarr(n)
    e = np.zeros(n)
    for k, d in enumerate((0.0, 0.012, 0.024)):
        e += np.where(t >= d, np.exp(-(t - d) / 0.006), 0)
    e += np.where(t >= 0.03, np.exp(-(t - 0.03) / 0.09) * 0.6, 0)
    return (bp(noise(n), 900, 3500) * e * vel * 1.3).astype(np.float32)


def hat(open_=False, vel=1.0):
    n = N(0.4 if open_ else 0.08)
    t = tarr(n)
    ratios = [2.0, 3.0, 4.16, 5.43, 6.79, 8.21]
    m = sum(square(40 * r * 8, n) for r in ratios) / 6
    y = hp(m * 0.6 + noise(n) * 0.5, 7000) * np.exp(-t / (0.22 if open_ else 0.025))
    return (y * vel).astype(np.float32)


def shaker(vel=1.0):
    n = N(0.09)
    t = tarr(n)
    e = np.minimum(1, t / 0.02) * np.exp(-t / 0.03)
    return (bp(noise(n), 5000, 14000) * e * vel).astype(np.float32)


def crash(vel=1.0, dur=2.5):
    n = N(dur)
    t = tarr(n)
    ratios = [1.0, 1.47, 1.93, 2.61, 3.37, 4.9, 6.1]
    m = sum(square(310 * r, n) for r in ratios) / 7
    y = hp(m * 0.5 + noise(n), 4000) * np.exp(-t / (dur * 0.35))
    return (y * vel * 0.8).astype(np.float32)


def tom(f=110, vel=1.0):
    n = N(0.45)
    t = tarr(n)
    ff = f * (1 + 0.6 * np.exp(-t / 0.04))
    y = np.sin(2 * np.pi * np.cumsum(ff / SR)) * np.exp(-t / 0.22)
    y += bp(noise(n), 200, 2000) * np.exp(-t / 0.03) * 0.3
    return (y * vel).astype(np.float32)


def orch_hit(root=62, vel=1.0):
    n = N(0.9)
    t = tarr(n)
    y = np.zeros(n, np.float32)
    for m in (root - 12, root, root + 4, root + 7, root + 12):
        fdrop = hz(m) * (1 + 0.05 * np.exp(-t / 0.05))
        y += saw(fdrop, n) * 0.25
    y = svf_lp(y, 800 + 7000 * np.exp(-t / 0.12), 0.8)
    y += bp(noise(n), 300, 5000) * np.exp(-t / 0.05) * 0.6
    return (y * np.exp(-t / 0.3) * vel).astype(np.float32)


def boom(vel=1.0, dur=1.6):
    n = N(dur)
    t = tarr(n)
    f = 28 + 70 * np.exp(-t / 0.15)
    y = np.sin(2 * np.pi * np.cumsum(f / SR)) * np.exp(-t / (dur * 0.35))
    y += lp(noise(n), 400) * np.exp(-t / 0.3) * 0.6
    return softclip(y.astype(np.float32) * vel, 2.0)


# ---------------------------------------------------------------- tonal instruments

def bass_pluck(m, dur, vel=1.0, bright=1.0):
    n = N(dur + 0.08)
    t = tarr(n)
    f = hz(m)
    x = saw(f, n) * 0.7 + square(f * 0.5, n) * 0.5
    cut = 180 + 2600 * bright * np.exp(-t / 0.09)
    y = svf_lp(x, cut.astype(np.float32), 1.2)
    return (y * env_adsr(n, 0.003, 0.25, 0.6, 0.05, dur) * vel).astype(np.float32)


def epiano(m, dur, vel=1.0):
    n = N(dur + 0.6)
    t = tarr(n)
    f = hz(m)
    I = 1.6 * np.exp(-t / 0.45) * vel + 0.25
    mod = np.sin(2 * np.pi * f * t) * I
    y = np.sin(2 * np.pi * f * t + mod)
    if f * 14 < 18000:
        y += np.sin(2 * np.pi * f * 14 * t) * 0.15 * np.exp(-t / 0.04) * vel
    y *= np.exp(-t / 1.6)
    rel = np.clip(1 - (t - dur) / 0.25, 0, 1)
    y *= np.where(t > dur, rel, 1)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    return (y * trem * vel * 0.5).astype(np.float32)


def pad(ms, dur, vel=1.0, cutoff=2400, attack=0.25, release=0.5):
    n = N(dur + release)
    t = tarr(n)
    y = np.zeros(n, np.float32)
    for i, m in enumerate(ms):
        for d in (-0.09, 0.0, 0.1):
            y += saw(hz(m + d) * (1 + 0.002 * np.sin(2 * np.pi * (0.3 + 0.1 * i) * t)), n, ph0=_rng.random())
    y /= max(1, len(ms)) * 3
    y = svf_lp(y, (cutoff * (1 + 0.25 * np.sin(2 * np.pi * 0.2 * t))).astype(np.float32), 0.7)
    return (y * env_adsr(n, attack, 0.5, 0.85, release, dur) * vel).astype(np.float32)


def supersaw(ms, dur, vel=1.0, cutoff=6000):
    n = N(dur + 0.2)
    t = tarr(n)
    y = np.zeros(n, np.float32)
    for m in ms:
        for d in (-0.25, -0.15, -0.05, 0.0, 0.06, 0.14, 0.24):
            y += saw(hz(m + d), n, ph0=_rng.random())
    y /= max(1, len(ms)) * 5
    y = svf_lp(y, cutoff, 0.7)
    return (y * env_adsr(n, 0.005, 0.3, 0.7, 0.15, dur) * vel).astype(np.float32)


def brass(m, dur, vel=1.0):
    n = N(dur + 0.15)
    t = tarr(n)
    f = hz(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.25) / 0.2, 0, 1))
    x = saw(f * 2 ** (-5 / 1200), n) + saw(f * 2 ** (6 / 1200), n)
    cut = 500 + 4200 * np.minimum(1, t / 0.035) * (0.55 + 0.45 * np.exp(-t / 0.18))
    y = svf_lp(x, cut.astype(np.float32), 1.1)
    return (y * env_adsr(n, 0.012, 0.2, 0.75, 0.1, dur) * vel * 0.45).astype(np.float32)


def sax(m, dur, vel=1.0):
    n = N(dur + 0.12)
    t = tarr(n)
    scoop = -0.7 * np.exp(-t / 0.04)
    vib = 0.18 * np.sin(2 * np.pi * 5.3 * t) * np.clip((t - 0.15) / 0.25, 0, 1)
    f = hz(m + scoop + vib)
    x = saw(f, n) * 0.6 + square(f, n, 0.3) * 0.5
    x += noise(n) * 0.04
    y = svf_lp(x, (1800 + 1500 * np.minimum(1, t / 0.05)), 0.8)
    y = peaking(y, 1200, 6, 1.5)
    y = hp(y, 220)
    return (softclip(y * env_adsr(n, 0.02, 0.3, 0.8, 0.08, dur) * vel, 1.4) * 0.5).astype(np.float32)


def bell(m, dur=1.5, vel=1.0):
    n = N(dur)
    t = tarr(n)
    f = hz(m)
    y = np.sin(2 * np.pi * f * t + 2.2 * np.exp(-t / 0.6) * np.sin(2 * np.pi * f * 3.5 * t))
    return (y * np.exp(-t / (dur * 0.45)) * env_exp(n, 10, 0.002) * vel * 0.4).astype(np.float32)


def music_box(m, dur=1.4, vel=1.0):
    n = N(dur)
    t = tarr(n)
    f = hz(m) * (1 + 0.003 * np.sin(2 * np.pi * 3 * t))
    y = np.sin(2 * np.pi * np.cumsum(f / SR)) + 0.25 * np.sin(2 * np.pi * np.cumsum(4.02 * f / SR)) * np.exp(-t / 0.2)
    return (y * np.exp(-t / 0.7) * vel * 0.4).astype(np.float32)


def piano(m, dur, vel=0.8):
    n = N(dur + 1.2)
    t = tarr(n)
    f = hz(m)
    y = np.zeros(n)
    B = 0.0004
    for k in range(1, 13):
        fk = k * f * math.sqrt(1 + B * k * k)
        if fk > 16000:
            break
        amp = (1 / k ** 1.25) * (0.6 + 0.4 * vel)
        y += amp * np.sin(2 * np.pi * fk * t + k) * np.exp(-t * (0.5 + 0.28 * k * (0.6 + vel)))
    y += lp(noise(n), 3000) * np.exp(-t / 0.01) * 0.1 * vel
    rel = np.clip(1 - (t - dur) / 0.35, 0, 1)
    y *= np.where(t > dur, rel, 1)
    return (y * vel * 0.35).astype(np.float32)


def chip_square(m, dur, duty=0.25, vel=1.0, vib=0.0):
    n = N(dur)
    t = tarr(n)
    f = hz(m + vib * np.sin(2 * np.pi * 6 * t) * np.clip((t - 0.1) / 0.1, 0, 1))
    y = np.sign(square(f, n, duty))
    y = np.round(y * 7) / 7
    return (y * env_adsr(n, 0.002, 0.2, 0.7, 0.01, dur) * vel * 0.3).astype(np.float32)


def chip_tri(m, dur, vel=1.0):
    n = N(dur)
    y = tri(hz(m), n)
    y = np.round(y * 7.5) / 7.5
    return (y * env_adsr(n, 0.002, 0.1, 0.95, 0.01, dur) * vel * 0.5).astype(np.float32)


def chip_noise(dur, vel=1.0, period=4, decay=0.06):
    n = N(dur)
    k = max(1, period)
    v = np.repeat(np.sign(noise(n // k + 1)), k)[:n]
    return (v * env_exp(n, decay, 0.001) * vel * 0.3).astype(np.float32)


def arp_saw(m, dur, vel=1.0, cutoff=2600):
    n = N(dur + 0.05)
    t = tarr(n)
    x = saw(hz(m), n) + 0.5 * square(hz(m) * 1.003, n, 0.5)
    y = svf_lp(x, (400 + cutoff * np.exp(-t / 0.1)).astype(np.float32), 1.6)
    return (y * env_adsr(n, 0.002, 0.1, 0.4, 0.04, dur) * vel * 0.4).astype(np.float32)


# ---------------------------------------------------------------- sound effects

def sfx_pop(p=1.0, vel=1.0):
    n = N(0.18)
    t = tarr(n)
    f = 500 * p * (0.6 + 1.2 * (1 - np.exp(-t / 0.025)))
    y = np.sin(2 * np.pi * np.cumsum(f / SR)) * np.exp(-t / 0.05)
    y += hp(noise(n), 4000) * np.exp(-t / 0.003) * 0.3
    return (y * vel * 0.8).astype(np.float32)


def sfx_click(vel=1.0):
    n = N(0.04)
    t = tarr(n)
    y = hp(noise(n), 2500) * np.exp(-t / 0.0025) + np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.004) * 0.5
    return (y * vel).astype(np.float32)


def sfx_key(vel=1.0):
    n = N(0.08)
    t = tarr(n)
    y = bp(noise(n), 1800, 6000) * np.exp(-t / 0.012) + np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.015) * 0.6
    return (y * vel * 0.8).astype(np.float32)


def sfx_whoosh(dur=0.5, vel=1.0, up=True):
    n = N(dur)
    t = tarr(n) / dur
    c = 300 + 3500 * (np.sin(np.pi * t) if not up else t ** 1.5)
    y = svf_bp(noise(n), c.astype(np.float32), 1.5)
    return (y * np.sin(np.pi * t) ** 2 * vel * 1.2).astype(np.float32)


def sfx_scratch(dur=0.45, vel=1.0):
    n = N(dur)
    t = tarr(n)
    mod = np.sin(2 * np.pi * (4 + 10 * t / dur) * t)
    c = 900 + 700 * mod
    y = svf_bp(noise(n), c.astype(np.float32), 3.0) * (0.5 + 0.5 * np.abs(mod))
    y += saw(160 * (1 + 0.6 * mod), n) * 0.25 * np.abs(mod)
    return (y * np.exp(-t / dur) * vel).astype(np.float32)


def sfx_ding(vel=1.0, p=1.0):
    n = N(1.2)
    t = tarr(n)
    y = np.zeros(n)
    for f, a, d in ((1318.5, 1.0, 0.5), (2637, 0.4, 0.25), (1760 * 1.0, 0.0, 0.3)):
        y += a * np.sin(2 * np.pi * f * p * t) * np.exp(-t / d)
    y2 = np.where(t > 0.12, np.sin(2 * np.pi * 1760 * p * (t - 0.12)) * np.exp(-(t - 0.12) / 0.5), 0)
    return ((y + y2) * vel * 0.3).astype(np.float32)


def sfx_error(vel=1.0):
    n = N(0.45)
    t = tarr(n)
    y = square(110, n) + square(116, n)
    y = lp(y, 1500) * env_adsr(n, 0.005, 0.1, 0.9, 0.05, 0.38)
    return (y * vel * 0.35).astype(np.float32)


def sfx_squeak(vel=1.0, p=1.0):
    n = N(0.14)
    t = tarr(n)
    f = (1900 + 1500 * np.sin(np.pi * t / 0.14)) * p
    return (np.sin(2 * np.pi * np.cumsum(f / SR)) * np.sin(np.pi * t / 0.14) * vel * 0.3).astype(np.float32)


def sfx_boing(vel=1.0):
    n = N(0.6)
    t = tarr(n)
    f = 180 + 120 * np.sin(2 * np.pi * 9 * t) * np.exp(-t / 0.2) + 200 * np.exp(-t / 0.1)
    return (np.sin(2 * np.pi * np.cumsum(f / SR)) * np.exp(-t / 0.25) * vel * 0.6).astype(np.float32)


def sfx_fan(dur, vel=1.0, f0=300, f1=2200):
    n = N(dur)
    t = tarr(n) / dur
    f = f0 + (f1 - f0) * t ** 2
    y = saw(f, n) * 0.15 + saw(f * 1.5, n) * 0.08
    y = lp(y, 5000)
    y += bp(noise(n), 800, 6000) * (0.3 + 0.7 * t)
    return (y * t * vel * 0.5).astype(np.float32)


def sfx_power_down(dur=1.4, vel=1.0):
    n = N(dur)
    t = tarr(n) / dur
    f = 900 * (1 - t) ** 2.5 + 30
    y = saw(f, n) * 0.4 + np.sin(2 * np.pi * np.cumsum(f * 0.5 / SR)) * 0.5
    return (lp(y, 3000) * (1 - t) * vel * 0.6).astype(np.float32)


def sfx_explosion(vel=1.0, dur=2.2):
    n = N(dur)
    t = tarr(n)
    y = lp(noise(n), 1200) * np.exp(-t / 0.5) * 1.2 + boom(1.0, dur)[:n]
    return softclip(y.astype(np.float32) * vel, 1.8)


def sfx_thunder(vel=1.0, dur=3.0):
    n = N(dur)
    t = tarr(n)
    b = np.cumsum(noise(n))
    b = hp(b / (np.abs(b).max() + 1e-9), 30)
    crack = hp(noise(n), 1500) * np.exp(-t / 0.08)
    rumble = lp(noise(n), 250) * (np.exp(-t / 1.0) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t)))
    return softclip((crack * 0.8 + rumble * 2.0 + b * 0.5 * np.exp(-t / 1.2)) * vel, 1.5)


def sfx_riser(dur, vel=1.0):
    n = N(dur)
    t = tarr(n) / dur
    y = svf_bp(noise(n), (300 + 9000 * t ** 2).astype(np.float32), 2.0) * t ** 1.5
    y += saw(80 * 2 ** (4 * t), n) * 0.2 * t ** 2
    return (y * vel).astype(np.float32)


def sfx_glitch(dur=0.3, vel=1.0, seed=0):
    n = N(dur)
    r = np.random.default_rng(seed)
    y = np.zeros(n, np.float32)
    pos = 0
    while pos < n:
        L = int(r.integers(200, 2400))
        kind = r.integers(0, 3)
        if kind == 0:
            seg = square(r.uniform(80, 3000), L)
        elif kind == 1:
            seg = noise(L) * r.uniform(0.2, 1)
        else:
            seg = np.zeros(L, np.float32)
        y[pos:pos + L] = seg[:max(0, min(L, n - pos))]
        pos += L
    return bitcrush(y * vel * 0.5, 4, 3)


def sfx_hum(dur, vel=1.0):
    n = N(dur)
    t = tarr(n)
    y = sum(np.sin(2 * np.pi * 60 * k * t) / k for k in (1, 2, 3, 5))
    return (y * vel * 0.15).astype(np.float32)


def sfx_static(dur, vel=1.0):
    n = N(dur)
    return (hp(noise(n), 2000) * vel * 0.25).astype(np.float32)


def sfx_freeze(vel=1.0):
    """Freeze-frame whomp: reverse swell + thump."""
    n = N(0.35)
    t = tarr(n)
    sw = hp(noise(n), 1500) * (t / 0.35) ** 3
    th = np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.08)
    return ((sw * 0.4)[::-1][:n] * 0 + sw * 0.35 + th * 0.0).astype(np.float32) * vel


def sfx_shutter(vel=1.0):
    n = N(0.22)
    t = tarr(n)
    y = bp(noise(n), 1500, 8000) * (np.exp(-t / 0.01) + np.where(t > 0.07, np.exp(-(t - 0.07) / 0.02), 0) * 0.7)
    return (y * vel).astype(np.float32)


def sfx_sparkle(vel=1.0, base=84):
    out = np.zeros(N(1.2), np.float32)
    for i, m in enumerate((0, 4, 7, 12, 16, 19, 24)):
        b = bell(base + m, 0.7, 0.5)
        o = N(i * 0.045)
        out[o:o + len(b)] += b[:len(out) - o]
    return out * vel


def sfx_heartbeat(vel=1.0):
    n = N(0.7)
    out = np.zeros(n, np.float32)
    for d, a in ((0.0, 1.0), (0.22, 0.7)):
        k = kick(a)[:N(0.3)]
        o = N(d)
        out[o:o + len(k)] += lp(k, 150)
    return out * vel
