"""The cast: tab-shaped sitcom characters, the Restorer, the Cursor, Ramsey the hamster."""
import math
import cairo
from .util import PI, TAU, clamp, lerp, hrand, hsign, smooth, ease_out
from . import gfx
from .gfx import OUTLINE, src, rrect, tab_path, circle, ellipse, fill_stroke, text, favicon, shade, rgba, desat, mix

CAST = {
    'newtab': dict(actor='Tabitha Newman', role='NEW TAB', col='#f3efe6', fav='plus', favc='#ffffff',
                   acc=['bow'], title='New Tab', backdrop=('dots', '#ff8fc4', '#ffb3d6')),
    'recipe': dict(actor='Rex Scrollsworth', role='PASTA RECIPE (WITH LIFE STORY)', col='#ff9d45', fav='fork',
                   favc='#fff3d6', acc=['chef_hat', 'mustache'], title='Pasta Recipe - My Journey',
                   backdrop=('zigzag', '#22b8b0', '#5fd6cf')),
    'loading': dict(actor='Buffy Spinwheel', role='LOADING...', col='#6fb2ff', fav='spinner', favc='#ffffff',
                    acc=['antenna'], eyes='spiral', title='Loading...', backdrop=('triangles', '#ffcf3f', '#ffe27e')),
    'inbox': dict(actor='Dr. Ina Box', role='INBOX (3)', col='#ff6166', fav='envelope', favc='#ffffff',
                  acc=['frazzle', 'glasses'], title='Inbox (3)', badge='3', backdrop=('stripes', '#7a5cff', '#9a82ff')),
    'audio': dict(actor='Sonny Mute', role='THE TAB PLAYING AUDIO', col='#a878ff', fav='speaker', favc='#ffffff',
                  acc=['shades'], title='??? (playing audio)', backdrop=('rays', '#1ec8ff', '#62dcff')),
    'cart': dict(actor='Carter Cartwright', role='CART (1)', col='#3fcf8a', fav='cart', favc='#ffffff',
                 acc=['tie'], title='Your Cart (1)', badge='1', backdrop=('checker', '#ff7a45', '#ff9a6f')),
    'forum': dict(actor='Prof. Hugh Answers', role='FORUM ANSWER FROM 2011', col='#e0cfa8', fav='check',
                  favc='#ffffff', acc=['beard', 'cobweb', 'monocle'], title='[SOLVED] (not solved)',
                  backdrop=('squiggle', '#8a6a4a', '#a88763')),
    'later': dict(actor='Laterna Reid', role='ARTICLE TO READ LATER', col='#c4c4d4', fav='book', favc='#ffffff',
                  acc=['nightcap'], eyes='sleepy', title='Read later (since 2019)',
                  backdrop=('dots', '#5b6a8a', '#6f7fa1')),
    'localhost': dict(actor='Dev Nullman', role='localhost:3000', col='#2b2f3a', fav='terminal', favc='#0d0f14',
                      acc=['hood', 'mug'], title='localhost:3000', dark=True,
                      backdrop=('plus', '#0f3d24', '#17603a')),
    'justincase': dict(actor='Justin Case', role='A TAB OPENED JUST IN CASE', col='#ffd84a', fav='shield',
                       favc='#ffffff', acc=['hardhat', 'floaties'], title='Just in case',
                       backdrop=('stripes', '#ff5d8f', '#ff85aa')),
}

ORDER1 = ['newtab', 'recipe', 'loading', 'inbox', 'audio', 'cart']
ORDER2 = ['forum', 'later', 'localhost', 'justincase']
ALL = ORDER1 + ORDER2


BODY_CY = -240  # vertical centre of the tab body relative to the feet, at s=1
CLOSE_BTN = (104, -362)  # centre of the close button relative to the feet, at s=1


def close_button_pos(x, y, s=1.0, tilt=0.0, bob=0.0):
    """Screen position of the close button of a character drawn by draw_char with these arguments."""
    px, py = CLOSE_BTN[0], CLOSE_BTN[1] - BODY_CY
    ca, sa = math.cos(tilt), math.sin(tilt)
    return x + s * (px * ca - py * sa), y + s * (px * sa + py * ca + BODY_CY - bob)


