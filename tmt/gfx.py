"""Cairo drawing primitives. All coordinates are in 1920x1080 logical units."""
import math
import cairo
from .util import PI, TAU, clamp, lerp, hrand, hsign, smooth, ease_out

OUTLINE = (0.11, 0.10, 0.18, 1.0)

_col_cache = {}


def hexc(h, a=1.0):
    key = (h, a)
    v = _col_cache.get(key)
    if v is None:
        s = h.lstrip('#')
        if len(s) == 3:
            s = ''.join(ch * 2 for ch in s)
        v =(int(s[0:2], 16) / 255, int(s[2:4], 16) / 255, int(s[4:6], 16) / 255, a)
        _col_cache[key] = v
    return v


def rgba(col, a=None):
    if isinstance(col, str):
        col = hexc(col)
    if len(col) == 3:
        col = (col[0], col[1], col[2], 1.0)
    if a is not None:
        col = (col[0], col[1], col[2], col[3] * a)
    return col


def src(c, col, a=None):
    c.set_source_rgba(*rgba(col, a))


def mix(c1, c2, t):
    a, b = rgba(c1), rgba(c2)
    return tuple(lerp(a[i], b[i], t) for i in range(4))


def shade(col, f):
    """f<1 darker, f>1 lighter."""
    r, g, b, a = rgba(col)
    if f < 1:
        return (r * f, g * f, b * f, a)
    k = f - 1
    return (r + (1 - r) * k, g + (1 - g) * k, b + (1 - b) * k, a)


def desat(col, amt):
    r, g, b, a = rgba(col)
    y = 0.3 * r + 0.59 * g + 0.11 * b
    return (lerp(r, y, amt), lerp(g, y, amt), lerp(b, y, amt), a)


def hsv(h, s, v, a=1.0):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]
    return (r, g, b, a)


# ---------------------------------------------------------------- shapes

def rrect(c, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -PI / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, PI / 2)
    c.arc(x + r, y + h - r, r, PI / 2, PI)
    c.arc(x + r, y + r, r, PI, 1.5 * PI)
    c.close_path()


def tab_path(c, x, y, w, h, r=None, flare=None):
    """Browser-tab silhouette. (x,y) top-left of body, flares stick out at the bottom."""
    r = r if r is not None else min(w, h) * 0.2
    r = min(r, w / 2, h / 2)
    f = flare if flare is not None else r * 0.6
    c.new_sub_path()
    c.move_to(x - f, y + h)
    c.curve_to(x - f * 0.2, y + h, x, y + h - f * 0.2, x, y + h - f)
    c.line_to(x, y + r)
    c.arc(x + r, y + r, r, PI, 1.5 * PI)
    c.line_to(x + w - r, y)
    c.arc(x + w - r, y + r, r, 1.5 * PI, TAU)
    c.line_to(x + w, y + h - f)
    c.curve_to(x + w, y + h - f * 0.2, x + w + f * 0.2, y + h, x + w + f, y + h)
    c.close_path()


def star_path(c, cx, cy, r1, r2, n=5, rot=-PI / 2):
    c.new_sub_path()
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = rot + i * PI / n
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        if i == 0:
            c.move_to(x, y)
        else:
            c.line_to(x, y)
    c.close_path()


def fill_stroke(c, fill, stroke=OUTLINE, lw=6.0, alpha=1.0):
    if fill is not None:
        src(c, fill, alpha)
        if stroke is not None:
            c.fill_preserve()
        else:
            c.fill()
    if stroke is not None:
        src(c, stroke, alpha)
        c.set_line_width(lw)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.stroke()


def circle(c, x, y, r):
    c.new_sub_path()
    c.arc(x, y, r, 0, TAU)


def ellipse(c, x, y, rx, ry):
    c.save()
    c.translate(x, y)
    c.scale(max(rx, 1e-3), max(ry, 1e-3))
    c.new_sub_path()
    c.arc(0, 0, 1, 0, TAU)
    c.restore()


