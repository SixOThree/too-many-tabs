"""Master timeline shared by audio and video. One bar = 2 seconds (120 BPM, 4/4)."""
from .config import BAR, BEAT, EIGHTH
from . import notation

# name, start bar, length in bars
SECTIONS = [
    ('cold_open', 0, 4),
    ('s1', 4, 16),
    ('episode', 20, 4),
    ('s2', 24, 16),
    ('space', 40, 8),
    ('ytp', 48, 8),
    ('hamster', 56, 8),
    ('s3', 64, 16),
    ('recursion', 80, 8),
    ('finale', 88, 8),
    ('crash', 96, 3),
    ('epilogue', 99, 13),
]
SEC = {name: (start * BAR, n * BAR) for name, start, n in SECTIONS}
TOTAL = (SECTIONS[-1][1] + SECTIONS[-1][2]) * BAR


def section_at(t):
    for name, start, n in SECTIONS:
        if start * BAR <= t < (start + n) * BAR:
            return name, t - start * BAR
    return SECTIONS[-1][0], t - SECTIONS[-1][1] * BAR


def bar_t(section, bar, beat=0.0):
    """Absolute time of 1-based bar and 0-based beat inside a section."""
    return SEC[section][0] + (bar - 1) * BAR + beat * BEAT


# ---------------------------------------------------------------- harmony (key of D, transposed per season)
# each bar: list of (beats, chord) ; chord = (root midi, quality, bass override or None)
D, E, Fs, G, A, B, Cs = 50, 52, 54, 55, 57, 59, 61
CHORDS_LOOP = [
    [(4, (D, 'maj'))], [(4, (A, 'sus4'))],                        # 1-2 intro
    [(4, (D, 'maj'))], [(4, (B, 'min'))], [(4, (G, 'maj'))], [(4, (A, 'maj'))],   # 3-6
    [(4, (G, 'maj'))], [(4, (A, 'maj'))], [(2, (Fs, 'min')), (2, (B, 'min'))], [(2, (E, 'min')), (2, (A, '7'))],  # 7-10
    [(4, (D, 'maj'))], [(4, (A, 'maj', Cs))], [(4, (B, 'min'))], [(4, (G, 'maj'))],  # 11-14
    [(2, (E, 'min')), (2, (A, '7'))], [(2, (G, 'maj')), (2, (A, 'sus4'))],          # 15-16
]

QUAL = {'maj': (0, 4, 7), 'min': (0, 3, 7), '7': (0, 4, 7, 10), 'sus4': (0, 5, 7), 'dim': (0, 3, 6),
        'min7': (0, 3, 7, 10), 'maj7': (0, 4, 7, 11), 'add9': (0, 4, 7, 14)}


def minorize(m, tonic=62):
    deg = (int(round(m)) - tonic) % 12
    return m - 1 if deg in (4, 9, 11) else m


def minor_chord(ch):
    root, q = ch[0], ch[1]
    deg = (root - 50) % 12
    # D->Dm, Bm->Bb, G->Gm, A->A (keep dominant), F#m->F, Em->Edim-ish, C#->C
    if deg == 0:
        return (root, 'min')
    if deg == 9:
        return (root - 1, 'maj')
    if deg == 5:
        return (root, 'min')
    if deg == 4:
        return (root - 1, 'maj')
    if deg == 2:
        return (root, 'dim')
    if deg == 7:
        return (root, q if q in ('7', 'maj', 'sus4') else 'maj')
    return ch


def chord_notes(ch, octave_shift=0):
    root, q = ch[0], ch[1]
    return [root + i + octave_shift for i in QUAL[q]]


