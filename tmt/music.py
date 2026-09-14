"""Arrangement and mixdown of the whole soundtrack."""
import math
import os
import time
import wave

import numpy as np
from numba import njit

from .config import SR, BAR, BEAT, EIGHTH, BUILD, OUT
from . import synth as S
from . import score as SC
from . import voice, tts, notation, edits

LEN = SC.TOTAL + 4.0
NS = int(LEN * SR)
SIXT = EIGHTH / 2


def log(*a):
    print(f'[audio {time.strftime("%H:%M:%S")}]', *a, flush=True)


class Mixer:
    def __init__(self):
        self.stems = {}

    def buf(self, name):
        if name not in self.stems:
            self.stems[name] = np.zeros((2, NS), np.float32)
        return self.stems[name]

    def add(self, name, sig, t, gain=1.0, pan=0.0):
        if gain == 0:
            return
        b = self.buf(name)
        sig = np.asarray(sig, np.float32)
        if sig.ndim == 1:
            sig = S.pan(sig, pan)
        i = int(round(t * SR))
        if i < 0:
            sig = sig[:, -i:]
            i = 0
        n = min(sig.shape[1], NS - i)
        if n <= 0:
            return
        b[:, i:i + n] += sig[:, :n] * gain


# ---------------------------------------------------------------- shared samples
class Kit:
    def __init__(self):
        self.kick = S.kick()
        sn = S.snare()
        verb = S.reverb(sn, 0.9, 0.3, 1.0)
        gate = np.ones(verb.shape[1], np.float32)
        g0, g1 = S.N(0.24), S.N(0.28)
        gate[g0:g1] = np.linspace(1, 0, g1 - g0)
        gate[g1:] = 0
        self.snare_gated = S.pan(np.concatenate([sn, np.zeros(verb.shape[1] - len(sn), np.float32)]), 0) + verb * gate * 2.2
        self.snare = sn
        self.clap = S.clap()
        self.hat_c = S.hat(False)
        self.hat_o = S.hat(True)
        self.shaker = S.shaker()
        self.crash = S.crash()
        self.toms = [S.tom(f) for f in (200, 160, 120, 90)]


KIT = None


def loop_chords(t0, minor=False, tr=0, bars=range(1, 17)):
    out = []
    for b in bars:
        tb = t0 + (b - 1) * BAR
        acc = 0
        for beats, ch in SC.CHORDS_LOOP[(b - 1) % 16]:
            c = SC.minor_chord(ch) if minor else ch
            root = c[0] + tr
            bass = ((ch[2] if len(ch) > 2 and not minor else c[0]) + tr)
            notes = [root + i for i in SC.QUAL[c[1]]]
            out.append((tb + acc * BEAT, beats * BEAT, notes, bass))
            acc += beats
    return out


def play_line(mx, stem, inst, line, t0, tr=0, gain=1.0, pan=0.0, minor=False, **kw):
    ev, _ = notation.parse(line, t0)
    for e in ev:
        for p in e['pitches']:
            p = SC.minorize(p) if minor else p
            mx.add(stem, inst(p + tr, e['d'] * 0.95, **kw), e['t'], gain, pan)


# ---------------------------------------------------------------- dialog fx

def whisperize(x):
    Sx = voice.stft(x)
    mag = np.abs(Sx)
    rng = np.random.default_rng(3)
    ph = np.exp(1j * rng.uniform(0, 2 * np.pi, mag.shape)).astype(np.complex64)
    y = voice.istft(ph * mag, len(x))
    return S.hp(y, 300)


def dialog_clip(text, vc, rate, semis, fx):
    x = tts.load(text, vc, rate)
    if fx == 'whisper':
        x = whisperize(x) * 1.6
    if semis:
        x = S.pitch(x, semis)
    if fx == 'announcer':
        x = S.peaking(x, 150, 5, 0.8)
        x = S.softclip(x * 1.4, 1.2)
        wet = S.reverb(x, 0.5, 0.6, 0.8) * 0.25
        return S.pan(np.concatenate([x, np.zeros(wet.shape[1] - len(x), np.float32)])) + wet
    if fx == 'radio':
        y = S.bp(x, 350, 3200, 3)
        y = S.softclip(y * 3.0, 2.0) * 0.6
        y += S.hp(S.noise(len(y)), 3000) * 0.03
        wet = S.reverb(y, 0.3, 0.5, 0.5) * 0.2
        return S.pan(np.concatenate([y, np.zeros(wet.shape[1] - len(y), np.float32)])) + wet
    if fx == 'robot':
        t = np.arange(len(x)) / SR
        y = x * np.sin(2 * np.pi * 60 * t).astype(np.float32)
        y = S.bp(y * 1.5 + x * 0.3, 250, 5000)
        wet = S.reverb(y, 0.6, 0.4, 1.2) * 0.35
        return S.pan(np.concatenate([y, np.zeros(wet.shape[1] - len(y), np.float32)])) + wet
    if fx == 'whisper':
        wet = S.reverb(x, 0.95, 0.3, 3.0) * 0.9
        return S.pan(np.concatenate([x, np.zeros(wet.shape[1] - len(x), np.float32)])) * 0.7 + wet
    if fx == 'room':
        wet = S.reverb(x, 0.35, 0.7, 0.5) * 0.12
        return S.pan(np.concatenate([x, np.zeros(wet.shape[1] - len(x), np.float32)])) + wet
    return S.pan(x)