def sparkle(c, x, y, r, a=1.0, col=(1, 1, 1, 1), rot=0.0):
    if a <= 0 or r <= 0:
        return
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, r * 0.9)
    g.add_color_stop_rgba(0, col[0], col[1], col[2], 0.9 * a)
    g.add_color_stop_rgba(1, col[0], col[1], col[2], 0)
    c.set_source(g)
    circle(c, 0, 0, r)
    c.fill()
    src(c, col, a)
    c.new_path()
    for ang in (0, PI / 2):
        c.save()
        c.rotate(ang)
        c.move_to(-r, 0)
        c.curve_to(-r * 0.1, -r * 0.05, -r * 0.05, -r * 0.1, 0, -r * 0.0)
        c.restore()
    c.move_to(0, -r)
    c.curve_to(r * 0.08, -r * 0.08, r * 0.08, -r * 0.08, r, 0)
    c.curve_to(r * 0.08, r * 0.08, r * 0.08, r * 0.08, 0, r)
    c.curve_to(-r * 0.08, r * 0.08, -r * 0.08, r * 0.08, -r, 0)
    c.curve_to(-r * 0.08, -r * 0.08, -r * 0.08, -r * 0.08, 0, -r)
    c.close_path()
    c.fill()
    c.restore()


# ---------------------------------------------------------------- text

_SL = {False: cairo.FONT_SLANT_NORMAL, True: cairo.FONT_SLANT_ITALIC}
_WT = {False: cairo.FONT_WEIGHT_NORMAL, True: cairo.FONT_WEIGHT_BOLD}


def set_font(c, font, size, bold=False, italic=False):
    c.select_font_face(font, _SL[italic], _WT[bold])
    c.set_font_size(size)


def text_width(c, s, size, font='Segoe UI', bold=False, italic=False):
    set_font(c, font, size, bold, italic)
    return c.text_extents(s).x_advance


def text(c, s, x, y, size, font='Segoe UI', bold=False, italic=False, col='#ffffff',
         align='l', valign='base', outline=None, ow=0.0, shadow=None, soff=(5, 5),
         alpha=1.0, max_w=None, fill_pattern=None, extrude=None, extrude_n=0, extrude_d=(2, 2)):
    """Draw text. align l/c/r, valign base/mid/top. Returns (width, height)."""
    if not s or alpha <= 0:
        return (0, 0)
    set_font(c, font, size, bold, italic)
    ext = c.text_extents(s)
    if max_w and ext.x_advance > max_w:
        size = size * max_w / ext.x_advance
        c.set_font_size(size)
        ext = c.text_extents(s)
    dx = {'l': 0, 'c': -ext.x_advance / 2, 'r': -ext.x_advance}[align]
    if valign == 'mid':
        dy = -(ext.y_bearing + ext.height / 2)
    elif valign == 'top':
        dy = -ext.y_bearing
    else:
        dy = 0
    ox, oy = x + dx, y + dy
    if shadow is not None:
        c.move_to(ox + soff[0], oy + soff[1])
        c.text_path(s)
        if outline is not None and ow > 0:
            src(c, shadow, alpha)
            c.set_line_width(ow * 2)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            c.stroke_preserve()
        src(c, shadow, alpha)
        c.fill()
    if extrude is not None and extrude_n > 0:
        for i in range(extrude_n, 0, -1):
            c.move_to(ox + extrude_d[0] * i, oy + extrude_d[1] * i)
            c.text_path(s)
            src(c, extrude, alpha)
            if outline is not None and ow > 0:
                c.set_line_width(ow * 2)
                c.set_line_join(cairo.LINE_JOIN_ROUND)
                c.stroke_preserve()
            c.fill()
    c.move_to(ox, oy)
    c.text_path(s)
    if outline is not None and ow > 0:
        src(c, outline, alpha)
        c.set_line_width(ow * 2)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke_preserve()
    if fill_pattern is not None:
        c.set_source(fill_pattern)
        if alpha < 1:
            c.clip()
            c.paint_with_alpha(alpha)
            c.reset_clip()
        else:
            c.fill()
    else:
        src(c, col, alpha)
        c.fill()
    c.new_path()
    return (ext.x_advance, ext.height)


def chrome_pattern(y0, y1, style='sunset'):
    g = cairo.LinearGradient(0, y0, 0, y1)
    if style == 'sunset':
        stops = [(0, '#ffffff'), (0.22, '#bfe9ff'), (0.48, '#3a6fd8'), (0.5, '#1b1f4a'),
                 (0.53, '#ff5fa2'), (0.75, '#ffb347'), (1, '#fff3a0')]
    elif style == 'gold':
        stops = [(0, '#fffbe0'), (0.4, '#ffd24a'), (0.5, '#a8620a'), (0.55, '#ffcf3d'), (1, '#fff2b0')]
    elif style == 'blood':
        stops = [(0, '#ff9a9a'), (0.45, '#c20018'), (0.5, '#3a0006'), (0.6, '#a0000f'), (1, '#ff3030')]
    elif style == 'space':
        stops = [(0, '#ffffff'), (0.3, '#9ff3ff'), (0.49, '#2b6cff'), (0.51, '#0b0b30'),
                 (0.6, '#b44cff'), (1, '#ffd6ff')]
    else:
        stops = [(0, '#ffffff'), (0.5, '#888888'), (1, '#ffffff')]
    for p, h in stops:
        r, gg, b, a = hexc(h)
        g.add_color_stop_rgba(p, r, gg, b, a)
    return g


