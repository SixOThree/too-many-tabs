"""Scenes for cold open, episode, space, YTP, hamster, horror, recursion, finale, crash, epilogue."""
import functools
import math

import cairo

from .util import PI, TAU, clamp, lerp, smooth, ease_out, ease_in, ease_in_out, ease_out_back, hrand, hsign, bounce
from . import gfx, cast, loop, edits, tts
from .gfx import OUTLINE, src, rrect, circle, ellipse, text
from .common import (W, H, FX, living_room, couch_back, couch_front, slam_text, credit, talk_mouth, blink_at,
                     random_tabs, mini_tab, FAVS, TAB_COLS, RANDOM_TITLES, sky, tab_cloud)
from . import score as SC
from .config import REPO_URL

BAR = 2.0


def fmt_int(n):
    return f'{n:,}'


def dialog_mouth(t_abs, idx_filter=None, voice=None):
    """Mouth amount from the spoken DIALOG table (approximate durations)."""
    for (t, vc, rate, txt, semis, fx) in SC.DIALOG:
        if voice and vc != voice:
            continue
        dur = 0.075 * len(txt) * (2 ** (-semis / 12)) * (1 - rate * 0.06)
        if t <= t_abs <= t + dur:
            return talk_mouth(t_abs, t, dur, int(t * 7))
    return 0.0


_line_durs = {}


def line_duration(start, text_len=12, semis=0, rate=0):
    """Duration of the DIALOG line starting at `start`, from its generated voice clip when available."""
    if start not in _line_durs:
        dur = None
        for (t0, vc, r, txt, st, _fx) in SC.DIALOG:
            if abs(t0 - start) < 1e-6:
                d = tts.cached_duration(txt, vc, r)
                if d is not None:
                    dur = d * 2 ** (-st / 12)
                break
        _line_durs[start] = dur
    dur = _line_durs[start]
    if dur is None:
        dur = 0.075 * text_len * (2 ** (-semis / 12)) * (1 - rate * 0.06)
    return dur


def spoken(t_abs, start, text_len, semis=0, rate=0):
    return talk_mouth(t_abs, start, line_duration(start, text_len, semis, rate), int(start * 7))


# ================================================================ COLD OPEN (0-8)

COLD_TITLES = ['rain gear reviews', 'umbrella history', 'why do clouds float', 'cloud shaped cats', 'is rain wet',
               'Inbox (1)', 'best umbrella 2026', 'umbrella vs poncho', 'poncho history', 'how to fold a poncho',
               'is a poncho a blanket', 'blanket forts', 'fort history', 'Inbox (2)', 'how to close tabs',
               'tabs keep opening help', 'Loading...', 'Loading...', 'Loading...', 'Loading...']

# search results on the page: the three the cursor clicks come first, and each one opens the next tab to pop
COLD_LINK_X, COLD_LINK_Y0, COLD_LINK_DY, COLD_LINK_SIZE = 870, 350, 110, 42


def _cold_links():
    clicked, used = [], set()
    for ct in SC.CLOSE_CLICKS_COLD:
        # each click owns the first tab pop after it that no earlier click has claimed
        nxt = next(i for i, (pt, _) in enumerate(SC.POP_TIMES_COLD) if pt > ct and i not in used)
        used.add(nxt)
        clicked.append(COLD_TITLES[nxt % len(COLD_TITLES)])
    others = [tl for tl in ('best umbrella 2026', 'umbrella vs poncho', 'poncho history') if tl not in clicked]
    return clicked + others


COLD_LINKS = _cold_links()


def draw_cold_open(c, lt, t, fx):
    if lt < 1.2:
        src(c, '#1030b8')
        c.paint()
        pw, _ = text(c, 'PLAY', 90, 130, 80, 'Consolas', bold=True, col='#ffffff', shadow=(0, 0, 0, 0.5), soff=(4, 4))
        # Consolas has no play glyph, so draw the triangle
        tx, ty = 90 + pw + 36, 130 - 29
        for (ox, oy), col in (((4, 4), (0, 0, 0, 0.5)), ((0, 0), '#ffffff')):
            c.move_to(tx + ox, ty - 26 + oy)
            c.line_to(tx + 46 + ox, ty + oy)
            c.line_to(tx + ox, ty + 26 + oy)
            c.close_path()
            src(c, col)
            c.fill()
        text(c, 'SP', 1780, 130, 70, 'Consolas', bold=True, col='#ffffff', align='r')
        text(c, '0:00:0' + str(int(lt)), 1780, 1000, 64, 'Consolas', bold=True, col='#ffffff', align='r')
        if lt < 0.3:
            fx.add('slices', seed=int(lt * 60), count=40, maxshift=400)
            fx.add('flash', amt=0.3 * (1 - lt / 0.3), col=(200, 200, 200))
        fx.vhs = 1.0
        return
    # desk wallpaper
    gfx.vgrad(c, 0, 0, W, H, [(0, '#5ec2c9'), (1, '#2b7f9e')])
    typed = 'is it going to rain'
    n_typed = int(clamp((lt - 2.55) / 0.058 + 1, 0, len(typed)))
    entered = lt >= 3.72
    pops = sum(1 for (pt, _) in SC.POP_TIMES_COLD if lt >= pt)
    tabs = [('is it going to rain - Search' if entered else 'New Tab', 'search' if entered else 'plus', '#ffffff')]
    for i in range(pops):
        tabs.append((COLD_TITLES[i % len(COLD_TITLES)], FAVS[(i * 5) % len(FAVS)], TAB_COLS[i % len(TAB_COLS)]))
    zoom = 1.0
    shake = 0.0
    if lt > 6.0:
        u = lt - 6.0
        zoom = 1 + 1.6 * ease_in(u / 2.0)
        shake = 18 * u
    c.save()
    c.translate(W / 2, 90)
    c.scale(zoom, zoom)
    c.translate(-W / 2, -90)
    if shake:
        c.translate(hsign(int(lt * 30), 1) * shake, hsign(int(lt * 30), 2) * shake)
    wx, wy, ww, wh = 90, 60, 1740, 960

    def to_screen(px, py):
        sdx = hsign(int(lt * 30), 1) * shake if shake else 0.0
        sdy = hsign(int(lt * 30), 2) * shake if shake else 0.0
        return W / 2 + (px + sdx - W / 2) * zoom, 90 + (py + sdy - 90) * zoom

    # cursor path: into the search box, then onto each result link it clicks
    link_boxes = []
    for i, title in enumerate(COLD_LINKS):
        base = COLD_LINK_Y0 + i * COLD_LINK_DY
        lw = gfx.text_width(c, title, COLD_LINK_SIZE, 'Segoe UI')
        link_boxes.append((COLD_LINK_X, base - 38, COLD_LINK_X + lw, base + 10))
    keys = [(1.2, 1500, 900), (2.3, 1000, 500), (3.8, 1000, 500), (4.6, 1350, 300)]
    for i, ct in enumerate(SC.CLOSE_CLICKS_COLD):
        x0, y0, x1, y1 = link_boxes[i]
        lx, ly = x0 + min(x1 - x0, 260) * 0.45, (y0 + y1) / 2
        keys.append((ct - 0.12, lx, ly))
        keys.append((ct + 0.1, lx, ly))
    keys.append((7.0, 1200, 700))
    keys.sort()
    cx, cy = keys[-1][1], keys[-1][2]
    if lt < keys[0][0]:
        cx, cy = keys[0][1], keys[0][2]
    for (ta, xa, ya), (tb, xb, yb) in zip(keys[:-1], keys[1:]):
        if ta <= lt <= tb:
            k = ease_in_out((lt - ta) / max(1e-3, tb - ta))
            cx, cy = lerp(xa, xb, k), lerp(ya, yb, k)
            break
    if lt > 6.2:
        cx += math.sin(lt * 40) * 60
        cy += math.cos(lt * 33) * 40
    hovered = -1
    if entered:
        for i, (x0, y0, x1, y1) in enumerate(link_boxes):
            sx0, sy0 = to_screen(x0, y0)
            sx1, sy1 = to_screen(x1, y1)
            if sx0 <= cx <= sx1 and sy0 <= cy <= sy1:
                hovered = i
                break

    def page(cc, x, y, w, h):
        if not entered:
            text(cc, 'Search', x + w / 2, y + 300, 150, 'Georgia', bold=True, col='#4a6cf7', align='c')
            rrect(cc, x + w / 2 - 520, y + 380, 1040, 96, 48)
            gfx.fill_stroke(cc, '#ffffff', '#c3c8d4', 3)
            gfx.favicon(cc, 'search', x + w / 2 - 460, y + 428, 50, lt, bg=False)
            text(cc, typed[:n_typed] + ('|' if (lt * 2) % 1 < 0.5 else ''), x + w / 2 - 410, y + 445, 46, 'Segoe UI',
                 col='#222')
        else:
            text(cc, typed, x + 60, y + 80, 44, 'Segoe UI', col='#222')
            rrect(cc, x + 60, y + 130, 640, 300, 24)
            gfx.fill_stroke(cc, '#eef5ff', '#c3d4ee', 3)
            gfx.favicon(cc, 'weather', x + 180, y + 260, 150, lt, bg=False)
            text(cc, '70%', x + 330, y + 300, 120, 'Segoe UI', bold=True, col='#1a3a7a')
            text(cc, 'chance of rain', x + 330, y + 360, 40, 'Segoe UI', col='#4a5a7a')
            for i, title in enumerate(COLD_LINKS):
                visited = i < len(SC.CLOSE_CLICKS_COLD) and lt >= SC.CLOSE_CLICKS_COLD[i]
                x0, y0, x1, y1 = link_boxes[i]
                base = COLD_LINK_Y0 + i * COLD_LINK_DY
                text(cc, title, x0, base, COLD_LINK_SIZE, 'Segoe UI', col='#681da8' if visited else '#1a0dab')
                if i == hovered:
                    src(cc, '#681da8' if visited else '#1a0dab')
                    cc.rectangle(x0, base + 6, x1 - x0, 3)
                    cc.fill()
                src(cc, '#c9cdd6')
                cc.rectangle(x0, base + 25, 700, 14)
                cc.fill()
    gfx.browser_window(c, wx, wy, ww, wh, tabs, lt, 0, 'https://search.example/?q=is+it+going+to+rain' if entered
                       else 'about:newtab', page, chrome_h=120)
    c.restore()
    gfx.cursor(c, cx, cy, 1.6, 'hand' if hovered >= 0 else 'arrow')
    for ct in SC.CLOSE_CLICKS_COLD:
        v = lt - ct
        if 0 <= v < 0.25:
            circle(c, cx, cy, 20 + v * 200)
            src(c, (1, 0.2, 0.3, 1 - v / 0.25))
            c.set_line_width(6)
            c.stroke()
    if lt > 7.8:
        fx.add('flash', amt=clamp((lt - 7.8) / 0.2))
    fx.vhs = 0.7


