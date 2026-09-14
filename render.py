"""Too Many Tabs build script.

  python render.py audio                 render the soundtrack to build/soundtrack.wav
  python render.py still T [T ...]       render preview frames at times (seconds) to build/stills
  python render.py video [--res 1080|4k] [--from A --to B] [--workers N]
  python render.py all [--res 1080|4k]   audio + video + mux into out/
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['audio', 'still', 'video', 'all', 'mux'])
    ap.add_argument('times', nargs='*', type=float)
    ap.add_argument('--res', default='1080')
    ap.add_argument('--from', dest='t_from', type=float, default=0.0)
    ap.add_argument('--to', dest='t_to', type=float, default=None)
    ap.add_argument('--workers', type=int, default=0)
    ap.add_argument('--out', default=None)
    ap.add_argument('--stems', default=None, help='directory to write per-bus float WAV stems')
    a = ap.parse_args()
    if a.cmd in ('audio', 'all'):
        from tmt import music
        music.render(stems_dir=a.stems)
    if a.cmd == 'still':
        from tmt import video
        video.stills(a.times, a.res)
    if a.cmd in ('video', 'all'):
        from tmt import video
        video.render(a.res, a.t_from, a.t_to, a.workers, a.out)
    if a.cmd in ('mux', 'all'):
        from tmt import video
        video.mux(a.res, a.out)


if __name__ == '__main__':
    sys.exit(main())