# ---------------------------------------------------------------- icons

def favicon(c, kind, cx, cy, size, t=0.0, col=None, bg=True):
    """Small generic icon glyphs."""
    s = size / 2
    c.save()
    c.translate(cx, cy)
    if bg:
        rrect(c, -s, -s, size, size, size * 0.24)
        fill_stroke(c, col or '#ffffff', OUTLINE, max(1.5, size * 0.06))
    ink = OUTLINE
    lw = max(1.2, size * 0.09)
    c.set_line_width(lw)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    k = s * 0.62
    if kind == 'plus':
        src(c, '#ff4f9a')
        c.set_line_width(lw * 1.6)
        c.move_to(-k, 0); c.line_to(k, 0); c.move_to(0, -k); c.line_to(0, k); c.stroke()
    elif kind == 'fork':
        src(c, ink)
        c.move_to(0, -k); c.line_to(0, k); c.stroke()
        for dx in (-k * 0.5, 0, k * 0.5):
            c.move_to(dx, -k); c.line_to(dx, -k * 0.2); c.stroke()
        c.move_to(-k * 0.5, -k * 0.2); c.curve_to(-k * 0.5, k * 0.1, k * 0.5, k * 0.1, k * 0.5, -k * 0.2); c.stroke()
    elif kind == 'spinner':
        for i in range(8):
            a = i * TAU / 8 + t * TAU * 1.3
            fade = ((i / 8.0) + (t * 1.3) % 1.0) % 1.0
            src(c, (0.2, 0.45, 1.0, 0.25 + 0.75 * (i / 8)))
            circle(c, math.cos(a) * k * 0.8, math.sin(a) * k * 0.8, lw * 0.9)
            c.fill()
    elif kind == 'envelope':
        rrect(c, -k, -k * 0.7, 2 * k, 1.4 * k, k * 0.12)
        fill_stroke(c, '#fff7e0', ink, lw * 0.8)
        c.move_to(-k, -k * 0.7); c.line_to(0, k * 0.1); c.line_to(k, -k * 0.7)
        src(c, ink); c.set_line_width(lw * 0.8); c.stroke()
    elif kind == 'speaker':
        c.move_to(-k, -k * 0.35); c.line_to(-k * 0.45, -k * 0.35); c.line_to(k * 0.1, -k * 0.85)
        c.line_to(k * 0.1, k * 0.85); c.line_to(-k * 0.45, k * 0.35); c.line_to(-k, k * 0.35); c.close_path()
        fill_stroke(c, ink, ink, lw * 0.5)
        src(c, ink)
        for i, rr in enumerate((0.45, 0.8)):
            ph = 0.5 + 0.5 * math.sin(t * 12 - i)
            src(c, OUTLINE, 0.4 + 0.6 * ph)
            c.new_sub_path(); c.arc(k * 0.15, 0, k * rr + k * 0.2, -0.8, 0.8); c.stroke()
    elif kind == 'cart':
        src(c, ink)
        c.move_to(-k, -k * 0.7); c.line_to(-k * 0.6, -k * 0.7); c.line_to(-k * 0.3, k * 0.35)
        c.line_to(k * 0.8, k * 0.35); c.line_to(k, -k * 0.4); c.line_to(-k * 0.5, -k * 0.4); c.stroke()
        circle(c, -k * 0.2, k * 0.72, lw); circle(c, k * 0.6, k * 0.72, lw); c.fill()
    elif kind == 'check':
        src(c, '#1e9e4a')
        c.set_line_width(lw * 1.5)
        c.move_to(-k * 0.8, 0); c.line_to(-k * 0.2, k * 0.6); c.line_to(k * 0.9, -k * 0.7); c.stroke()
    elif kind == 'book':
        rrect(c, -k * 0.8, -k, k * 1.6, k * 2, k * 0.15)
        fill_stroke(c, '#6a7bd6', ink, lw * 0.7)
        src(c, '#ffffff')
        c.set_line_width(lw * 0.6)
        for i in range(3):
            c.move_to(-k * 0.45, -k * 0.5 + i * k * 0.45); c.line_to(k * 0.45, -k * 0.5 + i * k * 0.45)
        c.stroke()
    elif kind == 'terminal':
        rrect(c, -k, -k * 0.8, 2 * k, 1.6 * k, k * 0.15)
        fill_stroke(c, '#0d0f14', ink, lw * 0.5)
        src(c, '#39ff7a')
        c.set_line_width(lw * 0.8)
        c.move_to(-k * 0.6, -k * 0.35); c.line_to(-k * 0.2, 0); c.line_to(-k * 0.6, k * 0.35); c.stroke()
        if (t * 2) % 1 < 0.6:
            c.move_to(0, k * 0.4); c.line_to(k * 0.6, k * 0.4); c.stroke()
    elif kind == 'shield':
        c.move_to(0, -k); c.line_to(k * 0.85, -k * 0.6); c.curve_to(k * 0.85, k * 0.3, k * 0.3, k * 0.8, 0, k)
        c.curve_to(-k * 0.3, k * 0.8, -k * 0.85, k * 0.3, -k * 0.85, -k * 0.6); c.close_path()
        fill_stroke(c, '#ffb000', ink, lw * 0.7)
    elif kind == 'globe':
        circle(c, 0, 0, k)
        fill_stroke(c, '#5ec8ff', ink, lw * 0.7)
        src(c, ink); c.set_line_width(lw * 0.5)
        ellipse(c, 0, 0, k * 0.45, k); c.stroke()
        c.move_to(-k, 0); c.line_to(k, 0); c.stroke()
    elif kind == 'doc':
        c.move_to(-k * 0.7, -k); c.line_to(k * 0.35, -k); c.line_to(k * 0.7, -k * 0.6)
        c.line_to(k * 0.7, k); c.line_to(-k * 0.7, k); c.close_path()
        fill_stroke(c, '#ffffff', ink, lw * 0.6)
        src(c, '#4a7cff'); c.set_line_width(lw * 0.5)
        for i in range(3):
            c.move_to(-k * 0.4, -k * 0.3 + i * k * 0.4); c.line_to(k * 0.4, -k * 0.3 + i * k * 0.4)
        c.stroke()
    elif kind == 'restore':
        src(c, '#2fd8ff')
        c.set_line_width(lw * 1.2)
        c.new_sub_path(); c.arc(0, 0, k * 0.75, -PI * 0.3, PI * 1.45); c.stroke()
        a = -PI * 0.3
        px, py = math.cos(a) * k * 0.75, math.sin(a) * k * 0.75
        c.move_to(px + k * 0.35, py - k * 0.05); c.line_to(px, py); c.line_to(px + k * 0.05, py + k * 0.38); c.stroke()
    elif kind == 'weather':
        circle(c, -k * 0.2, -k * 0.2, k * 0.5)
        fill_stroke(c, '#ffcc33', None)
        ellipse(c, k * 0.2, k * 0.3, k * 0.75, k * 0.45)
        fill_stroke(c, '#ffffff', ink, lw * 0.5)
    elif kind == 'search':
        src(c, ink)
        circle(c, -k * 0.2, -k * 0.2, k * 0.5); c.stroke()
        c.set_line_width(lw * 1.3)
        c.move_to(k * 0.15, k * 0.15); c.line_to(k * 0.8, k * 0.8); c.stroke()
    elif kind == 'video':
        rrect(c, -k, -k * 0.7, 2 * k, 1.4 * k, k * 0.3)
        fill_stroke(c, '#ff3b3b', None)
        c.move_to(-k * 0.3, -k * 0.4); c.line_to(k * 0.45, 0); c.line_to(-k * 0.3, k * 0.4); c.close_path()
        src(c, '#ffffff'); c.fill()
    elif kind == 'heart':
        c.move_to(0, k * 0.8)
        c.curve_to(-k * 1.3, -k * 0.1, -k * 0.6, -k * 1.1, 0, -k * 0.35)
        c.curve_to(k * 0.6, -k * 1.1, k * 1.3, -k * 0.1, 0, k * 0.8)
        fill_stroke(c, '#ff4d6d', None)
    elif kind == 'map':
        c.move_to(0, k); c.curve_to(-k * 0.9, -k * 0.1, -k * 0.7, -k, 0, -k)
        c.curve_to(k * 0.7, -k, k * 0.9, -k * 0.1, 0, k); c.close_path()
        fill_stroke(c, '#34c759', ink, lw * 0.5)
        circle(c, 0, -k * 0.35, k * 0.28); src(c, '#ffffff'); c.fill()
    elif kind == 'cookie':
        circle(c, 0, 0, k)
        fill_stroke(c, '#d9a066', ink, lw * 0.5)
        src(c, '#5a3a1a')
        for i in range(5):
            circle(c, math.cos(i * 1.9) * k * 0.5, math.sin(i * 1.9) * k * 0.5, lw * 0.7)
            c.fill()
    else:  # generic letter
        text(c, kind[:1].upper(), 0, 0, size * 0.7, 'Arial Black', col=OUTLINE, align='c', valign='mid')
    c.restore()


