"""Tiny text notation for melodies.

Tokens: syl[:eighths][/pitch]   rest: r[:eighths]
A syllable ending in '-' continues into the next token's word ("re- ci- pe").
pitch: note name (C#4, Bb3) or midi int, chords joined with '+'. '_' repeats the previous pitch.
"""
import re

from .config import EIGHTH

_NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

PRONOUNCE = {
    'favicons': 'fave icons', 'localhost': 'local host', 'thirty': 'thirty', "can't": "can't",
    'w': 'double you', 'ctrl': 'control', 'doubleyou': 'double you', 'aah': 'ah',
}


def note(nm):
    if isinstance(nm, (int, float)):
        return float(nm)
    s = nm.strip()
    if re.fullmatch(r'-?\d+(\.\d+)?', s):
        return float(s)
    m = re.fullmatch(r'([A-G])([#b]?)(-?\d)', s)
    if not m:
        raise ValueError(f'bad note {nm}')
    n = _NOTE[m.group(1)] + (1 if m.group(2) == '#' else -1 if m.group(2) == 'b' else 0)
    return float(12 * (int(m.group(3)) + 1) + n)


def parse(line, start=0.0, transpose=0, gain=1.0, voice=None, word_prefix=''):
    """Returns (events, end_time). Times in seconds, start in seconds."""
    events = []
    t = start
    prev = [60.0]
    word_syls = []
    wid_counter = [0]

    def flush():
        if not word_syls:
            return
        text = ''.join(e['syl_text'] for e in word_syls)
        key = re.sub(r"[^a-z']", '', text.lower())
        spoken = PRONOUNCE.get(key, text.lower())
        wid_counter[0] += 1
        wid = f'{word_prefix}{start:.3f}_{wid_counter[0]}'
        for i, e in enumerate(word_syls):
            e['word'] = spoken
            e['syl'] = i
            e['nsyl'] = len(word_syls)
            e['word_id'] = wid
        word_syls.clear()

    for tok in line.split():
        if tok == '|':
            continue
        dur = 1.0
        pitch = None
        m = re.fullmatch(r"([^:/]+)(?::([\d.]+))?(?:/(.+))?", tok)
        if not m:
            raise ValueError(tok)
        syl, d, p = m.group(1), m.group(2), m.group(3)
        if d:
            dur = float(d)
        if syl == 'r':
            flush()
            t += dur * EIGHTH
            continue
        if p is None or p == '_':
            pitches = list(prev)
        else:
            pitches = [note(x) + transpose for x in p.split('+')]
            prev = pitches
        cont = syl.endswith('-')
        clean = syl.rstrip('-').replace('~', ' ')
        ev = dict(t=t, d=dur * EIGHTH, pitches=pitches, syl_text=clean, gain=gain, lyric=clean)
        if voice:
            ev['voice'] = voice
        events.append(ev)
        word_syls.append(ev)
        if not cont:
            flush()
        t += dur * EIGHTH
    flush()
    return events, t