# ---------------------------------------------------------------- melody + lyrics
# melody: per slot (eighths) with pitch; lyrics tokens aligned in order with sung slots.
MELODY = [
    # bar 3
    ('r', 1), ('F#4', 1), ('F#4', 1), ('E4', 1), ('D4', 2), ('F#4', 1), ('F#4', 1),
    # bar 4
    ('A4', 1), ('F#4', 3), ('r', 4),
    # bar 5
    ('r', 1), ('D4', 1), ('F#4', 1), ('G4', 1), ('A4', 2), ('B4', 1), ('A4', 1),
    # bar 6
    ('G4', 1), ('E4', 3), ('r', 4),
    # bar 7
    ('r', 1), ('G4', 1), ('B4', 1), ('B4', 1), ('D5', 2), ('B4', 1), ('A4', 1),
    # bar 8
    ('B4', 1), ('A4', 3), ('r', 4),
    # bar 9
    ('r', 1), ('A4', 1), ('A4', 1), ('A4', 1), ('C#5', 2), ('D5', 1), ('D5', 1),
    # bar 10
    ('B4', 1), ('C#5', 3), ('r', 1), ('A4', 1), ('B4', 1), ('C#5', 1),
    # bar 11
    ('D5', 4), ('r', 4),
    # bar 12
    ('r', 5), ('A4', 1), ('B4', 1), ('C#5', 1),
    # bar 13
    ('D5', 4), ('r', 4),
    # bar 14
    ('r', 5), ('F#4', 1), ('F#4', 1), ('E4', 1),
    # bar 15
    ('D4', 2), ('E4', 1), ('F#4', 1), ('E4', 1), ('E4', 3),
    # bar 16
    ('A4', 1), ('B4', 1), ('C#5', 1), ('D5', 5),
]

CHORUS = "Too ma- ny tabs Too ma- ny tabs"

LYRICS = {
    's1': ("Just one quick search, just one quick look, a re- ci- pe, a how- to book, "
           "I close one down and two pop through, now there are eight, now thir- ty two! "
           "Too ma- ny TABS! Too ma- ny TABS! Can't find the one that's play- ing sound, too ma- ny tabs!"),
    's2': ("The ti- ny i- cons shrink and fade, a hun- dred fav- i- cons pa- rade, "
           "I'll read that ar- ti- cle some- day, it's been there o- pen since last May. "
           "Too ma- ny TABS! Too ma- ny TABS! Can't find the one that's play- ing sound, too ma- ny tabs!"),
    's3': ("A sha- dow creeps a- long the bar, it knows ex- act- ly where you are. "
           "You close them all, you think you're free. Re- store pre- vi- ous ses- sion? Yes. "
           "Too ma- ny TABS! Too ma- ny TABS! They all come back, they all come back, too ma- ny tabs!"),
}

# backing choir "too ma- ny TABS" responses: (bar, slot start, chord pitch sets)
CHOIR_RESP = [
    (11, 5, [('D4', 'F#4', 'A3'), ('E4', 'G4', 'B3'), ('F#4', 'A4', 'C#4')], ('C#4', 'E4', 'A4')),
    (13, 5, [('B3', 'D4', 'F#3'), ('C#4', 'E4', 'G3'), ('D4', 'F#4', 'A3')], ('B3', 'D4', 'G4')),
]


def _clean_tokens(lyr):
    toks = []
    for raw in lyr.split():
        w = raw.strip(',.!?')
        toks.append(w)
    return toks


def lead_line(season):
    """Notation string for the lead vocal of a season (bars 3..16 of the loop)."""
    toks = _clean_tokens(LYRICS[season])
    out = []
    i = 0
    for p, d in MELODY:
        if p == 'r':
            out.append(f'r:{d}')
            continue
        syl = toks[i]
        i += 1
        out.append(f'{syl}:{d}/{p}')
    assert i == len(toks), (season, i, len(toks))
    return ' '.join(out)


def lead_events(season, t0, transpose=0, minor=False, voice='david'):
    line = lead_line(season)
    ev, _ = notation.parse(line, t0 + 2 * BAR, transpose=0, voice=voice, word_prefix=season)
    for e in ev:
        ps = e['pitches']
        if minor:
            ps = [minorize(p) for p in ps]
        e['pitches'] = [p + transpose for p in ps]
    return ev