# ---------------------------------------------------------------- UI bits

def cursor(c, x, y, s=1.0, kind='arrow', alpha=1.0, fill='#ffffff'):
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    if kind == 'arrow':
        pts = [(0, 0), (0, 36), (9, 27), (15.5, 41), (21, 38.5), (14.5, 25), (26, 25)]
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.close_path()
        fill_stroke(c, fill, '#000000', 2.6, alpha)
    elif kind == 'hand':
        c.translate(-12, -2)
        rrect(c, 8, 0, 9, 30, 4.5)
        rrect(c, 17, 13, 8, 20, 4)
        rrect(c, 25, 15, 8, 19, 4)
        rrect(c, 33, 18, 7, 17, 3.5)
        fill_stroke(c, fill, '#000000', 2.4, alpha)
        c.move_to(8, 26); c.line_to(1, 20); c.curve_to(-3, 24, 2, 32, 6, 38)
        c.line_to(12, 50); c.line_to(38, 50); c.curve_to(41, 42, 40, 36, 40, 33); c.line_to(8, 33); c.close_path()
        fill_stroke(c, fill, '#000000', 2.4, alpha)
    elif kind == 'wait':
        cursor(c, 0, 0, 1.0, 'arrow', alpha)
        circle(c, 30, 40, 10)
        fill_stroke(c, '#3a8bff', '#000000', 2, alpha)
    c.restore()


