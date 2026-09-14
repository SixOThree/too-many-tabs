"""Season 1 and Season 2 of the looping sitcom intro."""
import math

from .util import PI, TAU, clamp, lerp, smooth, ease_out, ease_out_back, ease_in, hrand, hsign, bounce
from . import gfx, cast
from .gfx import OUTLINE, src, rrect, circle, text
from .common import W, H, FX, title_card, cast_intro, living_room, couch_back, couch_front, slam_text, credit
from .common import mouth_at, sung_spans, blink_at, random_tabs, mini_tab, FAVS, TAB_COLS
from . import common
from . import score as SC


# ---------------------------------------------------------------- character props

def props_recipe(c, u, layer, cx):
    if layer != 'front':
        return
    hx, hy = cx - 170, 700
    L = 60 + 900 * ease_out(clamp((u - 0.4) / 1.6))
    c.save()
    c.move_to(hx, hy)
    c.line_to(hx + 70, hy)
    c.line_to(hx + 70 + 40 * math.sin(u * 3), hy + L)
    c.line_to(hx + 40 * math.sin(u * 3), hy + L)
    c.close_path()
    gfx.fill_stroke(c, '#fff8e6', OUTLINE, 5)
    for i in range(int(L / 26)):
        y = hy + 20 + i * 26
        src(c, (0.3, 0.3, 0.35, 0.6))
        c.rectangle(hx + 10 + 40 * math.sin(u * 3) * (i * 26 / max(L, 1)), y, 50 * (0.5 + 0.5 * hrand(i, 3)), 5)
        c.fill()
    c.restore()
    if 0.6 < u < 2.9:
        a = clamp((u - 0.6) / 0.2)
        c.save()
        c.translate(cx + 300, 330)
        rrect(c, -40, -80, 560, 150, 40)
        gfx.fill_stroke(c, '#ffffff', OUTLINE, 6, a)
        c.move_to(0, 60); c.line_to(-60, 130); c.line_to(60, 68)
        gfx.fill_stroke(c, '#ffffff', OUTLINE, 6, a)
        lines = ['It all began in 1987,', 'when my grandmother...']
        for i, ln in enumerate(lines):
            text(c, ln, 240, -30 + i * 56, 44, 'Comic Sans MS', col='#222', align='c', valign='mid', alpha=a)
        c.restore()


def props_loading(c, u, layer, cx):
    if layer != 'front':
        return
    x, y, w = cx - 260, 1010, 520
    rrect(c, x, y, w, 36, 18)
    gfx.fill_stroke(c, '#ffffff', OUTLINE, 5)
    prog = min(0.99, 0.2 + u * 0.5)
    rrect(c, x + 5, y + 5, (w - 10) * prog, 26, 13)
    src(c, '#3a8bff')
    c.fill()
    text(c, f'{int(prog * 100)}%', x + w + 20, y + 30, 40, 'Impact', col='#ffffff', outline=OUTLINE, ow=3)


def props_inbox(c, u, layer, cx):
    if layer == 'back':
        n = 3 if u < 1.0 else (8 if u < 2.25 else 32)
        k = 1.0 + 0.4 * max(0.0, 1 - ((u - (1.0 if u < 2.25 else 2.25)) / 0.25)) if u > 1.0 else 1.0
        c.save()
        c.translate(cx - 500, 300)
        c.scale(k, k)
        circle(c, 0, 0, 120)
        gfx.fill_stroke(c, '#ff2d2d', OUTLINE, 8)
        text(c, str(n), 0, 4, 130 if n < 10 else 110, 'Arial Black', col='#ffffff', align='c', valign='mid')
        c.restore()
        return
    for i in range(10):
        st = 0.3 + i * 0.28
        v = u - st
        if v < 0:
            continue
        x = lerp(W + 100, cx + 40, clamp(v / 0.35))
        y = 250 + hrand(i, 3) * 420
        if v > 0.35:
            x = cx + 40 + (v - 0.35) * 600
            y = y + (v - 0.35) * 900 * (v - 0.35) - 150 * (v - 0.35)
        c.save()
        c.translate(x, y)
        c.rotate(v * 8 + i)
        gfx.favicon(c, 'envelope', 0, 0, 90, u, col='#fff7e0')
        c.restore()


