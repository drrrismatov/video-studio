#!/usr/bin/env python3
"""AI Video Studio — pipeline orchestrator.

  python3 studio.py new <slug>                 # create project skeleton (script.json)
  python3 studio.py storyboard <slug>          # VO + keyframes contact sheet for approval
  python3 studio.py build <slug> [--draft]     # full production: VO, render, music, edit, mix
  python3 studio.py stage <slug> vo|render|music|edit
  python3 studio.py ingest <slug> part1.mp4 part2.mp4 …   # join uploaded parts -> media/
  python3 studio.py look <slug> <file.mp4|inbox:file.mp4>  # contact sheet + speech map of footage
  python3 studio.py inbox                      # videos in the Inbox folder (read-only source)
  python3 studio.py pull                       # fetch new videos from the cloud Inbox (GitHub release "inbox")
  python3 studio.py voices                     # list voices

Projects live in projects/<slug>/ ; final video -> projects/<slug>/out/<slug>.mp4
"""
from __future__ import annotations

import hashlib
import inspect
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

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts", ".3gp"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".svg", ".webp", ".heic"}
AUDIO_EXT = {".m4a", ".mp3", ".wav", ".ogg", ".opus", ".aac", ".flac", ".amr", ".caf"}


def inbox_dir() -> Path:
    """Папка «Входящие»: студия только ЧИТАЕТ отсюда видео. Путь: $STUDIO_INBOX или ./inbox"""
    import os
    return Path(os.environ.get("STUDIO_INBOX") or ROOT / "inbox").expanduser()