def close_x(c, cx, cy, r, col=OUTLINE, lw=3.0, hover=0.0, alpha=1.0):
    if hover > 0:
        circle(c, cx, cy, r * 1.5)
        src(c, (0.9, 0.2, 0.25, 0.9 * hover * alpha))
        c.fill()
        col = mix(col, '#ffffff', hover)
    src(c, col, alpha)
    c.set_line_width(lw)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(cx - r, cy - r); c.line_to(cx + r, cy + r)
    c.move_to(cx + r, cy - r); c.line_to(cx - r, cy + r)
    c.stroke()


def ui_tab(c, x, y, w, h, title='New Tab', fav='globe', active=False, col=None, t=0.0,
           alpha=1.0, close_hover=0.0, fav_col='#ffffff', text_col=None, audio=False):
    """A browser tab as seen in a tab strip. y is the tab top; bottom at y+h."""
    if w < 1:
        return
    base = col or ('#ffffff' if active else '#dfe3ec')
    r = min(h * 0.28, w * 0.3)
    tab_path(c, x, y, w, h, r, min(r * 0.7, 10))
    src(c, base, alpha)
    c.fill_preserve()
    src(c, '#9aa3b5', alpha * 0.9)
    c.set_line_width(1.5)
    c.stroke()
    fs = h * 0.5
    pad = min(h * 0.28, w * 0.12)
    if w > h * 0.8:
        favicon(c, fav, x + pad + fs / 2, y + h * 0.52, fs, t, col=fav_col)
    elif w > 6:
        favicon(c, fav, x + w / 2, y + h * 0.52, min(fs, w * 0.8), t, col=fav_col)
    tx = x + pad + fs + pad * 0.7
    avail = w - (tx - x) - (h * 0.7 if w > h * 3 else pad)
    if avail > h * 0.6 and title:
        c.save()
        c.rectangle(tx, y, avail, h)
        c.clip()
        set_font(c, 'Segoe UI', h * 0.38)
        src(c, text_col or '#1f2330', alpha)
        c.move_to(tx, y + h * 0.63)
        c.show_text(title)
        # fade-out
        g = cairo.LinearGradient(tx + avail - h * 0.6, 0, tx + avail, 0)
        bc = rgba(base)
        g.add_color_stop_rgba(0, bc[0], bc[1], bc[2], 0)
        g.add_color_stop_rgba(1, bc[0], bc[1], bc[2], alpha)
        c.set_source(g)
        c.rectangle(tx + avail - h * 0.6, y, h * 0.6, h)
        c.fill()
        c.restore()
    if w > h * 3:
        close_x(c, x + w - h * 0.42, y + h * 0.52, h * 0.13, '#4a5163', max(1.2, h * 0.05), close_hover, alpha)
    if audio and w > h * 2.2:
        favicon(c, 'speaker', x + w - h * 0.95, y + h * 0.52, h * 0.36, t, bg=False)


