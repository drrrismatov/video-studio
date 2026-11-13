# AI Video Studio — регламент для Claude

Один промпт: `/video <идея>` (см. .claude/skills/video/SKILL.md).

Изолированный проект студии (не связан с другими проектами). Всё работает офлайн:
нейроголос Piper (ru: dmitri, denis, irina), процедурная музыка и SFX (numpy/scipy),
моушн-графика HTML/CSS → Chromium (Playwright) покадрово → ffmpeg.

## Процесс производства (строго по шагам)
1. **Промпт** от пользователя → Claude (режиссёр-сценарист) пишет `projects/<slug>/script.json`.
2. `python3 studio.py storyboard <slug>` → `out/storyboard.png` + `out/storyboard.md`.
   Показать пользователю сценарий (таблица) и раскадровку. **Ждать одобрения.** Без одобрения не рендерить.
3. После одобрения: `python3 studio.py build <slug>` → `out/<slug>.mp4`, `out/poster.jpg`.
4. Проверить: кадры (ffmpeg -ss … -frames:v 1), громкость (ebur128 ≈ −14 LUFS). Отдать пользователю.
5. Правки → менять script.json → `build` снова (озвучка и сцены кешируются, перерисуются только изменённые).

## script.json
Глобально: `title, logline, format (16:9|9:16|1:1|4:5), fps, theme, voice, voice_speed,
music{mood,key,bpm,volume,duck,file}, subtitles, grade{grain,vignette,letterbox,contrast,saturation},
bg{particles,grid,speed,blobAlpha}, transition_duration, whoosh`.

Сцена: `template, narration (закадр; *слово* — акцент, _слово_ — акцент2), say (текст для TTS, если
нужно иначе произнести), data{…}, transition (вход), energy 0–1 (управляет музыкой), hit (удар),
riser (нарастание), min_duration, duration, subs:false, theme, accent, visual_note (для раскадровки), voice`.

Шаблоны (`engine/web/templates.js`) и их data:
- `title` {kicker,title,subtitle,size,align}
- `chapter` {number,kicker,title}
- `statement` {kicker,text,size,style: blur|rise|slide}
- `stat` {kicker,value,prefix,suffix,decimals,percent,label}
- `list` {title,items[]}
- `quote` {text,author}
- `compare` {left{title,points[]},right{…},vs}
- `timeline` {title,points[{label,text}]}
- `media` {src (абсолютный путь к фото/видео),title,caption,kenburns{from:[s,x,y],to:[s,x,y]},video,start}
- `outro` {title,cta,logo}

Темы: midnight, ember, noir, aurora, medical, clean, gold.
Музыка mood: cinematic, epic, tense, calm, upbeat, tech, inspire. Или `music.file` — свой трек.
Переходы: fade, fadeblack, fadewhite, dissolve, slideleft/right/up/down, smoothleft/right/up,
circleopen/close, zoomin, wipeleft/right, radial, pixelize, hblur, distance, squeezev, diagtl, cut.

## Режиссёрские правила
- Хук в первые 2–3 секунды; одна мысль на сцену; 6–12 слов на экране максимум.
- Закадр короче визуала: 2–3 предложения на сцену; общая длина под площадку (Shorts/Reels ≤ 60 с).
- Кривая энергии: тихое начало → рост → пик (hit) → разрядка → финал/CTA.
- Чередовать шаблоны и переходы; hit на смене смысла; riser перед пиком.
- Субтитры отключать там, где текст уже на экране (quote, statement с тем же текстом).
- Числа в закадре писать словами («тридцать»), в data — цифрами.

## Живое видео пользователя
- **Облачные Входящие**: пользователь перетаскивает видео в браузере в GitHub-релиз `inbox`
  (https://github.com/drrrismatov/video-studio/releases/tag/inbox → Edit → прикрепить файлы, до 2 ГБ/файл).
  `python3 studio.py pull` скачивает новые в `inbox/`. Работает в облачной сессии без установки чего-либо.
- **Основной путь — папка «Входящие»** (`inbox/` или путь из `$STUDIO_INBOX`): любые размеры, без загрузки в чат.
  `python3 studio.py inbox` — список видео; в сцене `"src": "inbox:файл.mp4"`; `look <slug> inbox:файл.mp4`.
  Студия только читает эту папку (запрет Edit/Write в .claude/settings.json, выход за пределы папки блокируется).
- Приём: файлы ≤30 МБ (лимит чата) → `python3 studio.py ingest <slug> часть1.mp4 часть2.mp4` → `media/<имя>.mp4`
  (склейка без перекодирования) + контактный лист `media/<имя>.sheet.jpg` и карта тишины (где речь).
- Сцена `footage`: {src:"media/x.mp4", in, out, audio:true|false, volume, zoom:1.05, fit:auto|cover|blur,
  look:warm|cool|bw|punch, speed, overlay:{template:"lower", data:{title:"Имя", caption:"Должность"}}, narration?}
  fit:auto — если ориентация не совпадает, кадр вписывается целиком с размытым фоном (лица не режутся).
  Живой звук идёт в микс как диалог, музыка под ним приглушается автоматически.
- Лица и речь не меняем. Только монтаж.

## Ограничения
Нет стоковых видео/фото, нет распознавания речи (ASR-модели недоступны в сети) — субтитры к живой речи пишутся вручную через overlay и генеративного AI-видео (сеть закрыта, нет ключей). Свои материалы —
через шаблон `media`. Для Veo/Kling/Runway/ElevenLabs нужны API-ключи.