def pose_default():
    return dict(look=(0.0, 0.0), blink=0.0, mouth=0.0, expr='happy', arm_l=0.15, arm_r=-0.15,
                wave=0.0, bob=0.0, tilt=0.0, squash=0.0, walk=0.0, gray=0.0, brow=0.0,
                eyes=None, alpha=1.0, legs=True, arms=True, sweat=0.0, blush=0.0, close_hover=0.0)


def _c(col, gray):
    return desat(col, gray) if gray > 0 else rgba(col)


def draw_char(c, key, x, y, s=1.0, t=0.0, **kw):
    """Tab character standing with feet at (x,y). Body ~300 wide, ~420 tall at s=1."""
    spec = CAST[key] if isinstance(key, str) else key
    p = pose_default()
    p.update(kw)
    g = p['gray']
    a = p['alpha']
    if a <= 0.001:
        return
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.translate(0, -p['bob'])
    # tilt pivots on the middle of the tab body, not the feet
    c.translate(0, BODY_CY)
    c.rotate(p['tilt'])
    c.translate(0, -BODY_CY)
    sq = p['squash']
    c.scale(1 + sq * 0.4, 1 - sq * 0.4)
    if a < 1:
        c.push_group()
    body = _c(spec['col'], g)
    dark = spec.get('dark', False)
    ink = OUTLINE
    lw = 7
    # ---- legs
    if p['legs']:
        wk = p['walk']
        for side in (-1, 1):
            ph = math.sin(wk * TAU + (0 if side < 0 else PI))
            hx = side * 55
            fx = side * 70 + ph * 30
            fy = -min(0, ph) * -10
            c.move_to(hx, -70)
            c.curve_to(hx, -40, fx - side * 10, -25, fx, -8 - fy)
            src(c, ink, 1)
            c.set_line_width(14)
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.stroke()
            ellipse(c, fx + side * 16, -4 - fy, 34, 16)
            fill_stroke(c, _c('#2d2a3e', g), ink, 5)
    # ---- arms behind body when down? draw after body for visibility
    top = -420
    bw, bh = 300, 360
    tab_path(c, -bw / 2, top, bw, bh, 52, 30)
    grd = cairo.LinearGradient(0, top, 0, top + bh)
    grd.add_color_stop_rgba(0, *shade(body, 1.12)[:3], 1)
    grd.add_color_stop_rgba(1, *shade(body, 0.9)[:3], 1)
    c.set_source(grd)
    c.fill_preserve()
    src(c, ink)
    c.set_line_width(lw)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.stroke()
    # shine
    c.move_to(-118, top + 150)
    c.curve_to(-118, top + 60, -100, top + 30, -60, top + 26)
    src(c, (1, 1, 1, 0.45))
    c.set_line_width(12)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.stroke()
    # favicon + close x
    favicon(c, spec['fav'], -98, top + 58, 56, t, col=_c(spec.get('favc', '#ffffff'), g))
    if spec.get('badge'):
        circle(c, -70, top + 30, 20)
        fill_stroke(c, _c('#ff2d2d', g), ink, 4)
        text(c, str(spec['badge']), -70, top + 31, 24 if len(str(spec['badge'])) < 3 else 15, 'Arial Black',
             col='#ffffff', align='c', valign='mid')
    gfx.close_x(c, CLOSE_BTN[0], CLOSE_BTN[1], 15, (1, 1, 1, 1) if dark else ink, 6, p['close_hover'])
    # title strip
    rrect(c, -122, top + 268, 244, 50, 14)
    src(c, (1, 1, 1, 0.8) if not dark else (0, 0, 0, 0.55))
    c.fill()
    c.save()
    rrect(c, -122, top + 268, 244, 50, 14)
    c.clip()
    text(c, spec.get('title', spec['role']), -110, top + 302, 28, 'Segoe UI', bold=True,
         col='#39ff7a' if dark else '#20232e')
    c.restore()
    _face(c, spec, p, t, top, g, dark)
    _accessories(c, spec, p, t, top, g)
    # ---- arms
    if p['arms']:
        for side, ang in ((-1, p['arm_l']), (1, p['arm_r'])):
            wave = p['wave'] * math.sin(t * 14) * 0.35 if side == 1 else 0
            ang = ang + wave
            # angle in radians from hanging down; positive raises the arm outward
            sx, sy = side * 142, top + 205
            L = 150
            hx = sx + side * math.sin(ang) * L
            hy = sy + math.cos(ang) * L
            mx = sx + side * 60 * math.cos(ang * 0.5)
            my = (sy + hy) / 2 + 25
            c.move_to(sx, sy)
            c.curve_to(mx, sy + 10, mx, my, hx, hy)
            src(c, ink)
            c.set_line_width(13)
            c.stroke()
            circle(c, hx, hy, 24)
            fill_stroke(c, _c('#ffffff', g), ink, 5)
            if 'mug' in spec.get('acc', []) and side == -1:
                rrect(c, hx - 28, hy - 44, 44, 52, 8)
                fill_stroke(c, _c('#e04040', g), ink, 5)
                c.new_sub_path(); c.arc(hx - 32, hy - 20, 12, PI * 0.5, PI * 1.5)
                src(c, ink); c.set_line_width(5); c.stroke()
                for k in range(2):
                    c.move_to(hx - 16 + k * 14, hy - 54)
                    c.curve_to(hx - 26 + k * 14, hy - 70, hx - 6 + k * 14, hy - 80, hx - 16 + k * 14,
                               hy - 96 - 6 * math.sin(t * 5 + k))
                    src(c, (1, 1, 1, 0.6)); c.set_line_width(4); c.stroke()
    if a < 1:
        c.pop_group_to_source()
        c.paint_with_alpha(a)
    c.restore()