def tab_strip(c, x, y, w, h, tabs, t=0.0, active=0, min_w=None, max_w=420, bg='#c9cfdb', alpha=1.0,
              hover=-1, hover_amt=0.0):
    """tabs: list of (title, fav, fav_col). Tabs shrink to fit like a real browser, then overflow."""
    src(c, bg, alpha)
    c.rectangle(x, y, w, h)
    c.fill()
    n = len(tabs)
    if n == 0:
        return
    th = h * 0.8
    ty = y + h - th
    tw = min(max_w, (w - 20) / n)
    for i, tb in enumerate(tabs):
        tx = x + 10 + i * tw
        if tx > x + w:
            break
        title, fav, fcol = tb[0], tb[1], (tb[2] if len(tb) > 2 else '#ffffff')
        ui_tab(c, tx, ty, max(0.5, tw - 2), th, title, fav, active=(i == active), t=t + i * 0.13,
               alpha=alpha, fav_col=fcol, close_hover=hover_amt if i == hover else 0.0,
               audio=(len(tb) > 3 and tb[3]))


def browser_window(c, x, y, w, h, tabs, t=0.0, active=0, url='about:blank', content=None,
                   chrome_h=None, alpha=1.0, frame_col='#c9cfdb', shadow=True):
    """content(c, x, y, w, h) draws the page."""
    ch = chrome_h or max(60, h * 0.12)
    strip_h = ch * 0.55
    if shadow:
        rrect(c, x + 14, y + 20, w, h, 18)
        src(c, (0, 0, 0, 0.25 * alpha))
        c.fill()
    c.save()
    rrect(c, x, y, w, h, 16)
    c.clip()
    tab_strip(c, x, y, w, strip_h, tabs, t, active, bg=frame_col, alpha=alpha)
    # toolbar
    src(c, '#ffffff', alpha)
    c.rectangle(x, y + strip_h, w, ch - strip_h)
    c.fill()
    bh = (ch - strip_h)
    cy = y + strip_h + bh / 2
    for i, sym in enumerate(['<', '>', 'r']):
        bx = x + 26 + i * bh * 0.95
        src(c, '#5d6475', alpha)
        c.set_line_width(max(2, bh * 0.07))
        k = bh * 0.16
        if sym == '<':
            c.move_to(bx + k, cy - k); c.line_to(bx - k * 0.5, cy); c.line_to(bx + k, cy + k); c.stroke()
        elif sym == '>':
            c.move_to(bx - k, cy - k); c.line_to(bx + k * 0.5, cy); c.line_to(bx - k, cy + k); c.stroke()
        else:
            c.new_sub_path(); c.arc(bx, cy, k, -0.3, PI * 1.6); c.stroke()
    ax = x + 26 + 3 * bh * 0.95
    rrect(c, ax, cy - bh * 0.34, w - (ax - x) - 70, bh * 0.68, bh * 0.34)
    src(c, '#eef0f5', alpha)
    c.fill()
    set_font(c, 'Segoe UI', bh * 0.36)
    src(c, '#2b3040', alpha)
    c.move_to(ax + bh * 0.4, cy + bh * 0.13)
    c.show_text(url)
    for i in range(3):
        circle(c, x + w - 34, cy - bh * 0.2 + i * bh * 0.2, max(2, bh * 0.045))
        c.fill()
    # page
    src(c, '#ffffff', alpha)
    c.rectangle(x, y + ch, w, h - ch)
    c.fill()
    src(c, '#d5d9e2', alpha)
    c.rectangle(x, y + ch - 1.5, w, 1.5)
    c.fill()
    if content is not None:
        c.save()
        c.rectangle(x, y + ch, w, h - ch)
        c.clip()
        content(c, x, y + ch, w, h - ch)
        c.restore()
    c.restore()
    rrect(c, x, y, w, h, 16)
    src(c, '#8a93a6', alpha)
    c.set_line_width(2)
    c.stroke()