# ================================================================ EPISODE (40-48)

def draw_episode(c, lt, t, fx):
    if lt < 1.2:
        src(c, '#000000')
        c.paint()
        a = clamp(lt / 0.2) * clamp((1.2 - lt) / 0.2)
        text(c, 'Episode 1', W / 2, 470, 96, 'Georgia', italic=True, col='#ffffff', align='c', alpha=a)
        text(c, '"Just One More"', W / 2, 600, 80, 'Georgia', col='#ffe9a8', align='c', alpha=a)
        fx.vhs = 0.6
        return
    click1, click2 = SC.EPISODE_CLICKS
    split1, split2 = click1 + SC.EPISODE_SPLIT_DELAY, click2 + SC.EPISODE_SPLIT_DELAY
    push = 1.0 + 0.02 * (lt - 1.2) + (0.12 * ease_in((lt - 7.25) / 0.75) if lt > 7.25 else 0)
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(push, push)
    c.translate(-W / 2, -H / 2)
    living_room(c, t, 3)
    couch_back(c)
    look_cam = lt > 7.25
    # tabs on the couch: 1, then 2 after the first click, then 4 after the second
    if lt < split1:
        positions, hi_starts, target = [960.0], [], 0
    elif lt < split2:
        k1 = ease_out_back(clamp((lt - split1) / 0.35))
        positions, hi_starts, target = [960 - 130 * k1, 960 + 130 * k1], [43.3, 43.36], 1
    else:
        k2 = ease_out_back(clamp((lt - split2) / 0.35))
        left, right = lerp(830, 780, k2), lerp(1090, 1140, k2)
        positions = [left - 90 * k2, left + 90 * k2, right - 90 * k2, right + 90 * k2]
        hi_starts, target = [44.5, 44.57, 44.64, 44.71], -1
    next_click = click1 if lt < split1 else click2
    for i, x in enumerate(positions):
        hi_t = hi_starts[i] if i < len(hi_starts) else None
        greeting = hi_t is not None and hi_t - 0.2 < t < hi_t + 0.9
        hover = clamp(1 - abs(lt - next_click) / 0.35) if i == target else 0.0
        cast.draw_char(c, 'newtab', x, 780, 0.62, t + i * 0.3, legs=False,
                       mouth=spoken(t, hi_t, 3, 7, 3) if hi_t is not None else 0.0,
                       blink=blink_at(t, i + 3), look=(0.8, 0) if not look_cam else (0, 0),
                       arm_r=2.6 if greeting else 0.4, wave=1.0 if greeting else 0.0,
                       blush=1.0 if lt > split1 else 0.0, close_hover=hover)
    couch_front(c)
    # the user: the cursor tip lands on the close button of the tab it clicks
    keys = [(0.0, 1480, 640), (click1 - 0.4, 1480, 640), (click1, 1159, 736), (click1 + 0.08, 1159, 740),
            (click1 + 0.45, 1435, 650), (click2 - 0.35, 1435, 650), (click2, 1289, 736), (click2 + 0.08, 1289, 740),
            (click2 + 0.5, 1560, 640), (8.0, 1560, 640)]
    ux, uy = keys[-1][1], keys[-1][2]
    for (ta, xa, ya), (tb, xb, yb) in zip(keys[:-1], keys[1:]):
        if ta <= lt <= tb:
            k = ease_in_out((lt - ta) / max(1e-3, tb - ta))
            ux, uy = lerp(xa, xb, k), lerp(ya, yb, k)
            break
    lean = max(clamp(1 - abs(lt - click1) / 0.4), clamp(1 - abs(lt - click2) / 0.4))
    talk = max(spoken(t, 41.3, 22, 0, 3), spoken(t, 46.15, 12, 0, 1))
    upset = (split1 + 0.3 < lt < click2 - 0.3) or (split2 + 0.25 < lt < 7.25)
    expr = 'talk' if talk >= 0.05 else ('frown' if upset else 'happy')
    cast.draw_user(c, ux, uy, 0.9, t, mouth=talk, expr=expr, look=(-0.8, 0.1) if not look_cam else (0, 0),
                   blink=blink_at(t, 9), tilt=-0.08 * lean)
    for ct in SC.EPISODE_CLICKS:
        v = lt - ct
        if 0 <= v < 0.3:
            circle(c, ux - 135, uy - 180, 14 + v * 260)
            src(c, (1, 0.2, 0.3, 1 - v / 0.3))
            c.set_line_width(6)
            c.stroke()
    c.restore()
    # laugh sign
    (l1, d1), (l2, _d2) = SC.EPISODE_LAUGHS
    lit = (l1 < lt < l1 + d1 - 0.15) or (l2 < lt < 8.0)
    blink = lit and ((lt * 4) % 1 < 0.7)
    rrect(c, W / 2 - 230, 24, 460, 120, 20)
    gfx.fill_stroke(c, '#2a0a0a', OUTLINE, 6)
    text(c, 'LAUGH', W / 2, 88, 92, 'Impact', col='#ff3030' if blink else '#5a1a1a', align='c', valign='mid')
    if blink:
        gfx.radial_glow(c, W / 2, 84, 320, (1, 0.2, 0.2, 0.35))
    for sp in (split1, split2):
        if sp <= lt < sp + 0.2:
            fx.add('flash', amt=0.35 * (1 - (lt - sp) / 0.2))
    fx.vhs = 0.7


# ================================================================ SPACE (80-96)

def starfield(c, t, speed, n=260):
    src(c, '#04030c')
    c.paint()
    gfx.radial_glow(c, 500, 300, 700, (0.35, 0.1, 0.6, 0.45))
    gfx.radial_glow(c, 1500, 800, 800, (0.05, 0.3, 0.6, 0.4))
    cx, cy = W / 2, H / 2
    for i in range(n):
        x0, y0 = hsign(i, 1), hsign(i, 2)
        z = 1 - ((hrand(i, 3) + t * 0.12 * speed) % 1.0)
        z = max(z, 0.02)
        px, py = cx + x0 / z * 380, cy + y0 / z * 380
        z2 = min(1.0, z + 0.02 * speed)
        qx, qy = cx + x0 / z2 * 380, cy + y0 / z2 * 380
        a = clamp((1 - z) * 1.4)
        src(c, (0.85, 0.9, 1.0, a))
        c.set_line_width(1.5 + 3 * (1 - z))
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(qx, qy)
        c.line_to(px + 0.1, py)
        c.stroke()


