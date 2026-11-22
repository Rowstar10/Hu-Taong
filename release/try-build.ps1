# Tries out a Windows build of Hu Taong the way a player gets it: unzips it, starts Hu Taong.exe,
# waits for its window, closes it as a player would, and checks it saved its settings to
# %APPDATA%\HuTaong (a scratch one here) and wrote nothing into its own folder.
#   pwsh release/try-build.ps1 -Zip dist/Hu-Taong-1.9-windows.zip [-NoSave]
# -NoSave is for versions before 0.9, which saved nothing.
param([Parameter(Mandatory)][string]$Zip, [switch]$NoSave)
$ErrorActionPreference = "Stop"

$root = Join-Path ([IO.Path]::GetTempPath()) "hutaong-try-$PID"
$appdata = Join-Path $root "appdata"
New-Item -ItemType Directory -Force -Path $appdata | Out-Null
Expand-Archive -Path $Zip -DestinationPath (Join-Path $root "game")
$game = Join-Path $root "game\Hu Taong"
$exe = Join-Path $game "Hu Taong.exe"
if (-not (Test-Path $exe)) { throw "The zip has no Hu Taong\Hu Taong.exe" }
$before = (Get-ChildItem -Recurse -File $game | Measure-Object).Count

$env:APPDATA = $appdata                  # the game keeps its saves under %APPDATA%\HuTaong
$env:SDL_AUDIODRIVER = "dummy"           # (a CI machine has no sound card)
$process = Start-Process -FilePath $exe -WorkingDirectory $game -PassThru

$window = $false
foreach ($i in 1..120) {
    Start-Sleep -Milliseconds 500
    $process.Refresh()
    if ($process.HasExited) { throw "Hu Taong closed by itself (exit code $($process.ExitCode))" }
    if ($process.MainWindowHandle -ne 0) { $window = $true; break }
}
if (-not $window) { Stop-Process $process -Force; throw "Hu Taong never opened its window" }
Start-Sleep -Seconds 8                   # let it reach the main menu
$process.Refresh()
if ($process.HasExited) { throw "Hu Taong closed by itself (exit code $($process.ExitCode))" }
if ($process.MainWindowTitle -match "Unhandled exception|Error") {
    Stop-Process $process -Force
    throw "Hu Taong failed to start: '$($process.MainWindowTitle)'"
}
Write-Host "Running: '$($process.MainWindowTitle)'"

$process.CloseMainWindow() | Out-Null    # as if the player closed the window
if (-not $process.WaitForExit(30000)) { Stop-Process $process -Force; throw "Hu Taong didn't close when asked" }
Write-Host "Closed (exit code $($process.ExitCode))"

if (-not $NoSave) {
    $save = Join-Path $appdata "HuTaong\save.json"
    if (-not (Test-Path $save)) { throw "Hu Taong didn't save its settings to %APPDATA%\HuTaong" }
    Write-Host "Saved its settings: $save"
}
$after = (Get-ChildItem -Recurse -File $game | Measure-Object).Count
if ($after -ne $before) { throw "Hu Taong wrote files into its own folder ($before files before, $after after)" }
Write-Host "Nothing written into its folder: OK"
Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
Write-Host "Windows build: OK"