def _eye(c, ex, ey, p, t, kind, g, side):
    blink = clamp(p['blink'])
    lx, ly = p['look']
    ink = OUTLINE
    if kind == 'x':
        src(c, ink)
        c.set_line_width(9)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(ex - 22, ey - 22); c.line_to(ex + 22, ey + 22)
        c.move_to(ex + 22, ey - 22); c.line_to(ex - 22, ey + 22)
        c.stroke()
        return
    ry = 44 * (1 - blink)
    if kind == 'sleepy':
        ry = 44 * max(0.0, 0.35 - blink * 0.35)
    ellipse(c, ex, ey, 36, max(ry, 2))
    fill_stroke(c, _c('#ffffff', g), ink, 6)
    if ry < 6:
        return
    c.save()
    ellipse(c, ex, ey, 36, ry)
    c.clip()
    if kind == 'spiral':
        src(c, ink)
        c.set_line_width(5)
        rot = t * 9 * side
        c.new_path()
        for i in range(60):
            aa = rot + i * 0.35
            rr = i * 0.55
            px, py = ex + math.cos(aa) * rr, ey + math.sin(aa) * rr
            if i == 0:
                c.move_to(px, py)
            else:
                c.line_to(px, py)
        c.stroke()
    elif kind == 'evil':
        circle(c, ex + lx * 14, ey + ly * 14 + 6, 13)
        src(c, '#ff1e3c')
        c.fill()
    elif kind == 'tiny':
        circle(c, ex + lx * 18, ey + ly * 20, 7)
        src(c, ink)
        c.fill()
    else:
        pr = 17
        circle(c, ex + lx * 14, ey + ly * 18 + 4, pr)
        src(c, ink)
        c.fill()
        circle(c, ex + lx * 14 + 6, ey + ly * 18 - 4, 6)
        src(c, '#ffffff')
        c.fill()
    if kind == 'sleepy':
        pass
    c.restore()


