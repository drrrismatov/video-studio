"""Offline speech recognition for footage (sherpa-onnx).

whisper-medium  -> accurate text (multilingual, ru/uz/en), per ~segment
zipformer-ru    -> word-level timestamps (Russian)
usage: python3 engine/asr.py <video> [lang]
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import sherpa_onnx

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets" / "asr"
SR = 16000


def load_audio(path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def segments(x: np.ndarray, max_len=25.0, min_sil=0.35):
    """Split on pauses so every chunk is < max_len seconds."""
    win = int(0.03 * SR)
    e = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, mode="same"))
    thr = max(0.01, np.percentile(e, 20) * 2.5)
    quiet = e < thr
    cuts, start, i, n = [], 0, 0, len(x)
    run = 0
    best = None
    for i in range(0, n, win):
        if quiet[i]:
            run += win
            if run >= min_sil * SR:
                best = i - run // 2
        else:
            run = 0
        if i - start >= max_len * SR and best and best > start + SR:
            cuts.append((start, best)); start = best; best = None
    cuts.append((start, n))
    return cuts


def whisper(x, lang=""):
    d = A / "sherpa-onnx-whisper-medium"
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(d / "medium-encoder.int8.onnx"), decoder=str(d / "medium-decoder.int8.onnx"),
        tokens=str(d / "medium-tokens.txt"), language=lang, task="transcribe", num_threads=4)
    out = []
    for a, b in segments(x):
        s = rec.create_stream()
        s.accept_waveform(SR, x[a:b])
        rec.decode_stream(s)
        out.append({"start": round(a / SR, 2), "end": round(b / SR, 2), "text": s.result.text.strip()})
    return out


def words_ru(x):
    d = A / "sherpa-onnx-zipformer-ru-2024-09-18"
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(d / "encoder.int8.onnx"), decoder=str(d / "decoder.int8.onnx"), joiner=str(d / "joiner.int8.onnx"),
        tokens=str(d / "tokens.txt"), num_threads=4, decoding_method="greedy_search")
    words = []
    for a, b in segments(x, max_len=20):
        s = rec.create_stream()
        s.accept_waveform(SR, x[a:b])
        rec.decode_stream(s)
        r = s.result
        cur, t0 = "", None
        for tok, ts in zip(r.tokens, r.timestamps):
            t = a / SR + ts
            if tok.startswith(("▁", " ")):
                if cur:
                    words.append({"w": cur, "t": round(t0, 2)})
                cur, t0 = tok[1:].strip(), t
            else:
                cur += tok
                t0 = t if t0 is None else t0
        if cur:
            words.append({"w": cur, "t": round(t0, 2)})
    # word end = next word start (capped)
    for i, w in enumerate(words):
        nxt = words[i + 1]["t"] if i + 1 < len(words) else w["t"] + 0.6
        w["end"] = round(min(nxt, w["t"] + 1.2), 2)
    return words


if __name__ == "__main__":
    x = load_audio(sys.argv[1])
    lang = sys.argv[2] if len(sys.argv) > 2 else ""
    res = {"file": sys.argv[1], "text": whisper(x, lang), "words_ru": words_ru(x)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