def tab_ship(c, x, y, s, t, col='#6fb2ff', fav='globe', rot=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(s, s)
    for k in range(3):
        fl = 60 + 30 * math.sin(t * 40 + k * 2)
        c.move_to(-90, -20 + k * 20)
        c.line_to(-90 - fl, -10 + k * 10)
        c.line_to(-90, 0 + k * 20)
        src(c, (1, 0.6 - k * 0.15, 0.1, 0.9))
        c.fill()
    for side in (-1, 1):
        c.move_to(-60, side * 30)
        c.line_to(-110, side * 80)
        c.line_to(-20, side * 40)
        gfx.fill_stroke(c, '#d0d6e4', OUTLINE, 4)
    c.rotate(PI / 2)
    gfx.tab_path(c, -60, -110, 120, 200, 40, 16)
    gfx.fill_stroke(c, col, OUTLINE, 5)
    c.rotate(-PI / 2)
    gfx.favicon(c, fav, 20, 0, 54, t, col='#ffffff')
    c.restore()


def letterbox(c, h=90):
    src(c, '#000000')
    c.rectangle(0, 0, W, h)
    c.rectangle(0, H - h, W, h)
    c.fill()


def draw_space(c, lt, t, fx):
    speed = 4.0 * math.exp(-lt * 2.5) + 0.6
    if lt > 12:
        speed += (lt - 12) * 1.2
    starfield(c, t, speed)
    if lt < 4:
        k = ease_out(clamp(lt / 1.3))
        s = lerp(0.05, 1.0, k)
        c.save()
        c.translate(W / 2, H / 2)
        c.scale(s, s)
        c.rotate((1 - k) * 0.6)
        pat = gfx.chrome_pattern(-140, 60, 'space')
        text(c, 'TABS', 0, -30, 300, 'Impact', align='c', fill_pattern=pat, outline='#0a0a30', ow=9, extrude='#3a1a6a',
             extrude_n=14, extrude_d=(0, 2.4))
        pat2 = gfx.chrome_pattern(40, 200, 'space')
        text(c, 'IN SPACE', 0, 190, 170, 'Impact', align='c', fill_pattern=pat2, outline='#0a0a30', ow=7,
             extrude='#3a1a6a', extrude_n=10, extrude_d=(0, 2))
        c.restore()
        if 1.2 < lt < 2.2:
            gfx.sparkle(c, 1250, 330, 260 * math.sin(PI * (lt - 1.2)), 1.0, (0.7, 0.9, 1, 1), rot=lt)
    elif lt < 8:
        u = lt - 4
        for i in range(7):
            row = abs(i - 3)
            x = 1100 - row * 170 + math.sin(t * 1.3 + i) * 20 - (u * 30)
            y = 540 + (i - 3) * 110 + math.cos(t * 1.7 + i) * 14
            tab_ship(c, x, y, 0.8 - row * 0.08, t + i, TAB_COLS[i % len(TAB_COLS)], FAVS[i % len(FAVS)])
        # viewscreen
        c.save()
        rrect(c, 1270, 170, 560, 380, 30)
        gfx.fill_stroke(c, '#10141e', '#39ff7a', 6)
        rrect(c, 1270, 170, 560, 380, 30)
        c.clip()
        gfx.backdrop(c, 'plus', '#0f3d24', '#17603a', t)
        cast.draw_char(c, 'localhost', 1550, 620, 0.8, t, mouth=spoken(t, 84.1, 62, -1, 0), legs=False,
                       blink=blink_at(t, 4), arm_l=0.3, arm_r=0.3)
        c.restore()
        text(c, "CAPTAIN'S LOG", 1290, 158, 44, 'Consolas', bold=True, col='#39ff7a')
        text(c, 'TABS OPEN: 4,000', 90, 960, 64, 'Consolas', bold=True, col='#39ff7a')
        if u > 2.5:
            text(c, 'MORALE: LOW', 1290, 600, 44, 'Consolas', bold=True, col='#ff6060')
    elif lt < 12:
        u = lt - 8
        rot = t * 1.2
        gfx.radial_glow(c, W / 2, H / 2, 620, (0.2, 0.5, 1.0, 0.5))
        for i in range(12):
            a = rot + i * TAU / 12
            circle(c, W / 2 + math.cos(a) * 300, H / 2 + math.sin(a) * 300, 60)
            src(c, (0.4, 0.7, 1.0, 0.25 + 0.75 * (i / 12)))
            c.fill()
        for i in range(14):
            ph = (u * 0.35 + i / 14) % 1
            r = lerp(900, 60, ph ** 1.5)
            a = t * 1.5 + i * 2.2  # increasing angle turns clockwise on screen; ships face along the path
            tab_ship(c, W / 2 + math.cos(a) * r, H / 2 + math.sin(a) * r * 0.6, 0.6 * (1 - ph) + 0.05, t + i,
                     TAB_COLS[i % len(TAB_COLS)], FAVS[(i + 3) % len(FAVS)], a + PI / 2)
        text(c, 'LOADING...', W / 2, H / 2 + 20, 70, 'Impact', col='#ffffff', align='c', valign='mid', alpha=0.9)
        if lt > 9.9:
            pulse = 0.5 + 0.5 * math.sin((lt - 9.9) * 12)
            src(c, (1, 0, 0, 0.25 * pulse))
            c.rectangle(0, 0, W, H)
            c.fill()
            text(c, 'WARNING: MEMORY CRITICAL', W / 2, 190, 90, 'Impact', col='#ff2a2a', align='c', outline='#000000',
                 ow=4, alpha=0.4 + 0.6 * pulse)
    else:
        u = lt - 12
        n = min(420, int(7 * 2 ** int(u / 0.5)))
        for i in range(n):
            x = (hrand(i, 21) * (W + 400) - (u * (300 + 400 * hrand(i, 22)))) % (W + 400) - 200
            y = hrand(i, 23) * H
            tab_ship(c, x, y, 0.25 + 0.4 * hrand(i, 24), t + i, TAB_COLS[i % len(TAB_COLS)], FAVS[i % len(FAVS)],
                     PI + hsign(i, 25) * 0.2)
        credit(c, 'Sonny Mute', 'THE TAB PLAYING AUDIO (IN SPACE)', u - 0.2, 110, 820, 'l')
        text(c, 'In space, no one can find the tab playing audio.', W / 2, 1040 - 90, 44, 'Georgia', italic=True,
             col='#ffffff', align='c', alpha=clamp((u - 1.0) / 0.4))
        if lt > 15.55:
            v = lt - 15.55
            circle(c, W / 2, H / 2, v * 4000)
            src(c, (1, 1, 1, 1))
            c.fill()
    letterbox(c)
    fx.vhs = 0.5


# ================================================================ YTP (96-112)

def draw_ytp(c, lt, t, fx):
    s, e = edits.ytp_source_time(lt)
    if e is None:
        src(c, '#000')
        c.paint()
        return
    vfx = e['vfx']
    if 'black' in vfx:
        src(c, '#000')
        c.paint()
        return
    u = lt - e['o']
    inner = FX()
    c.save()
    if 'shake' in vfx:
        c.translate(hsign(int(lt * 30), 5) * 40, hsign(int(lt * 30), 6) * 30)
    if 'zoom' in vfx:
        z = 1.35 - 0.35 * ease_out(clamp(u / 0.2))
        c.translate(W / 2, H / 2)
        c.scale(z, z)
        c.rotate(hsign(int(e['o'] * 8), 3) * 0.08)
        c.translate(-W / 2, -H / 2)
    if 'tapestop' in vfx:
        k = u / e['d']
        c.translate(0, k * k * 300)
    loop.draw_loop(c, s, SC.SEC['s1'][0] + s, inner, 's1')
    c.restore()
    if 'buffer' in vfx:
        src(c, (0, 0, 0, 0.55))
        c.paint()
        for i in range(10):
            a = t * 7 + i * TAU / 10
            circle(c, W / 2 + math.cos(a) * 110, H / 2 + math.sin(a) * 110, 22)
            src(c, (1, 1, 1, 0.15 + 0.85 * i / 10))
            c.fill()
    if 'speed' in vfx:
        for i in range(40):
            y = hrand(i, int(lt * 20)) * H
            src(c, (1, 1, 1, 0.5))
            c.rectangle(0, y, W, 3 + 6 * hrand(i, 3))
            c.fill()
    if 'circle' in vfx:
        cx, cy = 1320 + math.sin(lt * 3) * 20, 380
        ellipse(c, cx, cy, 330, 190)
        src(c, (1, 0, 0, 1))
        c.set_line_width(18)
        c.stroke()
        c.move_to(500, 900); c.line_to(1000, 520)
        c.set_line_width(26); c.stroke()
        c.move_to(1000, 520); c.line_to(930, 540); c.line_to(980, 600); c.close_path()
        c.fill()
    if e['text']:
        cols = ['#ffffff', '#ffe14d', '#ff3b5c', '#62dcff', '#7dff7a']
        slam_text(c, e['text'], u, W / 2 + hsign(int(e['o'] * 4), 1) * 200, H / 2 + hsign(int(e['o'] * 4), 2) * 250,
                  230, cols[int(e['o'] * 4) % len(cols)], rot=hsign(int(e['o'] * 4), 9) * 0.2, life=e['d'] + 0.01)
    for name in vfx:
        if name == 'invert':
            fx.add('invert')
        elif name == 'hue':
            fx.add('hue', ang=lt * 9.0)
        elif name == 'mirror':
            fx.add('mirror')
        elif name == 'kaleido':
            fx.add('kaleido')
        elif name == 'fry':
            fx.add('fry', q=6)
    if 'tapestop' in vfx:
        fx.add('grade', sat=1 - u / e['d'], contrast=1.0, bright=-0.5 * u / e['d'])
    if int(lt * 30) % 7 == 0:
        fx.add('slices', seed=int(lt * 30), count=6, maxshift=120)
    fx.vhs = 0.9


# ================================================================ HAMSTER (112-128)

def pcb(c, t):
    src(c, '#1f6e45')
    c.paint()
    c.set_line_width(6)
    for i in range(40):
        x = hrand(i, 1) * W
        y = hrand(i, 2) * H
        src(c, (0.85, 0.7, 0.3, 0.35))
        c.move_to(x, y)
        c.line_to(x + hsign(i, 3) * 200, y)
        c.line_to(x + hsign(i, 3) * 200, y + hsign(i, 4) * 200)
        c.stroke()
        circle(c, x, y, 10)
        c.fill()


def ram_stick(c, x, y, w, h, t):
    rrect(c, x, y, w, h, 12)
    gfx.fill_stroke(c, '#1a8a3a', OUTLINE, 8)
    for i in range(8):
        rrect(c, x + 40 + i * (w - 80) / 8, y + 25, (w - 80) / 8 - 24, h - 70, 6)
        gfx.fill_stroke(c, '#1b1b1f', OUTLINE, 4)
    for i in range(int(w / 26)):
        c.rectangle(x + 16 + i * 26, y + h - 30, 14, 26)
    src(c, '#e8b83a')
    c.fill()
    text(c, 'RAM', x + w - 30, y + h - 44, 40, 'Jokerman', col='#ffffff', align='r')


def gauge(c, x, y, r, value, label):
    c.new_sub_path()
    c.arc(x, y, r, PI, TAU)
    c.close_path()
    gfx.fill_stroke(c, '#ffffff', OUTLINE, 8)
    for i in range(3):
        c.new_sub_path()
        c.arc(x, y, r * 0.8, PI + i * PI / 3, PI + (i + 1) * PI / 3)
        src(c, ['#3fcf8a', '#ffd23f', '#ff4d4d'][i])
        c.set_line_width(24)
        c.stroke()
    a = PI + clamp(value, 0, 9) * PI
    c.move_to(x, y)
    c.line_to(x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9)
    src(c, OUTLINE)
    c.set_line_width(10)
    c.stroke()
    circle(c, x, y, 16)
    c.fill()
    text(c, f'{label} {int(value * 100)}%', x, y + 70, 56, 'Jokerman', col='#ffffff', align='c', outline=OUTLINE, ow=4)


def draw_hamster(c, lt, t, fx):
    if lt < 2:
        gfx.backdrop(c, 'rays', '#ffd23f', '#ffe27e', lt, speed=3)
        word = 'Ramsey'
        x0 = W / 2 - 520
        for i, ch in enumerate(word):
            y = 330 + math.sin(lt * 8 + i) * 20 - bounce(clamp((lt - i * 0.08) / 0.5)) * 0
            k = ease_out_back(clamp((lt - i * 0.07) / 0.35))
            c.save()
            c.translate(x0 + i * 175, y)
            c.scale(k, k)
            c.rotate(math.sin(lt * 6 + i) * 0.12)
            text(c, ch, 0, 0, 260, 'Jokerman', col=['#ff4f9a', '#3a8bff', '#3fcf8a', '#ff9d45', '#a878ff', '#ff4d4d'][i],
                 align='c', valign='mid', outline=OUTLINE, ow=9)
            c.restore()
        text(c, 'the RAM Hamster', W / 2, 600, 120, 'Jokerman', col='#ffffff', align='c', outline=OUTLINE, ow=7,
             alpha=clamp((lt - 0.5) / 0.3))
        pop = ease_out_back(clamp((lt - 0.6) / 0.4), 2.0)
        cast.draw_hamster(c, W / 2, lerp(1300, 900, pop), 1.1, t, mouth=0.6)
        fx.vhs = 0.4
        return
    pcb(c, t)
    if lt < 12.5:
        spd = 1.2 + (lt - 2) * 0.75
        run = (lt - 2) * 1.2 + 0.375 * (lt - 2) ** 2
        wheel_x, wheel_y = W / 2, 520
        ram_stick(c, 260, 820, 1400, 190, t)
        c.move_to(wheel_x, wheel_y); c.line_to(wheel_x - 160, 830); c.move_to(wheel_x, wheel_y); c.line_to(wheel_x + 160, 830)
        src(c, '#9aa3b5'); c.set_line_width(22); c.stroke()
        circle(c, wheel_x, wheel_y, 290)
        src(c, '#c9d1de'); c.set_line_width(26); c.stroke()
        for i in range(10):
            a = -run * 0.9 + i * TAU / 10
            c.move_to(wheel_x, wheel_y)
            c.line_to(wheel_x + math.cos(a) * 280, wheel_y + math.sin(a) * 280)
            src(c, (0.6, 0.65, 0.72, 0.8 if spd < 6 else 0.3))
            c.set_line_width(8)
            c.stroke()
        if spd > 5:
            for k in range(3):
                c.new_sub_path()
                c.arc(wheel_x, wheel_y, 250 - k * 40, -run * 0.9, -run * 0.9 + 2.5)
                src(c, (1, 1, 1, 0.25))
                c.set_line_width(14)
                c.stroke()
        m = max(spoken(t, 114.6, 26, 10, 3), spoken(t, 119.8, 22, 10, 3), spoken(t, 123.2, 14, 11, 4))
        cast.draw_hamster(c, wheel_x, wheel_y + 150, 0.75, t, run=run, sweat=clamp((lt - 6) / 1.0), mouth=0.2 + m)
        # tab pipe
        rrect(c, 60, 60, 190, 260, 20)
        gfx.fill_stroke(c, '#8a93a6', OUTLINE, 8)
        rate = 1 + (lt - 2) * 1.8
        for i in range(int((lt - 2) * rate)):
            ph = ((lt - 2) * 1.3 - i * 0.13) % 1.0
            mini_tab(c, 155 + ph * 300, 330 + ph * ph * 450, 0.5, FAVS[i % len(FAVS)], TAB_COLS[i % len(TAB_COLS)],
                     ph * 10, lt) if ph < 0.98 and i < 60 else None
        val = 0.4 + (lt - 2) * 0.1 if lt < 8 else 0.99 + (lt - 8) ** 2 * 0.4
        gauge(c, 1600, 260, 170, val, 'RAM')
        if lt > 9:
            for k in range(4):
                ph = ((lt - 9) * 1.5 + k / 4) % 1
                circle(c, wheel_x - 120 + k * 80, wheel_y - 60 - ph * 300, 40 + ph * 50)
                src(c, (1, 1, 1, 0.5 * (1 - ph)))
                c.fill()
            c.translate(hsign(int(lt * 30), 1) * (lt - 9) * 4, 0)
    else:
        u = lt - 12.5
        ram_stick(c, 260, 820, 1400, 190, t)
        wx = W / 2 + u * 1500
        circle(c, wx, 520 + u * 200, 290)
        src(c, '#c9d1de'); c.set_line_width(26); c.stroke()
        pile = clamp((u - 0.7) / 0.5)
        if u < 0.7:
            hx = W / 2 - u * 300
            hy = 670 - math.sin(PI * u / 0.7) * 500
            c.save()
            c.translate(hx, hy)
            c.rotate(u * 14)
            cast.draw_hamster(c, 0, 0, 0.75, t, eyes='x', mouth=0.8)
            c.restore()
        # explosion + pile
        if u > 0.7:
            v = u - 0.7
            for i in range(160):
                a = hrand(i, 31) * TAU
                r = min(1.0, v * 2.5) * (300 + hrand(i, 32) * 900)
                x = W / 2 + math.cos(a) * r
                y = min(1000 - hrand(i, 33) * 380 * pile, 560 + math.sin(a) * r * 0.7 + v * v * 900)
                mini_tab(c, x, y, 0.55, FAVS[i % len(FAVS)], TAB_COLS[i % len(TAB_COLS)], i, lt)
            if v < 0.25:
                fx.add('flash', amt=1 - v / 0.25, col=(255, 240, 180))
        if lt >= 14:
            pop = ease_out_back(clamp((lt - 14) / 0.4), 2.0)
            cast.draw_hamster(c, W / 2, lerp(1250, 700, pop), 0.8, t, dizzy=1.0, mouth=spoken(t, 126.1, 7, 9, -4) + 0.1)
        if lt > 14.8:
            k = smooth(clamp((lt - 14.6) / 1.1))
            r = lerp(1300, 0, k)
            c.save()
            c.rectangle(0, 0, W, H)
            c.new_sub_path()
            c.arc_negative(W / 2, 680, max(r, 0.1), TAU, 0)
            c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            src(c, '#000000')
            c.fill()
            c.restore()
            text(c, 'please close some tabs', W / 2, 200, 80, 'Jokerman', col='#ffffff', align='c',
                 alpha=clamp((lt - 15.1) / 0.3))
    fx.vhs = 0.4


# ================================================================ SEASON 3: HORROR (128-160)

HORROR_CLOSE = ['recipe', 'loading', 'inbox', 'audio', 'cart', 'forum', 'later', 'localhost']


def rain(c, t, n=160, a=0.35):
    src(c, (0.7, 0.75, 0.9, a))
    c.set_line_width(2.5)
    for i in range(n):
        x = (hrand(i, 1) * (W + 300) - t * 400) % (W + 300)
        y = (hrand(i, 2) * H + t * 2400 * (0.7 + 0.3 * hrand(i, 3))) % (H + 100) - 50
        c.move_to(x, y)
        c.line_to(x - 12, y + 44)
    c.stroke()


def lightning(fx, lt, times):
    for tt in times:
        v = lt - tt
        if 0 <= v < 0.18:
            fx.add('flash', amt=0.9 * (1 - v / 0.18) * (1 if int(v * 60) % 2 == 0 else 0.4))


def dark_vignette(c, a=0.75):
    gfx.vignette(c, W, H, a)


def horror_title(c, lt, t, fx):
    gfx.vgrad(c, 0, 0, W, H, [(0, '#12040a'), (1, '#3a0610')])
    rain(c, t)
    c.save()
    c.translate(W / 2 + hsign(int(t * 20), 1) * 4, 520)
    pat = gfx.chrome_pattern(-200, 80, 'blood')
    text(c, 'TOO MANY TABS', 0, 0, 260, 'Chiller', bold=True, align='c', fill_pattern=pat, outline='#000000', ow=8,
         extrude='#1a0003', extrude_n=10, extrude_d=(0, 2.5))
    for i in range(14):
        x = -760 + i * 115 + hsign(i, 5) * 20
        L = 40 + 200 * hrand(i, 6) * clamp(lt / 3)
        rrect(c, x, 20, 16, L, 8)
        src(c, (0.6, 0, 0.04, 1))
        c.fill()
        circle(c, x + 8, 20 + L, 13)
        c.fill()
    text(c, 'SEASON 3', 0, 190, 110, 'Chiller', bold=True, col='#d8c8c8', align='c', alpha=clamp((lt - 1.0) / 0.5))
    c.restore()
    lightning(fx, lt, (0.0, 1.0, 1.25))
    dark_vignette(c, 0.8)


def hallway(c, lt, t, fx):
    src(c, '#07060a')
    c.paint()
    vx, vy = W / 2, 470
    for i in range(12, -1, -1):
        z = i - (lt * 1.2 % 1.0)
        s = 1.0 / (1 + z * 0.45)
        shade = clamp(s * 1.2)
        for side in (-1, 1):
            x = vx + side * 1100 * s
            gfx.tab_path(c, x - 180 * s, vy - 420 * s, 360 * s, 800 * s, 60 * s, 30 * s)
            gfx.fill_stroke(c, gfx.mix('#0a0a10', TAB_COLS[(i * 3) % len(TAB_COLS)], 0.25 * shade), '#000000', 3)
    c.move_to(0, H)
    c.line_to(vx, vy + 60)
    c.line_to(W, H)
    src(c, '#140c10')
    c.fill()
    k = clamp((lt - 4) / 4)
    rs = lerp(0.22, 0.95, k)
    ry = lerp(620, 1180, k)
    cast.draw_restorer(c, vx + math.sin(lt * 2) * 30, ry, rs, t, glow=0.7 + 0.3 * math.sin(t * 9),
                       eyes=1.0 if lt < 7.0 or lt > 7.6 else 1.6, silhouette=0.6)
    # flashlight
    c.save()
    c.rectangle(0, 0, W, H)
    fl = 0.8 + 0.2 * (hrand(int(t * 24), 3) > 0.15)
    g = cairo.RadialGradient(vx + math.sin(t * 1.3) * 200, 600, 60, vx + math.sin(t * 1.3) * 200, 600, 720)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.92 * fl)
    c.set_source(g)
    c.fill()
    c.restore()