def _face(c, spec, p, t, top, g, dark):
    ink = OUTLINE
    kind = p['eyes'] or spec.get('eyes', 'normal')
    if p['expr'] == 'dead':
        kind = 'x'
    ey = top + 150
    shades = 'shades' in spec.get('acc', []) and p['expr'] not in ('dead',)
    if not shades:
        for side in (-1, 1):
            _eye(c, side * 58, ey, p, t, kind, g, side)
        if p['brow'] != 0 or p['expr'] in ('scared', 'angry', 'evil'):
            br = p['brow']
            for side in (-1, 1):
                if p['expr'] == 'angry' or p['expr'] == 'evil':
                    c.move_to(side * 90, ey - 62)
                    c.line_to(side * 28, ey - 44)
                else:
                    c.move_to(side * 88, ey - 58 - br * 16)
                    c.curve_to(side * 70, ey - 72 - br * 20, side * 45, ey - 72 - br * 20, side * 30, ey - 60 - br * 12)
                src(c, ink)
                c.set_line_width(8)
                c.set_line_cap(cairo.LINE_CAP_ROUND)
                c.stroke()
    else:
        rrect(c, -106, ey - 34, 96, 62, 20)
        rrect(c, 10, ey - 34, 96, 62, 20)
        fill_stroke(c, '#16131f', ink, 6)
        c.move_to(-10, ey - 20); c.line_to(10, ey - 20)
        src(c, ink); c.set_line_width(7); c.stroke()
        c.move_to(-90, ey - 22); c.line_to(-60, ey - 22)
        c.move_to(26, ey - 22); c.line_to(56, ey - 22)
        src(c, (1, 1, 1, 0.5)); c.set_line_width(5); c.stroke()
    if p['blush'] > 0:
        for side in (-1, 1):
            ellipse(c, side * 92, ey + 58, 22, 12)
            src(c, (1, 0.35, 0.5, 0.5 * p['blush']))
            c.fill()
    # mouth
    my = top + 228
    m = clamp(p['mouth'])
    e = p['expr']
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    if e == 'dead':
        c.move_to(-34, my + 6)
        for i in range(1, 9):
            c.line_to(-34 + i * 8.5, my + (8 if i % 2 else -2))
        src(c, ink); c.set_line_width(6); c.stroke()
    elif e in ('scared',) or (e == 'scream'):
        ellipse(c, 0, my + 6, 22 + m * 8, 18 + m * 22)
        fill_stroke(c, '#5a0f22', ink, 6)
    elif e == 'flat':
        c.move_to(-30, my + 4); c.line_to(30, my + 4)
        src(c, ink); c.set_line_width(7); c.stroke()
    elif e == 'frown':
        c.move_to(-34, my + 14); c.curve_to(-14, my - 10, 14, my - 10, 34, my + 14)
        src(c, ink); c.set_line_width(7); c.stroke()
    elif e == 'evil':
        c.move_to(-60, my - 10); c.curve_to(-30, my + 30, 30, my + 30, 60, my - 10)
        c.close_path()
        fill_stroke(c, '#1a0a12', ink, 6)
        for i in range(-2, 3):
            c.move_to(i * 18 - 7, my - 4); c.line_to(i * 18, my + 8); c.line_to(i * 18 + 7, my - 4)
        src(c, '#ffffff'); c.fill()
    else:  # happy / talking
        if m < 0.05:
            c.move_to(-40, my - 4)
            c.curve_to(-20, my + 22, 20, my + 22, 40, my - 4)
            src(c, ink); c.set_line_width(7); c.stroke()
        else:
            h = 12 + m * 46
            c.move_to(-44, my - 6)
            c.curve_to(-40, my + h, 40, my + h, 44, my - 6)
            c.curve_to(20, my - 2, -20, my - 2, -44, my - 6)
            c.close_path()
            fill_stroke(c, '#5a0f22', ink, 6)
            c.save()
            c.move_to(-44, my - 6)
            c.curve_to(-40, my + h, 40, my + h, 44, my - 6)
            c.close_path()
            c.clip()
            ellipse(c, 0, my + h * 0.75, 26, 14 + m * 6)
            src(c, '#ff6f91'); c.fill()
            c.rectangle(-30, my - 8, 60, 12)
            src(c, '#ffffff'); c.fill()
            c.restore()
    if p['sweat'] > 0:
        sx, sy = 120, top + 110 + (t * 80 % 60)
        c.move_to(sx, sy - 22)
        c.curve_to(sx + 16, sy, sx + 14, sy + 16, sx, sy + 16)
        c.curve_to(sx - 14, sy + 16, sx - 16, sy, sx, sy - 22)
        fill_stroke(c, (0.55, 0.85, 1, p['sweat']), ink, 4, p['sweat'])


