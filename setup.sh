#!/usr/bin/env bash
# Установка зависимостей студии (идемпотентно, повторный запуск — секунды)
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "Нужен ffmpeg: https://ffmpeg.org/download.html"; exit 1; }
python3 -c "import piper, scipy, numpy, PIL" 2>/dev/null || pip install -q piper-tts scipy numpy pillow
node -e "require('playwright')" 2>/dev/null || { npm i -g playwright && npx playwright install chromium; }
mkdir -p assets/voices && cd assets/voices
for v in dmitri-medium denis-medium irina-medium; do
  [ -d vits-piper-ru_RU-$v ] || (curl -sSL -o $v.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ru_RU-$v.tar.bz2 && tar xjf $v.tar.bz2 && rm $v.tar.bz2)
done
echo "Студия готова"