def props_audio_decoys(c, u, layer, cx):
    if layer != 'back':
        return
    for i, dx in enumerate((-620, -310, 310)):
        cast.draw_char(c, 'audio', cx + dx, 900, 0.8, u + i, bob=0, mouth=0, arm_l=0.1, arm_r=0.1)
    for i in range(6):
        v = (u * 0.8 + i / 6) % 1
        x = cx + (hrand(i, 2) - 0.5) * 1200
        y = 800 - v * 700
        text(c, '♪' if i % 2 else '♫', x, y, 90, 'Segoe UI Symbol', col='#ffffff', outline=OUTLINE, ow=3, alpha=1 - v)


def props_cart(c, u, layer, cx):
    if layer != 'front':
        return
    c.save()
    c.translate(cx + 250, 560)
    rrect(c, -80, -70, 160, 140, 10)
    gfx.fill_stroke(c, '#d9a066', OUTLINE, 6)
    c.move_to(-80, -20); c.line_to(80, -20)
    src(c, (0, 0, 0, 0.3)); c.set_line_width(8); c.stroke()
    c.restore()
    if u > 0.8:
        a = clamp((u - 0.8) / 0.2)
        rrect(c, cx - 520, 250, 340, 110, 20)
        gfx.fill_stroke(c, '#ffffff', OUTLINE, 6, a)
        text(c, 'in cart since', cx - 350, 290, 34, 'Segoe UI', bold=True, col='#333', align='c', alpha=a)
        text(c, '2 YEARS AGO', cx - 350, 338, 46, 'Impact', col='#e02040', align='c', alpha=a)


def props_forum(c, u, layer, cx):
    if layer == 'back':
        c.save()
        c.translate(cx + 360, 520)
        c.rotate(0.06)
        c.move_to(0, 60); c.line_to(0, 420)
        src(c, '#6a4a2a'); c.set_line_width(20); c.stroke()
        rrect(c, -180, -80, 360, 160, 12)
        gfx.fill_stroke(c, '#fff4d0', OUTLINE, 6)
        text(c, '✓ SOLVED', 0, -20, 50, 'Impact', col='#1e9e4a', align='c', valign='mid')
        text(c, '"nvm fixed it"', 0, 40, 40, 'Comic Sans MS', col='#333', align='c', valign='mid')
        c.restore()
    else:
        for i in range(30):
            x = (hrand(i, 1) * W + u * 20) % W
            y = (hrand(i, 2) * H + u * 30 * (0.5 + hrand(i, 3))) % H
            circle(c, x, y, 3 + hrand(i, 4) * 4)
            src(c, (1, 0.95, 0.8, 0.5))
            c.fill()


def props_localhost(c, u, layer, cx):
    if layer == 'back':
        for i in range(12):
            x = ((u * 180 + i * 150) % (W + 300)) - 150
            y = 820 + math.sin(u * 10 + i) * 8
            c.save()
            c.translate(x, y)
            for side in (-1, 1):
                c.move_to(side * 12, 20); c.line_to(side * 12 + math.sin(u * 14 + i) * 10 * side, 50)
                src(c, OUTLINE); c.set_line_width(6); c.stroke()
            gfx.favicon(c, FAVS[i % len(FAVS)], 0, 0, 64, u, col=TAB_COLS[i % len(TAB_COLS)])
            c.restore()
        return
    c.save()
    c.translate(cx, 780)
    c.move_to(-230, 0); c.line_to(230, 0); c.line_to(260, 30); c.line_to(-260, 30); c.close_path()
    gfx.fill_stroke(c, '#9aa3b5', OUTLINE, 6)
    rrect(c, -210, -260, 420, 260, 16)
    gfx.fill_stroke(c, '#0d0f14', OUTLINE, 6)
    lines = ['$ npm run dev', 'ready on :3000', 'Cannot GET /', 'Cannot GET /', 'Cannot GET /']
    shown = int(u * 3)
    for i, ln in enumerate(lines[:shown]):
        text(c, ln, -190, -210 + i * 44, 32, 'Consolas', col='#ff6060' if 'Cannot' in ln else '#39ff7a')
    c.restore()