def _accessories(c, spec, p, t, top, g):
    ink = OUTLINE
    acc = spec.get('acc', [])
    if 'bow' in acc:
        c.save()
        c.translate(96, top - 8)
        c.rotate(0.25)
        for side in (-1, 1):
            c.move_to(0, 0)
            c.curve_to(side * 40, -40, side * 70, -10, side * 62, 18)
            c.curve_to(side * 50, 34, side * 20, 20, 0, 0)
            fill_stroke(c, _c('#ff4f9a', g), ink, 5)
        circle(c, 0, 4, 14)
        fill_stroke(c, _c('#ff2f7f', g), ink, 5)
        c.restore()
    if 'chef_hat' in acc:
        rrect(c, -86, top - 46, 172, 58, 10)
        fill_stroke(c, _c('#ffffff', g), ink, 6)
        for i, (dx, dy, r) in enumerate([(-70, -80, 48), (0, -118, 62), (70, -80, 48)]):
            circle(c, dx, top + dy, r)
            fill_stroke(c, _c('#ffffff', g), ink, 6)
        rrect(c, -84, top - 44, 168, 40, 8)
        src(c, _c('#ffffff', g)); c.fill()
    if 'mustache' in acc:
        my = top + 196
        for side in (-1, 1):
            c.move_to(0, my)
            c.curve_to(side * 30, my - 26, side * 70, my - 20, side * 86, my - 2)
            c.curve_to(side * 100, my - 18, side * 104, my - 36, side * 90, my - 40)
            c.curve_to(side * 110, my - 30, side * 110, my + 14, side * 80, my + 18)
            c.curve_to(side * 50, my + 20, side * 20, my + 12, 0, my)
            fill_stroke(c, _c('#4a2a12', g), ink, 5)
    if 'antenna' in acc:
        c.move_to(0, top); c.curve_to(10, top - 50, -20, top - 70, 0, top - 110)
        src(c, ink); c.set_line_width(7); c.stroke()
        circle(c, 0, top - 118, 16 + 4 * math.sin(t * 10))
        fill_stroke(c, _c('#ff4fd8', g), ink, 5)
    if 'frazzle' in acc:
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(9):
            x0 = -120 + i * 30
            c.move_to(x0, top + 6)
            wob = math.sin(t * 13 + i) * 8
            c.curve_to(x0 - 20 + wob, top - 30, x0 + 20 - wob, top - 50, x0 + hsign(i, 4) * 25, top - 70 - hrand(i, 5) * 30)
            src(c, _c('#2f1b4a', g)); c.set_line_width(12); c.stroke()
    if 'glasses' in acc:
        for side in (-1, 1):
            circle(c, side * 58, top + 150, 50)
            src(c, ink); c.set_line_width(8); c.stroke()
        c.move_to(-10, top + 146); c.line_to(10, top + 146)
        src(c, ink); c.set_line_width(8); c.stroke()
    if 'monocle' in acc:
        circle(c, 58, top + 150, 50)
        src(c, _c('#c9a227', g)); c.set_line_width(8); c.stroke()
        c.move_to(104, top + 170); c.curve_to(130, top + 240, 110, top + 290, 130, top + 330)
        src(c, _c('#c9a227', g)); c.set_line_width(3); c.stroke()
    if 'beard' in acc:
        by = top + 205
        c.move_to(-100, by - 20)
        for i in range(11):
            ang = PI * i / 10
            r = 110 + (12 if i % 2 else 0)
            c.line_to(-math.cos(ang) * 100, by + math.sin(ang) * r * 0.9)
        c.line_to(100, by - 20)
        c.curve_to(60, by + 20, -60, by + 20, -100, by - 20)
        c.close_path()
        fill_stroke(c, _c('#f4f1ea', g), ink, 6)
        # mouth hole handled by redrawing mouth small
        ellipse(c, 0, by + 22, 26, 8 + 16 * clamp(p['mouth']))
        fill_stroke(c, '#5a0f22', ink, 5)
    if 'cobweb' in acc:
        c.save()
        tab_path(c, -150, top, 300, 360, 52, 30)
        c.clip()
        src(c, (1, 1, 1, 0.8))
        c.set_line_width(2.5)
        ox, oy = 150, top
        for i in range(6):
            aa = PI / 2 + i * (PI / 2) / 5
            c.move_to(ox, oy); c.line_to(ox + math.cos(aa) * 130, oy + math.sin(aa) * 130)
        for r in (30, 60, 95, 125):
            c.new_sub_path(); c.arc(ox, oy, r, PI / 2, PI)
        c.stroke()
        c.restore()
    if 'nightcap' in acc:
        c.move_to(-120, top + 30)
        c.curve_to(-80, top - 60, 60, top - 90, 150 + 10 * math.sin(t * 2), top - 20)
        c.curve_to(110, top - 20, 60, top - 10, 120, top + 30)
        c.close_path()
        fill_stroke(c, _c('#3d5bd9', g), ink, 6)
        rrect(c, -126, top + 12, 250, 36, 18)
        fill_stroke(c, _c('#ffffff', g), ink, 5)
        circle(c, 158 + 10 * math.sin(t * 2), top - 14, 22)
        fill_stroke(c, _c('#ffffff', g), ink, 5)
        for k in range(3):
            ph = (t * 0.6 + k / 3) % 1
            text(c, 'z', 170 + ph * 90, top + 60 - ph * 160, 30 + ph * 40, 'Comic Sans MS', bold=True,
                 col='#ffffff', outline=OUTLINE, ow=3, alpha=1 - ph)
    if 'hood' in acc:
        c.move_to(-170, top + 180)
        c.curve_to(-190, top - 60, 190, top - 60, 170, top + 180)
        c.curve_to(140, top + 20, -140, top + 20, -170, top + 180)
        c.close_path()
        fill_stroke(c, _c('#3b3f4a', g), OUTLINE, 6)
        c.move_to(-40, top + 20); c.line_to(-46, top + 90)
        c.move_to(40, top + 20); c.line_to(46, top + 90)
        src(c, '#dddddd'); c.set_line_width(5); c.stroke()
    if 'hardhat' in acc:
        c.move_to(-120, top + 6)
        c.curve_to(-120, top - 110, 120, top - 110, 120, top + 6)
        c.close_path()
        fill_stroke(c, _c('#ff9f1c', g), ink, 6)
        rrect(c, -160, top - 4, 320, 26, 12)
        fill_stroke(c, _c('#ff9f1c', g), ink, 6)
        circle(c, 0, top - 68, 20)
        fill_stroke(c, _c('#fff26a', g), ink, 4)
    if 'floaties' in acc:
        for side in (-1, 1):
            ellipse(c, side * 160, top + 200, 34, 44)
            fill_stroke(c, _c('#ff5050', g), ink, 6)
            ellipse(c, side * 160, top + 200, 12, 18)
            src(c, _c(CAST['justincase']['col'], g)); c.fill()
    if 'tie' in acc:
        c.move_to(-16, top + 318); c.line_to(16, top + 318); c.line_to(26, top + 344)
        c.line_to(0, top + 380); c.line_to(-26, top + 344); c.close_path()
        fill_stroke(c, _c('#d6284b', g), ink, 5)


