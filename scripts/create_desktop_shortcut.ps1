# Put a "Resume Taylor" shortcut on your desktop that starts the app.
# Run once from PowerShell:   powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root "Launch Resume Taylor.bat"
$icon = Join-Path $root "webapp\assets\resume-taylor.ico"
if (-not (Test-Path $target)) { throw "Can't find $target" }

$desktop = [Environment]::GetFolderPath("Desktop")
$link = Join-Path $desktop "Resume Taylor.lnk"
# The app used to be called Resume Studio; its shortcut would now point nowhere.
$old = Join-Path $desktop "Resume Studio.lnk"
if (Test-Path $old) { Remove-Item $old; Write-Host "Removed the old Resume Studio shortcut" }
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $root
$shortcut.Description = "Start Resume Taylor in your browser"
$shortcut.WindowStyle = 7  # start the console minimized; the app opens in the browser
if (Test-Path $icon) { $shortcut.IconLocation = "$icon,0" }
$shortcut.Save()
Write-Host "Created $link"
