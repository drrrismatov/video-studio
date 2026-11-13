#!/bin/bash
# Создаёт ярлык «Video Studio» на рабочем столе с иконкой студии
cd "$(dirname "$0")"
D="$HOME/Desktop/Video Studio.webloc"
cat > "$D" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>URL</key><string>https://claude.ai/code</string></dict></plist>
PLIST
osascript -l JavaScript -e "ObjC.import('AppKit'); \$.NSWorkspace.sharedWorkspace.setIconForFileOptions(\$.NSImage.alloc.initWithContentsOfFile('$PWD/VideoStudio.icns'), '$D', 0)" >/dev/null
echo "Готово: ярлык «Video Studio» на рабочем столе."