# ---------------------------------------------------------------- villain

def draw_restorer(c, x, y, s=1.0, t=0.0, glow=1.0, eyes=1.0, arm=0.0, alpha=1.0, silhouette=0.0, spin=1.0):
    """Tall trench-coat figure whose head is a restore arrow. Feet at (x,y), ~820 tall at s=1."""
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    if alpha < 1:
        c.push_group()
    coat = mix('#34323f', '#050508', silhouette)
    ink = OUTLINE
    # legs
    for side in (-1, 1):
        rrect(c, side * 40 - 22, -150, 44, 150, 10)
        fill_stroke(c, mix('#1b1a22', '#000000', silhouette), ink, 6)
        ellipse(c, side * 50, -6, 46, 18)
        fill_stroke(c, '#0b0b10', ink, 5)
    # coat
    c.move_to(-110, -560)
    c.curve_to(-150, -520, -170, -300, -150, -120)
    c.line_to(150, -120)
    c.curve_to(170, -300, 150, -520, 110, -560)
    c.close_path()
    fill_stroke(c, coat, ink, 7)
    # coat details
    if silhouette < 0.9:
        src(c, (0, 0, 0, 0.35))
        c.set_line_width(5)
        c.move_to(0, -540); c.line_to(0, -120); c.stroke()
        for i in range(3):
            circle(c, 22, -470 + i * 90, 8)
            c.fill()
        c.move_to(-110, -350); c.line_to(150, -330); c.set_line_width(22)
        src(c, mix('#5a4a3a', '#000000', silhouette)); c.stroke()
    # collar
    for side in (-1, 1):
        c.move_to(side * 20, -560); c.line_to(side * 130, -600); c.line_to(side * 110, -500); c.close_path()
        fill_stroke(c, shade(coat, 0.8), ink, 6)
    # arm with giant cursor
    c.save()
    c.translate(140, -500)
    c.rotate(-0.2 - arm * 1.1)
    rrect(c, -26, 0, 52, 240, 24)
    fill_stroke(c, coat, ink, 6)
    # held by the tail: the stem sits in the hand and the tip points away from him
    c.translate(-10, 230)
    c.rotate(PI)
    cs = 4.2
    gfx.cursor(c, -gfx.ARROW_TAIL[0] * cs, -gfx.ARROW_TAIL[1] * cs, cs, 'arrow', 1.0, fill='#f5f5f5')
    c.restore()
    # head: restore ring
    hx, hy = 0, -700
    rot = t * 2.2 * spin
    for i in range(5, 0, -1):
        src(c, (0.18, 0.85, 1.0, 0.07 * glow))
        c.set_line_width(40 + i * 22)
        c.new_sub_path(); c.arc(hx, hy, 110, rot, rot + PI * 1.6); c.stroke()
    circle(c, hx, hy, 100)
    src(c, '#07070c')
    c.fill()
    src(c, mix('#2fd8ff', '#0a2a35', 1 - glow))
    c.set_line_width(34)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.new_sub_path(); c.arc(hx, hy, 110, rot, rot + PI * 1.6); c.stroke()
    ex, ey = hx + math.cos(rot) * 110, hy + math.sin(rot) * 110
    c.save()
    c.translate(ex, ey)
    c.rotate(rot)
    c.move_to(-50, 10); c.line_to(0, -58); c.line_to(52, 12); c.close_path()
    src(c, mix('#2fd8ff', '#0a2a35', 1 - glow))
    c.fill()
    c.restore()
    if eyes > 0:
        for side in (-1, 1):
            c.save()
            c.translate(hx + side * 36, hy - 4)
            c.rotate(side * 0.35)
            ellipse(c, 0, 0, 26, 9 * eyes)
            src(c, (1, 0.1, 0.2, 1))
            c.fill()
            c.restore()
            gfx.radial_glow(c, hx + side * 36, hy - 4, 60, (1, 0.1, 0.2, 0.6 * eyes))
    if alpha < 1:
        c.pop_group_to_source()
        c.paint_with_alpha(alpha)
    c.restore()


