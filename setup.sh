#!/usr/bin/env bash
# Установка зависимостей студии
set -e
cd "$(dirname "$0")"
pip install -q piper-tts scipy numpy pillow
mkdir -p assets/voices && cd assets/voices
for v in dmitri-medium denis-medium irina-medium; do
  [ -d vits-piper-ru_RU-$v ] || (curl -sSL -o $v.tar.bz2 https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ru_RU-$v.tar.bz2 && tar xjf $v.tar.bz2 && rm $v.tar.bz2)
done
echo "Студия готова"
