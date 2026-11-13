"""Build timed captions from ASR: whisper text (correct spelling) aligned to zipformer word times."""
import difflib, json, re, sys

def norm(w): return re.sub(r"[^\wё]", "", w.lower().replace("ё", "е"))

def build(asr_json, maxc=46):
    d = json.load(open(asr_json))
    W = " ".join(s["text"] for s in d["text"]).split()
    Z = d["words_ru"]
    sm = difflib.SequenceMatcher(None, [norm(w) for w in W], [norm(z["w"]) for z in Z], autojunk=False)
    t = [None] * len(W)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n): t[a + k] = (Z[b + k]["t"], Z[b + k]["end"])
    known = [i for i, x in enumerate(t) if x]
    for i in range(len(W)):  # interpolate unmatched words
        if t[i] is None:
            prev = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
            if prev is not None and nxt is not None:
                f = (i - prev) / (nxt - prev); s0 = t[prev][1] + (t[nxt][0] - t[prev][1]) * f
                t[i] = (s0, s0 + 0.3)
            elif prev is not None: t[i] = (t[prev][1], t[prev][1] + 0.4)
            else: t[i] = (t[nxt][0] - 0.4, t[nxt][0])
    caps, cur, cs = [], [], None
    for i, w in enumerate(W):
        if cs is None: cs = t[i][0]
        cur.append(w)
        line = " ".join(cur)
        end_sent = w.endswith((".", "!", "?"))
        nxtlen = len(line) + 1 + (len(W[i + 1]) if i + 1 < len(W) else 0)
        comma = w.endswith((",", "—", ":")) and len(line) > 26
        if end_sent or comma or nxtlen > maxc or i == len(W) - 1:
            caps.append({"start": round(cs - 0.05, 2), "end": round(t[i][1] + 0.15, 2), "text": line})
            cur, cs = [], None
    merged = []
    for c in caps:  # glue flicker-short or tiny lines to the previous one
        if merged and ((c["end"] - c["start"]) < 0.8 or len(c["text"]) < 12) and len(merged[-1]["text"]) + len(c["text"]) < maxc + 14:
            merged[-1]["text"] += " " + c["text"]; merged[-1]["end"] = c["end"]
        else:
            merged.append(c)
    caps = merged
    for a, b in zip(caps, caps[1:]):  # no overlaps, no flicker gaps
        if b["start"] - a["end"] < 0.35: a["end"] = b["start"]
    return caps

if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1]), ensure_ascii=False, indent=1))
