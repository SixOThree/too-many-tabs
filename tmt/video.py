"""Frame dispatcher, post-processing, parallel rendering and muxing."""
import math
import multiprocessing as mp
import os
import subprocess
import sys
import time

import cairo
import numpy as np

from .config import FPS, BUILD, OUT
from . import score as SC
from . import post
from .common import FX, W as LW, H as LH
from .util import hrand, clamp

RES = {'1080': (1920, 1080), '4k': (3840, 2160), '720': (1280, 720), '540': (960, 540)}

_state = {}


def init(res):
    Wp, Hp = RES[res]
    _state['W'], _state['H'] = Wp, Hp
    _state['S'] = Wp / 1920.0
    _state['surf'] = cairo.ImageSurface(cairo.FORMAT_RGB24, Wp, Hp)


def _scene(name):
    from . import loop, scenes
    table = {
        's1': lambda c, lt, t, fx: loop.draw_loop(c, lt, t, fx, 's1'),
        's2': lambda c, lt, t, fx: loop.draw_loop(c, lt, t, fx, 's2'),
    }
    for nm in ('cold_open', 'episode', 'space', 'ytp', 'hamster', 's3', 'recursion', 'finale', 'crash', 'epilogue'):
        fn = getattr(scenes, 'draw_' + nm, None)
        if fn is not None:
            table[nm] = fn
    return table.get(name)


def draw_frame(c, t, fx):
    name, lt = SC.section_at(t)
    fn = _scene(name)
    if fn is None:
        c.set_source_rgb(0.1, 0.1, 0.15)
        c.paint()
        from . import gfx
        gfx.text(c, f'{name} {lt:.2f}', 960, 540, 90, 'Impact', col='#ffffff', align='c', valign='mid')
        return name
    fn(c, lt, t, fx)
    return name


def apply_post(arr, fx, t, frame_idx):
    S = _state['S']
    for name, kw in fx.ops:
        if name == 'flash':
            col = kw.get('col', (255, 255, 255))
            post.flash(arr, float(kw['amt']), col[0], col[1], col[2])
        elif name == 'grade':
            post.grade(arr, float(kw.get('sat', 1.0)), float(kw.get('contrast', 1.0)), float(kw.get('bright', 0.0)),
                       float(kw.get('tr', 1.0)), float(kw.get('tg', 1.0)), float(kw.get('tb', 1.0)),
                       float(kw.get('tint', 0.0)))
        elif name == 'invert':
            post.invert(arr)
        elif name == 'hue':
            post.hue_rotate(arr, float(kw['ang']))
        elif name == 'mirror':
            post.mirror(arr)
        elif name == 'kaleido':
            post.kaleido(arr)
        elif name == 'fry':
            post.fry(arr, int(kw.get('q', 8)))
        elif name == 'melt':
            post.melt(arr, float(kw['amt']), int(kw.get('seed', 1)), float(t))
        elif name == 'slices':
            post.slices(arr, int(kw['seed']), int(kw['count']), int(kw['maxshift'] * S))
        elif name == 'rgbsplit':
            d = int(kw['amt'] * S)
            post.vhs(arr, d, d, 0, 0.0, 0.0, frame_idx, 0.0, 0.0, 0, 0)
        elif name == 'posterize':
            post.posterize(arr, int(kw.get('bits', 3)))
    if fx.vhs > 0:
        a = fx.vhs
        sh = max(1, int(round(2.5 * S * a)))
        scan_h = max(1, int(round(2 * S)))
        track_h = int(26 * S) if a > 0.5 else 0
        track_y = int(((t * 0.37) % 1.3) * _state['H']) if track_h else 0
        post.vhs(arr, sh, max(1, sh - 1), scan_h, 0.10 * a, 14.0 * a, frame_idx, 1.2 * S * a, t * 7.0,
                 track_y, track_h)


def render_frame(t, frame_idx):
    surf = _state['surf']
    c = cairo.Context(surf)
    c.set_source_rgb(0, 0, 0)
    c.paint()
    S = _state['S']
    fx = FX()
    c.save()
    c.scale(S, S)
    draw_frame(c, t, fx)
    c.restore()
    surf.flush()
    buf = surf.get_data()
    arr = np.ndarray((_state['H'], _state['W'], 4), np.uint8, buffer=buf)
    apply_post(arr, fx, t, frame_idx)
    return arr


def _worker_init(res):
    init(res)


def _worker_frame(i):
    t = i / FPS
    arr = render_frame(t, i)
    return i, bytes(arr.data)


def stills(times, res='1080'):
    init(res)
    os.makedirs(os.path.join(BUILD, 'stills'), exist_ok=True)
    from PIL import Image
    for t in times:
        i = int(round(t * FPS))
        t0 = time.time()
        arr = render_frame(i / FPS, i)
        im = Image.frombuffer('RGBX', (_state['W'], _state['H']), bytes(arr.data), 'raw', 'BGRX').convert('RGB')
        p = os.path.join(BUILD, 'stills', f'f_{t:07.2f}.png')
        im.save(p)
        print(p, f'{(time.time() - t0) * 1000:.0f} ms')