def dialog(c, cx, cy, w, h, title, body, buttons, t=0.0, hot=-1, press=0.0, alpha=1.0, scale=1.0):
    c.save()
    c.translate(cx, cy)
    c.scale(scale, scale)
    x, y = -w / 2, -h / 2
    rrect(c, x + 12, y + 18, w, h, 22)
    src(c, (0, 0, 0, 0.35 * alpha))
    c.fill()
    rrect(c, x, y, w, h, 22)
    fill_stroke(c, '#ffffff', '#5b6275', 3, alpha)
    favicon(c, 'restore', x + 62, y + 70, 56, t, col='#10202a')
    text(c, title, x + 110, y + 82, 40, 'Segoe UI', bold=True, col='#1c2030', alpha=alpha, max_w=w - 140)
    lines = body.split('\n') if body else []
    for i, ln in enumerate(lines):
        text(c, ln, x + 42, y + 150 + i * 42, 30, 'Segoe UI', col='#3b4152', alpha=alpha, max_w=w - 84)
    n = len(buttons)
    bw = min(230, (w - 60 - (n - 1) * 20) / max(1, n))
    bx0 = x + w - 30 - n * bw - (n - 1) * 20
    for i, b in enumerate(buttons):
        bx = bx0 + i * (bw + 20)
        by = y + h - 92
        pr = press if i == hot else 0.0
        primary = i == n - 1
        rrect(c, bx, by + pr * 4, bw, 62, 31)
        fill_stroke(c, '#1a73e8' if primary else '#eef1f7', '#1a4fa8' if primary else '#aab2c3', 2.5, alpha)
        text(c, b, bx + bw / 2, by + 31 + pr * 4, 30, 'Segoe UI', bold=True,
             col='#ffffff' if primary else '#1a73e8', align='c', valign='mid', alpha=alpha, max_w=bw - 20)
    c.restore()


def keycap(c, cx, cy, w, h, label, press=0.0, col='#f2f2f2', alpha=1.0):
    depth = 26 * (1 - press * 0.8)
    rrect(c, cx - w / 2, cy - h / 2 + 22, w, h, 26)
    src(c, (0, 0, 0, 0.35 * alpha))
    c.fill()
    rrect(c, cx - w / 2, cy - h / 2 + (26 - depth), w, h + depth * 0.2, 26)
    fill_stroke(c, shade(col, 0.62), OUTLINE, 5, alpha)
    top_y = cy - h / 2 + (26 - depth) - depth
    rrect(c, cx - w / 2, top_y + depth * 0.2, w, h, 26)
    fill_stroke(c, shade(col, 0.8), OUTLINE, 5, alpha)
    rrect(c, cx - w / 2 + w * 0.08, top_y + depth * 0.2 + h * 0.06, w * 0.84, h * 0.78, 20)
    g = cairo.LinearGradient(0, top_y, 0, top_y + h)
    a = rgba(col)
    g.add_color_stop_rgba(0, *shade(col, 1.15)[:3], alpha)
    g.add_color_stop_rgba(1, a[0], a[1], a[2], alpha)
    c.set_source(g)
    c.fill()
    text(c, label, cx, top_y + depth * 0.2 + h * 0.45, h * 0.42, 'Segoe UI', bold=True, col='#2a2d38',
         align='c', valign='mid', alpha=alpha, max_w=w * 0.75)


# ---------------------------------------------------------------- backgrounds

def vgrad(c, x, y, w, h, stops):
    g = cairo.LinearGradient(0, y, 0, y + h)
    for p, col in stops:
        g.add_color_stop_rgba(p, *rgba(col))
    c.set_source(g)
    c.rectangle(x, y, w, h)
    c.fill()


def radial_glow(c, x, y, r, col, a=1.0):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    cc = rgba(col)
    g.add_color_stop_rgba(0, cc[0], cc[1], cc[2], cc[3] * a)
    g.add_color_stop_rgba(1, cc[0], cc[1], cc[2], 0)
    c.set_source(g)
    c.rectangle(x - r, y - r, 2 * r, 2 * r)
    c.fill()