# ---------------------------------------------------------------- the user (cursor character)

def draw_user(c, x, y, s=1.0, t=0.0, mouth=0.0, expr='happy', look=(0, 0), blink=0.0, tilt=0.0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.rotate(tilt)
    gfx.cursor(c, -150, -200, 11, 'arrow', 1.0)
    p = pose_default()
    p.update(mouth=mouth, expr=expr, look=look, blink=blink)
    c.translate(-150, -200)
    for side in (-1, 1):
        _eye(c, 62 + side * 34, 170, dict(p), t, 'normal', 0, side)
    my = 240
    if mouth < 0.05 and expr == 'happy':
        c.move_to(40, my); c.curve_to(55, my + 18, 80, my + 18, 95, my)
        src(c, OUTLINE); c.set_line_width(6); c.stroke()
    elif expr == 'frown':
        c.move_to(40, my + 14); c.curve_to(55, my - 4, 80, my - 4, 95, my + 14)
        src(c, OUTLINE); c.set_line_width(6); c.stroke()
    else:
        ellipse(c, 68, my + 6, 26, 8 + 22 * mouth)
        fill_stroke(c, '#5a0f22', OUTLINE, 5)
    c.restore()


# ---------------------------------------------------------------- Ramsey the RAM hamster (boiling-line cartoon)

def _boil(i, t, amt=3.0):
    q = int(t * 10)
    return hsign(i, q, 7) * amt


def draw_hamster(c, x, y, s=1.0, t=0.0, run=0.0, sweat=0.0, eyes='normal', mouth=0.3, dizzy=0.0):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    ink = OUTLINE
    b = lambda i: _boil(i, t)
    ph = run * TAU
    # feet
    for i, side in enumerate((-1, 1)):
        fx = side * 60 + math.sin(ph + side) * 50
        fy = 115 + math.cos(ph + side) * 12
        ellipse(c, fx + b(i), fy + b(i + 10), 30, 16)
        fill_stroke(c, '#ffb8c6', ink, 6)
    # body
    c.move_to(-150 + b(1), 20 + b(2))
    c.curve_to(-160 + b(3), -120 + b(4), 160 + b(5), -130 + b(6), 150 + b(7), 20 + b(8))
    c.curve_to(150 + b(9), 130 + b(10), -150 + b(11), 130 + b(12), -150 + b(1), 20 + b(2))
    c.close_path()
    fill_stroke(c, '#e8a45a', ink, 8)
    c.move_to(-80 + b(13), 40)
    c.curve_to(-80, 120, 80, 120, 80 + b(14), 40)
    c.curve_to(60, 0, -60, 0, -80 + b(13), 40)
    fill_stroke(c, '#fff1dc', None)
    # ears
    for i, side in enumerate((-1, 1)):
        circle(c, side * 95 + b(20 + i), -95 + b(22 + i), 36)
        fill_stroke(c, '#e8a45a', ink, 7)
        circle(c, side * 95 + b(20 + i), -95 + b(22 + i), 18)
        fill_stroke(c, '#ffb8c6', None)
    # eyes
    for i, side in enumerate((-1, 1)):
        ex, ey = side * 50 + b(30 + i), -40 + b(32 + i)
        if eyes == 'x' or dizzy > 0.5:
            src(c, ink); c.set_line_width(8)
            if dizzy > 0.5:
                c.new_path()
                for k in range(40):
                    aa = t * 12 * side + k * 0.45
                    rr = k * 0.7
                    px, py = ex + math.cos(aa) * rr, ey + math.sin(aa) * rr
                    (c.move_to if k == 0 else c.line_to)(px, py)
                c.stroke()
            else:
                c.move_to(ex - 16, ey - 16); c.line_to(ex + 16, ey + 16)
                c.move_to(ex + 16, ey - 16); c.line_to(ex - 16, ey + 16); c.stroke()
        else:
            circle(c, ex, ey, 26)
            fill_stroke(c, '#ffffff', ink, 6)
            circle(c, ex + 4, ey + 4, 13)
            src(c, ink); c.fill()
            circle(c, ex + 8, ey - 2, 5)
            src(c, '#ffffff'); c.fill()
    # cheeks + nose + mouth
    for side in (-1, 1):
        ellipse(c, side * 95, 5, 30, 20)
        src(c, (1, 0.5, 0.6, 0.6)); c.fill()
    ellipse(c, 0, -2, 12, 9)
    fill_stroke(c, '#ff6f91', ink, 4)
    c.move_to(-20, 16); c.curve_to(-10, 26 + mouth * 20, 0, 20, 0, 12)
    c.curve_to(0, 20, 10, 26 + mouth * 20, 20, 16)
    src(c, ink); c.set_line_width(5); c.stroke()
    if mouth > 0.3:
        rrect(c, -9, 18, 18, 18 + mouth * 6, 3)
        fill_stroke(c, '#ffffff', ink, 3)
    if sweat > 0:
        for k in range(3):
            ph2 = (t * 1.5 + k / 3) % 1
            sx = 150 + k * 20
            sy = -90 + ph2 * 120
            c.move_to(sx, sy - 18); c.curve_to(sx + 12, sy, sx + 10, sy + 12, sx, sy + 12)
            c.curve_to(sx - 10, sy + 12, sx - 12, sy, sx, sy - 18)
            fill_stroke(c, (0.55, 0.85, 1, sweat), ink, 3, sweat * (1 - ph2))
    if dizzy > 0:
        for k in range(4):
            aa = t * 6 + k * TAU / 4
            gfx.star_path(c, math.cos(aa) * 150, -150 + math.sin(aa) * 30, 26, 11)
            fill_stroke(c, '#ffe14d', ink, 4, dizzy)
    c.restore()
