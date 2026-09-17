import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
OUT = os.path.join(ROOT, 'out')
os.makedirs(BUILD, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

REPO_URL = 'https://github.com/SixOThree/too-many-tabs'  # the QR code on the crash screen points here

SR = 48000
BPM = 120.0
BEAT = 60.0 / BPM   # 0.5 s
BAR = 4 * BEAT      # 2.0 s
EIGHTH = BEAT / 2
FPS = int(os.environ.get('TMT_FPS', '30'))  # render.py --fps sets this before the tmt modules load