def resolve_src(src: str, base: Path) -> Path:
    if str(src).startswith("inbox:"):
        p = (inbox_dir() / src[6:]).resolve()
        if inbox_dir().resolve() not in p.parents:
            raise SystemExit(f"запрещено: {src} вне папки Входящие")
        return p
    p = Path(src)
    return p if p.is_absolute() else base / p


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
            text = re.sub(r"\+([аеёиоуыэюяАЕЁИОУЫЭЮЯ])", "\\1\u0301", text)  # «век+а» -> stress on last syllable
            if not text:
                sc["_vo"] = None
                continue
            v = sc.get("voice", voice)
            key = h([text, v, sc.get("voice_speed", speed), sc.get("voice_fx")])
            f = self.build / "vo" / f"{sc['id']}.wav"
            if cache.get(sc["id"], {}).get("key") != key or not f.exists():
                log(f"озвучка {sc['id']} ({v})")
                dur = audio.tts(text, f, v, sc.get("voice_speed", speed))
                if sc.get("voice_fx"):
                    dur = audio.voice_fx(f, sc["voice_fx"])
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
            lead = sc.get("lead", 0.6 if i == 0 else td_in + 0.25)
            vo = sc["_vo"]["dur"] if sc.get("_vo") else 0
            tail = 0.7 + td_out
            dur = max(sc.get("min_duration", 3.0), lead + vo + tail if vo else 0)
            if sc.get("template") in ("footage", "mosaic") and "out" in sc:
                if sc.get("audio", True) and not vo:
                    lead = 0.0  # live sound starts with the picture
                dur = max(dur, sc["out"] - sc.get("in", 0) + (td_out if sc.get("audio", True) else 0))
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
        if sc.get("captions") is not None:
            if sc.get("subs") is False:
                return []
            off = sc.get("in", 0)
            return [{"start": round(c["start"] - off, 2), "end": round(c["end"] - off, 2), "text": c["text"]}
                    for c in sc["captions"] if c["end"] > off + 0.3 and c["start"] < sc.get("out", 1e9) - 0.3]
        text = (sc.get("narration") or "").replace("*", "").replace("_", "").replace("+", "").replace("\u0301", "").strip()
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

    def mouth_env(self, wav):
        """Lip-sync curve: per-frame mouth opening 0..1 from voice loudness (cartoon style, slightly snappy)."""
        import numpy as np
        x = np.abs(audio.read_wav(Path(wav))).mean(axis=1)
        hop = audio.SR // self.fps
        n = len(x) // hop
        r = np.sqrt(np.array([np.mean(x[i * hop:(i + 1) * hop] ** 2) for i in range(n)]) + 1e-12)
        ref = np.percentile(r, 92) + 1e-9
        m = np.clip((r / ref - 0.12) * 1.25, 0, 1)
        m = np.round(np.convolve(m, [0.25, 0.5, 0.25], mode="same") * 4) / 4   # 5 mouth shapes
        return [round(float(v), 2) for v in m]

    def scene_payload(self, sc, i):
        if sc.get("template") == "cartoon" and sc.get("_vo"):
            sc.setdefault("data", {})
            sc["data"]["env"] = self.mouth_env(sc["_vo"]["file"])
            sc["data"]["envLead"] = sc["_t"]["lead"]
            sc["data"]["fps"] = self.fps
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
        for st, sc in zip(stills, self.scenes):
            if sc.get("template") in ("footage", "mosaic"):
                ov = sc.get("overlay") or {}
                st["scene"].update(template=ov.get("template", "none"), data=ov.get("data", {}), transparent=True)
                if sc.get("overlay", {}).get("template") == "lower":
                    st["t"] = 2.5
        self.run_render({"width": self.W, "height": self.H, "fps": self.fps, "stills": stills})
        for st, sc in zip(stills, self.scenes):
            if sc.get("template") == "mosaic":
                bg = self.build / "stills" / f"{sc['id']}.bg.png"
                subprocess.run(self.mosaic_cmd(sc, str(bg), st["out"], ss=st["t"], frames=1), check=True)
                bg.replace(st["out"])
                continue
            if sc.get("template") == "footage":
                bg = self.build / "stills" / f"{sc['id']}.bg.png"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{sc.get('in', 0) + min(st['t'], sc['out'] - sc.get('in', 0) - 0.1):.2f}",
                                "-i", str(self.media(sc["src"])), "-i", st["out"], "-filter_complex",
                                f"[0:v]{self.footage_vf(sc)}[b];[b][1:v]overlay=0:0", "-frames:v", "1", str(bg)], check=True)
                bg.replace(st["out"])
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
        clips, footage_todo, cache_f = [], [], self.build / "clips" / "cache.json"
        cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
        for i, sc in enumerate(self.scenes):
            p = self.scene_payload(sc, i)
            out = self.build / "clips" / f"{sc['id']}.mp4"
            key = h([p, tpl_key, self.W, self.H, self.fps])
            sc["_clip"] = str(out)
            if sc.get("template") in ("footage", "mosaic"):
                key = h([key, self.media(sc["src"]).stat().st_mtime, {k: v for k, v in sc.items() if not k.startswith("_")},
                         inspect.getsource(Project.footage_vf), inspect.getsource(Project.render_footage)])
                if cache.get(sc["id"]) != key or not out.exists():
                    ov = sc.get("overlay") or {}
                    p.update(template=ov.get("template", "none"), data=ov.get("data", {}), transparent=True)
                    sc["_ovl"] = str(self.build / "clips" / f"{sc['id']}.ovl.mov")
                    clips.append({"scene": p, "out": sc["_ovl"]})
                    footage_todo.append(sc)
                    cache[sc["id"]] = key
                continue
            if cache.get(sc["id"]) != key or not out.exists():
                clips.append({"scene": p, "out": str(out)})
                cache[sc["id"]] = key
        if clips:
            log(f"рендер {len(clips)} сцен {self.W}x{self.H}@{self.fps}")
            self.run_render({"width": self.W, "height": self.H, "fps": self.fps, "clips": clips,
                             "concurrency": self.script.get("concurrency", 3)})
        else:
            log("рендер: все сцены в кеше")
        for sc in footage_todo:
            self.render_footage(sc)
        cache_f.write_text(json.dumps(cache, indent=1))

    # ---------------------------------------------------------- live footage
    def media(self, src) -> Path:
        return resolve_src(src, self.dir)

    def footage_vf(self, sc):
        """Real video: cover/blur-fit to format, slow push-in, grade, unmirror. Faces untouched."""
        src, t = self.media(sc["src"]), sc["_t"]
        D, z = t["dur"], sc.get("zoom", 1.05)
        W, H = self.W, self.H
        fit = sc.get("fit", "auto")
        if fit == "auto":
            pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                 "stream=width,height:stream_side_data=rotation", "-of", "json", str(src)],
                                capture_output=True, text=True).stdout
            st = json.loads(pr)["streams"][0]
            sw, sh = st["width"], st["height"]
            if any(abs(int(d.get("rotation", 0))) == 90 for d in st.get("side_data_list", [])):
                sw, sh = sh, sw
            fit = "blur" if (sw >= sh) != (W >= H) else "cover"
        push = f"scale=w='trunc({W}*(1+({z}-1)*t/{D})/2)*2':h=-2:eval=frame,crop={W}:{H}"
        if fit == "blur":  # whole frame visible (faces never cropped), blurred fill behind
            vf = (f"fps={self.fps},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"boxblur=40:2,eq=brightness=-0.08[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
                  f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{push},setsar=1")
        else:
            vf = f"fps={self.fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{push},setsar=1"
        if sc.get("speed"):
            vf = f"setpts=PTS/{sc['speed']}," + vf
        if sc.get("sharpen"):  # low-res phone source: gentle detail recovery after upscale
            vf += ",unsharp=5:5:0.5:5:5:0.0"
        if sc.get("hflip"):  # selfie camera mirror -> true orientation (text readable)
            vf = "hflip," + vf
        if sc.get("look"):
            vf += "," + {"warm": "colorbalance=rs=.05:bs=-.05", "cool": "colorbalance=rs=-.04:bs=.06",
                         "bw": "hue=s=0", "punch": "eq=contrast=1.1:saturation=1.15"}.get(sc["look"], "null")
        return vf

    def mosaic_cmd(self, sc, out, ovl, ss=0.0, frames=None):
        """All doctors on one screen: grid of live cells, face-centred crops, staggered fade-in."""
        cells = sc["cells"]; W, H = self.W, self.H
        cols = sc.get("cols", 3); rows = (len(cells) + cols - 1) // cols
        gap = sc.get("gap", 10)
        cw, ch = (W - gap * (cols + 1)) // cols // 2 * 2, (H - gap * (rows + 1)) // rows // 2 * 2
        D = sc["_t"]["dur"]; stg = sc.get("stagger", 0.35)
        ins, fc, lay = [], [], []
        for i, c in enumerate(cells):
            ins += ["-stream_loop", "-1", "-ss", f"{c.get('in', 0) + ss:.3f}", "-i", str(self.media(c["src"]))]
            fy = c.get("face", 0.4)
            pre = "hflip," if c.get("hflip") else ""
            fc.append(f"[{i}:v]{pre}fps={self.fps},scale={cw}:-2,crop={cw}:{ch}:0:'min(max(ih*{fy}-{ch}/2,0),ih-{ch})',"
                      f"colorbalance=rs=.04:bs=-.04,setsar=1" + ("" if frames else f",fade=t=in:st={i * stg:.2f}:d=0.6") + f"[c{i}]")
            lay.append(f"{gap + (i % cols) * (cw + gap)}_{gap + (i // cols) * (ch + gap)}")
        n = len(cells)
        fc.append("".join(f"[c{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={'|'.join(lay)}:fill=0x050404[g]")
        fc.append(f"[g]pad={W}:{H}:0:0:color=0x050404,scale=w='trunc({W}*(1+0.04*t/{D})/2)*2':h=-2:eval=frame,crop={W}:{H}[gz]")
        fc.append(f"[gz][{n}:v]overlay=0:0:format=auto,format=yuv420p[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", *ins, "-i", ovl, "-filter_complex", ";".join(fc), "-map", "[v]"]
        if frames:
            cmd += ["-frames:v", str(frames)]
        else:
            cmd += ["-t", f"{D:.3f}", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16"]
        return cmd + [out]

    def render_footage(self, sc):
        if sc.get("template") == "mosaic":
            log(f"мозаика {sc['id']}: {len(sc['cells'])} врачей")
            subprocess.run(self.mosaic_cmd(sc, sc["_clip"], sc["_ovl"]), check=True)
            return
        src, t = self.media(sc["src"]), sc["_t"]
        D = t["dur"]
        vf = self.footage_vf(sc)
        log(f"видео {sc['id']}: {src.name} {sc.get('in', 0)}–{sc.get('out', '…')}s")
        cmd = ["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-ss", str(sc.get("in", 0)), "-i", str(src),
               "-i", sc["_ovl"], "-filter_complex", f"[0:v]{vf}[b];[b][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
               "-map", "[v]", "-t", f"{D:.3f}", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16", sc["_clip"]]
        subprocess.run(cmd, check=True)

    def level_dialog(self, f, target=0.11):
        """Phones record at wildly different levels: bring every voice to the same loudness, then tame peaks."""
        import numpy as np
        from scipy import signal as sg
        x = audio.read_wav(f)
        x = audio.highpass(x, 90)
        m = np.abs(x).mean(axis=1)
        win = int(0.03 * audio.SR)
        e = np.sqrt(np.convolve(m ** 2, np.ones(win) / win, mode="same"))
        active = e > max(e.max() * 0.08, 1e-4)
        rms = np.sqrt((x[active] ** 2).mean()) if active.any() else np.sqrt((x ** 2).mean())
        x = x * min(target / max(rms, 1e-5), 30)
        env = sg.lfilter([0.003], [1, -0.997], np.abs(x).max(axis=1))  # gentle compressor above 0.3
        g = np.where(env > 0.3, (0.3 / np.maximum(env, 1e-6)) ** 0.5, 1.0)
        x = audio.softclip(x * g[:, None], 1.2) * 0.95
        audio.write_wav(f, x)

    def footage_audio(self):
        out = []
        for sc in self.scenes:
            if sc.get("template") not in ("footage", "mosaic") or not sc.get("audio", True):
                continue
            f = self.build / "vo" / f"{sc['id']}.live.wav"
            dur = sc.get("audio_out", sc.get("out", sc.get("in", 0) + sc["_t"]["dur"])) - sc.get("in", 0)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(sc.get("in", 0)), "-t", f"{dur:.3f}",
                            "-i", str(self.media(sc["src"])), "-vn", "-ac", "2", "-ar", str(audio.SR),
                            "-af", "highpass=f=70,afftdn=nr=10:nf=-40,afade=t=in:d=0.04,areverse,afade=t=in:d=0.08,areverse", str(f)], check=False)
            if f.exists() and f.stat().st_size > 1000:
                self.level_dialog(f)
                out.append({"file": str(f), "start": sc["_t"]["start"], "gain": sc.get("volume", 1.0)})
        return out

    # ---------------------------------------------------------- music + mix
    def stage_music(self):
        m = self.script.get("music", {})
        secs = []
        for sc in self.scenes:
            secs.append({"start": sc["_t"]["start"], "energy": sc.get("energy", 0.5), "pause": bool(sc.get("music_pause"))})
            if sc.get("music_pause") and isinstance(sc["music_pause"], (int, float)):  # pause only for N seconds
                secs.append({"start": sc["_t"]["start"] + sc["music_pause"], "energy": sc.get("energy", 0.5)})
        if m.get("file"):
            log("музыка: используем файл " + m["file"])
            return
        if m.get("mood") == "suite":
            segs = []
            for i, sc in enumerate(self.scenes):
                end = self.scenes[i + 1]["_t"]["start"] if i + 1 < len(self.scenes) else self.length
                segs.append({"start": sc["_t"]["start"], "end": end, "style": sc.get("music_style", "piano"),
                             "energy": sc.get("energy", 0.5), "pause": sc.get("music_pause")})
            log("музыка: сюита — " + " → ".join(dict.fromkeys(x["style"] for x in segs)))
            audio.write_wav(self.build / "music.wav", audio.compose_suite(self.length, segs))
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
                sfx.append({"kind": "impact", "start": t["start"] + t["td_in"] + sc.get("hit_offset", 0), "gain": 0.9})
            if sc.get("riser"):
                sfx.append({"kind": "riser", "start": t["start"] + t["td_in"], "gain": 0.7})
            for fx in sc.get("sfx", []):  # scene-level effects, e.g. {"kind": "applause", "at": 0.3, "gain": 0.5}
                sfx.append({"kind": fx["kind"], "start": t["start"] + fx.get("at", 0), "gain": fx.get("gain", 0.6)})
        music = m.get("file") or str(self.build / "music.wav")
        log("сведение: голос + музыка (sidechain) + эффекты → −14 LUFS")
        audio.mix({"length": self.length, "vo": vo + self.footage_audio(), "music": music, "sfx": sfx}, self.build / "mix.wav",
                  music_vol=m.get("volume", 0.8), duck=m.get("duck", 0.3))

    def master_loudness(self, final, target=-14.0):
        """Measure the finished file and trim audio to exactly the streaming target (video stream copied)."""
        out = subprocess.run(["ffmpeg", "-i", str(final), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
        if not m:
            return
        delta = target - float(m[-1])
        peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", subprocess.run(["ffmpeg", "-i", str(final), "-af", "ebur128=peak=true", "-f", "null", "-"],
                                                                     capture_output=True, text=True).stderr)
        if abs(delta) < 0.3 and (not peak or float(peak[-1]) < -1.0):
            return
        log(f"мастеринг громкости: {float(m[-1]):.1f} → {target} LUFS")
        tmp = final.with_suffix(".lufs.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(final), "-c:v", "copy", "-af", f"volume={delta:.2f}dB,alimiter=limit=0.89:level=false",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)], check=True)
        tmp.replace(final)

    # ---------------------------------------------------------- edit
    def stage_edit(self):
        g = self.script.get("grade", {})
        inputs, fc = [], []
        for sc in self.scenes:
            inputs += ["-i", sc["_clip"]]
        for i in range(len(self.scenes)):  # normalise timebase/fps so cut+xfade chains mix safely
            fc.append(f"[{i}:v]fps={self.fps},format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[n{i}]")
        prev = "[n0]"
        for i, sc in enumerate(self.scenes[1:], start=1):
            t = sc["_t"]
            out = f"[v{i}]"
            if t["tr_in"] == "cut" or t["td_in"] == 0:
                fc.append(f"{prev}[n{i}]concat=n=2:v=1:a=0,settb=AVTB{out}")
            else:
                tr = t["tr_in"] if t["tr_in"] in XFADE else "fade"
                fc.append(f"{prev}[n{i}]xfade=transition={tr}:duration={t['td_in']}:offset={t['start']:.3f},settb=AVTB{out}")
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
        self.master_loudness(final)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{self.scenes[0]['_t']['dur'] * 0.7:.2f}", "-i", str(final),
                        "-frames:v", "1", str(self.out / "poster.jpg")], check=True)
        log(f"ГОТОВО → {final}  ({self.length:.1f} c)")
        return final


def cmd_ingest(slug, files, name=None):
    """Join uploaded parts (≤30 MB each) into one source file in projects/<slug>/media/."""
    d = ROOT / "projects" / slug / "media"
    d.mkdir(parents=True, exist_ok=True)
    files = [Path(f).resolve() if Path(f).exists() else resolve_src("inbox:" + f.removeprefix("inbox:"), ROOT) for f in files]
    name = name or re.sub(r"[_-]?(part)?\d+$", "", files[0].stem) or "clip"
    out = d / f"{name}.mp4"
    if len(files) == 1:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(files[0]), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    else:
        lst = d / f"{name}.txt"
        lst.write_text("".join(f"file '{f}'\n" for f in files))
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
        if r.returncode:  # different codecs/sizes -> re-encode
            ins = sum((["-i", str(f)] for f in files), [])
            fc = "".join(f"[{i}:v][{i}:a]" for i in range(len(files))) + f"concat=n={len(files)}:v=1:a=1[v][a]"
            subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                            "-c:v", "libx264", "-crf", "17", "-c:a", "aac", "-b:a", "192k", str(out)], check=True)
        lst.unlink()
    log(f"исходник → {out}")
    cmd_look(slug, out.name)


