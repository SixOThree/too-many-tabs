"""Reusable scene pieces: title cards, credits, cast intros, living room, slam text, lip sync."""
import math
import cairo

from .util import PI, TAU, clamp, lerp, smooth, ease_out, ease_out_back, ease_in, hrand, hsign, decay, bounce
from . import gfx, cast
from .gfx import OUTLINE, src, rrect, circle, text, hexc
from . import score as SC

W, H = 1920, 1080


class FX:
    """Collects post-processing requests for a frame."""

    def __init__(self):
        self.ops = []
        self.vhs = 0.0
        self.shake = 0.0
        self.zoom = 1.0

    def add(self, name, **kw):
        self.ops.append((name, kw))


# ---------------------------------------------------------------- lip sync

_spans = {}


def sung_spans(season):
    if season not in _spans:
        t0 = SC.SEC[season][0]
        ev = SC.lead_events(season, t0)
        spans = [(e['t'], e['t'] + e['d']) for e in ev]
        ch = SC.choir_events(t0, season=season)
        spans += [(e['t'], e['t'] + e['d']) for e in ch]
        spans.sort()
        _spans[season] = spans
    return _spans[season]


def mouth_at(t, spans, jitter=0):
    for a, b in spans:
        if a - 0.02 <= t < b:
            u = t - a
            d = b - a
            op = min(1.0, u / 0.05) * (0.75 + 0.25 * math.sin(u * 25 + jitter))
            if d - u < 0.06:
                op *= max(0.0, (d - u) / 0.06)
            return clamp(op)
        if a > t:
            break
    return 0.0


def talk_mouth(t, start, dur, seed=0):
    if t < start or t > start + dur:
        return 0.0
    u = t - start
    return clamp(0.25 + 0.75 * abs(math.sin(u * 11 + seed)) * (0.6 + 0.4 * math.sin(u * 3.3 + seed)))


def blink_at(t, seed=0):
    ph = (t + hrand(seed) * 3) % (2.6 + hrand(seed, 2))
    return 1.0 if ph < 0.09 else 0.0


# ---------------------------------------------------------------- text helpers

def slam_text(c, s, t_since, x=W / 2, y=H / 2, size=200, col='#ffe14d', rot=0.0, font='Impact', outline='#1b1030',
              life=0.45, style='slam'):
    if t_since < 0 or t_since > life:
        return
    u = t_since / life
    sc = 1.6 - 0.6 * ease_out_back(min(1, t_since / 0.12)) if style == 'slam' else 1.0
    a = 1.0 if u < 0.7 else 1 - (u - 0.7) / 0.3
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.scale(sc, sc)
    text(c, s, 0, 0, size, font, col=col, align='c', valign='mid', outline=outline, ow=size * 0.06, shadow=(0, 0, 0, 0.5),
         soff=(size * 0.04, size * 0.05), alpha=a, max_w=W * 0.95)
    c.restore()


def credit(c, actor, role, t_since, x=110, y=870, align='l', col_role='#ffe14d', alpha=1.0, pre='as', role_font='Impact',
           scale=1.0, closed=0.0, drip=False):
    if t_since < 0 or alpha <= 0:
        return
    a1 = clamp(t_since / 0.25) * alpha
    a2 = clamp((t_since - 0.18) / 0.25) * alpha
    slide = (1 - ease_out(t_since / 0.4)) * 60
    c.save()
    c.translate(x, y)
    c.scale(scale, scale)
    dx = -slide if align == 'l' else slide
    al = 'l' if align == 'l' else 'r'
    text(c, actor, dx, 0, 116, 'Brush Script MT', col='#ffffff', align=al, outline=OUTLINE, ow=4, shadow=(0, 0, 0, 0.45),
         soff=(5, 6), alpha=a1)
    w_as = gfx.text_width(c, pre + ' ', 50, 'Georgia', italic=True) if pre else 0
    rw = gfx.text_width(c, role, 76, role_font)
    if al == 'l':
        rx = dx * 1.5 + 8
        if pre:
            text(c, pre, rx, 92, 50, 'Georgia', italic=True, col='#ffffff', outline=OUTLINE, ow=3, alpha=a2)
        text(c, role, rx + w_as, 92, 76, role_font, col=col_role, outline=OUTLINE, ow=5, shadow=(0, 0, 0, 0.4),
             soff=(4, 5), alpha=a2)
        cx = rx + w_as + rw / 2
    else:
        rx = dx * 1.5
        text(c, role, rx, 92, 76, role_font, col=col_role, align='r', outline=OUTLINE, ow=5, shadow=(0, 0, 0, 0.4),
             soff=(4, 5), alpha=a2)
        if pre:
            text(c, pre, rx - rw - 16, 92, 50, 'Georgia', italic=True, col='#ffffff', align='r', outline=OUTLINE, ow=3,
                 alpha=a2)
        cx = rx - rw / 2
    if closed > 0:
        size = 150
        hw = gfx.text_width(c, 'CLOSED', size, 'Impact') / 2 + 40
        hh = size * 0.62
        # keep the whole stamp on screen; credit coordinates are scaled by `scale` around x
        scx = min(max(cx, (40 - x) / scale + hw), (W - 40 - x) / scale - hw)
        a = min(1, closed * 4)
        c.save()
        c.translate(scx, 64)
        c.rotate(-0.12)
        sc = 1 + 1.5 * (1 - ease_out(a))
        c.scale(sc, sc)
        rrect(c, -hw, -hh, 2 * hw, 2 * hh, 16)
        src(c, (0.85, 0.05, 0.1, 0.9 * a))
        c.set_line_width(14)
        c.stroke()
        text(c, 'CLOSED', 0, 0, size, 'Impact', col=(0.85, 0.05, 0.1, 1), align='c', valign='mid', alpha=a)
        c.restore()
    c.restore()