def choir_events(t0, transpose=0, minor=False, voice='zira', season='x'):
    evs = []
    for bar, slot, picks, hit in CHOIR_RESP:
        tb = t0 + (bar - 1) * BAR + slot * EIGHTH
        s = ' '.join([f"too/{'+'.join(picks[0])}", f"ma-/{'+'.join(picks[1])}", f"ny/{'+'.join(picks[2])}",
                      f"tabs:4/{'+'.join(hit)}"])
        ev, _ = notation.parse(s, tb, voice=voice, word_prefix=f'{season}c{bar}')
        evs += ev
    # final line doubled in harmony
    tb = t0 + 15 * BAR
    ev, _ = notation.parse("Too/F#4+D4 ma-/G4+D4 ny/A4+E4 tabs:5/A4+F#4", tb, voice=voice, word_prefix=f'{season}cf')
    evs += ev
    for e in evs:
        ps = e['pitches']
        if minor:
            ps = [minorize(p) for p in ps]
        e['pitches'] = [p + transpose for p in ps]
    return evs


def lyric_spans(season, t0):
    """(start, end, text) of each sung syllable for on-screen karaoke and lip sync."""
    ev = lead_events(season, t0)
    return [(e['t'], e['t'] + e['d'], e['lyric']) for e in ev]


# ---------------------------------------------------------------- cold open tab pops (accelerating)
POP_TIMES_COLD = []
_tt, _gap, _i = 3.95, 0.95, 0
while _tt < 7.9:
    POP_TIMES_COLD.append((_tt, 1.0 + _i * 0.06))
    _tt += _gap
    _gap = max(0.05, _gap * 0.72)
    _i += 1
CLOSE_CLICKS_COLD = (5.15, 5.65, 6.05)

# ---------------------------------------------------------------- spoken lines (absolute seconds)
# (time, voice, rate, text, semitones, fx)
DIALOG = [
    (1.5, 'zira', 0, "Okay. I'll just check one thing.", 0, 'room'),
    (4.3, 'david', -2, "It started... with one tab.", -3, 'announcer'),
    (40.25, 'david', -1, "Episode one. Just one more.", -3, 'announcer'),
    (41.7, 'david', 1, "Okay. I am closing ONE tab.", 0, 'room'),
    (44.05, 'zira', 2, "Hi!", 7, 'room'),
    (44.1, 'zira', 2, "Hi!", 4, 'room'),
    (46.0, 'david', 0, "Oh, come on.", 0, 'room'),
    (84.1, 'david', 0, "Captain's log. We have four thousand tabs open. Morale is low.", -1, 'radio'),
    (89.9, 'zira', -1, "Warning. Memory critical.", -2, 'robot'),
    (92.3, 'david', 2, "Close them! Close them all!", 0, 'radio'),
    (114.6, 'zira', 3, "Oh gosh. Oh gosh. Oh gosh.", 10, 'dry'),
    (119.8, 'zira', 3, "I need more gigabytes!", 10, 'dry'),
    (123.2, 'zira', 4, "Too many tabs!", 11, 'dry'),
    (126.1, 'zira', -4, "tabs...", 9, 'dry'),
    (135.05, 'david', -4, "restore", -7, 'whisper'),
    (139.05, 'david', -4, "restore", -7, 'whisper'),
    (193.0, 'zira', -1, "Your browser ran into a problem.", 0, 'room'),
    (195.6, 'zira', -1, "Restoring four billion tabs.", 0, 'room'),
    (205.2, 'zira', -2, "It's okay.", 6, 'room'),
    (211.3, 'david', -3, "Restore previous session?", -6, 'whisper'),
    (218.6, 'david', -2, "Too Many Tabs will return. In a new tab.", -3, 'announcer'),
]
