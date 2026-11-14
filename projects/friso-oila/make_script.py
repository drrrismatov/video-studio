"""Generates script.json for «Friso — One Family. One Oila.» (run from repo root)."""
import json
import sys

sys.path.insert(0, 'engine')
import captions  # noqa: E402

P = 'projects/friso-oila'
# transcript fixes: spelling/punctuation only, spoken words unchanged
fix = {"IMG_8304": [(" - ", " — ")], "IMG_7246": [(" - ", " — "), ("сплоченность", "сплочённость")],
       "IMG_3350": [(" - ", " — ")], "IMG_8005": [(" – ", " — ")], "IMG_9695": [("всю ее", "всю её"), ("еще", "ещё")]}
for f, rules in fix.items():
    p = f'{P}/asr/{f}.json'
    d = json.load(open(p))
    for sg in d["text"]:
        for a, b in rules:
            sg["text"] = sg["text"].replace(a, b)
    json.dump(d, open(p, 'w'), ensure_ascii=False, indent=1)
C = {f: captions.build(f'{P}/asr/{f}.json') for f in ["IMG_8005", "IMG_3350", "IMG_9695", "IMG_7046", "IMG_8304", "IMG_7246"]}
json.dump(C, open(f'{P}/asr/captions.json', 'w'), ensure_ascii=False, indent=1)

D = {d["video"]: d for d in json.load(open('data/doctors.json'))["doctors"] if d.get("video")}


def plate(v):
    d = D[v]
    where = ", ".join(x for x in [d.get("clinic"), d.get("city")] if x and "?" not in x)
    name = d["full_name"].replace(" (фамилия?)", "")
    return {"template": "lower", "data": {"title": name, "caption": d["role"] + (" · " + where if where else ""),
                                          "plain": True, "at": 0.8, "hold": 5.5}}


def doc(v, a, b, energy, tr="dissolve", note="", **kw):
    sc = {"template": "footage", "src": "inbox:" + v, "in": a, "out": b, "audio": True, "look": "warm", "zoom": 1.04,
          "transition": tr, "energy": energy, "captions": C[v.split('.')[0]], "overlay": plate(v), "visual_note": note}
    sc.update(kw)
    return sc


def word(text, size=10):
    return {"template": "statement", "data": {"text": f"*{text}*", "size": size, "style": "blur", "pos": "bottom",
                                              "shadow": True, "stagger": 0.07, "delay": 0.05}}


def chain(v, a, b, ao, text, energy, tr="cut", **kw):
    sc = {"template": "footage", "src": "inbox:" + v, "in": a, "out": b, "audio_out": ao, "audio": True, "volume": 1.1,
          "look": "warm", "zoom": 1.1, "transition": tr, "energy": energy, "min_duration": 0.5, "subs": False,
          "captions": [], "overlay": word(text), "whoosh": False, "visual_note": "ЦЕПОЧКА: «" + text + "»"}
    sc.update(kw)
    return sc


def smile(v, a, dur, **kw):
    sc = {"template": "footage", "src": "inbox:" + v, "in": a, "out": a + dur, "audio": False, "look": "warm", "zoom": 1.06,
          "transition": "cut", "energy": 0.12, "min_duration": 0.3, "subs": False, "captions": [], "whoosh": False,
          "visual_note": "холодное открытие: улыбки"}
    sc.update(kw)
    return sc


