#!/usr/bin/env python3
"""AI Video Studio — pipeline orchestrator.

  python3 studio.py new <slug>                 # create project skeleton (script.json)
  python3 studio.py storyboard <slug>          # VO + keyframes contact sheet for approval
  python3 studio.py build <slug> [--draft]     # full production: VO, render, music, edit, mix
  python3 studio.py stage <slug> vo|render|music|edit
  python3 studio.py voices                     # list voices

Projects live in projects/<slug>/ ; final video -> projects/<slug>/out/<slug>.mp4
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "engine"))
import audio  # noqa: E402

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}
XFADE = {"fade", "fadeblack", "fadewhite", "dissolve", "slideleft", "slideright", "slideup", "slidedown",
         "circleopen", "circleclose", "zoomin", "wipeleft", "wiperight", "smoothleft", "smoothright",
         "smoothup", "radial", "pixelize", "hblur", "distance", "squeezev", "diagtl", "cut"}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def h(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


class Project:
    def __init__(self, slug: str):
        self.slug = slug
        self.dir = ROOT / "projects" / slug
        self.build = self.dir / "build"
        self.out = self.dir / "out"
        for d in (self.build / "vo", self.build / "clips", self.build / "stills", self.out):
            d.mkdir(parents=True, exist_ok=True)
        self.script = json.loads((self.dir / "script.json").read_text())
        s = self.script
        self.W, self.H = FORMATS[s.get("format", "16:9")]
        self.fps = s.get("fps", 30)
        self.scenes = s["scenes"]
        for i, sc in enumerate(self.scenes):
            sc.setdefault("id", f"s{i + 1:02d}")

    # ---------------------------------------------------------- voice
    def stage_vo(self):
        s = self.script
        voice, speed = s.get("voice", "dmitri"), s.get("voice_speed", 1.0)
        cache_f = self.build / "vo" / "cache.json"
        cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
        for sc in self.scenes:
            text = sc.get("say") or sc.get("narration") or ""
            text = re.sub(r"[*_]", "", text).strip()
            if not text:
                sc["_vo"] = None
                continue
            v = sc.get("voice", voice)
            key = h([text, v, speed])
            f = self.build / "vo" / f"{sc['id']}.wav"
            if cache.get(sc["id"], {}).get("key") != key or not f.exists():
                log(f"озвучка {sc['id']} ({v})")
                dur = audio.tts(text, f, v, speed)
                cache[sc["id"]] = {"key": key, "dur": dur}
            sc["_vo"] = {"file": str(f), "dur": cache[sc["id"]]["dur"]}
        cache_f.write_text(json.dumps(cache, indent=1))

    # ---------------------------------------------------------- timing
    def plan_timing(self):
        td_default = self.script.get("transition_duration", 0.7)
        t = 0.0
        n = len(self.scenes)
        for i, sc in enumerate(self.scenes):
            tr_in = sc.get("transition", "fade" if i else "none")
            td_in = 0.0 if i == 0 or tr_in == "cut" else sc.get("transition_duration", td_default)
            nxt = self.scenes[i + 1] if i + 1 < n else None
            td_out = 0.0 if not nxt or nxt.get("transition") == "cut" else nxt.get("transition_duration", td_default)
            lead = 0.6 if i == 0 else td_in + 0.25
            vo = sc["_vo"]["dur"] if sc.get("_vo") else 0
            tail = 0.7 + td_out
            dur = max(sc.get("min_duration", 3.0), lead + vo + tail if vo else 0)
            if sc.get("duration"):
                dur = sc["duration"]
            if i == n - 1:
                dur += sc.get("hold", 1.5)
            sc["_t"] = {"start": t, "dur": round(dur, 3), "lead": lead, "td_in": td_in, "tr_in": tr_in}
            t += dur - td_out
        self.length = t + 0.0
        last = self.scenes[-1]["_t"]
        self.length = last["start"] + last["dur"]
        # subtitles (scene-relative)
        for sc in self.scenes:
            sc["_subs"] = self.subtitles(sc) if self.script.get("subtitles", True) else []

    def subtitles(self, sc):
        text = (sc.get("narration") or "").replace("*", "").replace("_", "").strip()
        if not text or not sc.get("_vo") or sc.get("subs") is False:
            return []
        maxc = 42 if self.W >= self.H else 30
        sentences = re.split(r"(?<=[.!?…])\s+", text)
        chunks = []
        for s in sentences:
            words, cur = s.split(), ""
            for w in words:
                if len(cur) + len(w) + 1 > maxc and cur:
                    chunks.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            if cur:
                chunks.append(cur)
        merged = []
        for c in chunks:  # avoid orphan fragments like "свет."
            if merged and (len(c) < 14 or len(merged[-1]) < 10) and len(merged[-1]) + len(c) < maxc + 14:
                merged[-1] += " " + c
            else:
                merged.append(c)
        chunks = merged
        total = sum(len(c) + 6 for c in chunks)
        t = sc["_t"]["lead"]
        vo = sc["_vo"]["dur"]
        out = []
        for c in chunks:
            d = vo * (len(c) + 6) / total
            out.append({"start": round(t, 3), "end": round(t + d, 3), "text": c})
            t += d
        return out

    def scene_payload(self, sc, i):
        return {
            "template": sc.get("template", "statement"), "data": sc.get("data", {}),
            "theme": sc.get("theme", self.script.get("theme", "midnight")), "accent": sc.get("accent"),
            "bg": {**self.script.get("bg", {}), **sc.get("bg", {})}, "duration": sc["_t"]["dur"],
            "subs": sc["_subs"], "seed": i + 1, "tOffset": sc["_t"]["start"],
        }

    # ---------------------------------------------------------- render
    def run_render(self, job):
        jf = self.build / "job.json"
        jf.write_text(json.dumps(job, ensure_ascii=False))
        subprocess.run(["node", str(ROOT / "engine" / "render.js"), str(jf)], check=True)

    def stage_storyboard(self):
        stills = []
        for i, sc in enumerate(self.scenes):
            p = self.scene_payload(sc, i)
            stills.append({"scene": p, "t": round(p["duration"] * 0.62, 2),
                           "out": str(self.build / "stills" / f"{sc['id']}.png")})
        log(f"раскадровка: {len(stills)} кадров")
        self.run_render({"width": self.W, "height": self.H, "fps": self.fps, "stills": stills})
        self.contact_sheet()
        self.write_storyboard_md()

    def contact_sheet(self):
        from PIL import Image, ImageDraw, ImageFont
        cols = 3 if self.W >= self.H else 4
        tw = 640 if self.W >= self.H else 360
        th = int(tw * self.H / self.W)
        rows = (len(self.scenes) + cols - 1) // cols
        pad, lab = 24, 64
        sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + lab + pad) + pad + 70), "#0e0f13")
        d = ImageDraw.Draw(sheet)
        f1 = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 30)
        f2 = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Regular.otf", 18)
        d.text((pad, 20), f"{self.script.get('title', self.slug)} — раскадровка · {self.length:.0f} c", font=f1, fill="#ffffff")
        for i, sc in enumerate(self.scenes):
            im = Image.open(self.build / "stills" / f"{sc['id']}.png").convert("RGB").resize((tw, th), Image.LANCZOS)
            x = pad + (i % cols) * (tw + pad)
            y = 70 + pad + (i // cols) * (th + lab + pad)
            sheet.paste(im, (x, y))
            t = sc["_t"]
            d.text((x, y + th + 8), f"{i + 1}. {sc.get('template')} · {t['start']:.1f}–{t['start'] + t['dur']:.1f}s", font=f2, fill="#9aa4ff")
            nar = (sc.get("narration") or "").replace("*", "")
            d.text((x, y + th + 32), (nar[:62] + "…") if len(nar) > 62 else nar, font=f2, fill="#c8ccd8")
        sheet.save(self.out / "storyboard.png")
        log(f"раскадровка → {self.out / 'storyboard.png'}")

    def write_storyboard_md(self):
        s = self.script
        lines = [f"# {s.get('title', self.slug)}", "",
                 f"**Формат:** {s.get('format', '16:9')} · **Длительность:** ~{self.length:.0f} c · "
                 f"**Голос:** {s.get('voice', 'dmitri')} · **Музыка:** {s.get('music', {}).get('mood', 'cinematic')} · "
                 f"**Стиль:** {s.get('theme', 'midnight')}", ""]
        if s.get("logline"):
            lines += [f"> {s['logline']}", ""]
        lines += ["| # | Время | Сцена (визуал) | Закадровый текст | Звук / переход |", "|---|---|---|---|---|"]
        for i, sc in enumerate(self.scenes):
            t = sc["_t"]
            vis = sc.get("visual_note") or sc.get("template")
            snd = []
            if i:
                snd.append(f"переход: {t['tr_in']}")
            if sc.get("hit"):
                snd.append("удар")
            if sc.get("riser"):
                snd.append("нарастание")
            snd.append(f"энергия {sc.get('energy', 0.5)}")
            lines.append(f"| {i + 1} | {t['start']:.1f}–{t['start'] + t['dur']:.1f}s | {vis} | "
                         f"{(sc.get('narration') or '—').replace('*', '')} | {', '.join(snd)} |")
        (self.out / "storyboard.md").write_text("\n".join(lines) + "\n")

    def stage_render(self, draft=False):
        tpl_key = h([(ROOT / "engine/web/templates.js").read_text(), (ROOT / "engine/web/player.html").read_text()])
        clips, cache_f = [], self.build / "clips" / "cache.json"
        cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
        for i, sc in enumerate(self.scenes):
            p = self.scene_payload(sc, i)
            out = self.build / "clips" / f"{sc['id']}.mp4"
            key = h([p, tpl_key, self.W, self.H, self.fps])
            sc["_clip"] = str(out)
            if cache.get(sc["id"]) != key or not out.exists():
                clips.append({"scene": p, "out": str(out)})
                cache[sc["id"]] = key
        if clips:
            log(f"рендер {len(clips)} сцен {self.W}x{self.H}@{self.fps}")
            self.run_render({"width": self.W, "height": self.H, "fps": self.fps, "clips": clips,
                             "concurrency": self.script.get("concurrency", 3)})
        else:
            log("рендер: все сцены в кеше")
        cache_f.write_text(json.dumps(cache, indent=1))

    # ---------------------------------------------------------- music + mix
    def stage_music(self):
        m = self.script.get("music", {})
        secs = [{"start": sc["_t"]["start"], "energy": sc.get("energy", 0.5)} for sc in self.scenes]
        if m.get("file"):
            log("музыка: используем файл " + m["file"])
            return
        log(f"музыка: {m.get('mood', 'cinematic')} · {self.length:.1f}s")
        x = audio.compose(self.length, secs, mood=m.get("mood", "cinematic"), key=m.get("key", "A"),
                          bpm=m.get("bpm"), seed=m.get("seed", 1))
        audio.write_wav(self.build / "music.wav", x)

    def stage_mix(self):
        m = self.script.get("music", {})
        vo = [{"file": sc["_vo"]["file"], "start": sc["_t"]["start"] + sc["_t"]["lead"]}
              for sc in self.scenes if sc.get("_vo")]
        sfx = []
        for i, sc in enumerate(self.scenes):
            t = sc["_t"]
            if i and t["tr_in"] != "cut" and sc.get("whoosh", self.script.get("whoosh", True)):
                sfx.append({"kind": "whoosh", "start": t["start"] + t["td_in"] / 2, "gain": 0.6})
            if sc.get("hit"):
                sfx.append({"kind": "impact", "start": t["start"] + t["td_in"], "gain": 0.9})
            if sc.get("riser"):
                sfx.append({"kind": "riser", "start": t["start"] + t["td_in"], "gain": 0.7})
        music = m.get("file") or str(self.build / "music.wav")
        log("сведение: голос + музыка (sidechain) + эффекты → −14 LUFS")
        audio.mix({"length": self.length, "vo": vo, "music": music, "sfx": sfx}, self.build / "mix.wav",
                  music_vol=m.get("volume", 0.8), duck=m.get("duck", 0.3))

    # ---------------------------------------------------------- edit
    def stage_edit(self):
        g = self.script.get("grade", {})
        inputs, fc = [], []
        for sc in self.scenes:
            inputs += ["-i", sc["_clip"]]
        prev = "[0:v]"
        for i, sc in enumerate(self.scenes[1:], start=1):
            t = sc["_t"]
            out = f"[v{i}]"
            if t["tr_in"] == "cut" or t["td_in"] == 0:
                fc.append(f"{prev}[{i}:v]concat=n=2:v=1:a=0{out}")
            else:
                tr = t["tr_in"] if t["tr_in"] in XFADE else "fade"
                fc.append(f"{prev}[{i}:v]xfade=transition={tr}:duration={t['td_in']}:offset={t['start']:.3f}{out}")
            prev = out
        post = [f"eq=contrast={g.get('contrast', 1.04)}:saturation={g.get('saturation', 1.06)}"]
        if g.get("vignette", True):
            post.append("vignette=PI/5")
        grain = g.get("grain", 4)
        if grain:
            post.append(f"noise=alls={grain}:allf=t")
        if g.get("letterbox"):
            bar = int(self.H * 0.1)
            post.append(f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill")
        post.append("format=yuv420p")
        fc.append(f"{prev}{','.join(post)}[vout]")
        final = self.out / f"{self.slug}.mp4"
        mix = self.build / "mix.wav"
        log("монтаж: склейка, переходы, цветокор, зерно → финал")
        cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-i", str(mix), "-filter_complex", ";".join(fc),
               "-map", "[vout]", "-map", f"{len(self.scenes)}:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
               "-c:a", "aac", "-b:a", "192k", "-t", f"{self.length:.3f}", "-movflags", "+faststart", str(final)]
        subprocess.run(cmd, check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{self.scenes[0]['_t']['dur'] * 0.7:.2f}", "-i", str(final),
                        "-frames:v", "1", str(self.out / "poster.jpg")], check=True)
        log(f"ГОТОВО → {final}  ({self.length:.1f} c)")
        return final


def cmd_new(slug):
    d = ROOT / "projects" / slug
    d.mkdir(parents=True, exist_ok=True)
    f = d / "script.json"
    if not f.exists():
        shutil.copy(ROOT / "docs" / "script.example.json", f)
    print(f)


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    if a[0] == "voices":
        print("\n".join(audio.VOICES))
        return
    if a[0] == "new":
        return cmd_new(a[1])
    p = Project(a[1])
    t0 = time.time()
    if a[0] == "storyboard":
        p.stage_vo(); p.plan_timing(); p.stage_storyboard()
    elif a[0] == "build":
        p.stage_vo(); p.plan_timing(); p.stage_render(); p.stage_music(); p.stage_mix(); p.stage_edit()
    elif a[0] == "stage":
        p.stage_vo(); p.plan_timing()
        st = a[2]
        if st == "render": p.stage_render()
        if st == "music": p.stage_music()
        if st == "mix": p.stage_mix()
        if st == "edit": p.stage_render(); p.stage_edit()
    log(f"время: {time.time() - t0:.0f} c")


if __name__ == "__main__":
    main()