def laugh_track(dur=2.2, seed=0, vel=1.0):
    r = np.random.default_rng(seed)
    out = np.zeros((2, S.N(dur + 1.0)), np.float32)
    for k in range(16):
        vc = 'zira' if k % 2 else 'david'
        rate = int(r.integers(2, 7))
        x = tts.load('ha ha ha ha ha', vc, rate)
        x = S.pitch(x, r.uniform(-5, 6))
        x = S.bp(x, 250, 5000)
        L = min(len(x), S.N(dur))
        x = x[:L] * np.linspace(1, 0.2, L).astype(np.float32)
        o = S.N(r.uniform(0, 0.25))
        out[:, o:o + L] += S.pan(x, r.uniform(-0.8, 0.8)) * r.uniform(0.3, 0.7)
    bed = S.bp(S.noise(out.shape[1]), 400, 3000) * np.exp(-np.arange(out.shape[1]) / SR / (dur * 0.5)).astype(np.float32) * 0.15
    out += S.pan(bed)
    wet = S.reverb(out.mean(0), 0.6, 0.5, 1.0) * 0.4
    out2 = np.zeros((2, wet.shape[1]), np.float32)
    out2[:, :out.shape[1]] = out
    return (out2 + wet) * vel


# ---------------------------------------------------------------- vocals

def add_vocals(mx, season, t0, tr=0, minor=False, lead_gain=1.0, choir_gain=0.8, formant=1.0, stem='vox'):
    ev = SC.lead_events(season, t0, tr, minor)
    base = ev[0]['t']
    for e in ev:
        e['t'] -= base
    y = voice.sing(ev, 'david', mode='blend', octave_psola=-1, formant=formant, vocoder_gain=0.45)
    mx.add(stem, y, base, lead_gain * 0.9)
    ch = SC.choir_events(t0, tr, minor, season=season)
    cb = min(e['t'] for e in ch)
    for e in ch:
        e['t'] -= cb
    yc = voice.sing(ch, 'zira', mode='vocoder', detune=0.12, vibrato=0.25)
    d = S.N(0.018)
    st = np.stack([yc, np.concatenate([np.zeros(d, np.float32), yc[:-d]])])
    mx.add('choir', st, cb, choir_gain)
    return ev


# ---------------------------------------------------------------- sections

