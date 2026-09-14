"""Robot singer: TTS words time-warped onto notes, pitched with TD-PSOLA and/or a vocoder carrier."""
import numpy as np

from .config import SR
from . import tts

N_FFT = 1024
HOP = 256
NB = N_FFT // 2 + 1
OFF = N_FFT // 2  # frame i is centred on sample i*HOP - OFF
_WIN = np.hanning(N_FFT + 1)[:-1].astype(np.float32)
_FREQS = np.fft.rfftfreq(N_FFT, 1.0 / SR)
FPS_A = SR / HOP


def stft(x):
    x = np.concatenate([np.zeros(N_FFT, np.float32), np.asarray(x, np.float32), np.zeros(N_FFT + HOP, np.float32)])
    nfr = 1 + (len(x) - N_FFT) // HOP
    fr = np.lib.stride_tricks.sliding_window_view(x, N_FFT)[::HOP][:nfr]
    return np.fft.rfft(fr * _WIN, axis=1).astype(np.complex64)


def istft(S, length):
    y = np.fft.irfft(S, n=N_FFT, axis=1).astype(np.float32) * _WIN
    nfr = S.shape[0]
    out = np.zeros(N_FFT + HOP * (nfr - 1), np.float32)
    for i in range(nfr):
        out[i * HOP:i * HOP + N_FFT] += y[i]
    out /= 1.5
    return out[N_FFT:N_FFT + length]


def cep_env(mag, lifter=46):
    logm = np.log(np.maximum(mag, 1e-6))
    full = np.concatenate([logm, logm[:, -2:0:-1]], axis=1)
    cep = np.fft.fft(full, axis=1).real
    cep[:, lifter:N_FFT - lifter + 1] = 0
    return np.exp(np.fft.fft(cep, axis=1).real / N_FFT)[:, :NB].astype(np.float32)


def midi_hz(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=np.float64) - 69) / 12.0)


def blit(f0):
    f0 = np.maximum(f0, 30.0)
    ph = np.cumsum(f0 / SR)
    M = 2 * np.floor(0.45 * SR / f0) + 1
    x = np.pi * ph
    den = np.sin(x)
    num = np.sin(M * x)
    small = np.abs(den) < 1e-5
    out = np.where(small, 1.0, num / np.where(small, 1.0, M * den))
    return ((out - 1.0 / M) * (M / 2)).astype(np.float32)


# ---------------------------------------------------------------- analysis