def cmd_look(slug, name, every=None):
    """Make the footage visible to the director: probe, timecoded contact sheet, speech map."""
    from PIL import Image, ImageDraw, ImageFont
    src = resolve_src(name, ROOT / "projects" / slug / "media")
    (ROOT / "projects" / slug / "media").mkdir(parents=True, exist_ok=True)  # outputs go to project; inbox stays read-only
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(src)],
                                     capture_output=True, text=True).stdout)
    dur = float(info["format"]["duration"])
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    every = every or max(1.0, round(dur / 24, 1))
    tmp = ROOT / "projects" / slug / "media" / f".{src.stem}_thumbs"
    tmp.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", f"fps=1/{every},scale=360:-2", str(tmp / "%04d.jpg")], check=True)
    thumbs = sorted(tmp.glob("*.jpg"))
    im0 = Image.open(thumbs[0]); tw, th = im0.size
    cols = 6 if tw > th else 8
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 26)), "#111")
    dr = ImageDraw.Draw(sheet)
    f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 18)
    for i, p in enumerate(thumbs):
        x, y = (i % cols) * tw, (i // cols) * (th + 26)
        sheet.paste(Image.open(p), (x, y))
        dr.text((x + 6, y + th + 2), f"{int(i * every // 60)}:{i * every % 60:04.1f}", font=f, fill="#ffd166")
    sheet_p = ROOT / "projects" / slug / "media" / (src.stem + ".sheet.jpg")
    sheet.save(sheet_p, quality=85)
    for p in thumbs: p.unlink()
    tmp.rmdir()
    sil = subprocess.run(["ffmpeg", "-v", "info", "-i", str(src), "-af", "silencedetect=n=-35dB:d=0.6", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    marks = re.findall(r"silence_(start|end): ([\d.]+)", sil)
    print(json.dumps({"file": str(src), "duration": round(dur, 2), "size": f"{v['width']}x{v['height']}",
                      "fps": v.get("r_frame_rate"), "has_audio": any(s["codec_type"] == "audio" for s in info["streams"]),
                      "silences": marks[:60], "sheet": str(sheet_p), "sheet_every_s": every}, ensure_ascii=False, indent=1))


def cmd_inbox():
    """Список видео во «Входящих» (только видеофайлы, только эта папка), отметка — использовалось ли."""
    d = inbox_dir()
    d.mkdir(parents=True, exist_ok=True)
    used = set()
    for sj in (ROOT / "projects").glob("*/script.json"):
        used |= set(re.findall(r'"inbox:([^"]+)"', sj.read_text()))
    rows = []
    for f in sorted(d.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix.lower() not in VIDEO_EXT | IMAGE_EXT | AUDIO_EXT or f.name.startswith("."):
            continue
        pr = "" if f.suffix.lower() in IMAGE_EXT else subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                            capture_output=True, text=True).stdout.strip()
        rows.append({"file": f.name, "src": f"inbox:{f.name}", "mb": round(f.stat().st_size / 2**20, 1),
                     "sec": round(float(pr or 0), 1), "new": f.name not in used,
                     "added": time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))})
    print(json.dumps({"inbox": str(d), "videos": rows}, ensure_ascii=False, indent=1))


REPO = "drrrismatov/video-studio"
INBOX_TAG = "inbox"


def cmd_pull():
    """Облачные «Входящие»: скачать новые видео из GitHub-релиза `inbox` (до 2 ГБ на файл) в inbox/."""
    import urllib.request
    d = inbox_dir()
    d.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(f"https://api.github.com/repos/{REPO}/releases/tags/{INBOX_TAG}", timeout=30) as r:
            rel = json.load(r)
    except Exception as e:
        print(f"Облачные Входящие ещё не созданы (релиз '{INBOX_TAG}'): {e}")
        print(f"Создать: https://github.com/{REPO}/releases/new?tag={INBOX_TAG}&title=Входящие")
        return
    got = 0
    for a in rel.get("assets", []):
        name = a["name"].removeprefix("default.")
        ctype = a.get("content_type", "")
        if Path(name).suffix.lower() not in VIDEO_EXT | IMAGE_EXT | AUDIO_EXT:
            if not ctype.startswith(("video/", "image/", "audio/")):
                continue
            name += {"video/quicktime": ".mov", "video/x-matroska": ".mkv", "video/webm": ".webm", "audio/mpeg": ".mp3",
                     "audio/mp4": ".m4a", "audio/x-m4a": ".m4a", "audio/wav": ".wav", "audio/ogg": ".ogg"}.get(ctype, ".mp4")
        dst = d / name
        if dst.exists() and dst.stat().st_size == a["size"]:
            continue
        log(f"скачиваю {a['name']} ({a['size'] / 2**20:.0f} МБ)")
        tmp = dst.with_name("." + dst.name + ".part")
        subprocess.run(["curl", "-sSL", "--retry", "4", "-H", "Accept: application/octet-stream", "-o", str(tmp), a["url"]], check=True)
        if tmp.stat().st_size != a["size"]:
            tmp.unlink()
            raise SystemExit(f"обрыв загрузки {a['name']}, повторите pull")
        tmp.rename(dst)
        got += 1
    log(f"новых видео: {got}")
    cmd_inbox()


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
    if a[0] == "ingest":
        return cmd_ingest(a[1], a[2:])
    if a[0] == "inbox":
        return cmd_inbox()
    if a[0] == "pull":
        return cmd_pull()
    if a[0] == "look":
        return cmd_look(a[1], a[2])
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