def sec_cold_open(mx):
    t0 = 0.0
    mx.add('sfx', S.sfx_static(1.25, 0.9), 0.0)
    mx.add('sfx', S.sfx_hum(1.3, 1.0), 0.0)
    beep = S.square(1000, S.N(0.12)) * 0.15
    mx.add('sfx', S.fade(beep), 0.25)
    mx.add('sfx', S.sfx_shutter(0.6), 1.2)
    room = S.lp(S.noise(S.N(6.8)), 500) * 0.04
    mx.add('sfx', S.fade(room, 0.3, 0.3), 1.2)
    # typing "is it going to rain"
    for i in range(19):
        mx.add('sfx', S.sfx_key(0.5 + 0.3 * ((i * 7) % 3) / 2), 2.55 + i * 0.058)
    mx.add('sfx', S.sfx_key(1.0), 3.72)
    for i, (tt, p) in enumerate(SC.POP_TIMES_COLD):
        mx.add('sfx', S.sfx_pop(p, 0.6 + 0.3 * min(1, i / 10)), tt)
    for tt in SC.CLOSE_CLICKS_COLD:
        mx.add('sfx', S.sfx_click(0.9), tt)
    # dread pad + fill
    mx.add('pad', S.pad([38, 45, 50], 3.6, 0.5, cutoff=900, attack=1.5), 4.2)
    for i in range(8):
        mx.add('drums', KIT.toms[min(3, i // 2)] * 0.7, 6.5 + i * SIXT, 1.0, -0.3 + i * 0.08)
    for i in range(8):
        mx.add('drums', KIT.snare * (0.3 + 0.7 * i / 7), 7.0 + i * SIXT)
    mx.add('sfx', S.sfx_riser(2.0, 0.5), 6.0)


def band_loop(mx, t0, style='s1', tr=0, minor=False):
    """16-bar sitcom band. style s1|s2|s3."""
    ch = loop_chords(t0, minor, tr)
    dense = style == 's2'
    horror = style == 's3'
    for b in range(1, 17):
        tb = t0 + (b - 1) * BAR
        chorus = b >= 11
        halftime = horror and 3 <= b <= 10
        if horror and b in (9, 10):
            # nearly silent: ticking clock
            for k in range(4):
                mx.add('sfx', S.sfx_click(0.6), tb + k * BEAT)
            if b == 10:
                mx.add('drums', S.boom(1.0, 2.0), tb + BEAT * 1.0, 0.9)
                mx.add('sfx', S.sfx_thunder(0.9), tb + BEAT * 1.0)
            continue
        # kick / snare
        if b == 1:
            mx.add('drums', KIT.crash, tb, 0.8, 0.3)
            if not horror:
                mx.add('keys', S.orch_hit(62 + tr), tb, 0.7)
        if halftime:
            mx.add('drums', KIT.kick, tb, 1.0)
            mx.add('drums', KIT.snare_gated, tb + 2 * BEAT, 0.9)
            mx.add('drums', KIT.hat_c, tb + 1 * BEAT, 0.3, 0.3)
            mx.add('drums', KIT.hat_c, tb + 3 * BEAT, 0.3, 0.3)
        else:
            kicks = [0, 2] + ([1.5] if b % 2 == 0 else []) + ([3.5] if chorus and horror else [])
            for k in kicks:
                mx.add('drums', KIT.kick, tb + k * BEAT, 0.95)
            fill = (b == 10 or b == 16)
            snare_beats = [1, 3] if not (fill and b == 16) else [1]
            for k in snare_beats:
                mx.add('drums', KIT.snare_gated, tb + k * BEAT, 0.85)
                if dense or horror:
                    mx.add('drums', KIT.clap, tb + k * BEAT, 0.5, 0.1)
            for k in range(8):
                acc = 0.55 if k % 2 else 0.3
                if fill and k >= 6 and b == 10:
                    continue
                mx.add('drums', KIT.hat_c, tb + k * EIGHTH, acc, 0.35)
            if b % 2 == 0:
                mx.add('drums', KIT.hat_o, tb + 3.5 * BEAT, 0.3, 0.35)
            if chorus or dense:
                for k in range(16):
                    mx.add('drums', KIT.shaker, tb + k * SIXT, 0.25 if k % 2 else 0.15, -0.4)
            if b == 10:
                for i in range(4):
                    mx.add('drums', KIT.toms[i], tb + (3 + i * 0.25) * BEAT, 0.8, 0.5 - i * 0.3)
            if b == 16:
                for i in range(12):
                    tt = tb + (2 + i * 0.25 / 1.5) * BEAT
                    mx.add('drums', KIT.snare, tb + 2 * BEAT + i * (2 * BEAT / 12), 0.35 + 0.55 * i / 11)
            if b in (11, 13):
                mx.add('drums', KIT.crash, tb, 0.7, -0.3)
                mx.add('brass', S.orch_hit(62 + tr + (0 if b == 11 else -3)), tb, 0.55 if not dense else 0.8)
    # bass
    for (t, d, notes, bass) in ch:
        bar_i = int((t - t0 + 1e-6) // BAR) + 1
        if horror and bar_i in (9, 10):
            continue
        if horror and 3 <= bar_i <= 10:
            mx.add('bass', S.bass_pluck(bass - 12, d * 0.95, 0.9, 0.4), t, 0.9)
            continue
        steps = int(round(d / EIGHTH))
        for k in range(steps):
            m = bass - 12 + (12 if k % 4 == 3 else 0)
            v = 0.9 if k % 2 == 0 else 0.7
            dist = horror and bar_i >= 11
            nt = S.bass_pluck(m, EIGHTH * 0.8, v, 1.4 if dist else 1.0)
            if dist:
                nt = S.softclip(nt * 2.5, 2.5) * 0.5
            mx.add('bass', nt, t + k * EIGHTH, 0.85)
    # keys
    for (t, d, notes, bass) in ch:
        bar_i = int((t - t0 + 1e-6) // BAR) + 1
        voicing = [n + 12 for n in notes]
        if horror:
            if bar_i in (9, 10):
                continue
            if bar_i >= 11:
                mx.add('pad', S.supersaw([n for n in voicing] + [voicing[0] - 12], d, 0.55, 3500), t, 0.8)
            else:
                mx.add('pad', S.pad([n - 12 for n in notes] + [notes[0] + 13], d, 0.6, 1200, 0.6), t, 0.9)
            continue
        hits = [(0, 0.75), (1.5, 0.45), (2.5, 0.45), (3.0, 0.9)] if d >= 4 * BEAT - 1e-6 else [(0, 0.75), (1.5, 0.45)]
        for off, dur in hits:
            for n in voicing:
                mx.add('keys', S.epiano(n, dur * BEAT, 0.7), t + off * BEAT, 0.55, -0.2)
        if chorus_bar(bar_i) or dense:
            mx.add('pad', S.pad(voicing + [voicing[0] + 12], d, 0.6, 2800), t, 0.6 if dense else 0.5)
    # intro brass riff
    riff = "x/D5 r x/A4 x/D5 x/E5 x:2/F#5 r | x/E5 x/D5 x/C#5 x:3/A4 r:2"
    play_line(mx, 'brass', S.brass, riff, t0, tr, 0.9, 0.15, minor=minor)
    if not horror:
        play_line(mx, 'brass', S.brass, riff.replace('5', '4').replace('A4', 'A3'), t0, tr, 0.5, -0.15)
    else:
        play_line(mx, 'keys', S.music_box, riff.replace('5', '6').replace('A4', 'A5'), t0, tr, 0.9, 0.3, minor=True)
    # stabs on TABS
    for b in (11, 12, 13, 14):
        tb = t0 + (b - 1) * BAR
        notes = [n + 12 for n in loop_chords(t0, minor, tr, [b])[0][2]]
        for n in notes:
            mx.add('brass', S.brass(n, BEAT * 0.9, 1.0), tb, 0.6, 0.2)
    # sax fills in the verse gaps
    if not horror:
        fills = {4: "x/F#5 x/A5 x/B5 x/A5", 6: "x/E5 x/G5 x/A5 x/C#6", 8: "x/A5 x/G5 x/F#5 x/E5"}
        for b, ln in fills.items():
            play_line(mx, 'lead', S.sax, ln, t0 + (b - 1) * BAR + 2 * BEAT, tr, 0.7, 0.25)
        if dense:
            play_line(mx, 'lead', S.sax, "x:2/D6 x:2/C#6 x:2/B5 x:2/A5", t0 + 14 * BAR, tr, 0.6, 0.25)
    else:
        # music box doubles the vocal melody an octave up
        line = SC.lead_line('s3')
        ev, _ = notation.parse(line, t0 + 2 * BAR)
        for e in ev:
            m = SC.minorize(e['pitches'][0]) + 12 + tr
            mx.add('keys', S.music_box(m, 1.2, 0.5), e['t'], 0.45, 0.35)
    # sparkle on title
    if not horror:
        mx.add('sfx', S.sfx_sparkle(0.6), t0 + 1.0)
        mx.add('sfx', S.sfx_sparkle(0.5, 88), t0 + 3.0)


def chorus_bar(b):
    return b >= 11


def sec_s1(mx):
    t0 = SC.SEC['s1'][0]
    band_loop(mx, t0, 's1', 0)
    add_vocals(mx, 's1', t0, 0)
    mx.add('drums', S.boom(0.7), t0, 0.7)
    # tab pops in the chorus (visual tabs spawn on every TABS)
    for b in (11, 12, 13, 14):
        for k in range(2 ** (b - 10)):
            mx.add('sfx', S.sfx_pop(1 + 0.1 * k, 0.35), t0 + (b - 1) * BAR + k * SIXT)
    # freeze-frame shutters on cast intros
    for b in (3, 5, 7, 9):
        mx.add('sfx', S.sfx_shutter(0.35), t0 + (b - 1) * BAR + 3.0)


def sec_episode(mx):
    t0 = SC.SEC['episode'][0]
    # sitcom sting
    for i, m in enumerate((38, 45, 50, 49, 47, 45)):
        mx.add('bass', S.bass_pluck(m, 0.11, 1.0, 1.5), t0 + i * 0.09, 0.9)
    for n in (62, 66, 69, 73):
        mx.add('keys', S.epiano(n, 0.9, 0.9), t0 + 0.54, 0.6)
    mx.add('sfx', S.sfx_click(1.0), t0 + 3.2)
    mx.add('sfx', S.sfx_pop(1.3, 0.8), t0 + 3.35)
    mx.add('sfx', S.sfx_pop(1.6, 0.8), t0 + 3.52)
    mx.add('sfx', laugh_track(2.0, 1, 0.9), t0 + 4.45)
    mx.add('sfx', laugh_track(1.4, 2, 0.7), t0 + 6.7)
    # theme sneaks back early
    play_line(mx, 'brass', S.brass, "x/A4 x/B4 x/C#5", t0 + 7.25, 1, 0.8)
    mx.add('drums', KIT.toms[0], t0 + 7.25, 0.6)
    mx.add('drums', KIT.toms[1], t0 + 7.5, 0.7)
    mx.add('drums', KIT.toms[2], t0 + 7.75, 0.8)


def sec_s2(mx):
    t0 = SC.SEC['s2'][0]
    band_loop(mx, t0, 's2', 1)
    add_vocals(mx, 's2', t0, 1, choir_gain=1.0)
    # extra: tabs pop constantly and faster
    r = np.random.default_rng(22)
    tt = t0
    while tt < t0 + 32:
        prog = (tt - t0) / 32
        mx.add('sfx', S.sfx_pop(r.uniform(0.8, 2.0), 0.18 + 0.12 * prog), tt, 1.0, r.uniform(-0.8, 0.8))
        tt += max(0.06, 0.7 * (1 - prog) ** 2)
    for b in (3, 5, 7, 9):
        mx.add('sfx', S.sfx_shutter(0.35), t0 + (b - 1) * BAR + 3.0)
    for k in range(6):
        mx.add('sfx', S.sfx_ding(0.25, 1 + k * 0.05), t0 + 16 + k * 0.33)
    mx.add('sfx', S.sfx_glitch(0.35, 0.6, 5), t0 + 31.65)


def sec_space(mx):
    t0 = SC.SEC['space'][0]
    tr = 2
    prog = [(52, 'min'), (48, 'maj'), (50, 'maj'), (47, 'min'), (52, 'min'), (48, 'maj'), (45, 'min'), (47, 'maj')]
    mx.add('drums', S.boom(1.0, 2.5), t0, 1.0)
    mx.add('sfx', S.sfx_whoosh(1.2, 0.7), t0 - 0.9)
    for b, (root, q) in enumerate(prog):
        tb = t0 + b * BAR
        notes = [root + i for i in SC.QUAL[q]]
        mx.add('pad', S.pad([n + 12 for n in notes] + [root + 24], BAR, 0.6, 1800, 0.4), tb, 0.8)
        # arp
        seq = [notes[0] + 24, notes[1] + 24, notes[2] + 24, notes[0] + 36, notes[2] + 24, notes[1] + 24]
        for k in range(16):
            m = seq[k % len(seq)]
            y = S.delay(S.arp_saw(m, SIXT * 0.9, 0.8), 3 * SIXT, 0.4, 3, 0.4)
            mx.add('keys', y, tb + k * SIXT, 0.45, 0.4 if k % 2 else -0.4)
        for k in range(16):
            mx.add('bass', S.bass_pluck(root - 12 + (12 if k % 8 == 7 else 0), SIXT * 0.8, 0.9, 0.8), tb + k * SIXT,
                   0.7 * (0.5 if k % 4 == 0 else 1.0))
        if b >= 1:
            for k in (0, 2):
                mx.add('drums', KIT.kick, tb + k * BEAT, 1.0)
            for k in (1, 3):
                mx.add('drums', KIT.snare_gated, tb + k * BEAT, 1.0)
            for k in range(16):
                mx.add('drums', KIT.hat_c, tb + k * SIXT, 0.25 if k % 2 else 0.4, 0.3)
    # theme on a spacey lead, minor
    play_line(mx, 'lead', S.sax, "r:5 x/B4 x/C5 x/D5 | x:4/E5 r:4 | r:5 x/B4 x/C5 x/D5 | x:6/E5 x/D5 x/B4",
              t0 + 4 * BAR, 0, 0.55, 0.0)
    # robot choir aah
    ah = []
    for b, (root, q) in enumerate(prog):
        notes = [root + i + 12 for i in SC.QUAL[q]]
        ah.append(dict(t=b * BAR, d=BAR * 0.95, pitches=notes, word='ah', word_id=f'ah{b}', voice='zira'))
    y = voice.sing(ah, 'zira', mode='vocoder', vibrato=0.2, detune=0.15)
    mx.add('choir', S.pan(y, -0.2), t0, 0.45)
    mx.add('sfx', S.sfx_riser(4.0, 0.6), t0 + 12)
    mx.add('sfx', S.sfx_explosion(0.8), t0 + 15.6)


def sec_hamster(mx):
    t0 = SC.SEC['hamster'][0]
    # 8 bars, loop bars 3..16 at double speed + ending
    chords = loop_chords(0.0, False, 0, range(3, 17))
    for (t, d, notes, bass) in chords:
        tt = t0 + t / 2
        dd = d / 2
        steps = int(round(dd / SIXT))
        arp = [notes[0] + 24, notes[1] + 24, notes[2] + 24, notes[1] + 24]
        for k in range(steps):
            mx.add('keys', S.chip_square(arp[k % 4], SIXT * 0.8, 0.125, 0.55), tt + k * SIXT, 0.85, 0.3)
        for k in range(max(1, steps // 2)):
            mx.add('bass', S.chip_tri(bass - 12 + (12 if k % 2 else 0), EIGHTH * 0.9), tt + k * EIGHTH, 1.4)
    ev, _ = notation.parse(' '.join(f'x:{d}/{p}' if p != 'r' else f'r:{d}' for p, d in SC.MELODY), 0.0)
    for e in ev:
        mx.add('lead', S.chip_square(e['pitches'][0] + 12, e['d'] / 2 * 0.9, 0.5, 0.9, vib=0.3 if e['d'] > 0.4 else 0),
               t0 + e['t'] / 2, 1.0)
    for b in range(8):
        tb = t0 + b * BAR
        for k in range(8):
            mx.add('drums', S.chip_noise(0.05, 0.6, 2, 0.02), tb + k * EIGHTH, 0.5)
            if k % 4 == 0:
                mx.add('drums', S.pitch(S.chip_tri(45, 0.08), -12), tb + k * EIGHTH, 0.9)
            if k % 4 == 2:
                mx.add('drums', S.chip_noise(0.15, 1.0, 8, 0.06), tb + k * EIGHTH, 0.7)
    # wheel squeaks get faster
    tt = t0 + 2.0
    gap = 0.5
    while tt < t0 + 12.5:
        mx.add('sfx', S.sfx_squeak(0.5, 1 + (tt - t0) * 0.03), tt, 1.0, 0.4)
        tt += gap
        gap = max(0.08, gap * 0.93)
    mx.add('sfx', S.sfx_boing(1.0), t0 + 12.5)
    mx.add('sfx', S.sfx_whoosh(0.6, 0.8), t0 + 12.6)
    mx.add('sfx', S.sfx_explosion(0.9, 2.0), t0 + 13.2)
    for k in range(20):
        mx.add('sfx', S.sfx_pop(1.0 + k * 0.1, 0.4), t0 + 13.3 + k * 0.05, 1.0, (k % 5) / 2.5 - 0.8)
    for k in range(6):
        mx.add('sfx', S.bell(96 + (k % 3) * 4, 0.3, 0.3), t0 + 14.3 + k * 0.18, 1.0, 0.5)


def sec_s3(mx):
    t0 = SC.SEC['s3'][0]
    band_loop(mx, t0, 's3', 2, minor=True)
    ev = add_vocals(mx, 's3', t0, 2, minor=True, formant=0.92, choir_gain=0.9, stem='vox_horror')
    mx.add('sfx', S.sfx_thunder(1.0), t0)
    mx.add('drums', S.boom(1.0, 2.5), t0, 0.9)
    for k in range(4):
        mx.add('drums', S.sfx_heartbeat(0.7), t0 + 4 * BEAT + k * 0.9, 0.6)
    # closes: 8 hits in bars 7-8
    for k in range(8):
        tt = t0 + 6 * BAR + k * BEAT
        mx.add('sfx', S.sfx_click(1.0), tt)
        mx.add('brass', S.pitch(S.orch_hit(40), -3 - k), tt, 0.5)
        mx.add('sfx', S.sfx_power_down(0.4, 0.4), tt + 0.05)
    # the restore click
    mx.add('sfx', S.sfx_click(1.0), t0 + 9 * BAR + 0.45)
    mx.add('sfx', S.sfx_sparkle(0.8, 79), t0 + 9 * BAR + 0.5)
    for k in range(24):
        mx.add('sfx', S.sfx_pop(0.7 + k * 0.05, 0.35), t0 + 10 * BAR + k * 0.04, 1.0, (k % 6) / 3 - 0.8)
    # zombie groans in bars 15-16
    for k in range(4):
        g = S.pitch(tts.load('uuuuhhhh', 'david', -6), -8 - k)
        mx.add('sfx', S.lp(g, 1500) * 0.8, t0 + 13 * BAR + 1.5 + k * 0.7, 0.8, -0.6 + k * 0.4)
    mx.add('sfx', S.sfx_thunder(0.8), t0 + 15 * BAR + 1.5)


def sec_finale(mx):
    t0 = SC.SEC['finale'][0]
    prog = [(52, 'maj'), (49, 'min'), (45, 'maj'), (47, 'maj')] * 2
    for b, (root, q) in enumerate(prog):
        tb = t0 + b * BAR
        notes = [root + i + 12 for i in SC.QUAL[q]]
        last = b == 7
        for k in range(4):
            mx.add('drums', KIT.kick, tb + k * BEAT, 1.0)
            if k % 2 == 1:
                mx.add('drums', KIT.snare_gated, tb + k * BEAT, 0.9)
                mx.add('drums', KIT.clap, tb + k * BEAT, 0.7)
            mx.add('drums', KIT.hat_o, tb + (k + 0.5) * BEAT, 0.35, 0.3)
        for k in range(16):
            mx.add('drums', KIT.hat_c, tb + k * SIXT, 0.3, -0.3)
        if b % 2 == 0:
            mx.add('drums', KIT.crash, tb, 0.6)
        for k in range(8):
            y = S.supersaw(notes + [notes[0] + 12], EIGHTH * 0.8, 0.8, 5000)
            y = y * (0.35 if k % 2 == 0 else 1.0)
            mx.add('pad', y, tb + k * EIGHTH, 0.5)
            m = root - 12 + (12 if k % 2 else 0)
            mx.add('bass', S.softclip(S.bass_pluck(m, EIGHTH * 0.8, 1.0, 1.8) * 2, 2) * 0.55, tb + k * EIGHTH, 0.9)
        mx.add('brass', S.orch_hit(notes[0] + 12), tb, 0.35 + b * 0.05)
    # chant
    chant = []
    for b in range(6):
        ev, _ = notation.parse("Con-/E4+G#4+B4 trol/_ dou-/_ ble-/_ you:2/_ r:2", t0 + b * BAR,
                               word_prefix=f'ch{b}', voice='david')
        chant += ev
    base = chant[0]['t']
    for e in chant:
        e['t'] -= base
    y = voice.sing(chant, 'david', mode='blend', octave_psola=-1, vibrato=0, vocoder_gain=0.8)
    mx.add('vox', y, base, 0.9)
    yz = voice.sing([dict(e, voice='zira') for e in chant], 'zira', mode='vocoder', vibrato=0, detune=0.15)
    mx.add('choir', S.pan(yz, 0.3), base, 0.7)
    fin, _ = notation.parse("Too/B4 ma-/C#5 ny/D#5 tabs:5/E5 | TOO/B5+E5 MA-/C#6+F#5 NY/D#6+G#5 TABS:5/E6+B5+G#5",
                            t0 + 6 * BAR, word_prefix='fin')
    b0 = fin[0]['t']
    for e in fin:
        e['t'] -= b0
    y = voice.sing(fin, 'david', mode='blend', octave_psola=-1)
    mx.add('vox', y, b0, 1.0)
    yz = voice.sing([dict(e, voice='zira') for e in fin], 'zira', mode='vocoder', detune=0.2)
    mx.add('choir', S.pan(yz, -0.3), b0, 0.8)
    mx.add('sfx', S.sfx_riser(16.0, 0.5), t0)
    mx.add('sfx', S.sfx_fan(16.0, 0.6), t0)
    # doubling tab pops on every beat
    for k in range(32):
        cnt = min(2 ** k, 16)
        for j in range(cnt):
            mx.add('sfx', S.sfx_pop(1 + k * 0.04 + j * 0.03, 0.12 + 0.2 / cnt), t0 + k * BEAT + j * BEAT / cnt, 1.0,
                   ((j * 37) % 17) / 8.5 - 1)
    mx.add('sfx', S.sfx_glitch(0.5, 1.0, 9), t0 + 15.5)


def sec_crash(mx):
    t0 = SC.SEC['crash'][0]
    mx.add('sfx', S.sfx_power_down(1.4, 1.0), t0)
    mx.add('sfx', S.sfx_hum(6.0, 0.5), t0 + 0.2)
    mx.add('sfx', S.fade(S.sfx_error(0.6), 0.001, 0.05), t0 + 0.6)
    for k in range(9):
        mx.add('sfx', S.sfx_key(0.25), t0 + 1.2 + k * 0.52)


def sec_epilogue(mx):
    t0 = SC.SEC['epilogue'][0]
    # 5 bars of slow piano
    chords = [(50, [62, 66, 69]), (49, [61, 64, 69]), (47, [62, 66, 71]), (43, [62, 67, 71]), (50, [62, 66, 69, 74])]
    mel = [("A4", 0.0, 1.2), ("B4", 1.2, 0.8), ("C#5", 2.0, 1.0), ("D5", 3.0, 5.0),
           ("A4", 8.0, 1.0), ("B4", 9.0, 1.0), ("C#5", 10.0, 1.0), ("F#5", 11.0, 5.0)]
    for b, (bass, notes) in enumerate(chords):
        tb = t0 + b * BAR
        mx.add('keys', S.piano(bass - 12, BAR * 1.0, 0.6), tb, 0.9)
        for i, n in enumerate(notes):
            mx.add('keys', S.piano(n, BAR - i * 0.25, 0.4), tb + i * 0.25, 0.7)
        mx.add('pad', S.pad([bass, notes[0], notes[-1]], BAR, 0.3, 900, 0.8, 1.0), tb, 0.4)
    for nm, st, d in mel:
        mx.add('lead', S.piano(notation.note(nm), d * BEAT, 0.7), t0 + st * BEAT, 0.8)
    mx.add('sfx', S.sfx_click(0.7), t0 + 8.0)
    mx.add('sfx', S.sfx_sparkle(0.6), t0 + 8.05)
    mx.add('keys', S.piano(38, 5.0, 0.7), t0 + 10.0, 0.9)
    for n in (62, 66, 69, 74):
        mx.add('keys', S.piano(n, 5.0, 0.4), t0 + 10.0, 0.6)
    # restore dialog ding + click at 213.5
    mx.add('sfx', S.sfx_ding(0.5), t0 + 13.0)
    mx.add('sfx', S.sfx_click(1.0), t0 + 15.5)
    # blast 214-218
    tb = t0 + 16.0
    mx.add('drums', KIT.crash, tb, 1.0)
    mx.add('drums', S.boom(1.0), tb, 0.9)
    for b in range(2):
        bb = tb + b * BAR
        for k in range(4):
            mx.add('drums', KIT.kick, bb + k * BEAT, 1.0)
            if k % 2:
                mx.add('drums', KIT.snare_gated, bb + k * BEAT, 1.0)
        for k in range(8):
            mx.add('drums', KIT.hat_c, bb + k * EIGHTH, 0.5)
            mx.add('bass', S.bass_pluck(38 + (12 if k % 2 else 0) + (5 if b == 1 and k >= 4 else 0), EIGHTH * 0.8, 1.0, 1.3),
                   bb + k * EIGHTH, 0.9)
        for n in ([62, 66, 69, 74] if b == 0 else [67, 71, 74, 79]):
            mx.add('brass', S.brass(n, BAR * 0.9), bb, 0.5)
            mx.add('pad', S.supersaw([n], BAR * 0.9, 0.5), bb, 0.5)
    for i in range(12):
        mx.add('drums', KIT.toms[i % 4], tb + BAR + 2 * BEAT + i * (1.5 * BEAT / 12), 0.8)
    # final hit
    for n in (50, 57, 62, 66, 69, 74):
        mx.add('brass', S.orch_hit(n + 12, 1.0), tb + 3.5, 0.3)
    mx.add('drums', KIT.crash, tb + 3.5, 1.0)
    fin, _ = notation.parse("Too/A4 ma-/B4 ny/C#5 tabs:5/D5 | TOO/A4+D5 MA-/B4+E5 NY/C#5+F#5 TABS:3/D5+A5", tb,
                            word_prefix='blast')
    b0 = fin[0]['t']
    for e in fin:
        e['t'] -= b0
    mx.add('vox', voice.sing(fin, 'david', mode='blend', octave_psola=-1), b0, 1.0)
    mx.add('choir', voice.sing([dict(e, voice='zira') for e in fin], 'zira', mode='vocoder', detune=0.2), b0, 0.8)
    # end card pop
    mx.add('sfx', S.sfx_pop(1.4, 0.7), SC.TOTAL - 1.0)


def add_dialog(mx):
    for (t, vc, rate, text, semis, fx) in SC.DIALOG:
        mx.add('dialog', dialog_clip(text, vc, rate, semis, fx), t, 1.0)


def collect_tts():
    for season in ('s1', 's2', 's3'):
        for e in SC.lead_events(season, 0):
            tts.request(e['word'], 'david')
        for e in SC.choir_events(0):
            tts.request(e['word'], 'zira')
    for w in ('con', 'control', 'double you', 'too', 'many', 'tabs', 'ah', 'uuuuhhhh'):
        tts.request(w, 'david')
        tts.request(w, 'zira')
    for r in range(2, 7):
        tts.request('ha ha ha ha ha', 'zira', r)
        tts.request('ha ha ha ha ha', 'david', r)
    tts.request('uuuuhhhh', 'david', -6)
    for (t, vc, rate, text, semis, fx) in SC.DIALOG:
        tts.request(text, vc, rate)
    n = tts.generate()
    log('tts generated', n)


# ---------------------------------------------------------------- master

@njit(cache=True)
def _limiter(x, thr, look, rel):
    n = x.shape[1]
    g = np.ones(n, np.float32)
    env = 1.0
    peak = np.zeros(n, np.float32)
    for i in range(n):
        a = abs(x[0, i])
        b = abs(x[1, i])
        peak[i] = a if a > b else b
    # sliding max over lookahead window
    need = np.ones(n, np.float32)
    for i in range(n):
        p = peak[i]
        if p > thr:
            need[i] = thr / p
    out_g = np.ones(n, np.float32)
    # backward pass: apply attack over lookahead
    cur = 1.0
    for i in range(n - 1, -1, -1):
        v = need[i]
        if v < cur:
            cur = v
        else:
            cur = cur + (1.0 - cur) * (1.0 / look)
            if cur > 1.0:
                cur = 1.0
        out_g[i] = cur
    # forward release smoothing
    cur = 1.0
    coef = 1.0 / rel
    for i in range(n):
        v = out_g[i]
        if v < cur:
            cur = v
        else:
            cur = cur + (v - cur) * coef
        g[i] = cur
    return g


def apply_ytp(pre, vox_only):
    t0 = SC.SEC['ytp'][0]
    s1 = SC.SEC['s1'][0]
    for e in edits.YTP:
        o = int(round((t0 + e['o']) * SR))
        n = int(round(e['d'] * SR))
        srcbuf = pre if e['src'] == 'mix' else vox_only
        if 'tapestop' in e['vfx']:
            a = int((s1 + e['s']) * SR)
            seg = srcbuf[:, a:a + n].copy()
            seg = S.tape_stop(seg)
        elif e['stutter']:
            L = int(round(e['stutter'] * e['speed'] * SR))
            a = int((s1 + e['s']) * SR)
            sl = srcbuf[:, a:a + L].copy()
            if e['reverse']:
                sl = sl[:, ::-1]
            if e['speed'] != 1.0:
                sl = np.stack([S.resample(ch, e['speed']) for ch in sl])
            sl = S.fade(sl, 0.003, 0.006)
            reps = int(math.ceil(n / sl.shape[1]))
            seg = np.tile(sl, (1, reps))[:, :n]
        else:
            L = int(round(e['d'] * e['speed'] * SR))
            a = int((s1 + e['s']) * SR)
            sl = srcbuf[:, a:a + L].copy()
            if e['reverse']:
                sl = sl[:, ::-1]
            if e['speed'] != 1.0:
                sl = np.stack([S.resample(ch, e['speed']) for ch in sl])
            seg = sl[:, :n]
            if seg.shape[1] < n:
                seg = np.concatenate([seg, np.zeros((2, n - seg.shape[1]), np.float32)], axis=1)
        if e['crush']:
            seg = np.stack([S.bitcrush(S.softclip(S.peaking(ch, 90, 12, 0.7) * 3.0, 3.0), 5, 3) for ch in seg])
        seg = S.fade(seg, 0.002, 0.004) * e['gain']
        pre[:, o:o + n] += seg[:, :max(0, min(n, pre.shape[1] - o))]
    # glue: stutter hits on bar downbeats
    for b in range(8):
        pre[:, int((t0 + b * BAR) * SR):int((t0 + b * BAR) * SR) + len(KIT.kick)] += S.pan(KIT.kick) * 0.6


def apply_recursion(pre):
    t0 = SC.SEC['recursion'][0]
    s1 = SC.SEC['s1'][0]
    n = int(SC.SEC['recursion'][1] * SR)
    o = np.arange(n) / SR
    src = s1 + np.array([edits.rec_source_time(x) for x in o[::48]])
    src = np.interp(o, o[::48], src)
    idx = src * SR
    base = np.arange(pre.shape[1])
    for ch in range(2):
        pre[ch, int(t0 * SR):int(t0 * SR) + n] += np.interp(idx, base, pre[ch]).astype(np.float32) * 0.95
    for b in range(8):
        w = S.sfx_whoosh(0.6, 0.5)
        pre[:, int((t0 + b * BAR - 0.3) * SR):int((t0 + b * BAR - 0.3) * SR) + len(w)] += S.pan(w) * 0.7


def render(out_wav=None, stems_dir=None):
    global KIT
    t_start = time.time()
    collect_tts()
    KIT = Kit()
    mx = Mixer()
    for fn in (sec_cold_open, sec_s1, sec_episode, sec_s2, sec_space, sec_hamster, sec_s3, sec_finale, sec_crash,
               sec_epilogue):
        t = time.time()
        fn(mx)
        log(fn.__name__, f'{time.time() - t:.1f}s')
    add_dialog(mx)
    log('stems done')
    # ---- bus processing
    def mono(x):
        return x.mean(0)
    buses = {}
    gains = dict(drums=0.85, bass=0.75, keys=0.5, pad=0.42, brass=0.5, lead=0.5, vox=1.0, vox_horror=1.0,
                 choir=0.5, sfx=0.8, dialog=1.15)
    sends = dict(keys=0.25, pad=0.3, brass=0.2, lead=0.3, vox=0.22, vox_horror=0.7, choir=0.45, drums=0.06)
    for name, b in mx.stems.items():
        x = b
        if name in ('vox', 'vox_horror'):
            x = np.stack([S.hp(S.peaking(ch, 3000, 3.5, 0.9), 120) for ch in x])
            x = S.softclip(x * 1.3, 1.3)
        if name == 'bass':
            x = np.stack([S.hp(ch, 35) for ch in x])
        if name in sends:
            wet = S.reverb(mono(x), 0.88 if name == 'vox_horror' else 0.75, 0.45, 0.01)[:, :NS]
            x = x + wet * sends[name] * 3.0
        buses[name] = x * gains.get(name, 1.0)
        log('bus', name)
    music = sum(v for k, v in buses.items() if k not in ('dialog',))
    # sidechain-ish ducking of music under dialog
    dl = buses['dialog']
    env = np.abs(dl).max(0)
    k = S.N(0.15)
    env = np.convolve(env, np.ones(k) / k, mode='same')
    duck = 1 - 0.45 * np.clip(env * 6, 0, 1)
    pre = music * duck.astype(np.float32) + dl
    vox_only = buses.get('vox', np.zeros_like(pre))
    apply_ytp(pre, vox_only)
    apply_recursion(pre)
    pre = np.stack([S.hp(ch, 25) for ch in pre])
    # master: normalise loud sections then limit
    pk_region = pre[:, int(SC.SEC['s1'][0] * SR):int(SC.SEC['s2'][0] * SR)]
    rms = np.sqrt((pk_region ** 2).mean())
    target = 10 ** (-15.5 / 20)
    pre *= target / (rms + 1e-9)
    master_gain = target / (rms + 1e-9)
    if stems_dir:
        from scipy.io import wavfile
        os.makedirs(stems_dir, exist_ok=True)
        for name, x in buses.items():
            wavfile.write(os.path.join(stems_dir, f'{name}.wav'), SR, (x * master_gain).T.astype(np.float32))
        log('stems written to', stems_dir)
    g = _limiter(pre, np.float32(0.89), S.N(0.004), S.N(0.08))
    out = pre * g
    out = np.clip(out, -0.98, 0.98)
    out_wav = out_wav or os.path.join(BUILD, 'soundtrack.wav')
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out.T * 32767).astype(np.int16).tobytes())
    log('wrote', out_wav, f'{time.time() - t_start:.0f}s total')
    # stats per section
    for name, st, nb in SC.SECTIONS:
        a, b2 = int(st * BAR * SR), int((st + nb) * BAR * SR)
        seg = out[:, a:b2]
        log(f'{name:10s} peak {20 * np.log10(np.abs(seg).max() + 1e-9):6.1f} dBFS  rms {20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9):6.1f} dBFS')
    return out_wav
