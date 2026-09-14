"""Time remapping shared by audio and video for the YTP breakdown and the recursion zoom.

An edit plays source material (seconds relative to the start of Season 1) at output time o (relative to
the section start) for d seconds. speed = source seconds per output second (pitch follows speed, like tape).
"""
import math

from .score import SEC

S1 = SEC['s1'][0]


def E(o, d, s, speed=1.0, reverse=False, stutter=None, gain=1.0, crush=False, vfx=(), text=None, src='mix'):
    return dict(o=o, d=d, s=s, speed=speed, reverse=reverse, stutter=stutter, gain=gain, crush=crush,
                vfx=tuple(vfx), text=text, src=src)


YTP = [
    # bar 1: T-T-T-TABS, rising pitch
    E(0.00, 0.50, 20.0, stutter=0.125, vfx=('zoom', 'shake'), text='T-T-T-'),
    E(0.50, 0.50, 20.0, vfx=('zoom',), text='TABS'),
    E(1.00, 0.50, 20.0, speed=1.335, vfx=('hue', 'zoom'), text='TABS'),
    E(1.50, 0.50, 20.0, speed=2.0, vfx=('invert', 'zoom'), text='TABS'),
    # bar 2: reversed search, then the close
    E(2.00, 1.00, 4.25, reverse=True, speed=1.25, vfx=('mirror', 'hue'), text='HCRAES KCIUQ'),
    E(3.00, 1.00, 12.25, vfx=()),
    # bar 3: down down dooown DOOOOWN
    E(4.00, 0.25, 13.0, vfx=('zoom',), text='DOWN'),
    E(4.25, 0.25, 13.0, vfx=('zoom', 'invert'), text='DOWN'),
    E(4.50, 0.50, 13.0, speed=0.5, vfx=('slow', 'fry'), text='DOOWN'),
    E(5.00, 1.00, 13.0, speed=0.25, vfx=('slow', 'fry', 'shake'), text='D O O O W N'),
    # bar 4: too ma too ma too ma ny ny
    E(6.00, 1.50, 19.25, stutter=0.5, vfx=('kaleido',), text='TOO MANY TOO MANY'),
    E(7.50, 0.50, 19.75, stutter=0.25, vfx=('mirror', 'zoom'), text='NY NY'),
    # bar 5: buffering
    E(8.00, 1.00, 14.25, stutter=0.1, vfx=('buffer',), text='BUFFERING'),
    E(9.00, 0.50, 14.35, stutter=0.5, gain=0.0, vfx=('buffer', 'freeze')),
    E(9.50, 0.50, 14.0, vfx=('zoom',)),
    # bar 6: eight eight EIGHT EIGHT
    E(10.00, 1.00, 16.25, vfx=()),
    E(11.00, 0.25, 17.0, vfx=('zoom',), text='8'),
    E(11.25, 0.25, 17.0 - 0.0, speed=1.26, vfx=('zoom', 'hue'), text='88'),
    E(11.50, 0.25, 17.0, speed=1.59, vfx=('zoom', 'invert'), text='888'),
    E(11.75, 0.25, 17.0, speed=2.0, vfx=('zoom', 'hue'), text='8888'),
    # bar 7: deep-fried TABS
    E(12.00, 2.00, 20.0, crush=True, gain=1.6, vfx=('fry', 'shake', 'circle'), text='TOO MANY TABS'),
    # bar 8: chipmunk, tape stop, silence
    E(14.00, 1.00, 28.0, speed=2.0, vfx=('hue', 'speed')),
    E(15.00, 0.75, 30.0, vfx=('tapestop',)),
    E(15.75, 0.25, 30.75, gain=0.0, vfx=('black',)),
]


def ytp_edit_at(o):
    for e in YTP:
        if e['o'] <= o < e['o'] + e['d']:
            return e
    return None


def ytp_source_time(o):
    """Source time (relative to S1 start) shown at output time o in the YTP section, and the edit."""
    e = ytp_edit_at(o)
    if e is None:
        return 0.0, None
    u = o - e['o']
    if e['vfx'] and 'tapestop' in e['vfx']:
        frac = u / e['d']
        # integral of (1-x)^1.3 from 0..frac, scaled to duration
        pos = (1 - (1 - frac) ** 2.3) / 2.3 * e['d']
        return e['s'] + pos, e
    if e['stutter']:
        u = u % e['stutter']
    if e['reverse']:
        span = (e['stutter'] or e['d'])
        u = span - u
    return e['s'] + u * e['speed'], e


# ---------------------------------------------------------------- recursion (nightcore zoom)
REC_DUR = SEC['recursion'][1]
REC_RATE1 = 2.6
_k = math.log(REC_RATE1) / REC_DUR


def rec_rate(o):
    return math.exp(_k * o)


def rec_source_time(o):
    """Source time relative to S1 start for output time o in the recursion section."""
    return (math.exp(_k * o) - 1) / _k
