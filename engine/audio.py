"""Audio engine: voiceover (Piper neural TTS), procedural score, SFX, mixing.

Everything runs offline. Sample rate 44.1 kHz, stereo float32 arrays shaped (n, 2).
"""
from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 44100
ROOT = Path(__file__).resolve().parent.parent
VOICES = {
    "dmitri": "vits-piper-ru_RU-dmitri-medium/ru_RU-dmitri-medium.onnx",
    "denis": "vits-piper-ru_RU-denis-medium/ru_RU-denis-medium.onnx",
    "irina": "vits-piper-ru_RU-irina-medium/ru_RU-irina-medium.onnx",
    "ruslan": "vits-piper-ru_RU-ruslan-medium/ru_RU-ruslan-medium.onnx",
}

# ---------------------------------------------------------------- utilities

def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def read_wav(path: Path) -> np.ndarray:
    """Read any audio via ffmpeg -> stereo float32 @ SR."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def write_wav(path: Path, x: np.ndarray) -> None:
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def stereo(m: np.ndarray, pan: float = 0.0) -> np.ndarray:
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([m * l, m * r], axis=1) * np.sqrt(2)


def place(buf: np.ndarray, x: np.ndarray, start: float, gain: float = 1.0) -> None:
    i = int(start * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n] * gain


def lowpass(x, cutoff, order=2):
    sos = signal.butter(order, min(cutoff, SR / 2 - 100) / (SR / 2), "low", output="sos")
    return signal.sosfilt(sos, x, axis=0)


def highpass(x, cutoff, order=2):
    sos = signal.butter(order, cutoff / (SR / 2), "high", output="sos")
    return signal.sosfilt(sos, x, axis=0)


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band", output="sos")
    return signal.sosfilt(sos, x, axis=0)


def env_adsr(n, a=0.01, d=0.1, s=0.8, r=0.2):
    t = np.arange(n) / SR
    dur = n / SR
    e = np.ones(n) * s
    e = np.where(t < a, t / max(a, 1e-4), e)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / max(d, 1e-4), e)
    rel_start = max(dur - r, a + d)
    e = np.where(t >= rel_start, e * np.clip(1 - (t - rel_start) / max(r, 1e-4), 0, 1), e)
    return e


_IR_CACHE: dict = {}


def reverb(x: np.ndarray, size: float = 2.8, mix: float = 0.3, seed: int = 7) -> np.ndarray:
    key = (size, seed)
    if key not in _IR_CACHE:
        n = int(size * SR)
        g = rng(seed)
        t = np.arange(n) / SR
        decay = np.exp(-6.9 * t / size)
        ir = g.standard_normal((n, 2)) * decay[:, None]
        ir = lowpass(ir, 6000)
        ir[: int(0.012 * SR)] = 0  # predelay
        ir /= np.sqrt((ir ** 2).sum(axis=0))
        _IR_CACHE[key] = ir
    ir = _IR_CACHE[key]
    wet = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], axis=1)
    return x * (1 - mix) + wet * mix


def delay(x, time=0.375, fb=0.35, mix=0.3, pingpong=True):
    d = int(time * SR)
    out = x.copy()
    tap = x.copy()
    for k in range(1, 6):
        tap = np.roll(tap, d, axis=0) * fb
        tap[:d] = 0
        if pingpong:
            tap = tap[:, ::-1]
        out += tap * mix
    return out


def softclip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def note_hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)

# ---------------------------------------------------------------- voiceover

def tts(text: str, out: Path, voice: str = "dmitri", speed: float = 1.0) -> float:
    """Synthesize text with Piper; returns duration seconds. «|» inserts a dramatic pause (0.55 s)."""
    if "|" in text:
        parts = [p.strip() for p in text.split("|") if p.strip()]
        chunks = []
        for k, ptxt in enumerate(parts):
            f = out.with_suffix(f".p{k}.wav")
            tts(ptxt, f, voice, speed)
            chunks.append(read_wav(f)); f.unlink()
        gap = np.zeros((int(0.55 * SR), 2))
        x = chunks[0]; parts_t = [[0.0, len(x) / SR]]
        for c in chunks[1:]:
            x = np.concatenate([x, gap]); a = len(x) / SR
            x = np.concatenate([x, c]); parts_t.append([a, len(x) / SR])
        write_wav(out, x)
        out.with_suffix(".parts.json").write_text(json.dumps(parts_t))   # exact phrase boundaries for editing
        return len(x) / SR
    from piper import PiperVoice, SynthesisConfig

    model = ROOT / "assets" / "voices" / VOICES[voice]
    v = PiperVoice.load(str(model))
    cfg = SynthesisConfig(length_scale=1.0 / speed, noise_scale=0.6, noise_w_scale=0.7)
    tmp = out.with_suffix(".raw.wav")
    with wave.open(str(tmp), "wb") as w:
        v.synthesize_wav(text, w, syn_config=cfg)
    # polish: high-pass, gentle compression, presence, normalise peak
    x = read_wav(tmp)
    tmp.unlink()
    x = highpass(x, 80)
    # trim leading/trailing silence
    mag = np.abs(x).max(axis=1)
    idx = np.where(mag > 0.01)[0]
    if len(idx):
        x = x[max(idx[0] - int(0.03 * SR), 0): idx[-1] + int(0.12 * SR)]
    env = signal.lfilter([0.002], [1, -0.998], np.abs(x).mean(axis=1))
    gain = 1 / np.maximum(env / (env.max() + 1e-9), 0.35) ** 0.35
    x = x * gain[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.9
    x = reverb(x, size=0.6, mix=0.06)
    write_wav(out, x)
    return len(x) / SR

def voice_fx(path: Path, fx: dict) -> float:
    """Character voice design: pitch (semitones), tempo, EQ colour, grit, room. Rewrites file, returns duration."""
    p = 2 ** (fx.get("pitch", 0) / 12)
    tempo = fx.get("tempo", 1.0)
    chain = [f"asetrate={int(SR * p)}", f"aresample={SR}"]
    at = tempo / p
    while at < 0.5:
        chain.append("atempo=0.5"); at /= 0.5
    while at > 2.0:
        chain.append("atempo=2.0"); at /= 2.0
    chain.append(f"atempo={at:.4f}")
    eq = {"deep": "bass=g=5:f=140,treble=g=-2", "bright": "treble=g=4:f=4000,bass=g=-3",
          "phone": "highpass=f=300,lowpass=f=3400", "warm": "bass=g=2:f=180,treble=g=-1"}.get(fx.get("eq"))
    if eq:
        chain.append(eq)
    tmp = path.with_suffix(".fx.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-af", ",".join(chain), "-ar", str(SR), str(tmp)], check=True)
    x = read_wav(tmp); tmp.unlink()
    if fx.get("grit"):
        x = softclip(x * (1 + 3 * fx["grit"]), 1 + 2 * fx["grit"]) * 0.8
    room = fx.get("room")
    if room:
        size, mix = {"hall": (2.6, 0.28), "tent": (0.5, 0.10), "clinic": (0.9, 0.12), "close": (0.3, 0.05)}[room]
        x = reverb(x, size, mix)
    x = x / (np.abs(x).max() + 1e-9) * 0.9
    write_wav(path, x)
    pj = path.with_suffix(".parts.json")
    if pj.exists():  # tempo change rescales phrase boundaries
        pj.write_text(json.dumps([[a / tempo, b / tempo] for a, b in json.loads(pj.read_text())]))
    return len(x) / SR


# ---------------------------------------------------------------- music

SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "harmonic": [0, 2, 3, 5, 7, 8, 11],
}
KEYS = {k: i for i, k in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}

MOODS = {
    # bpm, scale, progression (scale degrees, 1-based), brightness, swing of arp
    "cinematic": dict(bpm=84, scale="minor", prog=[1, 6, 3, 7], bright=2400, arp="up"),
    "epic": dict(bpm=96, scale="minor", prog=[1, 6, 7, 5], bright=3200, arp="updown"),
    "tense": dict(bpm=100, scale="harmonic", prog=[1, 1, 6, 5], bright=1800, arp="pulse"),
    "calm": dict(bpm=72, scale="major", prog=[1, 5, 6, 4], bright=2000, arp="slow"),
    "upbeat": dict(bpm=118, scale="major", prog=[1, 5, 6, 4], bright=4200, arp="updown"),
    "tech": dict(bpm=110, scale="dorian", prog=[1, 4, 7, 1], bright=3600, arp="pulse"),
    "inspire": dict(bpm=92, scale="major", prog=[6, 4, 1, 5], bright=3000, arp="up"),
}


def chord_notes(root_midi: int, scale: list[int], degree: int) -> list[int]:
    notes = []
    for step in (0, 2, 4):
        i = degree - 1 + step
        notes.append(root_midi + scale[i % 7] + 12 * (i // 7))
    return notes


def supersaw(freq, n, voices=5, detune=0.012, seed=0):
    g = rng(seed)
    t = np.arange(n) / SR
    outl = np.zeros(n)
    outr = np.zeros(n)
    for v in range(voices):
        d = 1 + detune * (v - (voices - 1) / 2) / ((voices - 1) / 2 or 1)
        ph = g.random()
        saw = 2 * ((freq * d * t + ph) % 1) - 1
        pan = (v / max(voices - 1, 1)) * 2 - 1
        outl += saw * np.cos((pan + 1) * np.pi / 4)
        outr += saw * np.sin((pan + 1) * np.pi / 4)
    return np.stack([outl, outr], axis=1) / voices


def pluck(freq, n, bright=3000):
    t = np.arange(n) / SR
    x = np.zeros(n)
    for h in range(1, 9):
        x += np.sin(2 * np.pi * freq * h * t) / h * np.exp(-t * (6 + h * 3.5))
    x *= np.minimum(t / 0.003, 1)
    return lowpass(x, bright)


def kick(n=int(0.45 * SR)):
    t = np.arange(n) / SR
    f = 45 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) + 0.3 * np.sin(ph * 2) * np.exp(-t * 30)


def snare(n=int(0.3 * SR), seed=3):
    t = np.arange(n) / SR
    noise = bandpass(rng(seed).standard_normal(n), 1200, 9000) * np.exp(-t * 18)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)
    return noise * 0.8 + tone * 0.5


def hat(n=int(0.08 * SR), seed=5):
    t = np.arange(n) / SR
    return highpass(rng(seed).standard_normal(n), 7000) * np.exp(-t * 60) * 0.5


def compose(length: float, sections: list[dict], mood: str = "cinematic", key: str = "A",
            bpm: int | None = None, seed: int = 1) -> np.ndarray:
    """sections: list of {start, energy(0-1)} sorted by start. Returns stereo score."""
    if mood == "piano":
        return compose_piano(length, sections, key=key, bpm=bpm or 68, seed=seed)
    m = MOODS.get(mood, MOODS["cinematic"])
    bpm = bpm or m["bpm"]
    scale = SCALES[m["scale"]]
    prog = m["prog"]
    beat = 60 / bpm
    bar = beat * 4
    n_total = int((length + 3) * SR)
    pad = np.zeros((n_total, 2))
    bass = np.zeros((n_total, 2))
    arp = np.zeros((n_total, 2))
    drums = np.zeros((n_total, 2))
    root = 45 + KEYS.get(key, 9) % 12  # around A2
    if root > 50:
        root -= 12

    def energy_at(t):
        e = sections[0]["energy"] if sections else 0.5
        for s in sections:
            if s["start"] <= t + 1e-6:
                e = s["energy"]
        return e

    n_bars = int(np.ceil(length / bar)) + 1
    k, sn, hh = kick(), snare(seed=seed + 3), hat(seed=seed + 5)
    for b in range(n_bars):
        t0 = b * bar
        if t0 >= length + bar:
            break
        e = energy_at(t0)
        deg = prog[b % len(prog)]
        notes = chord_notes(root + 12, scale, deg)
        last = t0 + bar >= length
        nlen = int((bar + (2.5 if last else 0.25)) * SR)
        # pad: supersaw chord, opens with energy
        ch = np.zeros((nlen, 2))
        for j, nt in enumerate(notes + [notes[0] + 12]):
            ch += supersaw(note_hz(nt), nlen, seed=seed * 100 + b * 7 + j)
        cutoff = 500 + m["bright"] * (0.25 + 0.75 * e)
        ch = lowpass(ch, cutoff) * env_adsr(nlen, a=0.35 if b == 0 else 0.08, d=0.2, s=0.9,
                                             r=2.4 if last else 0.3)[:, None]
        place(pad, ch * 0.22, t0)
        # sub bass
        bn = note_hz(root + scale[(deg - 1) % 7])
        if e < 0.45:
            ln = nlen
            tt = np.arange(ln) / SR
            x = np.sin(2 * np.pi * bn * tt) * env_adsr(ln, a=0.05, s=1, r=1.5 if last else 0.25)
            place(bass, stereo(softclip(x, 1.5)) * 0.32, t0)
        else:
            for i8 in range(8):
                ln = int(beat / 2 * 0.9 * SR)
                tt = np.arange(ln) / SR
                x = np.sin(2 * np.pi * bn * tt) + 0.3 * np.sin(4 * np.pi * bn * tt)
                x *= env_adsr(ln, a=0.004, d=0.08, s=0.7, r=0.04)
                place(bass, stereo(softclip(x, 2)) * 0.28, t0 + i8 * beat / 2)
        # arpeggio
        if e >= 0.25 and not last:
            pattern = {
                "up": [0, 1, 2, 3],
                "updown": [0, 1, 2, 3, 2, 1],
                "pulse": [0, 0, 2, 0],
                "slow": [0, 2, 1, 3],
            }[m["arp"]]
            pool = notes + [notes[0] + 12]
            step = beat / 4 if (e > 0.55 and m["arp"] != "slow") else beat / 2
            steps = int(round(bar / step))
            for s_i in range(steps):
                nt = pool[pattern[s_i % len(pattern)] % len(pool)] + 12
                ln = int(0.5 * SR)
                x = pluck(note_hz(nt), ln, m["bright"])
                pan = 0.5 * np.sin(s_i * 0.8)
                acc = 1.0 if s_i % 4 == 0 else 0.7
                place(arp, stereo(x, pan) * 0.10 * acc, t0 + s_i * step)
        # drums
        if not last:
            for bt in range(4):
                tb = t0 + bt * beat
                if e >= 0.65 or (e >= 0.4 and bt in (0, 2)):
                    place(drums, stereo(k) * 0.55, tb)
                if e >= 0.65 and bt in (1, 3):
                    place(drums, stereo(sn) * 0.28, tb)
                if e >= 0.5:
                    for h in range(2):
                        place(drums, stereo(hh, 0.3 if h else -0.3) * (0.18 if h else 0.1), tb + h * beat / 2)

    arp = delay(arp, time=beat * 0.75, fb=0.4, mix=0.35)
    mix = reverb(pad, 3.2, 0.45) + bass + reverb(arp, 2.4, 0.3) + reverb(drums, 1.2, 0.12)
    mix = highpass(mix, 30)
    mix = softclip(mix * 1.2, 1.3) * 0.8
    out = mix[: int(length * SR)]
    fade = int(min(2.0, length / 4) * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    out[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    return out

# ---------------------------------------------------------------- sfx

def sfx_whoosh(dur=0.9, seed=11, rev=False):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng(seed).standard_normal(n)
    out = np.zeros(n)
    # sweep band-pass via chunks
    chunks = 24
    for c in range(chunks):
        a, b = c * n // chunks, (c + 1) * n // chunks
        p = c / chunks
        fc = 300 + 5000 * (np.sin(np.pi * p) ** 2)
        seg = bandpass(x, fc * 0.6, min(fc * 1.6, SR / 2 - 200))[a:b]
        out[a:b] = seg
    e = np.sin(np.pi * t / dur) ** 2
    if rev:
        e = (t / dur) ** 2 * (t < dur)
    out *= e
    return stereo(out / (np.abs(out).max() + 1e-9), 0) * 0.5


def sfx_impact(seed=12):
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    f = 32 + 70 * np.exp(-t * 10)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    crack = lowpass(rng(seed).standard_normal(n), 3000) * np.exp(-t * 14) * 0.5
    x = stereo(softclip(boom + crack, 2))
    return reverb(x, 3.0, 0.35) * 0.8


def sfx_riser(dur=2.0, seed=13):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng(seed).standard_normal(n)
    out = np.zeros(n)
    chunks = 30
    for c in range(chunks):
        a, b = c * n // chunks, (c + 1) * n // chunks
        fc = 400 * (2 ** (5 * c / chunks))
        out[a:b] = bandpass(x, fc * 0.7, min(fc * 1.4, SR / 2 - 200))[a:b]
    tone = np.sin(2 * np.pi * np.cumsum(200 * 2 ** (2 * t / dur)) / SR) * 0.3
    out = (out / (np.abs(out).max() + 1e-9) + tone) * (t / dur) ** 2
    return reverb(stereo(out) * 0.35, 1.5, 0.3)


def sfx_tick(seed=14):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 90) + highpass(rng(seed).standard_normal(n), 5000) * np.exp(-t * 200) * 0.3
    return stereo(x) * 0.25

def sfx_applause(dur=5.0, seed=15, people=40):
    """Warm crowd applause: many clappers, each a train of short filtered noise bursts."""
    n = int(dur * SR); g = rng(seed)
    out = np.zeros((n, 2))
    clap_len = int(0.025 * SR)
    tt = np.arange(clap_len) / SR
    for p_ in range(people):
        rate = 3.5 + g.random() * 2.5; t = g.random() * 0.4
        pan = g.random() * 1.6 - 0.8; fc = 900 + g.random() * 1800
        burst_base = bandpass(g.standard_normal(clap_len * 60), fc * 0.6, fc * 2.2)
        k = 0
        while t < dur:
            i = int(t * SR)
            b = burst_base[(k % 60) * clap_len:(k % 60 + 1) * clap_len] * np.exp(-tt * 140) * (0.6 + 0.4 * g.random())
            seg = stereo(b, pan)[: n - i]
            out[i:i + len(seg)] += seg
            t += 1 / rate * (0.85 + 0.3 * g.random()); k += 1
    env = np.minimum(np.arange(n) / (0.6 * SR), 1) * np.clip((dur - np.arange(n) / SR) / 1.8, 0, 1)
    out *= env[:, None]
    out = reverb(out / (np.abs(out).max() + 1e-9), 1.6, 0.35)
    return out * 0.6


# ---------------------------------------------------------------- mix

def mix(timeline: dict, out: Path, music_vol: float = 0.8, duck: float = 0.35) -> None:
    """timeline: {length, vo:[{file,start}], music:file|None, sfx:[{kind,start,gain}]}"""
    L = timeline["length"]
    n = int(L * SR)
    vo = np.zeros((n, 2))
    for c in timeline["vo"]:
        place(vo, read_wav(Path(c["file"])), c["start"])
    mus = np.zeros((n, 2))
    if timeline.get("music"):
        mx = read_wav(Path(timeline["music"]))
        place(mus, mx, 0)
    # sidechain: duck music under voice (smooth envelope, 150ms attack, 600ms release)
    env = np.abs(vo).mean(axis=1)
    env = np.convolve(env, np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
    active = (env > 0.01).astype(float)
    a = np.exp(-1 / (0.15 * SR))
    r = np.exp(-1 / (0.6 * SR))
    sm = signal.lfilter([1 - r], [1, -r], active)
    sm = np.maximum(sm, signal.lfilter([1 - a], [1, -a], active))
    gain = 1 - (1 - duck) * np.clip(sm * 1.5, 0, 1)
    mus *= gain[:, None] * music_vol
    fx = np.zeros((n, 2))
    gens = {"whoosh": sfx_whoosh, "impact": sfx_impact, "riser": sfx_riser, "tick": sfx_tick, "applause": sfx_applause,
            "shing": lambda seed: sfx_shing(seed), "heartbeat": lambda seed: sfx_heartbeat(seed), "ding": lambda seed: sfx_ding(seed)}
    for i, s in enumerate(timeline.get("sfx", [])):
        g = gens[s["kind"]]
        x = g(seed=20 + i)
        start = s["start"] - (len(x) / SR if s["kind"] == "riser" else 0)
        if s["kind"] == "whoosh":
            start -= 0.45
        place(fx, x, start, s.get("gain", 1.0))
    total = vo * 1.0 + mus + fx * 0.6
    total = softclip(total, 1.1) * 0.95
    tmp = out.with_suffix(".premaster.wav")
    write_wav(tmp, total)
    # loudness master to -14 LUFS (streaming standard), true peak -1 dB
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-af",
                    "loudnorm=I=-14:TP=-1.0:LRA=11", "-ar", str(SR), str(out)], check=True)
    tmp.unlink()


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "score":
        secs = json.loads(sys.argv[3]) if len(sys.argv) > 3 else [{"start": 0, "energy": 0.3}, {"start": 8, "energy": 0.7}]
        x = compose(20, secs, mood=sys.argv[2])
        write_wav(Path(f"/tmp/claude-0/score_{sys.argv[2]}.wav"), x)


# ---------------------------------------------------------------- piano + strings (documentary score)

def piano_note(midi, dur, vel=0.7, seed=0):
    """Additive piano: inharmonic partials, per-partial decay, 3 detuned strings, hammer noise."""
    f0 = note_hz(midi)
    n = int((dur + 1.8) * SR)
    t = np.arange(n) / SR
    B = 0.0004 * (f0 / 261.6) ** 0.5            # inharmonicity
    x = np.zeros(n)
    bright = 0.35 + 0.65 * vel
    for k in range(1, 14):
        fk = f0 * k * np.sqrt(1 + B * k * k)
        if fk > 12000:
            break
        amp = (1 / k ** 1.15) * (bright ** (k - 1) if k > 1 else 1)
        dec = 0.9 + 0.55 * k * (f0 / 440) ** 0.6     # higher partials die faster
        for d in (-0.6, 0.0, 0.7):                    # unison strings beating
            x += amp / 3 * np.sin(2 * np.pi * fk * (1 + d * 0.0006) * t + k * 0.7) * np.exp(-t * dec)
    x *= (1 - np.exp(-t / 0.002))
    # two-stage decay (prompt + aftersound) and damper release at note end
    x *= 0.6 * np.exp(-t * 2.2 * (f0 / 440) ** 0.3) + 0.4 * np.exp(-t * 0.35)
    rel = np.clip(1 - (t - dur) / 0.35, 0, 1)
    x *= np.where(t > dur, rel, 1)
    hammer = highpass(rng(seed).standard_normal(n), 1500) * np.exp(-t * 180) * 0.03
    x = (x + hammer) * vel
    pan = np.clip((midi - 60) / 40, -0.6, 0.6)
    return stereo(lowpass(x, 3500 + 5000 * vel), pan)


def strings_note(midi, dur, vel=0.5, seed=0):
    """Soft string ensemble: detuned saws with vibrato, slow bow attack, warm low-pass."""
    f0 = note_hz(midi)
    n = int((dur + 1.5) * SR)
    t = np.arange(n) / SR
    g = rng(seed)
    out = np.zeros((n, 2))
    for v in range(6):
        rate, depth = 4.6 + g.random() * 1.2, 0.0035 + g.random() * 0.002
        det = 1 + (g.random() - 0.5) * 0.008
        ph = 2 * np.pi * np.cumsum(f0 * det * (1 + depth * np.sin(2 * np.pi * rate * t + g.random() * 6))) / SR
        saw = np.zeros(n)
        for k in range(1, 9):
            saw += np.sin(k * ph) / k
        pan = (v / 5) * 1.4 - 0.7
        out += stereo(saw, pan) / 6
    env = np.clip(t / 0.9, 0, 1) ** 1.5 * np.where(t > dur, np.clip(1 - (t - dur) / 1.2, 0, 1), 1)
    return lowpass(out, min(1400 + 1600 * vel, max(f0 * 5, 500))) * env[:, None] * vel  # low notes: no whistling upper harmonics


def compose_piano(length, sections, key="D", bpm=68, seed=3):
    """Documentary score: solo piano -> + strings -> swell; supports musical pauses.
    sections: [{start, energy, pause?}] ; energy<0.3 piano only, >=0.3 adds strings, >=0.6 adds cellos+octaves."""
    scale = SCALES["major"]
    prog = [1, 5, 6, 4, 1, 5, 4, 4]          # warm, hopeful
    beat = 60 / bpm
    bar = beat * 4
    n_total = int((length + 4) * SR)
    pno = np.zeros((n_total, 2)); strs = np.zeros((n_total, 2))
    root = 50 + KEYS.get(key, 2)               # around D3
    while root > 52:
        root -= 12
    g = rng(seed)

    def sec_at(t):
        cur = sections[0] if sections else {"energy": 0.3}
        for s in sections:
            if s["start"] <= t + 1e-6:
                cur = s
        return cur

    melody_shape = [4, 2, 3, 1, 2, 0, 1, 2]  # chord-tone indices for gentle top line
    n_bars = int(np.ceil(length / bar)) + 1
    for b in range(n_bars):
        t0 = b * bar
        if t0 > length:
            break
        s = sec_at(t0)
        if s.get("pause"):
            continue
        e = s["energy"]
        deg = prog[b % len(prog)]
        ch = chord_notes(root + 12, scale, deg)          # mid voicing
        bass = root + scale[(deg - 1) % 7]
        last = t0 + bar >= length
        # left hand: bass + fifth, broken
        place(pno, piano_note(bass, bar * 0.95, 0.5 + 0.15 * e, seed + b), t0)
        place(pno, piano_note(bass + 7, beat * 1.8, 0.35, seed + b + 1), t0 + beat * 2)
        # right hand: broken chord eighths (sparser when calm)
        step = beat / 2 if e >= 0.25 else beat
        pool = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12]
        for i in range(int(round(bar / step))):
            if last and i > 0:
                break
            v = 0.32 + 0.18 * e + 0.06 * (i % 4 == 0)
            place(pno, piano_note(pool[i % 4], step * 1.6, v, seed + b * 17 + i), t0 + i * step + g.normal(0, 0.006))
        # top melody note every half bar when energy grows
        if e >= 0.35 and not last:
            for h in range(2):
                m = ch[melody_shape[(b * 2 + h) % 8] % 3] + 24
                place(pno, piano_note(m, beat * 1.9, 0.45 + 0.2 * e, seed + b * 31 + h), t0 + h * beat * 2 + 0.01)
        # strings
        if e >= 0.3:
            dur = bar + (3 if last else 0.15)
            for j, nt in enumerate(ch + ([ch[0] + 12] if e >= 0.5 else [])):
                place(strs, strings_note(nt + 12, dur, 0.22 + 0.3 * e, seed + b * 7 + j), t0)
            if e >= 0.6:
                place(strs, strings_note(bass, dur, 0.35 + 0.2 * e, seed + b * 9), t0)  # cellos
        if last:
            place(pno, piano_note(ch[0] + 24, 3.5, 0.45, seed + 999), t0)
    mix = reverb(pno * 0.55, 3.2, 0.32) + reverb(strs * 0.5, 4.0, 0.5)
    mix = highpass(mix, 35)
    # sample-accurate musical pauses: breathe out over 0.8 s, silence, gentle return
    gain = np.ones(len(mix))
    for i, sct in enumerate(sections):
        if sct.get("pause"):
            a = int(sct["start"] * SR)
            b = int(sections[i + 1]["start"] * SR) if i + 1 < len(sections) else len(mix)
            f = int(0.8 * SR)
            gain[a:b] = 0.0
            gain[max(a - f, 0):a] = np.minimum(gain[max(a - f, 0):a], np.linspace(1, 0, a - max(a - f, 0)) ** 2)
            gain[b:b + f] = np.minimum(gain[b:b + f], np.linspace(0, 1, len(gain[b:b + f])) ** 0.7)
    mix *= gain[:, None]
    mix = softclip(mix * 1.1, 1.1) * 0.85
    out = mix[: int(length * SR)]
    fade = int(min(3.0, length / 4) * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    return out


# ---------------------------------------------------------------- scene-scored suite (one style per scene, crossfaded)

def _oud(freq, n, vel=0.6, seed=0):
    t = np.arange(n) / SR
    bend = 1 + 0.012 * np.exp(-t * 30)                      # plectrum pitch bend
    ph = 2 * np.pi * np.cumsum(freq * bend) / SR
    x = np.zeros(n)
    for k in range(1, 12):
        x += np.sin(k * ph + k) / k ** 0.9 * np.exp(-t * (3.5 + k * 2.2))
    x += highpass(rng(seed).standard_normal(n), 2000) * np.exp(-t * 120) * 0.15
    return lowpass(x * vel * np.minimum(t / 0.002, 1), 3200)


def _drum(kind, seed=0):
    n = int(0.5 * SR); t = np.arange(n) / SR
    if kind == "dum":
        return np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-t * 25)) / SR) * np.exp(-t * 6) * 0.9
    return (highpass(rng(seed).standard_normal(n), 2500) * np.exp(-t * 55) * 0.5
            + np.sin(2 * np.pi * 420 * t) * np.exp(-t * 40) * 0.25)


def style_oriental(L, energy=0.6, seed=4):
    bpm = 96; beat = 60 / bpm; n = int((L + 2) * SR)
    out = np.zeros((n, 2)); drums = np.zeros((n, 2))
    hijaz = [0, 1, 4, 5, 7, 8, 10, 12]                        # D Eb F# G A Bb C D
    root = 50                                                # D3
    phrase = [7, 6, 5, 4, 5, 4, 2, 1, 0, 1, 2, 4, 2, 1, 0, 0]
    for i in range(int(L / (beat / 2)) + 1):
        tt = i * beat / 2
        if i % 16 in (3, 11) and i % 32 > 15:
            continue
        nt = root + 12 + hijaz[phrase[i % 16] % 8] + (12 if phrase[i % 16] == 7 else 0)
        place(out, stereo(_oud(note_hz(nt), int(1.2 * SR), 0.45 + 0.1 * (i % 4 == 0), seed + i), 0.25), tt)
    maqsum = ["dum", "tek", None, "tek", "dum", None, "tek", None]
    for i in range(int(L / (beat / 2)) + 1):
        k = maqsum[i % 8]
        if k:
            place(drums, stereo(_drum(k, seed + i), -0.2 if k == "tek" else 0.1), i * beat / 2, 0.55 * (0.6 + 0.4 * energy))
    pad = np.zeros((n, 2))
    place(pad, strings_note(root - 12, L + 0.5, 0.45, seed) + strings_note(root - 5, L + 0.5, 0.3, seed + 1), 0)
    mix = reverb(out * 0.6, 2.2, 0.3) + reverb(drums, 1.0, 0.15) + reverb(pad * 0.5, 3.0, 0.4)
    return mix[: int(L * SR)]


def style_mountain(L, energy=0.5, seed=5):
    n = int((L + 2) * SR); g = rng(seed)
    out = np.zeros((n, 2))
    root = 50; penta = [0, 3, 5, 7, 10, 12, 15]
    t = 0.3
    while t < L:
        nt = root + 12 + penta[g.integers(0, len(penta))]
        place(out, stereo(_oud(note_hz(nt), int(1.6 * SR), 0.5, int(t * 100)), g.random() * 0.8 - 0.4), t)
        if g.random() < 0.35:
            place(out, stereo(_oud(note_hz(nt), int(1.2 * SR), 0.35, int(t * 77)), 0.3), t + 0.12)
        t += g.choice([0.6, 0.9, 1.2])
    out = delay(out, 0.42, 0.45, 0.4)
    drone = strings_note(root - 12, L + 0.5, 0.4, seed) + strings_note(root - 5, L + 0.5, 0.22, seed + 2)
    wn = int(L * SR); w = np.convolve(g.standard_normal(wn), np.ones(400) / 400, mode="same")
    wind = bandpass(g.standard_normal(wn), 250, 1400) * (0.4 + 0.6 * np.abs(np.sin(np.arange(wn) / SR * 0.35)))[:]
    mix = reverb(out * 0.5, 3.5, 0.45) + reverb(drone * 0.55, 3.0, 0.3)
    mix[:wn] += stereo(wind * 0.08, 0)[:len(mix[:wn])]
    return mix[: int(L * SR)]


def style_clinic(L, energy=0.6, seed=6):
    bpm = 116; beat = 60 / bpm; n = int((L + 2) * SR)
    pulse = np.zeros((n, 2)); tick = np.zeros((n, 2))
    chords = [[45, 52, 57, 60], [41, 48, 53, 57]]           # Am, F (cold, low)
    for i in range(int(L / (beat / 2)) + 1):
        tt = i * beat / 2; ch = chords[int(tt / (beat * 8)) % 2]
        ln = int(beat / 2 * 0.8 * SR); tl = np.arange(ln) / SR
        x = (np.sin(2 * np.pi * note_hz(ch[0] - 12) * tl) + 0.4 * np.sign(np.sin(2 * np.pi * note_hz(ch[0]) * tl)) * 0.3) * np.exp(-tl * 8)
        place(pulse, stereo(lowpass(x, 900), 0), tt, 0.32)
        if i % 2 == 0:
            place(tick, sfx_tick(seed + i) * 0.7, tt)
    pad = np.zeros((n, 2))
    for b in range(int(L / (beat * 8)) + 1):
        ch = chords[b % 2]; ln = int(beat * 8 * SR)
        for j, nt in enumerate(ch[1:]):
            place(pad, lowpass(supersaw(note_hz(nt), ln, seed=seed + b * 5 + j), 1100) * env_adsr(ln, 0.6, 0.2, 0.8, 0.6)[:, None] * 0.09, b * beat * 8)
    mix = pulse + tick * 0.5 + reverb(pad, 2.4, 0.35)
    return mix[: int(L * SR)]


def style_suspense(L, energy=0.4, seed=7):
    n = int((L + 2) * SR)
    out = np.zeros((n, 2))
    place(out, strings_note(38, L + 0.5, 0.5, seed) + strings_note(45, L + 0.5, 0.35, seed + 1) + strings_note(51, L + 0.5, 0.18, seed + 2), 0)
    t = np.arange(n) / SR
    high = stereo(np.sin(2 * np.pi * note_hz(86) * t) * 0.02 * np.clip(t / max(L, 1), 0, 1), 0)
    return reverb(out * 0.6 + high, 3.5, 0.4)[: int(L * SR)]


def style_piano(L, energy=0.5, seed=8):
    return compose_piano(L + 0.01, [{"start": 0, "energy": energy}], key="D", bpm=66, seed=seed)[: int(L * SR)]


STYLES = {"oriental": style_oriental, "mountain": style_mountain, "clinic": style_clinic,
          "suspense": style_suspense, "piano": style_piano}


def compose_suite(length, segs, xf=0.9):
    """segs: [{start, end, style, energy, pause}] -> one score, styles crossfaded at scene boundaries."""
    n = int((length + 1) * SR)
    out = np.zeros((n, 2))
    merged = []
    for s in segs:  # merge neighbours with the same style into one continuous cue
        if merged and merged[-1]["style"] == s["style"] and not s.get("pause"):
            merged[-1]["end"] = s["end"]; merged[-1]["energy"] = max(merged[-1]["energy"], s["energy"])
        else:
            merged.append(dict(s))
    for i, s in enumerate(merged):
        a = max(0.0, s["start"] - (xf / 2 if i else 0))
        b = min(length, s["end"] + (xf / 2 if i < len(merged) - 1 else 0))
        x = STYLES.get(s["style"], style_piano)(b - a, s.get("energy", 0.5), seed=11 + i)
        x = x / (np.sqrt((x ** 2).mean()) + 1e-9) * 0.12                       # equal loudness per cue
        m = len(x); f = int(xf * SR)
        env = np.ones(m)
        if i: env[:f] = np.linspace(0, 1, min(f, m))[:min(f, m)]
        if i < len(merged) - 1: env[-f:] = np.minimum(env[-f:], np.linspace(1, 0, f))
        if s.get("pause"):
            p = int(float(s["pause"]) * SR); env[:p] = 0; env[p:p + f] *= np.linspace(0, 1, len(env[p:p + f]))
        place(out, x * env[:, None], a)
    out = highpass(out, 55)                      # keep the low end clean under dialogue
    out = softclip(out * 1.6, 1.1) * 0.8
    out = out[: int(length * SR)]
    fade = int(min(2.5, length / 5) * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    return out


def sfx_shing(seed=21):
    n = int(1.8 * SR); t = np.arange(n) / SR; g = rng(seed)
    scrape = bandpass(g.standard_normal(n), 2500, 9000) * np.exp(-t * 6) * np.clip(t / 0.05, 0, 1) * (t < 0.45)
    ring = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) / (k + 1) for k, (f, d) in enumerate([(2100, 2.5), (3370, 3.2), (5230, 4.5), (7110, 6)]))
    return reverb(stereo(scrape * 0.4 + ring * 0.35 * np.clip((t - 0.3) / 0.02, 0, 1)), 2.0, 0.3) * 0.7


def sfx_heartbeat(seed=22, beats=8, bpm=62):
    n = int((beats * 60 / bpm + 1) * SR); out = np.zeros(n)
    k = kick(int(0.35 * SR)); k = lowpass(k, 180)
    for b in range(beats):
        t0 = b * 60 / bpm
        for off, g in ((0, 1.0), (0.22, 0.7)):
            i = int((t0 + off) * SR); out[i:i + len(k)] += k[: n - i] * g * (1 - b / beats * 0.4)
    return stereo(out * 0.7)


def sfx_ding(seed=23):
    n = int(1.0 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1318 * t) * np.exp(-t * 6) * (t < 0.5) + np.sin(2 * np.pi * 1760 * t) * np.exp(-(t - 0.12).clip(0) * 6) * (t > 0.12)
    return reverb(stereo(x * 0.3), 1.0, 0.2)
