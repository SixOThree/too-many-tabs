"""Too Many Tabs build script.

  python render.py audio                 render the soundtrack to build/soundtrack.wav
  python render.py still T [T ...]       render preview frames at times (seconds) to build/stills
  python render.py video [--res 1080|4k] [--fps 30|60] [--encoder x264|qsv] [--from A --to B] [--workers N]
  python render.py mux [--res 1080|4k] [--fps 30|60]
  python render.py all [--res 1080|4k] [--fps 30|60]   audio + video + mux into out/
  python render.py web                   streaming copy of the 1080p master + poster for site/
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['audio', 'still', 'video', 'all', 'mux', 'web'])
    ap.add_argument('times', nargs='*', type=float)
    ap.add_argument('--res', default='1080')
    ap.add_argument('--from', dest='t_from', type=float, default=0.0)
    ap.add_argument('--to', dest='t_to', type=float, default=None)
    ap.add_argument('--workers', type=int, default=0)
    ap.add_argument('--out', default=None)
    ap.add_argument('--stems', default=None, help='directory to write per-bus float WAV stems')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--encoder', choices=['x264', 'qsv', 'lossless'], default='x264',
                    help='qsv = Intel Quick Sync HEVC, much faster at 4K on Intel graphics')
    a = ap.parse_args()
    os.environ['TMT_FPS'] = str(a.fps)  # before any tmt import; spawned render workers inherit it
    if a.cmd in ('audio', 'all'):
        from tmt import music
        music.render(stems_dir=a.stems)
    if a.cmd == 'still':
        from tmt import video
        video.stills(a.times, a.res)
    if a.cmd in ('video', 'all'):
        from tmt import video
        video.render(a.res, a.t_from, a.t_to, a.workers, a.out, a.encoder)
    if a.cmd in ('mux', 'all'):
        from tmt import video
        video.mux(a.res, a.out)
    if a.cmd == 'web':
        from tmt import video
        video.web()


if __name__ == '__main__':
    sys.exit(main())