def horror_newtab(c, u, t, fx):
    gfx.backdrop(c, 'dots', gfx.mix('#ff8fc4', '#050308', 0.8), gfx.mix('#ffb3d6', '#0a0610', 0.8), u)
    closed = u >= 3.0
    gray = clamp((u - 3.0) / 0.2)
    fall = ease_in(clamp((u - 3.1) / 0.6))
    rise = ease_out(clamp((u - 1.6) / 1.2))
    cast.draw_restorer(c, 1300, lerp(1900, 1250, rise), 1.1, t, alpha=clamp(rise * 1.2), arm=clamp((u - 2.6) / 0.4))
    look = (math.sin(t * 5) * 0.9, 0) if not closed else (0, 0)
    cast.draw_char(c, 'newtab', 1150, 1000 + fall * 200, 1.1, t, expr='dead' if closed else 'scared', sweat=0 if closed else 1,
                   look=look, gray=gray, tilt=fall * 1.3, mouth=0.5, arm_l=2.2 * (1 - gray), arm_r=2.4 * (1 - gray),
                   bob=4 * math.sin(t * 40) if not closed else 0)
    credit(c, 'Tabitha Newman', 'NEW TAB', u - 0.4, 110, 860, 'l', closed=max(0, u - 3.0))
    if 3.0 <= u < 3.2:
        fx.add('flash', amt=0.8 * (1 - (u - 3.0) / 0.2), col=(255, 30, 40))
    dark_vignette(c, 0.85)