def props_later(c, u, layer, cx):
    if layer != 'back':
        return
    for i, yr in enumerate(range(2019, 2027)):
        v = u - i * 0.3
        if v < 0:
            continue
        x = cx - 700 + v * 260 + i * 30
        y = 200 + v * v * 300 + i * 20
        c.save()
        c.translate(x, y)
        c.rotate(v * 2)
        rrect(c, -80, -90, 160, 180, 10)
        gfx.fill_stroke(c, '#ffffff', OUTLINE, 5, clamp(2 - v))
        c.rectangle(-80, -90, 160, 44)
        src(c, (0.9, 0.2, 0.25, clamp(2 - v)))
        c.fill()
        text(c, str(yr), 0, 20, 52, 'Impact', col='#222', align='c', valign='mid', alpha=clamp(2 - v))
        c.restore()


def props_justincase(c, u, layer, cx):
    if layer != 'front':
        return
    c.save()
    c.translate(cx - 230, 470)
    c.rotate(-0.15)
    c.move_to(-200, 0)
    c.curve_to(-200, -190, 200, -190, 200, 0)
    for i in range(4):
        c.curve_to(200 - i * 100 - 20, -40, 200 - (i + 1) * 100 + 20, -40, 200 - (i + 1) * 100, 0)
    gfx.fill_stroke(c, '#ff5d8f', OUTLINE, 6)
    c.move_to(0, -150); c.line_to(0, 330)
    src(c, OUTLINE); c.set_line_width(8); c.stroke()
    c.restore()
    c.save()
    c.translate(cx + 360, 330)
    c.rotate(0.1)
    c.rectangle(-120, -110, 240, 220)
    gfx.fill_stroke(c, '#fff26a', None)
    text(c, 'opened:', 0, -40, 40, 'Comic Sans MS', col='#333', align='c', valign='mid')
    text(c, 'LAST MAY', 0, 30, 58, 'Impact', col='#e02040', align='c', valign='mid')
    c.restore()


PROPS = dict(recipe=props_recipe, loading=props_loading, inbox=props_inbox, audio=props_audio_decoys,
             cart=props_cart, forum=props_forum, localhost=props_localhost, later=props_later,
             justincase=props_justincase)


# ---------------------------------------------------------------- credit pile (season 2)

def credit_pile(c, u, t_abs, upto):
    names = cast.ORDER1 + cast.ORDER2
    for i in range(upto):
        k = names[i % len(names)]
        sp = cast.CAST[k]
        x = 200 + hrand(i, 71) * 1300
        y = 150 + hrand(i, 72) * 700
        c.save()
        c.translate(x, y)
        c.rotate(hsign(i, 73) * 0.25)
        credit(c, sp['actor'], sp['role'], 1.0, 0, 0, 'l', alpha=0.75, scale=0.7 + hrand(i, 74) * 0.5)
        c.restore()


# ---------------------------------------------------------------- chorus shots