S = {
    "title": "Friso — One Family. One Oila.",
    "logline": "Мы живём в разных городах и работаем в разных клиниках, но мы — одна большая семья. Оила.",
    "format": "16:9", "fps": 30, "theme": "documentary", "accent": "#e8c99a",
    "music": {"mood": "piano", "key": "D", "bpm": 66, "volume": 0.8, "duck": 0.14},
    "subtitles": True, "whoosh": False,
    "grade": {"grain": 3, "vignette": True, "letterbox": False, "contrast": 1.02, "saturation": 1.0},
    "bg": {"particles": 24, "speed": 0.4, "blobAlpha": 0.22},
    "transition_duration": 0.9,
    "scenes": [
        smile("IMG_7046.mov", 0.4, 0.6, transition="none"),
        smile("IMG_3350.mov", 15.7, 0.6),
        smile("IMG_8304.MOV", 57.3, 0.6, sharpen=True),
        smile("IMG_9695.mov", 16.4, 0.6),
        smile("IMG_7246.compressed.mp4", 26.9, 0.6),
        smile("IMG_8005.mov", 34.3, 0.9, hflip=True),
        {"template": "lines", "transition": "fadeblack", "energy": 0.12, "duration": 13.5, "subs": False,
         "visual_note": "Чёрный экран, фортепиано, фразы появляются по очереди",
         "data": {"lines": ["Мы живём в разных городах.", "Работаем в разных клиниках.", "У каждого — свой путь.",
                            "Но нас объединяет *любовь к детям*."], "size": 4.6}},
        doc("IMG_8005.mov", 1.8, 16.7, 0.18, "fadeblack", hflip=True, note="Первые годы жизни малыша — особенное время"),
        doc("IMG_8304.MOV", 1.25, 11.3, 0.22, sharpen=True, note="Ваша компания — это важная миссия"),
        doc("IMG_3350.mov", 0.0, 15.1, 0.28, note="Самое ценное — видеть, как растут детки"),
        doc("IMG_9695.mov", 0.9, 16.0, 0.32, note="От всей души поздравляю… сотрудничать вместе"),
        doc("IMG_7246.compressed.mp4", 1.5, 25.0, 0.38, note="Ценности остаются… идут к одной цели"),
        doc("IMG_7046.mov", 0.0, 14.85, 0.3, transition_duration=1.0,
            note="ЭМОЦИОНАЛЬНЫЙ ЦЕНТР: «не просто коллеги… одна оила, одна большая семья»"),
        {"template": "mosaic", "src": "inbox:IMG_7046.mov", "in": 14.85, "out": 20.45, "audio": True,
         "transition": "fadeblack", "transition_duration": 1.0, "energy": 0.5, "music_pause": 2.6, "duration": 10.5,
         "captions": C["IMG_7046"],
         "cells": [{"src": "inbox:IMG_8005.mov", "in": 24, "face": 0.4, "hflip": True},
                   {"src": "inbox:IMG_8304.MOV", "in": 18, "face": 0.43},
                   {"src": "inbox:IMG_3350.mov", "in": 8, "face": 0.3},
                   {"src": "inbox:IMG_9695.mov", "in": 5, "face": 0.52},
                   {"src": "inbox:IMG_7046.mov", "in": 14.85, "face": 0.47},
                   {"src": "inbox:IMG_7246.compressed.mp4", "in": 18, "face": 0.45}],
         "overlay": {"template": "statement", "data": {"text": "Мы — одна большая семья. *Оила.*", "size": 6, "style": "blur",
                                                        "pos": "bottom", "shadow": True, "delay": 6.4, "stagger": 0.12}},
         "visual_note": "ОБЩИЙ КАДР: все 6 врачей; пауза в музыке → голос Дили продолжает → «Мы — одна большая семья. Оила.»"},
        chain("IMG_8005.mov", 32.85, 34.4, 34.25, "Команда Friso!", 0.6, "fadeblack", hflip=True, transition_duration=0.6),
        chain("IMG_9695.mov", 0.82, 1.95, 1.72, "от всей души", 0.62),
        chain("IMG_7046.mov", 21.95, 22.75, 22.52, "спасибо", 0.64),
        chain("IMG_3350.mov", 15.08, 16.9, 16.67, "с праздником вас!", 0.66),
        chain("IMG_8304.MOV", 56.85, 58.5, 58.2, "с днём рождения!", 0.68, sharpen=True),
        chain("IMG_7246.compressed.mp4", 24.95, 27.2, 26.5, "с днём рождения, Friso!", 0.7, hit=True, hit_offset=1.6),
        {"template": "photo", "transition": "fadewhite", "transition_duration": 0.5, "energy": 0.85, "duration": 10,
         "subs": False, "sfx": [{"kind": "applause", "at": 0.2, "gain": 0.45}],
         "visual_note": "ВСПЛЕСК: общее фото оживает — движение камеры, тёплый свет, конфетти, аплодисменты",
         "data": {"src": "/home/user/video-studio/inbox/IMG_1104.JPG", "flash": True, "confetti": 160, "confettiAt": 0.2,
                  "kenburns": {"from": [1.0, 0, 0], "to": [1.16, 0, -3.5]}, "origin": "50% 62%",
                  "title": "Из разных уголков Узбекистана —", "subtitle": "с одним сердцем", "titleAt": 1.6, "size": 4.6}},
        {"template": "lines", "transition": "fadeblack", "energy": 0.55, "duration": 9, "subs": False,
         "visual_note": "Три благодарности, остаются на экране",
         "data": {"lines": ["С любовью к детям.", "С уважением к нашей профессии.", "С благодарностью компании *Friso*."],
                  "stack": True, "size": 4.2, "lead": 0.5, "tail": 1.6}},
        {"template": "outro", "transition": "fadeblack", "energy": 0.3, "duration": 7, "hold": 2,
         "visual_note": "Логотип Friso (нужен официальный файл) + One Family. One Oila.",
         "data": {"title": "*Friso*", "cta": "One Family. One Oila.", "logo": "♥", "size": 10}},
    ]}
json.dump(S, open(f'{P}/script.json', 'w'), ensure_ascii=False, indent=1)
print(len(S["scenes"]), "scenes")