def backdrop(c, kind, c1, c2, t, W=1920, H=1080, speed=1.0):
    src(c, c1)
    c.rectangle(-50, -50, W + 100, H + 100)
    c.fill()
    src(c, c2)
    if kind == 'dots':
        sp = 90
        off = (t * 40 * speed) % sp
        for j in range(-1, H // sp + 2):
            for i in range(-1, W // sp + 2):
                ox = (sp / 2 if j % 2 else 0)
                circle(c, i * sp + ox + off, j * sp + off, 16)
        c.fill()
    elif kind == 'stripes':
        sp = 120
        off = (t * 60 * speed) % (sp * 2)
        for i in range(-3, (W + H) // sp + 3):
            x0 = i * sp * 2 - H + off
            c.move_to(x0, 0); c.line_to(x0 + sp, 0); c.line_to(x0 + sp + H, H); c.line_to(x0 + H, H); c.close_path()
        c.fill()
    elif kind == 'zigzag':
        c.set_line_width(22)
        c.set_line_join(cairo.LINE_JOIN_MITER)
        sp = 130
        off = (t * 50 * speed) % sp
        for j in range(-1, H // sp + 2):
            y0 = j * sp + off
            c.move_to(-60, y0)
            for i in range(0, W // 60 + 3):
                c.line_to(-60 + i * 60, y0 + (28 if i % 2 else -28))
            c.stroke()
    elif kind == 'triangles':
        for i in range(34):
            x0 = (hrand(i, 1) * (W + 200) + t * 30 * speed * (0.5 + hrand(i, 5))) % (W + 200) - 100
            y0 = hrand(i, 2) * H
            r = 30 + hrand(i, 3) * 50
            a = t * (hsign(i, 4)) * 1.5 * speed + i
            c.save(); c.translate(x0, y0); c.rotate(a)
            c.move_to(0, -r); c.line_to(r * 0.87, r * 0.5); c.line_to(-r * 0.87, r * 0.5); c.close_path()
            c.restore()
        c.fill()
    elif kind == 'squiggle':
        c.set_line_width(14)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(26):
            x0 = hrand(i, 11) * W
            y0 = (hrand(i, 12) * (H + 200) - t * 40 * speed * (0.4 + hrand(i, 9))) % (H + 200) - 100
            c.save(); c.translate(x0, y0); c.rotate(hrand(i, 13) * TAU + t * 0.4)
            c.move_to(-60, 0)
            c.curve_to(-30, -40, -10, 40, 20, 0)
            c.curve_to(40, -30, 50, 20, 70, 0)
            c.restore()
            c.stroke()
    elif kind == 'checker':
        sp = 120
        off = (t * 50 * speed) % (sp * 2)
        for j in range(-2, H // sp + 2):
            for i in range(-2, W // sp + 2):
                if (i + j) % 2 == 0:
                    c.rectangle(i * sp + off, j * sp + off * 0.5, sp, sp)
        c.fill()
    elif kind == 'rays':
        cx, cy = W / 2, H / 2
        n = 18
        rot = t * 0.3 * speed
        for i in range(n):
            a0 = rot + i * TAU / n
            c.move_to(cx, cy)
            c.arc(cx, cy, 2000, a0, a0 + TAU / n / 2)
            c.close_path()
        c.fill()
    elif kind == 'plus':
        sp = 110
        off = (t * 45 * speed) % sp
        c.set_line_width(14)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for j in range(-1, H // sp + 2):
            for i in range(-1, W // sp + 2):
                px, py = i * sp + (sp / 2 if j % 2 else 0) - off, j * sp + off
                c.move_to(px - 18, py); c.line_to(px + 18, py)
                c.move_to(px, py - 18); c.line_to(px, py + 18)
        c.stroke()


def vignette(c, W, H, strength=0.55, col=(0, 0, 0)):
    g = cairo.RadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, W * 0.75)
    g.add_color_stop_rgba(0, col[0], col[1], col[2], 0)
    g.add_color_stop_rgba(1, col[0], col[1], col[2], strength)
    c.set_source(g)
    c.rectangle(0, 0, W, H)
    c.fill()


def spotlight(c, x, y, r, a=0.35):
    g = cairo.RadialGradient(x, y, r * 0.1, x, y, r)
    g.add_color_stop_rgba(0, 1, 1, 0.95, a)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    c.set_source(g)
    c.rectangle(x - r, y - r, r * 2, r * 2)
    c.fill()