def horror_closes(c, u, t, fx):
    k = min(7, int(u / 0.5))
    v = u - k * 0.5
    key = HORROR_CLOSE[k]
    spec = cast.CAST[key]
    bd = spec['backdrop']
    gfx.backdrop(c, bd[0], gfx.mix(bd[1], '#050308', 0.75), gfx.mix(bd[2], '#0a0610', 0.75), u)
    gray = clamp(v / 0.08)
    tilt = 0.2 * gray * hsign(k, 3)
    cast.draw_char(c, key, 1250, 1000, 1.05, t, expr='dead', gray=gray, tilt=tilt, arm_l=0.2, arm_r=0.2)
    credit(c, spec['actor'], spec['role'], 0.6, 110, 860, 'l', closed=v, scale=0.9)
    # the cursor tip lands on the close button and follows it as the tab keels over
    bx, by = cast.close_button_pos(1250, 1000, 1.05, tilt)
    gfx.cursor(c, lerp(1500, bx, clamp(v / 0.05)), lerp(200, by, clamp(v / 0.05)), 5.0, 'arrow')
    text(c, f'TABS: {7 - k}', W - 60, 110, 90, 'Chiller', bold=True, col='#ff3040', align='r')
    if v < 0.1:
        fx.add('flash', amt=0.6 * (1 - v / 0.1), col=(255, 20, 30))
    dark_vignette(c, 0.8)