# ---------------------------------------------------------------- title card

def sky(c, t, top='#7fd0ff', mid='#ffc9e8', bot='#ffe6a3'):
    gfx.vgrad(c, 0, 0, W, H, [(0, top), (0.6, mid), (1, bot)])
    gfx.radial_glow(c, W * 0.5, H * 0.78, 700, (1, 0.95, 0.7, 0.8))


def tab_cloud(c, x, y, s, a=1.0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    for dx, dy, w, h in ((-120, -40, 160, 90), (-10, -80, 190, 130), (120, -30, 150, 80)):
        gfx.tab_path(c, dx - w / 2, dy, w, h + 40, 30, 18)
        src(c, (1, 1, 1, 0.85 * a))
        c.fill()
    c.restore()


def mini_tab(c, x, y, s, fav='globe', col='#ffffff', flap=0.0, t=0.0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    for side in (-1, 1):
        c.save()
        c.translate(side * 40, -20)
        c.rotate(side * (-0.4 + 0.8 * abs(math.sin(flap))))
        c.move_to(0, 0)
        c.curve_to(side * 40, -30, side * 80, -10, side * 90, 10)
        c.curve_to(side * 60, 5, side * 30, 10, 0, 0)
        gfx.fill_stroke(c, '#ffffff', OUTLINE, 4)
        c.restore()
    gfx.tab_path(c, -50, -50, 100, 60, 16, 10)
    gfx.fill_stroke(c, col, OUTLINE, 4)
    gfx.favicon(c, fav, -18, -22, 26, t, col='#ffffff')
    c.restore()


FAVS = ['globe', 'plus', 'fork', 'spinner', 'envelope', 'speaker', 'cart', 'check', 'book', 'terminal', 'shield',
        'weather', 'search', 'video', 'heart', 'map', 'cookie', 'doc']
TAB_COLS = ['#ffffff', '#ff9d45', '#6fb2ff', '#ff6166', '#a878ff', '#3fcf8a', '#ffd84a', '#e0cfa8', '#ff85c8', '#62dcff']

RANDOM_TITLES = [
    'New Tab', 'how to close tabs', 'Inbox (3)', 'is rain wet', 'Pasta Recipe - My Journey', 'Loading...',
    'best umbrella 2026', 'localhost:3000', 'Untitled', 'Your Cart (1)', 'why is my laptop hot', 'Settings',
    'Read later', '[SOLVED] (not solved)', 'Meeting (started 12 min ago)', 'Document (unsaved)',
    'cat but its a loaf', 'how many tabs is too many', 'Privacy Settings > Cookies', 'Weather - 70%',
    'List of lists of lists', 'Just in case', 'download (37).pdf', 'Sign in', 'Page not found',
    'we value your privacy', 'Order confirmation?', 'tab i forgot about', '404', 'Untitled (2)',
]


def random_tabs(n, seed=0):
    return [(RANDOM_TITLES[int(hrand(i, seed) * len(RANDOM_TITLES))], FAVS[int(hrand(i, seed, 3) * len(FAVS))],
             TAB_COLS[int(hrand(i, seed, 5) * len(TAB_COLS))]) for i in range(n)]


def title_card(c, lt, fx, season='s1'):
    """lt in [0,4)."""
    t = lt
    if season == 's2':
        sky(c, t, '#ff9fd2', '#ffc07a', '#fff09a')
    else:
        sky(c, t)
    # clouds
    for i in range(6):
        x = (hrand(i, 1) * (W + 600) + t * (30 + 40 * hrand(i, 2))) % (W + 600) - 300
        tab_cloud(c, x, 180 + hrand(i, 3) * 420, 0.6 + hrand(i, 4) * 0.8, 0.8)
    nfly = 7 if season == 's1' else 40
    for i in range(nfly):
        sp = 160 + hrand(i, 7) * 260
        x = (hrand(i, 8) * (W + 400) + t * sp) % (W + 400) - 200
        y = 120 + hrand(i, 9) * 700 + math.sin(t * 3 + i) * 20
        mini_tab(c, x, y, 0.45 + hrand(i, 10) * 0.35, FAVS[i % len(FAVS)], TAB_COLS[i % len(TAB_COLS)], t * 9 + i, t)
    if season == 's2':
        gfx.tab_strip(c, 0, 0, W, 64, random_tabs(47, 3), t, active=5)
    # logo
    intro = ease_out_back(clamp(t / 0.65), 1.4)
    sc = lerp(3.2, 1.0, intro)
    rot = lerp(-0.35, 0.0, intro)
    bob = math.sin(t * 2.2) * 8
    copies = [0] if season == 's1' else [3, 2, 1, 0]
    for ci in copies:
        tt = max(0, t - ci * 0.12)
        ii = ease_out_back(clamp(tt / 0.65), 1.4)
        c.save()
        c.translate(W / 2 + ci * 26, 470 + bob + ci * 18)
        c.rotate(lerp(-0.35, 0.0, ii) + (ci * 0.03))
        c.scale(lerp(3.2, 1.0, ii), lerp(3.2, 1.0, ii))
        a = 1.0 if ci == 0 else 0.35
        pat = gfx.chrome_pattern(-40, 230, 'sunset')
        text(c, 'Too Many', 0, -115, 175, 'Brush Script MT', col='#ffffff', align='c', outline='#ff2f7f', ow=7,
             shadow=(0.25, 0, 0.35, 0.6), soff=(6, 8), alpha=a)
        text(c, 'TABS', 0, 225, 330, 'Impact', align='c', fill_pattern=pat, outline='#2a0f4a', ow=10, extrude='#2a0f4a',
             extrude_n=16, extrude_d=(1.6, 2.2), alpha=a)
        c.restore()
    for (ts, px, py) in ((1.0, 630, 520), (3.0, 1300, 640), (2.0, 1150, 330)):
        u = t - ts
        if 0 <= u < 0.6:
            gfx.sparkle(c, px, py, 90 * math.sin(PI * u / 0.6), 1.0, rot=u * 2)
    if t > 1.3:
        u = t - 1.3
        badge = 'SEASON 1' if season == 's1' else 'SEASON 2'
        c.save()
        c.translate(1560, 760)
        c.rotate(0.2 + math.sin(t * 3) * 0.05)
        s = ease_out_back(clamp(u / 0.35))
        c.scale(s, s)
        gfx.star_path(c, 0, 0, 150, 118, 18)
        gfx.fill_stroke(c, '#ffe14d', OUTLINE, 6)
        text(c, badge, 0, 0, 52, 'Impact', col='#ff2f7f', align='c', valign='mid')
        c.restore()
    if season == 's2' and t > 2.2:
        u = t - 2.2
        c.save()
        c.translate(420, 820)
        c.rotate(-0.18)
        s = 1 + 2 * (1 - ease_out(clamp(u / 0.2)))
        c.scale(s, s)
        rrect(c, -330, -70, 660, 140, 20)
        gfx.fill_stroke(c, '#ff2f4f', OUTLINE, 7, clamp(u / 0.15))
        text(c, 'NOW WITH MORE TABS!', 0, 0, 62, 'Impact', col='#ffffff', align='c', valign='mid', alpha=clamp(u / 0.15))
        c.restore()
        c.save()
        c.translate(1330, 360)
        circle(c, 0, 0, 70)
        gfx.fill_stroke(c, '#ff2d2d', OUTLINE, 6)
        text(c, '47', 0, 2, 64, 'Arial Black', col='#ffffff', align='c', valign='mid')
        c.restore()
    fx.vhs = 0.6


# ---------------------------------------------------------------- living room

def living_room(c, t, n_tabs=4, dark=0.0, warm=0.0, frame_pic='plus'):
    wall = gfx.mix('#ffe9c7', '#1a1522', dark)
    stripe = gfx.mix('#ffd9a8', '#231c2c', dark)
    src(c, wall)
    c.rectangle(0, 0, W, H)
    c.fill()
    src(c, stripe)
    for i in range(0, W, 120):
        c.rectangle(i, 0, 50, 760)
    c.fill()
    # window = browser
    wx, wy, ww, wh = 560, 90, 800, 470
    tabs = random_tabs(n_tabs, 11)
    tabs[0] = ('Too Many Tabs', 'plus', '#ffffff')

    def view(cc, x, y, w, h):
        gfx.vgrad(cc, x, y, w, h, [(0, gfx.mix('#6cc8ff', '#0a0a20', dark)), (1, gfx.mix('#ffd6ea', '#301830', dark))])
        for i in range(3):
            tab_cloud(cc, x + (i * 300 + t * 20) % (w + 300) - 150, y + 120 + i * 70, 0.45, 1 - dark)
    gfx.browser_window(c, wx, wy, ww, wh, tabs, t, 0, 'https://toomanytabs.tv', view, chrome_h=96, alpha=1.0)
    # baseboard + floor
    src(c, gfx.mix('#c98b5a', '#2a1c18', dark))
    c.rectangle(0, 760, W, H - 760)
    c.fill()
    src(c, gfx.mix('#fff6e8', '#302a30', dark))
    c.rectangle(0, 740, W, 26)
    c.fill()
    for i in range(0, W, 160):
        src(c, (0, 0, 0, 0.12))
        c.rectangle(i, 766, 4, H)
        c.fill()
    gfx.ellipse(c, W / 2, 960, 720, 110)
    src(c, gfx.mix('#ff8fb1', '#40202a', dark))
    c.fill()
    # lamp
    c.move_to(230, 740); c.line_to(230, 420)
    src(c, OUTLINE); c.set_line_width(10); c.stroke()
    c.move_to(150, 420); c.line_to(310, 420); c.line_to(270, 300); c.line_to(190, 300); c.close_path()
    gfx.fill_stroke(c, gfx.mix('#ffe14d', '#3a3320', dark), OUTLINE, 6)
    if dark < 0.5:
        gfx.radial_glow(c, 230, 420, 260, (1, 0.95, 0.6, 0.35))
    # plant
    rrect(c, 1640, 610, 120, 130, 16)
    gfx.fill_stroke(c, gfx.mix('#e0643c', '#301812', dark), OUTLINE, 6)
    for i in range(7):
        a = -PI / 2 + (i - 3) * 0.33 + math.sin(t * 1.5 + i) * 0.04
        c.move_to(1700, 615)
        c.curve_to(1700 + math.cos(a) * 80, 615 + math.sin(a) * 80, 1700 + math.cos(a) * 160, 615 + math.sin(a) * 180,
                   1700 + math.cos(a) * 190, 615 + math.sin(a) * 210)
        src(c, gfx.mix('#2fa35a', '#10301a', dark)); c.set_line_width(24); c.stroke()
    # picture frame
    rrect(c, 1450, 180, 200, 160, 8)
    gfx.fill_stroke(c, gfx.mix('#fff8ee', '#282430', dark), '#8a5a2a', 12)
    gfx.favicon(c, frame_pic, 1550, 260, 70, t, col='#ffffff')


def couch_back(c, dark=0.0):
    col = gfx.mix('#2fb5a8', '#132a28', dark)
    rrect(c, 330, 470, 1260, 300, 70)
    gfx.fill_stroke(c, col, OUTLINE, 8)


def couch_front(c, dark=0.0):
    col = gfx.mix('#2fb5a8', '#132a28', dark)
    rrect(c, 380, 660, 1160, 170, 40)
    gfx.fill_stroke(c, gfx.shade(col, 1.12), OUTLINE, 8)
    for side in (-1, 1):
        rrect(c, W / 2 + side * 640 - 90, 560, 180, 290, 60)
        gfx.fill_stroke(c, gfx.shade(col, 0.9), OUTLINE, 8)
    for x in (430, 1480):
        rrect(c, x, 830, 40, 60, 8)
        gfx.fill_stroke(c, '#5a3a1a', OUTLINE, 5)


# ---------------------------------------------------------------- cast intro

def cast_bit(key, u, t_abs):
    """Per-character animation during the intro. u = seconds since entering."""
    p = {}
    p['blink'] = blink_at(t_abs, hash(key) % 97)
    if key == 'newtab':
        p.update(arm_r=2.7, wave=1.0, bob=abs(math.sin(u * 6)) * 14, mouth=0.2 + 0.3 * abs(math.sin(u * 4)))
    elif key == 'recipe':
        p.update(arm_l=1.1, arm_r=0.6, mouth=talk_mouth(u, 0.4, 2.2, 1), look=(-0.4, 0.2), brow=0.6)
    elif key == 'loading':
        p.update(tilt=u * 2.6, arm_l=1.6, arm_r=1.6, mouth=0.4, bob=8 * math.sin(u * 9))
    elif key == 'inbox':
        p.update(expr='scared', sweat=1.0, mouth=0.6, look=(0.8, 0), arm_l=2.2, arm_r=2.4, bob=6 * math.sin(u * 30))
    elif key == 'audio':
        p.update(bob=abs(math.sin(u * PI * 2)) * 20, tilt=0.12 * math.sin(u * PI * 2), arm_r=2.2, arm_l=2.2,
                 mouth=0.3)
    elif key == 'cart':
        p.update(arm_l=1.4, look=(0.6, -0.6), mouth=0, expr='flat', bob=4 * abs(math.sin(u * 8)))
    elif key == 'forum':
        p.update(arm_r=1.8, look=(0.5, 0.2), mouth=talk_mouth(u, 0.3, 1.5, 3), brow=0.8)
    elif key == 'later':
        p.update(blink=0, arm_l=0.1, arm_r=0.1, bob=math.sin(u * 2) * 6, tilt=0.08 * math.sin(u * 1.3), mouth=0.1)
    elif key == 'localhost':
        p.update(arm_l=1.4, arm_r=1.2, look=(0, 0.7), mouth=0)
    elif key == 'justincase':
        p.update(arm_r=2.4, arm_l=2.4, look=(-0.6, -0.4), expr='scared', mouth=0.4, sweat=0.6)
    return p


def cast_intro(c, u, key, fx, t_abs, dur=4.0, side='right', season='s1', extras=None, freeze_at=None, credit_role=None,
               backdrop=None, dark=0.0, pile=None):
    """u in [0,dur). Character on one side, credits on the other."""
    spec = cast.CAST[key]
    fz = freeze_at if freeze_at is not None else dur * 0.75
    frozen = u >= fz
    ud = min(u, fz)
    bd = backdrop or spec['backdrop']
    c1, c2 = bd[1], bd[2]
    if dark > 0:
        c1, c2 = gfx.mix(c1, '#050308', dark), gfx.mix(c2, '#0a0610', dark)
    zoom = 1.0 + (0.05 * ease_out(clamp((u - fz) / 0.3)) if frozen else 0.0) + 0.04 * ud / dur
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(zoom, zoom)
    c.translate(-W / 2, -H / 2)
    gfx.backdrop(c, bd[0], c1, c2, ud)
    cx = 1300 if side == 'right' else 620
    gfx.spotlight(c, cx, 560, 700, 0.35 * (1 - dark))
    enter = ease_out_back(clamp(ud / 0.5), 1.2)
    x = lerp(-400 if side == 'right' else W + 400, cx, enter)
    walk = ud * 3 if ud < 0.5 else 0
    pose = cast_bit(key, max(0.0, ud - 0.4), t_abs if not frozen else t_abs - (u - fz))
    if ud > fz - 0.35:
        k = clamp((ud - (fz - 0.35)) / 0.2)
        pose.update(look=(0, 0), mouth=max(pose.get('mouth', 0), 0.55 * k), blush=k, expr=pose.get('expr', 'happy'))
        if key == 'loading':
            upright = round(pose['tilt'] / TAU) * TAU
            pose['tilt'] = lerp(pose['tilt'], upright, k)
    if extras:
        extras(c, ud, 'back', cx)
    cast.draw_char(c, key, x, 940, 1.25, ud, walk=walk, **pose)
    if extras:
        extras(c, ud, 'front', cx)
    c.restore()
    if pile:
        pile(c, u)
    role = credit_role or spec['role']
    if side == 'right':
        credit(c, spec['actor'], role, u - dur * 0.3, 110, 860, 'l')
    else:
        credit(c, spec['actor'], role, u - dur * 0.3, W - 110, 860, 'r')
    if frozen:
        f = clamp(1 - (u - fz) / 0.18)
        if f > 0:
            fx.add('flash', amt=0.85 * f)
        fx.add('grade', sat=0.82, contrast=1.08, bright=0.0)
    # whip-in lines
    if u < 0.25:
        a = 1 - u / 0.25
        for i in range(14):
            y = hrand(i, 44) * H
            src(c, (1, 1, 1, 0.6 * a))
            c.rectangle(0, y, W, 6 + hrand(i, 45) * 20)
            c.fill()
    fx.vhs = 0.7