def _tag(res):
    """'1080', '4k_60fps' ... used in intermediate file names; 30 fps keeps the original names."""
    return res if FPS == 30 else f'{res}_{FPS}fps'


def _encoder_args(res, out, encoder='x264'):
    Wp, Hp = RES[res]
    base = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr0', '-s', f'{Wp}x{Hp}',
            '-r', str(FPS), '-i', '-']
    if encoder == 'lossless':
        # exact RGB, for a render-once intermediate that final encodes are made from
        enc = ['-c:v', 'libx264rgb', '-preset', 'ultrafast', '-qp', '0', '-pix_fmt', 'bgr24']
        return base + enc + [out.replace('.mp4', '.mkv') if out.endswith('.mp4') else out]
    if encoder == 'qsv':
        # Intel Quick Sync HEVC: frees the CPU for drawing frames, which is the bottleneck at 4K
        enc = ['-c:v', 'hevc_qsv', '-preset', 'slower', '-global_quality', '18', '-pix_fmt', 'nv12', '-tag:v', 'hvc1']
    elif res == '4k':
        # slow preset: the frames are already the bottleneck, and it buys a cleaner master at the same size
        enc = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p']
    else:
        enc = ['-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p']
    return base + enc + ['-movflags', '+faststart', out]


def render(res='1080', t_from=0.0, t_to=None, workers=0, out=None, encoder='x264'):
    t_to = SC.TOTAL if t_to is None else t_to
    f0, f1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    out = out or os.path.join(BUILD, f'video_{_tag(res)}.mp4')
    workers = workers or max(1, (os.cpu_count() or 4) - 2)
    print(f'rendering frames {f0}..{f1} at {res} {FPS} fps with {workers} workers, {encoder} -> {out}', flush=True)
    enc = subprocess.Popen(_encoder_args(res, out, encoder), stdin=subprocess.PIPE)
    t0 = time.time()
    ctx = mp.get_context('spawn')
    # Frames are handed out in small batches so finished frames can never pile up in memory faster than the
    # encoder takes them (a 4K frame is 33 MB).
    batch = workers * 3
    with ctx.Pool(workers, initializer=_worker_init, initargs=(res,)) as pool:
        done = 0
        next_report = 150
        for b0 in range(f0, f1, batch):
            for i, data in pool.map(_worker_frame, range(b0, min(f1, b0 + batch)), chunksize=1):
                enc.stdin.write(data)
                done += 1
            if done >= next_report:
                next_report += 150
                el = time.time() - t0
                rate = done / el
                print(f'  frame {b0 + batch} ({(b0 + batch) / FPS:.1f}s)  {rate:.1f} fps  '
                      f'eta {(f1 - f0 - done) / rate:.0f}s', flush=True)
    enc.stdin.close()
    enc.wait()
    print(f'video done in {time.time() - t0:.0f}s', flush=True)
    return out


def mux(res='1080', out=None):
    vid = os.path.join(BUILD, f'video_{_tag(res)}.mp4')
    aud = os.path.join(BUILD, 'soundtrack.wav')
    rate = '' if FPS == 30 else str(FPS)
    name = f'too_many_tabs_4k{rate}.mp4' if res == '4k' else f'too_many_tabs_{res}p{rate}.mp4'
    out = out if (out and out.endswith('.mp4') and 'video_' not in out) else os.path.join(OUT, name)
    cmd = ['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', vid, '-i', aud, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k',
           '-shortest', '-movflags', '+faststart', out]
    subprocess.run(cmd, check=True)
    print('muxed', out)
    return out


SITE = os.path.join(os.path.dirname(OUT), 'site')


def web(poster_t=11.0):
    """Streaming copy of the 1080p master plus a poster frame, for the one-page site in site/."""
    src = os.path.join(OUT, 'too_many_tabs_1080p.mp4')
    out = os.path.join(SITE, 'too_many_tabs.mp4')
    # The VHS noise is expensive to encode, so the maxrate cap keeps the bitrate streamable; a keyframe every 2 s
    # makes seeking land quickly.
    cmd = ['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', src,
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-maxrate', '10M', '-bufsize', '20M',
           '-profile:v', 'high', '-level', '4.1', '-pix_fmt', 'yuv420p', '-g', str(2 * FPS),
           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out]
    t0 = time.time()
    subprocess.run(cmd, check=True)
    print(f'encoded {out} ({os.path.getsize(out) / 1e6:.0f} MB) in {time.time() - t0:.0f}s')
    poster = os.path.join(SITE, 'poster.jpg')
    subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-ss', str(poster_t), '-i', src,
                    '-frames:v', '1', '-q:v', '3', poster], check=True)
    print('poster', poster)
    return out