def couch_shot(c, lt, t_abs, fx, season, hits):
    keys = cast.ORDER1 if season == 's1' else cast.ORDER1 + cast.ORDER2
    passed = sum(1 for h in hits if lt >= h)
    ntabs = 2 ** (passed + 1) if season == 's1' else 12 * 2 ** passed
    punch = 0.0
    for h in hits:
        if 0 <= lt - h < 0.3:
            punch = 0.07 * (1 - (lt - h) / 0.3)
    c.save()
    c.translate(W / 2, H / 2)
    z = 1.0 + punch
    c.scale(z, z)
    c.translate(-W / 2, -H / 2)
    living_room(c, t_abs, min(ntabs, 400))
    couch_back(c)
    spans = sung_spans(season)
    n = len(keys)
    rows = [keys] if n <= 6 else [keys[6:], keys[:6]]
    for ri, row in enumerate(rows):
        m = len(row)
        for i, k in enumerate(row):
            x = 520 + i * (880 / max(1, m - 1))
            y = 760 - (130 if (len(rows) == 2 and ri == 0) else 0)
            beat = t_abs / 0.5
            sway = math.sin(beat * PI + i) * 0.08
            spec = cast.CAST[k]
            if season == 's2' and k == 'inbox':
                spec = dict(spec, badge='9,431', title='Inbox (9,431)')
            cast.draw_char(c, spec, x, y, 0.62, t_abs, tilt=sway, legs=False,
                           mouth=mouth_at(t_abs, spans, i), blink=blink_at(t_abs, i),
                           arm_l=0.6 + 0.4 * math.sin(beat * PI), arm_r=0.6 + 0.4 * math.sin(beat * PI + 1),
                           look=(math.sin(t_abs + i) * 0.3, 0))
    couch_front(c)
    c.restore()
    # burst of mini tabs on each hit
    for hi, h in enumerate(hits):
        v = lt - h
        if 0 <= v < 1.2:
            for i in range(18):
                a = hrand(hi, i, 1) * TAU
                sp = 600 + 700 * hrand(hi, i, 2)
                x = W / 2 + math.cos(a) * sp * v
                y = 420 + math.sin(a) * sp * v + 500 * v * v
                mini_tab(c, x, y, 0.5, FAVS[i % len(FAVS)], TAB_COLS[i % len(TAB_COLS)], v * 20, v)
        slam_text(c, 'TOO MANY TABS!', v, W / 2, 190, 170, ['#ffe14d', '#ff5fa2', '#62dcff', '#7dff7a'][hi % 4],
                  rot=hsign(hi, 5) * 0.08, life=1.2)
    fx.vhs = 0.7


def search_montage(c, u, t_abs, fx, season):
    rows = 7 if season == 's1' else 11
    per_row = 6 if season == 's1' else 14
    src(c, '#b9c1d1')
    c.rectangle(0, 0, W, H)
    c.fill()
    rh = H / rows
    tabs = random_tabs(rows * per_row, 21 if season == 's1' else 22)
    beat = int(t_abs / 0.25)
    for r in range(rows):
        off = math.sin(u * 2 + r) * 40
        gfx.tab_strip(c, -40 + off, r * rh, W + 80, rh, [tb + (hrand(i + r * per_row, beat) > 0.8,) for i, tb in
                                                        enumerate(tabs[r * per_row:(r + 1) * per_row])], t_abs,
                      active=-1, bg='#b9c1d1')
    # magnifier
    mx = W / 2 + math.sin(u * 4.1) * 650
    my = H / 2 + math.cos(u * 3.3) * 330
    c.save()
    circle(c, mx, my, 170)
    c.clip()
    c.translate(mx, my)
    c.scale(1.8, 1.8)
    c.translate(-mx, -my)
    for r in range(rows):
        off = math.sin(u * 2 + r) * 40
        gfx.tab_strip(c, -40 + off, r * rh, W + 80, rh, tabs[r * per_row:(r + 1) * per_row], t_abs, active=-1,
                      bg='#dfe4ee')
    c.restore()
    circle(c, mx, my, 170)
    src(c, OUTLINE)
    c.set_line_width(22)
    c.stroke()
    c.move_to(mx + 120, my + 120); c.line_to(mx + 300, my + 300)
    c.set_line_width(44)
    c.stroke()
    slam_text(c, 'WHICH ONE?!', u - 0.2, W / 2, H - 150, 150, '#ff3b5c', rot=-0.05, life=1.8, style='plain')
    fx.vhs = 0.7


