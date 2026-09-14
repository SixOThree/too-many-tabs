"""SAPI text-to-speech with a file cache. Call request() for everything first, then generate(), then load()."""
import hashlib
import json
import os
import subprocess
import wave

import numpy as np

from .config import BUILD, SR

VOICES = {'david': 'Microsoft David Desktop', 'zira': 'Microsoft Zira Desktop'}
CACHE = os.path.join(BUILD, 'tts')
os.makedirs(CACHE, exist_ok=True)

_requests = {}
_mem = {}


def _path(text, voice, rate):
    h = hashlib.sha1(f'{voice}|{rate}|{text}'.encode()).hexdigest()[:16]
    return os.path.join(CACHE, f'{voice}_{h}.wav')


def request(text, voice='david', rate=0):
    p = _path(text, voice, rate)
    if not os.path.exists(p):
        _requests[p] = dict(path=p, voice=VOICES[voice], rate=int(rate), text=text)
    return p


def generate():
    if not _requests:
        return 0
    jobs = os.path.join(CACHE, 'jobs.json')
    with open(jobs, 'w', encoding='utf-8') as f:
        json.dump(list(_requests.values()), f)
    script = os.path.join(os.path.dirname(__file__), 'tts.ps1')
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, '-Jobs', jobs],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    n = len(_requests)
    _requests.clear()
    return n


def _read_wav(p):
    with wave.open(p, 'rb') as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return x


def load(text, voice='david', rate=0, trim=True):
    p = _path(text, voice, rate)
    key = (p, trim)
    if key in _mem:
        return _mem[key]
    if not os.path.exists(p):
        request(text, voice, rate)
        generate()
    x = _read_wav(p)
    if trim and len(x):
        k = 240
        env = np.sqrt(np.convolve(x * x, np.ones(k) / k, mode='same'))
        thr = env.max() * 0.03
        idx = np.nonzero(env > thr)[0]
        if len(idx):
            a = max(0, idx[0] - 480)
            b = min(len(x), idx[-1] + 960)
            x = x[a:b].copy()
            fade = min(240, len(x) // 4)
            x[:fade] *= np.linspace(0, 1, fade)
            x[-fade:] *= np.linspace(1, 0, fade)
    _mem[key] = x
    return x
