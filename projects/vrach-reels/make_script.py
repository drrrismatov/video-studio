"""«Ничего не меняется» — cartoon Reels about doctors. Run from repo root."""
import json

V = {  # character voices
    "padishah": dict(voice="dmitri", voice_speed=0.85, voice_fx={"pitch": -3.5, "tempo": 0.9, "eq": "deep", "room": "hall"}),
    "warrior": dict(voice="ruslan", voice_speed=0.8, voice_fx={"pitch": -4, "tempo": 0.88, "eq": "deep", "grit": 0.25, "room": "tent"}),
    "woman": dict(voice="irina", voice_speed=1.1, voice_fx={"pitch": 1.5, "tempo": 1.08, "eq": "bright", "room": "clinic"}),
    "doctor": dict(voice="denis", voice_speed=0.9, voice_fx={"pitch": -2.5, "tempo": 0.86, "eq": "warm", "room": "close"}),
}
SK = {"doc": "#d9a77c", "pad": "#c98d63", "war": "#b98060", "wom": "#f1c9a8"}


def char(name, x, y, s, talk=False, **opts):
    return {"type": "char", "name": name, "x": x, "y": y, "s": s, "talk": talk, "opts": opts}


def svg(markup, **kw):
    return {"type": "svg", "x": 0, "y": 0, "s": 1, "svg": markup, **kw}


band = lambda y, c1, c2: f'<defs><linearGradient id="b{y}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs><rect x="0" y="{y}" width="1080" height="640" fill="url(#b{y})"/>'
HANDS = ('<rect width="1080" height="1920" fill="#2a1d16"/>'
         '<circle cx="250" cy="500" r="160" fill="#ffcf8a" opacity=".10"/><circle cx="860" cy="1500" r="220" fill="#ffcf8a" opacity=".08"/>'
         '<circle cx="800" cy="420" r="90" fill="#9fd3ff" opacity=".07"/>'
         # adult hand (from right) with extended index finger
         '<path d="M1180 820 C980 800,860 860,800 930 L460 930 C420 930,410 990,450 994 L760 1000 C740 1060,760 1120,820 1150 C900 1200,1060 1200,1180 1180 Z" fill="#d9a77c" stroke="#2a1a12" stroke-width="6"/>'
         '<path d="M800 1000 C850 1010,900 1000,940 980 M790 1060 C850 1080,900 1070,950 1050" stroke="#b9845c" stroke-width="5" fill="none"/>'
         '<path d="M840 1150 C900 1180,1000 1180,1080 1160" stroke="#f4f6f8" stroke-width="60"/>'
         # child hand gripping the finger
         '<path d="M180 1120 C240 1060,330 1040,400 1050 C430 1060,440 1100,420 1130 C380 1170,260 1190,180 1180 Z" fill="#e9b892" stroke="#2a1a12" stroke-width="5"/>'
         + ''.join(f'<ellipse cx="{400 + i * 34}" cy="{950 + (i % 2) * 6}" rx="22" ry="40" fill="#e9b892" stroke="#2a1a12" stroke-width="5"/>' for i in range(4))
         + '<ellipse cx="400" cy="1010" rx="28" ry="22" fill="#e9b892" stroke="#2a1a12" stroke-width="5"/>'
         '<path d="M150 1200 C200 1180,300 1180,380 1150 L380 1300 L150 1300 Z" fill="#9fc6e8" stroke="#2a1a12" stroke-width="5"/>')

