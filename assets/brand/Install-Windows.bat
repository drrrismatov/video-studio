@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=Join-Path $env:LOCALAPPDATA 'VideoStudio'; New-Item -ItemType Directory -Force $d | Out-Null; Copy-Item -Force '%~dp0VideoStudio.ico' $d; $ico=Join-Path $d 'VideoStudio.ico'; $f=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Video Studio.url'; Set-Content -Encoding ASCII $f @('[InternetShortcut]','URL=https://claude.ai/code',('IconFile='+$ico),'IconIndex=0')"
echo.
echo  Shortcut "Video Studio" created on your Desktop.
pause