def _pitch_marks(x):
    """Returns (marks array of sample idx, periods array, voiced bool array)."""
    n = len(x)
    from scipy.signal import butter, sosfiltfilt
    lp = sosfiltfilt(butter(4, 900, fs=SR, output='sos'), x)
    hop = 240
    win = 1920
    f0s, vs = [], []
    lag_min, lag_max = int(SR / 380), int(SR / 65)
    for i in range(0, max(1, n - win), hop):
        seg = lp[i:i + win]
        seg = seg - seg.mean()
        e = np.dot(seg, seg)
        if e < 1e-6 or len(seg) < win:
            f0s.append(0); vs.append(False); continue
        ac = np.correlate(seg, seg, 'full')[win - 1:]
        ac /= ac[0]
        sub = ac[lag_min:lag_max]
        k = int(np.argmax(sub)) + lag_min
        vs.append(sub.max() > 0.45)
        f0s.append(SR / k)
    f0s = np.array(f0s) if f0s else np.zeros(1)
    vs = np.array(vs) if vs else np.zeros(1, bool)
    rms = np.sqrt(np.convolve(x * x, np.ones(480) / 480, mode='same'))
    marks, periods, voiced = [], [], []
    pos = 0
    peak_env = rms.max() + 1e-9
    while pos < n:
        fi = min(len(f0s) - 1, max(0, (pos - win // 2) // hop))
        v = bool(vs[fi]) and rms[pos] > peak_env * 0.03
        if v:
            P = int(SR / max(f0s[fi], 60))
            a = pos
            b = min(n, pos + P)
            if marks and voiced[-1]:
                c0 = marks[-1] + P
                a = max(0, c0 - P // 5)
                b = min(n, c0 + P // 5)
            if b <= a:
                break
            m = a + int(np.argmax(lp[a:b]))
            if marks and m <= marks[-1]:
                m = marks[-1] + P
            marks.append(m); periods.append(P); voiced.append(True)
            pos = m + 1
        else:
            P = 240
            m = pos if not marks else max(pos, marks[-1] + P)
            marks.append(m); periods.append(P); voiced.append(False)
            pos = m + P
    return np.array(marks), np.array(periods), np.array(voiced)


def _syllable_bounds(mag, n):
    F = mag.shape[0]
    band = (_FREQS > 200) & (_FREQS < 4000)
    e = np.convolve(mag[:, band].sum(axis=1), np.ones(7) / 7, mode='same')
    even = lambda: ([int(round(F * i / n)) for i in range(n + 1)],
                    [int(round(F * (i + 0.5) / n)) for i in range(n)])
    if n <= 1:
        return [0, F], [int(np.argmax(e)) if F else 0]
    if F < n * 6:
        return even()
    peaks = [i for i in range(1, F - 1) if e[i] >= e[i - 1] and e[i] > e[i + 1]]
    peaks.sort(key=lambda i: -e[i])
    chosen = []
    for pk in peaks:
        if all(abs(pk - q) >= 12 for q in chosen):
            chosen.append(pk)
        if len(chosen) == n:
            break
    if len(chosen) < n:
        return even()
    chosen.sort()
    bounds = [0] + [a + int(np.argmin(e[a:b + 1])) for a, b in zip(chosen[:-1], chosen[1:])] + [F]
    return bounds, chosen


def _warp(s0, s1, p, D):
    nat = max(1, s1 - s0)
    if D <= 0:
        return np.zeros(0)
    if D <= nat * 1.05:
        return s0 + (np.arange(D) + 0.5) * nat / D
    a = min(max(p, s0), s0 + 14)
    r = max(min(p + 2, s1), s1 - 12)
    r = max(r, a)
    la, lr = a - s0, s1 - r
    if la + lr > D * 0.7:
        k = D * 0.7 / (la + lr)
        la, lr = la * k, lr * k
    na, nr = int(round(la)), int(round(lr))
    nm = max(1, D - na - nr)
    parts = []
    if na > 0:
        parts.append(np.linspace(s0, a, na, endpoint=False))
    parts.append(np.linspace(a, r, nm, endpoint=False))
    if nr > 0:
        parts.append(np.linspace(r, s1 - 0.5, nr))
    out = np.concatenate(parts)
    if len(out) != D:
        out = np.interp(np.linspace(0, len(out) - 1, D), np.arange(len(out)), out)
    return out


_word_cache = {}


def word_analysis(text, voice, rate):
    key = (text, voice, rate)
    if key in _word_cache:
        return _word_cache[key]
    x = tts.load(text, voice, rate).astype(np.float64)
    S = stft(x)
    mag = np.abs(S)
    env = cep_env(mag)
    tot = (mag ** 2).sum(axis=1) + 1e-9
    hf = (mag[:, _FREQS > 2500] ** 2).sum(axis=1) / tot
    rms = np.sqrt(tot)
    uv = (np.clip((hf - 0.08) / 0.3, 0, 1) * (rms > rms.max() * 0.02)).astype(np.float32)
    marks, periods, voiced = _pitch_marks(x)
    res = dict(x=x.astype(np.float32), mag=mag, env=env, uv=uv, marks=marks, periods=periods, voiced=voiced)
    _word_cache[key] = res
    return res


def _interp_frames(arr, pos):
    i0 = np.clip(np.floor(pos).astype(int), 0, arr.shape[0] - 1)
    i1 = np.clip(i0 + 1, 0, arr.shape[0] - 1)
    f = (pos - np.floor(pos)).astype(np.float32)
    if arr.ndim == 2:
        f = f[:, None]
    return arr[i0] * (1 - f) + arr[i1] * f


# ---------------------------------------------------------------- synthesis

def _f0_track(ev_sorted, length, v, glide, vibrato, tail):
    tt = np.arange(length) / SR
    f0 = np.full(length, np.nan)
    last = None
    for e in ev_sorted:
        m = e['pitches'][min(v, len(e['pitches']) - 1)]
        a = int(e['t'] * SR)
        b = min(length, int((e['t'] + e['d'] + tail) * SR))
        f0[a:b] = m
        if last is not None and 0 <= a - last[1] < int(0.08 * SR) and glide > 0:
            g = min(int(glide * SR), b - a)
            f0[a:a + g] = last[0] + (m - last[0]) * np.linspace(0, 1, g)
        if e['d'] > 0.3 and vibrato > 0:
            va, vb = int((e['t'] + 0.22) * SR), b
            if vb > va:
                ramp = np.clip((tt[va:vb] - tt[va]) / 0.3, 0, 1)
                f0[va:vb] += vibrato * ramp * np.sin(2 * np.pi * 5.6 * (tt[va:vb] - tt[va]))
        last = (m, int((e['t'] + e['d']) * SR))
    # hold through gaps
    idx = np.where(~np.isnan(f0), np.arange(length), 0)
    np.maximum.accumulate(idx, out=idx)
    f0 = f0[idx]
    first = np.argmax(~np.isnan(f0))
    f0[:first] = f0[first]
    return midi_hz(f0)


def sing(events, voice='david', rate=0, mode='blend', psola_gain=1.0, vocoder_gain=0.55, detune=0.08,
         vibrato=0.35, formant=1.0, noise_gain=1.4, glide=0.035, tail=0.12, octave_psola=0):
    """events: dicts with t, d, pitches(list of midi), word, word_id, [voice], [rate], [gain].
    mode: 'psola', 'vocoder', or 'blend'. Returns mono float32 normalised to 0.8 peak."""
    if not events:
        return np.zeros(1, np.float32)
    ev_sorted = sorted(events, key=lambda e: e['t'])
    length = int((max(e['t'] + e['d'] for e in events) + tail + 0.3) * SR)
    nfr = (length + OFF) // HOP + 3
    # ---- time maps: output frame -> (word index, source frame position, gain)
    src_pos = np.full(nfr, -1.0)
    src_word = np.full(nfr, -1, dtype=int)
    src_gain = np.zeros(nfr, np.float32)
    groups = []
    for e in ev_sorted:
        wid = e.get('word_id', id(e))
        if groups and groups[-1][0] == wid:
            groups[-1][1].append(e)
        else:
            groups.append((wid, [e]))
    analyses = []
    for gi, (wid, sy) in enumerate(groups):
        w = sy[0]
        an = word_analysis(w['word'], w.get('voice', voice), w.get('rate', rate))
        analyses.append(an)
        bounds, peaks = _syllable_bounds(an['mag'], len(sy))
        for k, e in enumerate(sy):
            last_syl = k == len(sy) - 1
            j0 = int(round((e['t'] * SR + OFF) / HOP))
            D = int(round((e['d'] + (tail * 0.5 if last_syl else 0)) * FPS_A))
            pos = _warp(bounds[k], bounds[k + 1], peaks[k], D)
            j1 = min(nfr, j0 + len(pos))
            L = j1 - j0
            if L <= 0:
                continue
            fade = np.ones(L, np.float32)
            if last_syl:
                fo = min(10, L // 2)
                if fo:
                    fade[-fo:] = np.linspace(1, 0, fo)
            src_pos[j0:j1] = pos[:L]
            src_word[j0:j1] = gi
            src_gain[j0:j1] = fade * e.get('gain', 1.0)
    maxpoly = max(len(e['pitches']) for e in events)
    out = np.zeros(length, np.float32)

    # ---- TD-PSOLA (first voice of each chord only; chords use the vocoder)
    if mode in ('psola', 'blend'):
        f0 = _f0_track(ev_sorted, length, 0, glide, vibrato, tail) * (2.0 ** octave_psola)
        ola = np.zeros(length + 4096, np.float32)
        wsum = np.zeros(length + 4096, np.float32)
        tau = 0
        active = np.nonzero(src_word >= 0)[0]
        if len(active):
            tau = max(0, active[0] * HOP - OFF - 400)
        end = min(length, active[-1] * HOP - OFF + 400) if len(active) else 0
        while tau < end:
            j = (tau + OFF) / HOP
            ji = int(j)
            if ji >= nfr or src_word[ji] < 0:
                tau += 120
                continue
            an = analyses[src_word[ji]]
            jf = min(nfr - 1, ji + 1)
            p = src_pos[ji] if src_word[jf] != src_word[ji] else src_pos[ji] + (src_pos[jf] - src_pos[ji]) * (j - ji)
            s = p * HOP - OFF
            marks = an['marks']
            if len(marks) == 0:
                tau += 120
                continue
            mi = int(np.clip(np.searchsorted(marks, s), 0, len(marks) - 1))
            if mi > 0 and abs(marks[mi - 1] - s) < abs(marks[mi] - s):
                mi -= 1
            P = int(an['periods'][mi])
            vo = bool(an['voiced'][mi])
            gl = int(P * 2)
            m = int(marks[mi])
            x = an['x']
            a, b = m - P, m + P
            grain = np.zeros(gl, np.float32)
            aa, bb = max(0, a), min(len(x), b)
            if bb > aa:
                grain[aa - a:bb - a] = x[aa:bb]
            wnd = np.hanning(gl).astype(np.float32)
            if formant != 1.0 and vo:
                newlen = max(8, int(gl / formant))
                grain = np.interp(np.linspace(0, gl - 1, newlen), np.arange(gl), grain).astype(np.float32)
                wnd = np.hanning(newlen).astype(np.float32)
                gl = newlen
            g = src_gain[ji] * psola_gain
            c0 = tau - gl // 2
            ca, cb = max(0, c0), min(length, c0 + gl)
            if cb > ca:
                ola[ca:cb] += grain[ca - c0:cb - c0] * wnd[ca - c0:cb - c0] * g
                wsum[ca:cb] += wnd[ca - c0:cb - c0]
            step = int(SR / f0[min(tau, length - 1)]) if vo else P
            tau += max(24, step)
        norm = np.maximum(wsum[:length], 1.0)
        ps = ola[:length] / norm
        pk = np.abs(ps).max() + 1e-9
        out += ps / pk * 0.8 * psola_gain

    # ---- vocoder (all chord voices)
    if mode in ('vocoder', 'blend') or maxpoly > 1:
        carrier = np.zeros(length, np.float32)
        for v in range(maxpoly):
            hz = _f0_track(ev_sorted, length, v, glide, vibrato, tail)
            carrier += blit(hz)
            if detune > 0:
                carrier += 0.7 * blit(hz * 2 ** (detune / 12))
        C = stft(carrier)[:nfr]
        n2 = C.shape[0]
        Ec = cep_env(np.abs(C))
        env_out = np.zeros((n2, NB), np.float32)
        mag_out = np.zeros((n2, NB), np.float32)
        uv_out = np.zeros(n2, np.float32)
        for gi, an in enumerate(analyses):
            sel = np.nonzero(src_word[:n2] == gi)[0]
            if len(sel) == 0:
                continue
            pos = src_pos[sel]
            gg = src_gain[sel][:, None]
            env_out[sel] = _interp_frames(an['env'], pos) * gg
            mag_out[sel] = _interp_frames(an['mag'], pos) * gg
            uv_out[sel] = _interp_frames(an['uv'], pos)
        if formant != 1.0:
            sb = np.clip(np.arange(NB) / formant, 0, NB - 1)
            i0 = np.floor(sb).astype(int)
            i1 = np.minimum(i0 + 1, NB - 1)
            f = (sb - i0).astype(np.float32)
            env_out = env_out[:, i0] * (1 - f) + env_out[:, i1] * f
            mag_out = mag_out[:, i0] * (1 - f) + mag_out[:, i1] * f
        ratio = env_out / np.maximum(Ec, 1e-4)
        voiced = C * (ratio * (1 - 0.8 * uv_out[:, None]))
        rng = np.random.default_rng(1234)
        ph = np.exp(1j * rng.uniform(0, 2 * np.pi, (n2, NB))).astype(np.complex64)
        hfmask = np.clip((_FREQS - 1200) / 2000, 0, 1).astype(np.float32)
        noise = ph * mag_out * hfmask * ((0.3 + 0.7 * uv_out[:, None]) * noise_gain)
        vc = istft(voiced + noise, length)
        vc = vc - np.convolve(vc, np.ones(480) / 480, mode='same')
        pk = np.abs(vc).max() + 1e-9
        out += vc / pk * 0.8 * (vocoder_gain if mode == 'blend' else 1.0)
    pk = np.abs(out).max() + 1e-9
    return (out / pk * 0.8).astype(np.float32)