def final_pose(c, u, t_abs, fx, season):
    frozen_at = 1.5
    ud = min(u, frozen_at)
    gfx.backdrop(c, 'rays', '#ff8fc4', '#ffc2e0', ud, speed=2)
    keys = cast.ORDER1 if season == 's1' else cast.ORDER1 + cast.ORDER2
    jump = 0.75
    n = len(keys)
    for i, k in enumerate(keys):
        x = 180 + i * (1560 / max(1, n - 1))
        v = ud - jump
        bob = 0 if v < 0 else math.sin(clamp(v / 0.5) * PI) * 160
        up = v >= 0
        spec = cast.CAST[k]
        if season == 's2' and k == 'inbox':
            spec = dict(spec, badge='9,431', title='Inbox (9,431)')
        cast.draw_char(c, spec, x, 1040, 0.62 if n <= 6 else 0.46, ud, bob=bob, arm_l=2.8 if up else 0.4,
                       arm_r=2.8 if up else 0.4, mouth=mouth_at(t_abs if u < frozen_at else t_abs - (u - frozen_at),
                                                               sung_spans(season)) if not up else 0.9, blush=1 if up else 0)
    drop = bounce(clamp((ud - 0.75) / 0.6))
    c.save()
    c.translate(W / 2, lerp(-300, 290, drop))
    pat = gfx.chrome_pattern(-40, 130, 'sunset')
    text(c, 'Too Many', 0, -60, 110, 'Brush Script MT', col='#ffffff', align='c', outline='#ff2f7f', ow=5)
    text(c, 'TABS', 0, 130, 200, 'Impact', align='c', fill_pattern=pat, outline='#2a0f4a', ow=8, extrude='#2a0f4a',
         extrude_n=10, extrude_d=(1.5, 2))
    c.restore()
    if u >= frozen_at:
        f = clamp(1 - (u - frozen_at) / 0.2)
        fx.add('flash', amt=0.9 * f)
        fx.add('grade', sat=0.85, contrast=1.05, bright=0.0)
        text(c, 'Created by A. Browser', W - 60, H - 40, 40, 'Georgia', italic=True, col='#ffffff', align='r',
             outline=OUTLINE, ow=3, alpha=clamp((u - frozen_at) / 0.2))
    if season == 's2' and u > 1.62:
        fx.add('slices', seed=int(t_abs * 30), count=14, maxshift=260)
        fx.add('rgbsplit', amt=14)
    fx.vhs = 0.7


# ---------------------------------------------------------------- the loop

INTROS = {
    's1': [('newtab', 'right'), ('recipe', 'left'), ('loading', 'right'), ('inbox', 'left')],
    's2': [('forum', 'right'), ('localhost', 'left'), ('later', 'right'), ('justincase', 'left')],
}
QUICK = {
    's1': [('audio', 'right', None), ('cart', 'left', None)],
    's2': [('newtab', 'right', 'NEW TAB (STILL OPEN)'), ('inbox', 'left', 'INBOX (9,431)')],
}


def draw_loop(c, lt, t_abs, fx, season):
    if lt < 4:
        title_card(c, lt, fx, season)
        return
    if lt < 20:
        i = int((lt - 4) // 4)
        key, side = INTROS[season][i]
        u = lt - 4 - i * 4
        pile = None
        if season == 's2':
            upto = 4 + i * 2
            pile = lambda cc, uu, _u=upto: credit_pile(cc, uu, t_abs, _u)
        extras = PROPS.get(key)
        cast_intro(c, u, key, fx, t_abs, 4.0, side, season, extras, pile=pile)
        if season == 's2' and key == 'forum':
            fx.add('grade', sat=0.3, contrast=1.0, bright=0.0, tint=0.6, tr=1.2, tg=1.0, tb=0.7)
        if season == 's2' and i in (1, 3):
            # the Restorer lurks in the background for a moment
            v = u - 1.3
            if 0 < v < 0.9:
                a = math.sin(PI * v / 0.9)
                cast.draw_restorer(c, 1700 if side == 'left' else 220, 1150, 0.9, t_abs, alpha=0.55 * a,
                                   silhouette=1.0, glow=0.4)
        if season == 's2' and key == 'justincase':
            for k in range(3):
                credit(c, 'Justin Case', 'JUST IN CASE', u - 1.6 - k * 0.3, 1000, 250 + k * 170, 'r', scale=0.8)
        return
    if lt < 24:
        hits = [20.0, 22.0, 24.0, 26.0]
        couch_shot(c, lt, t_abs, fx, season, hits)
        return
    if lt < 28:
        i = int((lt - 24) // 2)
        key, side, role = QUICK[season][i]
        u = lt - 24 - i * 2
        spec_override = None
        extras = PROPS.get(key) if season == 's1' else None
        cast_intro(c, u, key, fx, t_abs, 2.0, side, season, extras, freeze_at=1.5, credit_role=role)
        slam_text(c, 'TOO MANY TABS!', u, W / 2, 170, 150, '#ffe14d', rot=-0.06, life=0.9)
        return
    if lt < 30:
        search_montage(c, lt - 28, t_abs, fx, season)
        return
    final_pose(c, lt - 30, t_abs, fx, season)