def horror_restore(c, u, t, fx):
    src(c, '#1a1a1f')
    c.paint()
    living_room(c, t, 1, dark=0.85)
    relieved = u < 2.4
    cast.draw_user(c, 600, 960, 1.1, t, mouth=0, expr='happy' if relieved else 'frown', look=(0.6, -0.3))
    if u > 0.8:
        sc = ease_out_back(clamp((u - 0.8) / 0.35))
        hot = 1
        press = 1.0 if 2.45 <= u < 2.6 else 0.0
        gfx.dialog(c, W / 2 + 120, 480, 900, 380, 'Restore pages?',
                   "Your tabs didn't close correctly.\nRestore all of them?", ['Cancel', 'Restore'], t, hot, press,
                   scale=sc)
        # the Restorer's arm reaches in from the upper right; the hand points down the arm and the
        # fingertip lands on the Restore button
        bx, by = gfx.dialog_button_center(W / 2 + 120, 480, 900, 380, 2, 1, sc)
        k = ease_out(clamp((u - 1.2) / 1.0))
        fx_, fy_ = lerp(2300, bx, k), lerp(-200, by + 4 * press, k)
        arm_ang = -0.5
        point = arm_ang + PI
        if press:
            fx_, fy_ = fx_ + math.cos(point) * 8, fy_ + math.sin(point) * 8
        hs = 3.0
        tip = gfx.HAND_TIP
        rel = (gfx.HAND_WRIST[0] - tip[0], gfx.HAND_WRIST[1] - tip[1])
        spin = point - math.atan2(-rel[1], -rel[0])
        cs_, sn_ = math.cos(spin), math.sin(spin)
        wx_ = fx_ + hs * (rel[0] * cs_ - rel[1] * sn_)
        wy_ = fy_ + hs * (rel[0] * sn_ + rel[1] * cs_)
        c.save()
        c.translate(wx_, wy_)
        c.rotate(arm_ang)
        rrect(c, -30, -45, 1100, 90, 40)
        gfx.fill_stroke(c, '#34323f', OUTLINE, 6)
        c.restore()
        c.save()
        c.translate(fx_, fy_)
        c.rotate(spin)
        gfx.cursor(c, -tip[0] * hs, -tip[1] * hs, hs, 'hand')
        c.restore()
    if u >= 2.5:
        v = u - 2.5
        n = min(900, int((v * 12) ** 2))
        for i in range(n):
            x = (i % 30) * 64 + 16
            y = (i // 30) * 36 + 10
            gfx.ui_tab(c, x, y, 62, 34, '', FAVS[i % len(FAVS)], col=TAB_COLS[i % len(TAB_COLS)], fav_col='#ffffff')
        if v < 0.2:
            fx.add('flash', amt=0.7 * (1 - v / 0.2), col=(80, 230, 255))
    dark_vignette(c, 0.7)


def horror_return(c, u, t, fx, lt):
    gfx.backdrop(c, 'rays', '#3a0008', '#6a0010', u, speed=3)
    keys = cast.ALL
    for dup in (0, 1):
        for i, k in enumerate(keys):
            x = 120 + i * 185 + dup * 60
            y = 1000 - dup * 280
            sp = dict(cast.CAST[k])
            hue = (hrand(i, dup, 9) * 0.6 + 0.4)
            sp['col'] = gfx.hsv(hue, 0.7, 0.75)
            cast.draw_char(c, sp, x, y, 0.5, t + i, eyes='evil', expr='evil', bob=abs(math.sin(t * 6 + i)) * 30,
                           arm_l=2.5, arm_r=2.5)
    for hi, h in enumerate((20.0, 22.0)):
        slam_text(c, 'TOO MANY TABS', lt - h, W / 2, 300, 220, '#ff1a2a', rot=hsign(hi, 4) * 0.06, font='Chiller',
                  outline='#000000', life=1.8)
    lightning(fx, lt, (20.0, 20.3, 22.0))
    if int(t * 15) % 9 == 0:
        fx.add('invert')
    dark_vignette(c, 0.6)


def horror_introducing(c, u, t, fx, lt):
    strobe = (int(t * 12) % 2 == 0)
    src(c, '#300008' if strobe else '#080003')
    c.paint()
    cast.draw_restorer(c, W / 2 + 250, 1500, 1.9, t, glow=1.0, spin=2.0, arm=0.3 + 0.2 * math.sin(t * 3))
    credit(c, '???', 'RESTORE PREVIOUS SESSION', u - 0.2, 110, 820, 'l', pre='as', col_role='#ff2a3a', role_font='Chiller')
    text(c, 'and introducing', 110, 700, 64, 'Georgia', italic=True, col='#ffffff', alpha=clamp((u - 0.1) / 0.3))
    for hi, h in enumerate((24.0, 26.0)):
        slam_text(c, 'TOO MANY TABS', lt - h, W / 2, 180, 170, '#ff1a2a', font='Chiller', outline='#000000', life=1.0)
    dark_vignette(c, 0.7)


def graveyard(c, u, t, fx):
    gfx.vgrad(c, 0, 0, W, H, [(0, '#050818'), (1, '#1a2240')])
    circle(c, 1500, 220, 120)
    src(c, '#f2f0d8')
    c.fill()
    gfx.radial_glow(c, 1500, 220, 400, (0.9, 0.9, 0.7, 0.3))
    ground = 820
    keys = ['newtab', 'recipe', 'loading', 'inbox', 'cart', 'later']
    for i, k in enumerate(keys):
        x = 200 + i * 300
        gfx.tab_path(c, x - 110, ground - 260, 220, 260, 60, 0)
        gfx.fill_stroke(c, '#5a5f6e', '#1a1a22', 6)
        text(c, 'RIP', x, ground - 150, 60, 'Chiller', bold=True, col='#2a2a33', align='c')
    for i, k in enumerate(keys):
        x = 200 + i * 300 + 150
        rise = ease_out(clamp((u - i * 0.12) / 0.8))
        c.save()
        c.rectangle(0, 0, W, ground + 10)
        c.clip()
        sp = dict(cast.CAST[k])
        cast.draw_char(c, sp, x, ground + 460 - rise * 460, 0.7, t + i, gray=0.7, eyes='tiny', expr='scream',
                       mouth=0.6, arm_l=2.8, arm_r=2.9, tilt=math.sin(t * 3 + i) * 0.1)
        c.restore()
    src(c, '#0c0f18')
    c.rectangle(0, ground, W, H - ground)
    c.fill()
    for i in range(8):
        x = (hrand(i, 3) * W + t * 60 * (0.5 + hrand(i, 4))) % (W + 800) - 400
        gfx.radial_glow(c, x, ground + 40, 420, (0.7, 0.75, 0.85, 0.22))
    fx.add('grade', sat=0.5, contrast=1.1, bright=-0.03, tint=0.35, tr=0.6, tg=1.1, tb=0.8)
    dark_vignette(c, 0.75)


def restorer_closeup(c, u, t, fx):
    src(c, '#000000')
    c.paint()
    z = 3.2 + u * 0.6
    # spin speed ramps from 3 to 10 turns of the base rate; pass the accumulated angle, not speed * clock time
    spin_phase = 3.0 * u + 2.0 * u * u
    cast.draw_restorer(c, W / 2, H / 2 + 700 * z, z, spin_phase, glow=1.0, eyes=1.0 + 2.0 * clamp((u - 1.5) / 0.1))
    if u > 1.8:
        src(c, '#000000')
        c.paint()


def draw_s3(c, lt, t, fx):
    if lt < 4:
        horror_title(c, lt, t, fx)
    elif lt < 8:
        hallway(c, lt, t, fx)
    elif lt < 12:
        horror_newtab(c, lt - 8, t, fx)
    elif lt < 16:
        horror_closes(c, lt - 12, t, fx)
    elif lt < 20:
        horror_restore(c, lt - 16, t, fx)
    elif lt < 24:
        horror_return(c, lt - 20, t, fx, lt)
    elif lt < 28:
        horror_introducing(c, lt - 24, t, fx, lt)
    elif lt < 30:
        graveyard(c, lt - 28, t, fx)
    else:
        restorer_closeup(c, lt - 30, t, fx)
    lightning(fx, lt, (18.5, 31.5))
    fx.vhs = 0.8


# ================================================================ RECURSION (160-176)

REC_K = 1600 / 1920
REC_TH = 0.09
REC_V = (960.0, 140 / (1 - REC_K))
PAGE = (160, 140, 1600, 900)


def rec_chrome(c, level, t, wraps):
    src(c, '#0b0b12')
    c.rectangle(-4000, -4000, 12000, 12000)
    c.fill()
    n = 2 ** min(10, level + wraps + 1)
    tabs = [('Too Many Tabs', 'plus', TAB_COLS[(level + wraps) % len(TAB_COLS)])] + random_tabs(min(n, 80), level + wraps)
    gfx.browser_window(c, 40, 20, 1840, 1045, tabs, t, 0, 'https://toomanytabs.tv/' + '../' * (level + wraps + 1),
                       None, chrome_h=118, shadow=False)


def _nest(c):
    vx, vy = REC_V
    c.translate(vx, vy)
    c.scale(REC_K, REC_K)
    c.rotate(REC_TH)
    c.translate(-vx, -vy)


def draw_recursion(c, lt, t, fx):
    s = edits.rec_source_time(lt)
    p = (s / 2.0) % 1.0
    wraps = int(s / 2.0)
    s1t = SC.SEC['s1'][0] + s
    vx, vy = REC_V
    c.save()
    z = (1 / REC_K) ** p
    c.translate(vx, vy)
    c.scale(z, z)
    c.rotate(-REC_TH * p)
    c.translate(-vx, -vy)
    depth = 4
    for level in range(depth):
        rec_chrome(c, level, t, wraps)
        c.rectangle(*PAGE)
        c.clip()
        _nest(c)
    inner = FX()
    loop.draw_loop(c, s, s1t, inner, 's1')
    # fade in the next nesting level so the wrap is seamless
    c.push_group()
    rec_chrome(c, depth, t, wraps)
    c.rectangle(*PAGE)
    c.clip()
    _nest(c)
    loop.draw_loop(c, s, s1t, FX(), 's1')
    c.pop_group_to_source()
    c.paint_with_alpha(p)
    c.restore()
    # marquee
    rrect(c, -20, H - 96, W + 40, 90, 0)
    src(c, (0, 0, 0, 0.75))
    c.fill()
    msg = 'TAB as TAB as TAB as TAB as TAB as TAB as TAB as TAB as TAB as TAB as TAB as TAB as '
    off = (lt * 600) % 1400
    text(c, msg * 2, -off, H - 30, 64, 'Impact', col='#ffe14d')
    text(c, f'RECURSION LEVEL {wraps + 1}', W - 40, 80, 70, 'Impact', col='#ffffff', align='r', outline=OUTLINE, ow=4)
    fx.add('hue', ang=lt * 0.25)
    fx.vhs = 0.6


# ================================================================ FINALE (176-192)

def tab_mosaic(c, k, t):
    cols = min(96, 2 ** (k // 2 + 1))
    rows = max(1, int(cols * 9 / 16))
    cw, ch = W / cols, H / rows
    if cols <= 16:
        for j in range(rows):
            for i in range(cols):
                idx = i + j * cols
                gfx.ui_tab(c, i * cw + 2, j * ch + ch * 0.2, cw - 4, ch * 0.7, RANDOM_TITLES[idx % len(RANDOM_TITLES)],
                           FAVS[idx % len(FAVS)], col=TAB_COLS[idx % len(TAB_COLS)], t=t)
    else:
        for j in range(rows):
            for i in range(cols):
                h = (i * 0.013 + j * 0.021 + t * 0.4) % 1
                rrect(c, i * cw + 1, j * ch + ch * 0.25, cw - 2, ch * 0.7, min(cw, ch) * 0.25)
                src(c, gfx.hsv(h, 0.6, 1.0))
                c.fill()


def draw_finale(c, lt, t, fx):
    k = int(lt * 2)
    since = lt * 2 - k
    count = 2 ** (k + 1)
    tab_mosaic(c, k, t)
    shake = 6 + lt * 3
    c.save()
    c.translate(hsign(int(t * 30), 1) * shake, hsign(int(t * 30), 2) * shake)
    press = math.exp(-since * 6)
    if lt < 8:
        ks = 1.0 if lt < 4 else lerp(1.0, 0.45, ease_out((lt - 4) / 0.6))
        c.save()
        cx, cy = (W / 2, 600) if lt < 4 else (lerp(W / 2, 360, ease_out((lt - 4) / 0.6)), lerp(600, 880, ease_out((lt - 4) / 0.6)))
        c.translate(cx, cy)
        c.scale(ks, ks)
        gfx.keycap(c, -230, 0, 380, 300, 'Ctrl', press if k % 2 == 0 else 0.1)
        gfx.keycap(c, 230, 0, 300, 300, 'W', press)
        for r in range(2):
            circle(c, 0, 0, 200 + since * 900 + r * 60)
            src(c, (1, 1, 1, 0.6 * (1 - since)))
            c.set_line_width(14)
            c.stroke()
        c.restore()
    if lt >= 4:
        for i, key in enumerate(cast.ALL):
            a = t * (1.5 + lt * 0.15) + i * TAU / len(cast.ALL)
            r = 420 + 60 * math.sin(t * 3 + i)
            c.save()
            c.translate(W / 2 + math.cos(a) * r * 1.4, H / 2 + math.sin(a) * r * 0.8 + 150)
            cast.draw_char(c, key, 0, -cast.BODY_CY * 0.36, 0.36, t + i, tilt=a * 1.5, mouth=0.9,
                           expr='scream' if lt > 8 else 'happy', arm_l=2.8, arm_r=2.8,
                           eyes='spiral' if lt > 10 else None)
            c.restore()
    if lt >= 8:
        u = lt - 8
        fill = u / 3.0
        rrect(c, 160, 960, 1600, 70, 35)
        gfx.fill_stroke(c, '#10141e', '#ffffff', 6)
        rrect(c, 170, 970, max(10, 1580 * fill), 50, 25)
        src(c, '#ff3040' if fill > 1 else '#3fcf8a')
        c.fill()
        text(c, f'RAM {int(fill * 100)}%', W / 2, 1010, 56, 'Impact', col='#ffffff', align='c', valign='mid', outline=OUTLINE,
             ow=4)
        text(c, f'CPU {int(60 + u ** 3 * 300):,}°C', W - 60, 260, 90, 'Impact', col='#ff5a1f', align='r', outline=OUTLINE,
             ow=5)
        for i in range(24):
            fh = 120 + 180 * abs(math.sin(t * 9 + i * 1.7)) * clamp(u / 2)
            x = i * 84
            c.move_to(x, H)
            c.curve_to(x + 10, H - fh * 0.5, x + 30, H - fh * 0.8, x + 42, H - fh)
            c.curve_to(x + 55, H - fh * 0.7, x + 80, H - fh * 0.4, x + 84, H)
            src(c, (1, 0.45 + 0.3 * hrand(i, 2), 0.05, 0.85))
            c.fill()
    c.restore()
    counter = '∞' if k >= 31 else fmt_int(count)
    sc = 1 + 0.25 * press
    c.save()
    c.translate(W / 2, 150)
    c.scale(sc, sc)
    text(c, f'TABS OPEN: {counter}', 0, 0, 120, 'Impact', col='#ffffff', align='c', valign='mid', outline='#000000',
         ow=8, max_w=1800)
    c.restore()
    if 12 <= lt < 16:
        words = [(12.0, 'TOO'), (12.25, 'MANY'), (12.5, 'MANY'), (12.75, 'TABS'), (14.0, 'TOO'), (14.25, 'MANY'),
                 (14.5, 'MANY'), (14.75, 'TABS!!!')]
        for i, (tt, wd) in enumerate(words):
            slam_text(c, wd, lt - tt, W / 2, H / 2, 380 if i < 4 else 480, ['#ffe14d', '#ff3b5c', '#62dcff', '#ffffff'][i % 4],
                      rot=hsign(i, 7) * 0.15, life=0.25 if wd != 'TABS' else 1.2 if i < 4 else 1.3)
        fx.add('melt', amt=0.35 * ease_in(clamp((lt - 12) / 3.5)), seed=5)
    if lt >= 14:
        fx.add('hue', ang=t * 12)
    if lt > 15.5:
        fx.add('slices', seed=int(t * 30), count=30, maxshift=500)
    if lt > 15.85:
        fx.add('flash', amt=1.0)
    fx.add('rgbsplit', amt=4 + lt * 1.5)
    fx.vhs = 0.5


# ================================================================ CRASH (192-198)

def draw_crash(c, lt, t, fx):
    if lt < 0.6:
        src(c, '#000000')
        c.paint()
        w = W * (1 - ease_in(clamp(lt / 0.35)))
        h = 8 if lt < 0.35 else 8 * (1 - (lt - 0.35) / 0.25)
        rrect(c, W / 2 - max(w, 12) / 2, H / 2 - h / 2, max(w, 12), max(h, 1), 4)
        src(c, (1, 1, 1, 1 if lt < 0.5 else 1 - (lt - 0.5) / 0.1))
        c.fill()
        return
    a = clamp((lt - 0.6) / 0.25)
    purple = '#4b2a7b'
    src(c, gfx.mix('#000000', purple, a))
    c.paint()
    text(c, ':(', 180, 330, 280, 'Segoe UI', col='#ffffff', alpha=a)
    text(c, 'Your browser ran into a problem because you have too many tabs.', 180, 490, 50, 'Segoe UI',
         col='#ffffff', alpha=a, max_w=1560)
    text(c, "We're collecting all 4,294,967,296 of them, and then we'll restore every single one.", 180, 555, 50,
         'Segoe UI', col='#ffffff', alpha=a, max_w=1560)
    pct = int(100 * clamp((lt - 1.0) / 4.6) ** 1.6)
    pct = min(100, pct - pct % 7 if pct < 100 else 100)
    text(c, f'{pct}% complete', 180, 640, 50, 'Segoe UI', col='#ffffff', alpha=a)
    # a real, scannable QR code for the project's repository: dark modules on a white quiet zone
    rows = repo_qr()
    module = 8
    qx, qy = 180, 700
    size = len(rows) * module
    c.rectangle(qx, qy, size, size)
    src(c, (1, 1, 1, a))
    c.fill()
    for j, row in enumerate(rows):
        for i, dark in enumerate(row):
            if dark:
                c.rectangle(qx + i * module, qy + j * module, module, module)
    src(c, purple, a)
    c.fill()
    tx = qx + size + 44
    text(c, 'For more information, close some tabs.', tx, 800, 34, 'Segoe UI', col='#ffffff', alpha=a)
    text(c, 'Stop code: TOO_MANY_TABS', tx, 870, 34, 'Segoe UI', col='#ffffff', alpha=a)
    fx.vhs = 0.3


@functools.lru_cache(maxsize=1)
def repo_qr():
    """QR modules for REPO_URL as rows of booleans, including the 4-module quiet zone."""
    import segno
    qr = segno.make(REPO_URL, error='q', micro=False)
    return tuple(tuple(bool(v) for v in row) for row in qr.matrix_iter(scale=1, border=4))


# ================================================================ EPILOGUE (198-224)

def draw_epilogue(c, lt, t, fx):
    if lt < 10:
        push = 1.0 + lt * 0.012
        c.save()
        c.translate(W / 2, H / 2)
        c.scale(push, push)
        c.translate(-W / 2, -H / 2)
        living_room(c, t, 1)
        couch_back(c)
        gone = clamp((lt - 8.0) / 1.2)
        if gone < 1:
            m = spoken(t, 205.2, 10, 6, -2)
            look = (0.7, -0.2) if lt < 6.8 else (0, 0)
            cast.draw_char(c, 'newtab', 960, 780, 0.7, t, legs=False, alpha=1 - gone, mouth=m,
                           blink=blink_at(t, 2), look=look, blush=0.6 if lt > 6.8 else 0, arm_l=0.3, arm_r=0.3,
                           close_hover=clamp((lt - 6.0) / 0.5) * (1 - gone))
        for i in range(40):
            v = lt - 8.0 - hrand(i, 2) * 0.6
            if 0 < v < 2.0:
                gfx.sparkle(c, 960 + hsign(i, 3) * 160, 560 - v * 260 + hsign(i, 4) * 120, 26 * (1 - v / 2), 1 - v / 2,
                            (1, 0.95, 0.7, 1), v)
        couch_front(c)
        c.restore()
        # the cursor tip lands on the tab's close button; follow the slow push-in so it stays there
        bx, by = cast.close_button_pos(960, 780, 0.7)
        tx, ty = W / 2 + (bx - W / 2) * push, H / 2 + (by - H / 2) * push
        k = ease_out(clamp((lt - 3.0) / 3.5))
        press = 3.0 if 8.0 <= lt < 8.12 else 0.0
        cx, cy = lerp(2100, tx, k), lerp(700, ty, k) + press
        gfx.cursor(c, cx, cy, 2.2, 'arrow', alpha=clamp(1 - (lt - 9.0)))
        v = lt - 8.0
        if 0 <= v < 0.3:
            circle(c, cx, cy, 16 + v * 260)
            src(c, (1, 0.2, 0.3, 1 - v / 0.3))
            c.set_line_width(6)
            c.stroke()
        src(c, (1, 0.6, 0.2, 0.18))
        c.rectangle(0, 0, W, H)
        c.fill()
        dark_vignette(c, 0.5 + 0.4 * clamp((lt - 8) / 2))
        fx.vhs = 0.5
        return
    if lt < 16:
        src(c, '#000000')
        c.paint()
        a = clamp((lt - 10.3) / 0.8) * clamp((13.0 - lt) / 0.6)
        gfx.radial_glow(c, W / 2, H / 2, 600, (1, 0.9, 0.7, 0.18 * a))
        text(c, 'The End', W / 2, H / 2 + 40, 240, 'Brush Script MT', col='#ffffff', align='c', valign='mid', alpha=a)
        if lt > 13.0:
            sc = ease_out_back(clamp((lt - 13.0) / 0.3))
            press = 1.0 if 15.5 <= lt < 15.7 else 0.0
            gfx.dialog(c, W / 2, H / 2, 880, 360, 'Restore previous session?', 'You closed a tab.\nWant it back?',
                       ['No', 'Restore'], t, 1, press, scale=sc)
            hx = lerp(1700, W / 2 + 330, ease_in_out(clamp((lt - 14.4) / 0.9)))
            hy = lerp(1000, H / 2 + 120, ease_in_out(clamp((lt - 14.4) / 0.9)))
            gfx.cursor(c, hx, hy + (6 if press else 0), 2.0, 'hand')
        fx.vhs = 0.5
        return
    if lt < 20:
        u = lt - 16
        frozen = u >= 3.5
        ud = min(u, 3.5)
        gfx.backdrop(c, 'rays', '#ff4f9a', '#ffd23f', ud, speed=4)
        tab_mosaic(c, 6, ud) if int(ud * 8) % 2 == 0 else None
        for i, key in enumerate(cast.ALL):
            x = 140 + i * 182
            cast.draw_char(c, key, x, 1060, 0.55, ud + i, bob=abs(math.sin(ud * 8 + i)) * 90, arm_l=2.8, arm_r=2.8,
                           mouth=0.9, blush=1)
        cast.draw_restorer(c, 1780, 700, 0.55, ud, arm=1.0)
        cast.draw_hamster(c, 160, 300, 0.6, ud, mouth=0.9, run=ud * 3)
        c.save()
        c.translate(W / 2, 330)
        s = 1 + 0.08 * math.sin(ud * 16)
        c.scale(s, s)
        pat = gfx.chrome_pattern(-40, 130, 'sunset')
        text(c, 'Too Many', 0, -80, 130, 'Brush Script MT', col='#ffffff', align='c', outline='#ff2f7f', ow=6)
        text(c, 'TABS', 0, 150, 260, 'Impact', align='c', fill_pattern=pat, outline='#2a0f4a', ow=9, extrude='#2a0f4a',
             extrude_n=12, extrude_d=(1.5, 2))
        c.restore()
        if not frozen:
            fx.add('hue', ang=ud * 6)
        else:
            fx.add('flash', amt=0.9 * clamp(1 - (u - 3.5) / 0.2))
        fx.vhs = 0.7
        return
    u = lt - 20
    src(c, '#000000')
    c.paint()
    text(c, 'TOO MANY TABS', W / 2, 380, 110, 'Impact', col='#ffffff', align='c', alpha=clamp((u - 0.4) / 0.4))
    text(c, 'will return in a new tab.', W / 2, 500, 70, 'Georgia', italic=True, col='#ffffff', align='c',
         alpha=clamp((u - 1.2) / 0.5))
    text(c, 'No tabs were closed during the making of this program.', W / 2, 680, 44, 'Georgia', col='#bbbbbb',
         align='c', alpha=clamp((u - 2.5) / 0.5))
    text(c, '(That is a lie. We closed one.)', W / 2, 750, 40, 'Georgia', italic=True, col='#888888', align='c',
         alpha=clamp((u - 4.0) / 0.5))
    if u >= 5.0:
        k = ease_out_back(clamp((u - 5.0) / 0.3))
        c.save()
        c.translate(W - 330, H - 90)
        c.scale(k, k)
        gfx.ui_tab(c, 0, 0, 300, 60, 'New Tab', 'plus', active=True, t=t)
        c.restore()
    fx.vhs = 0.4
