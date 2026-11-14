"""«Ничего не меняется» — Reels from the user's artworks. Two passes: voices first, then cuts placed on phrases.
Run from repo root:  python3 projects/vrach-film/make_script.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, '.'); sys.path.insert(0, 'engine')
sys.argv = sys.argv[:1]
import audio  # noqa: E402
import studio  # noqa: E402

A = str(Path('projects/vrach-reels/art').resolve()) + '/'
SLUG = 'vrach-film'
V = {
    "padishah": dict(voice="dmitri", voice_speed=0.8, voice_fx={"pitch": -3.5, "tempo": 0.9, "eq": "deep", "room": "hall"}),
    "warrior": dict(voice="ruslan", voice_speed=0.78, voice_fx={"pitch": -4, "tempo": 0.88, "eq": "deep", "grit": 0.25, "room": "tent"}),
    "woman": dict(voice="irina", voice_speed=1.05, voice_fx={"pitch": 1.5, "tempo": 1.06, "eq": "bright", "room": "clinic"}),
    "doctor": dict(voice="denis", voice_speed=0.9, voice_fx={"pitch": -2.5, "tempo": 0.86, "eq": "warm", "room": "close"}),
}
# face anchors in the artworks (percent of image)
HAKIM = (50, 36); TENT_DOC = (26, 54); CLINIC_DOC = (66, 27); ROOF_DOC = (46, 33)


def kb(a, b): return {"from": [a, 0, 0], "to": [b, 0, 0]}


S = {
    "title": "Ничего не меняется", "format": "9:16", "fps": 30, "theme": "documentary", "accent": "#e8c99a",
    "logline": "Меняются века, меняются угрозы — врач всё равно лечит. Коллеги, хватит хейтить друг друга.",
    "music": {"mood": "suite", "volume": 0.8, "duck": 0.22},
    "subtitles": True, "whoosh": True,
    "grade": {"grain": 2, "vignette": False, "contrast": 1.02, "saturation": 1.02},
    "transition_duration": 0.5,
    "scenes": [
        {"template": "shots", "lead": 4.3, "energy": 0.6, "music_style": "oriental", "transition": "none",
         "narration": "Вылечишь моего сына — | осыплю золотом. | Не вылечишь — | голову с плеч.", **V["padishah"],
         "sfx": [{"kind": "shing", "at": 0.25, "gain": 0.8}],
         "visual_note": "ХУК: ятаган в камеру → дворец, XV век → падишах / принц / лекарь",
         "data": {"dust": 60, "rays": -62, "label": "XV век", "labelAt": 2.7,
                  "hook": "Быть врачом.<br>*В любом веке.*", "hookAt": 0.2, "hookHold": 1.9}},
        {"template": "shots", "lead": 1.8, "energy": 0.5, "music_style": "mountain", "transition": "fadeblack",
         "narration": "Выживет отец — | награжу. | Умрёт... | умрёшь вместе с ним.", **V["warrior"],
         "visual_note": "Палатка в горах, ночь: воин с автоматом, раненый отец, врач опустил глаза",
         "data": {"dust": 25, "flicker": True, "label": "XX век", "labelAt": 0.4}},
        {"template": "shots", "lead": 1.3, "energy": 0.6, "music_style": "clinic", "transition": "fadeblack",
         "narration": "Либо я выздоровлю, | либо я вас засужу! | Жалобу напишу, | в соцсетях уничтожу!", **V["woman"],
         "sfx": [{"kind": "ding", "at": 0.5, "gain": 0.5}],
         "visual_note": "Сегодня: кабинет, пациентка снимает врача на телефон",
         "data": {"label": "Сегодня", "labelAt": 0.4}},
        {"template": "shots", "lead": 1.4, "energy": 0.4, "music_style": "suspense", "transition": "fadewhite", "music_pause": 0.6,
         "narration": "Меняются век+а. | Меняются угр+озы. | Не меняется одно — | врач всё равно лечит.", **V["doctor"],
         "sfx": [{"kind": "heartbeat", "at": 0.2, "gain": 0.6}],
         "visual_note": "ПОВОРОТ: три эпохи — один мудрый взгляд врача"},
        {"template": "shots", "lead": 0.8, "energy": 0.4, "music_style": "piano", "transition": "fadeblack",
         "narration": "Собираешься стать врачом — | не жди справедливости. | Не жди одобрения. | Делай это сердцем. | Ошибаются все люди. | А спасают — единицы.", **V["doctor"],
         "visual_note": "Закат над Ташкентом: уставший врач на крыше больницы",
         "data": {"dust": 20, "rays": -35}},
        {"template": "shots", "lead": 0.8, "energy": 0.6, "music_style": "piano", "transition": "fadeblack",
         "narration": "Тебя по-настоящему поймут | только те, кто носит такой же халат.", **V["doctor"],
         "visual_note": "Три врача трёх эпох рядом"},
        {"template": "lines", "energy": 0.7, "music_style": "piano", "transition": "fadeblack", "duration": 7.5, "subs": False,
         "visual_note": "Призыв: коллеги, хватит хейтить друг друга",
         "data": {"lines": ["Коллеги,", "хватит хейтить друг друга.", "Нас и так есть *кому судить*.", "Отправь это коллеге ♥"],
                  "stack": True, "size": 5.6, "lead": 0.4, "tail": 1.4}},
    ]}

Path(f'projects/{SLUG}').mkdir(parents=True, exist_ok=True)
json.dump(S, open(f'projects/{SLUG}/script.json', 'w'), ensure_ascii=False, indent=1)

# ---- pass 1: voices + timing, then find phrase boundaries
p = studio.Project(SLUG)
p.stage_vo(); p.plan_timing()


def phrases(wav):
    x = np.abs(audio.read_wav(Path(wav))).mean(axis=1)
    w = int(0.03 * audio.SR); e = np.convolve(x, np.ones(w) / w, 'same')
    act = e > max(e.max() * 0.06, 0.004)
    out, on, st = [], False, 0
    for i in range(0, len(x), int(0.01 * audio.SR)):
        if act[i] and not on: st, on = i, True
        if not act[i] and on:
            out.append([st / audio.SR, i / audio.SR]); on = False
    if on: out.append([st / audio.SR, len(x) / audio.SR])
    merged = []
    for a, b in out:  # glue gaps shorter than 0.2 s (inside a phrase)
        if merged and a - merged[-1][1] < 0.2: merged[-1][1] = b
        else: merged.append([a, b])
    return [m for m in merged if m[1] - m[0] > 0.12]


cuts = {}
for i, sc in enumerate(p.scenes):
    if not sc.get("_vo"): continue
    pj = Path(sc["_vo"]["file"]).with_suffix(".parts.json")
    ph = json.loads(pj.read_text()) if pj.exists() else phrases(sc["_vo"]["file"])
    L = sc["_t"]["lead"]; D = sc["_t"]["dur"]
    st = [L + a for a, b in ph]  # absolute phrase starts within the scene
    cuts[i] = (L, D, st, ph)
    print(f"scene {i + 1}: lead {L:.2f} dur {D:.2f} phrases {[(round(a, 2), round(b, 2)) for a, b in ph]}")

SH = {}
L, D, st, ph = cuts[0]
SH[0] = [
    {"src": A + "padishah.webp", "from": 0, "to": 2.5, "origin": "40% 52%", "kb": kb(1.0, 1.12), "shake": 0.12},
    {"src": A + "bg_palace.webp", "from": 2.5, "to": L, "origin": "60% 42%", "kb": {"from": [1.04, 0, 0], "to": [1.18, 0, -1.5]}},
    {"src": A + "padishah.webp", "from": L, "to": L + ph[0][1] * 0.55, "origin": "45% 20%", "kb": kb(1.18, 1.26)},
    {"src": A + "prince.webp", "from": L + ph[0][1] * 0.55, "to": st[1], "origin": "45% 35%", "kb": kb(1.02, 1.1)},
    {"src": A + "padishah.webp", "from": st[1], "to": st[2], "origin": "45% 22%", "kb": kb(1.05, 1.2)},
    {"src": A + "hakim.webp", "from": st[2], "to": D + 1, "origin": f"{HAKIM[0]}% {HAKIM[1]}%", "kb": kb(1.0, 1.16)}]
L, D, st, ph = cuts[1]
SH[1] = [
    {"src": A + "tent_wide.webp", "from": 0, "to": st[0] + 0.55, "origin": "50% 45%", "kb": kb(1.0, 1.08)},
    {"src": A + "father.webp", "from": st[0] + 0.55, "to": st[1], "origin": "35% 30%", "kb": kb(1.04, 1.14)},
    {"src": A + "warrior.webp", "from": st[1], "to": st[2], "origin": "45% 22%", "kb": kb(1.05, 1.15)},
    {"src": A + "tent_wide.webp", "from": st[2], "to": st[3], "origin": f"{TENT_DOC[0]}% {TENT_DOC[1]}%", "kb": kb(1.55, 1.7)},
    {"src": A + "warrior.webp", "from": st[3], "to": D + 1, "origin": "45% 20%", "kb": kb(1.25, 1.5)}]
L, D, st, ph = cuts[2]
SH[2] = [
    {"src": A + "clinic.webp", "from": 0, "to": st[1], "posFrom": [0, 50], "posTo": [35, 50], "origin": "30% 50%", "kb": kb(1.0, 1.05)},
    {"src": A + "clinic.webp", "from": st[1], "to": st[2], "pos": "78% 50%", "origin": f"{CLINIC_DOC[0]}% {CLINIC_DOC[1]}%", "kb": kb(1.45, 1.6)},
    {"src": A + "clinic.webp", "from": st[2], "to": st[3], "pos": "0% 50%", "origin": "35% 48%", "kb": kb(1.7, 1.95), "shake": 0.08},
    {"src": A + "clinic.webp", "from": st[3], "to": D + 1, "pos": "78% 50%", "origin": f"{CLINIC_DOC[0]}% {CLINIC_DOC[1]}%", "kb": kb(1.7, 1.95)}]
L, D, st, ph = cuts[3]
SH[3] = [{"from": 0, "to": D + 1, "layout": "rows", "stagger": 0.45, "panels": [
    {"src": A + "hakim.webp", "pos": f"{HAKIM[0]}% {HAKIM[1]}%", "scale": 1.35},
    {"src": A + "tent_wide.webp", "pos": f"{TENT_DOC[0]}% {TENT_DOC[1]}%", "scale": 1.9},
    {"src": A + "clinic.webp", "pos": "66% 22%", "origin": "66% 40%", "scale": 1.6}]}]
L, D, st, ph = cuts[4]
SH[4] = [
    {"src": A + "doctor_roof.webp", "from": 0, "to": st[3], "pos": "45% 50%", "origin": "45% 40%", "kb": kb(1.0, 1.1)},
    {"src": A + "clinic.webp", "from": st[3], "to": st[4], "pos": "78% 50%", "origin": f"{CLINIC_DOC[0]}% {CLINIC_DOC[1]}%", "kb": kb(1.35, 1.45)},
    {"src": A + "doctor_roof.webp", "from": st[4], "to": D + 1, "pos": "45% 50%", "origin": f"{ROOF_DOC[0]}% {ROOF_DOC[1]}%", "kb": kb(1.3, 1.5)}]
L, D, st, ph = cuts[5]
SH[5] = [{"from": 0, "to": D + 1, "layout": "cols", "stagger": 0.3, "panels": [
    {"src": A + "hakim.webp", "pos": "50% 36%", "scale": 1.05},
    {"src": A + "tent_wide.webp", "pos": "24% 54%", "origin": "24% 54%", "scale": 1.25},
    {"src": A + "doctor_roof.webp", "pos": "40% 40%", "origin": "40% 30%", "scale": 1.05}]}]

S["scenes"][3].setdefault("data", {})["subsY"] = 0.645   # subtitle on the gold line between eras, not on a face
for i, shots in SH.items():
    S["scenes"][i].setdefault("data", {})["shots"] = shots
json.dump(S, open(f'projects/{SLUG}/script.json', 'w'), ensure_ascii=False, indent=1)
print("script ready:", len(S["scenes"]), "scenes")
