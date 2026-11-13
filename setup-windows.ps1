# Video Studio — установка на Windows (запуск: правый клик → «Выполнить с помощью PowerShell»)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Need($cmd, $id) { if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Host "Устанавливаю $id..."; winget install -e --id $id --accept-source-agreements --accept-package-agreements } }
Need git Git.Git
Need python Python.Python.3.12
Need node OpenJS.NodeJS.LTS
Need ffmpeg Gyan.FFmpeg
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
python -m pip install -q piper-tts scipy numpy pillow
npm i -g playwright; npx playwright install chromium
New-Item -ItemType Directory -Force assets\voices, inbox | Out-Null
foreach ($v in "dmitri-medium","denis-medium","irina-medium") {
  if (-not (Test-Path "assets\voices\vits-piper-ru_RU-$v")) {
    $f = "assets\voices\$v.tar.bz2"
    Invoke-WebRequest "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ru_RU-$v.tar.bz2" -OutFile $f
    tar -xjf $f -C assets\voices; Remove-Item $f
  }
}
# ярлык на папку «Входящие» на рабочем столе
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Video Studio - Inbox.lnk'))
$lnk.TargetPath = (Resolve-Path inbox).Path; $lnk.IconLocation = (Resolve-Path assets\brand\VideoStudio.ico).Path; $lnk.Save()
Write-Host "`nГотово! Кладите видео в папку 'Video Studio - Inbox' на рабочем столе."
Read-Host "Enter — закрыть"