S = {
    "title": "Ничего не меняется", "format": "9:16", "fps": 30, "theme": "documentary", "accent": "#e8c99a",
    "logline": "Меняются века, меняются угрозы — врач всё равно лечит. Коллеги, хватит хейтить друг друга.",
    "music": {"mood": "suite", "volume": 0.75, "duck": 0.2},
    "subtitles": True, "whoosh": True,
    "grade": {"grain": 2, "vignette": True, "contrast": 1.03, "saturation": 1.05},
    "transition_duration": 0.5,
    "scenes": [
        {"template": "cartoon", "lead": 2.6, "energy": 0.55, "music_style": "oriental", "transition": "none",
         "narration": "Вылечишь моего сына — осыплю золотом. Не вылечишь — голову с плеч.", **V["padishah"],
         "sfx": [{"kind": "shing", "at": 1.0, "gain": 0.7}],
         "visual_note": "ХУК: клинок у горла лекаря → отъезд: дворец, падишах, больной сын",
         "data": {"set": "palace", "label": "XV век", "labelAt": 3.2, "hook": "Быть врачом.<br>*В любом веке.*", "hookAt": 0.15, "hookHold": 2.3, "hookTop": "60%",
                  "cam": [[0, 790, 1050, 2.5], [1.6, 790, 1050, 2.3], [3.0, 540, 1000, 1.0], [12, 440, 980, 1.14]],
                  "actors": [char("boy", 560, 1570, 1.15),
                             char("doctor", 800, 900, 1.12, era="hakim", mood="fear", turn=-0.35, gaze=-1, sweat=0.8),
                             char("padishah", 290, 820, 1.25, talk=True, mood="angry"),
                             {"type": "arm", "x1": 470, "y1": 1140, "x2": 528, "y2": 1070, "sleeve": "#8e1b24", "skin": SK["pad"], "w": 62},
                             {"type": "prop", "name": "scimitar", "x": 530, "y": 1068, "s": 0.52, "rot": -6, "glint": [0.9, 2.1], "shake": 0.6}]}},
        {"template": "cartoon", "energy": 0.5, "music_style": "mountain", "transition": "fadeblack",
         "narration": "Выживет отец — награжу. Умрёт... умрёшь вместе с ним.", **V["warrior"],
         "visual_note": "Палатка в горах, ночь, лампа. Воин, пистолет у виска врача, больной отец",
         "data": {"set": "tent", "flicker": True, "label": "XX век", "labelAt": 0.5,
                  "cam": [[0, 560, 1010, 1.06], [10, 600, 980, 1.2]],
                  "actors": [char("oldman", 560, 1590, 1.15),
                             char("doctor", 800, 920, 1.12, era="field", mood="fear", turn=-0.35, gaze=-1, sweat=1),
                             char("warrior", 290, 880, 1.25, talk=True, mood="angry"),
                             {"type": "arm", "x1": 470, "y1": 1170, "x2": 545, "y2": 950, "sleeve": "#8a7c62", "skin": SK["war"], "w": 62},
                             {"type": "prop", "name": "pistol", "x": 545, "y": 905, "s": 0.78, "shake": 0.8}]}},
        {"template": "cartoon", "energy": 0.6, "music_style": "clinic", "transition": "fadeblack",
         "narration": "Либо я выздоровлю, либо я вас засужу! Жалобу напишу, в соцсетях уничтожу!", **V["woman"],
         "sfx": [{"kind": "ding", "at": 0.4, "gain": 0.5}],
         "visual_note": "Современная клиника. Женщина в шубе снимает врача на телефон",
         "data": {"set": "clinic", "label": "Сегодня", "labelAt": 0.5, "tint": "#7ad3e8", "tintA": 0.06,
                  "cam": [[0, 540, 1060, 1.04], [9, 470, 1040, 1.18]],
                  "actors": [char("doctor", 760, 860, 1.0, era="modern", mood="worried", turn=-0.25, gaze=-1),
                             svg('<rect x="480" y="1170" width="640" height="260" fill="#e8eef0" stroke="#2a1a12" stroke-width="6"/><rect x="480" y="1170" width="640" height="26" fill="#cfd8db"/>'),
                             char("woman", 320, 1090, 1.45, talk=True, mood="angry", turn=0.3, gaze=1),
                             {"type": "arm", "x1": 540, "y1": 1420, "x2": 600, "y2": 1070, "sleeve": "#c9ae8a", "skin": SK["wom"], "w": 66},
                             {"type": "prop", "name": "phone", "x": 612, "y": 955, "s": 0.95, "rot": 8}]}},
        {"template": "cartoon", "energy": 0.4, "music_style": "suspense", "transition": "fadewhite", "music_pause": 0.6,
         "narration": "Меняются век+а. Меняются угр+озы. Не меняется одно — врач всё равно лечит.", **V["doctor"],
         "sfx": [{"kind": "heartbeat", "at": 0.2, "gain": 0.6}],
         "visual_note": "ПОВОРОТ: три эпохи — одно лицо. Врач смотрит в камеру",
         "data": {"cam": [[0, 540, 960, 1.05], [9, 540, 960, 1.0]],
                  "actors": [svg(band(0, "#4a1520", "#2a0d12") + band(640, "#3a2a1c", "#1a140c") + band(1280, "#b7c8cc", "#8fa4aa")
                                 + '<path d="M0 640 H1080 M0 1280 H1080" stroke="#e8c99a" stroke-width="6"/>'),
                             char("doctor", 540, 230, 0.98, talk=True, era="hakim", mood="neutral"),
                             char("doctor", 540, 870, 0.98, talk=True, era="field", mood="neutral"),
                             char("doctor", 540, 1510, 0.98, talk=True, era="modern", mood="neutral")]}},
        {"template": "cartoon", "energy": 0.35, "music_style": "piano", "transition": "fadeblack",
         "narration": "Собираешься стать врачом — не жди справедливости. Не жди одобрения. Делай это сердцем. Ошибаются все люди. А спасают — единицы.", **V["doctor"],
         "visual_note": "Ночная смена: врач устало сидит в коридоре → детская ладонь сжимает его палец",
         "data": {"set": "corridor", "cam": [[0, 540, 1100, 1.0], [5.6, 540, 1150, 1.12], [5.7, 540, 1060, 1.0], [14, 420, 1040, 1.25]],
                  "actors": [svg('<rect x="300" y="1330" width="480" height="40" rx="10" fill="#4a5a64" stroke="#0e1418" stroke-width="5"/><rect x="330" y="1370" width="20" height="160" fill="#2e3a42"/><rect x="730" y="1370" width="20" height="160" fill="#2e3a42"/>', to=5.6),
                             char("doctor", 540, 1010, 1.1, era="modern", mood="tired", gazeY=1, to=5.6),
                             svg(HANDS, **{"from": 5.6})]}},
        {"template": "cartoon", "energy": 0.6, "music_style": "piano", "transition": "fadeblack",
         "narration": "Тебя по-настоящему поймут только те, кто носит такой же халат.", **V["doctor"],
         "visual_note": "Три врача трёх эпох плечом к плечу",
         "data": {"cam": [[0, 540, 1000, 1.12], [6, 540, 980, 1.0]],
                  "actors": [svg('<defs><radialGradient id="lg" cx=".5" cy=".42" r=".7"><stop offset="0" stop-color="#5a3e26"/><stop offset="1" stop-color="#120c08"/></radialGradient></defs><rect width="1080" height="1920" fill="url(#lg)"/>'),
                             char("doctor", 190, 980, 0.92, era="hakim", mood="neutral", smile=0.4),
                             char("doctor", 890, 980, 0.92, era="field", mood="neutral", smile=0.4),
                             char("doctor", 540, 930, 1.0, talk=True, era="modern", mood="neutral")]}},
        {"template": "lines", "energy": 0.7, "music_style": "piano", "transition": "fadeblack", "duration": 7.5, "subs": False,
         "visual_note": "Призыв: коллеги, хватит хейтить друг друга",
         "data": {"lines": ["Коллеги,", "хватит хейтить друг друга.", "Нас и так есть *кому судить*.", "Отправь это коллеге ♥"], "stack": True, "size": 5.6, "lead": 0.4, "tail": 1.4}},
    ]}
json.dump(S, open("projects/vrach-reels/script.json", "w"), ensure_ascii=False, indent=1)
print("ok", len(S["scenes"]))
