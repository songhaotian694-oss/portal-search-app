# Start the desktop app without keeping a console window open.
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$launcher = Join-Path $projectRoot 'launcher.py'
$venvPythonw = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'

if (Test-Path -LiteralPath $venvPythonw) {
    $python = $venvPythonw
} else {
    $command = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if (-not $command) {
        throw 'pythonw.exe not found. Create .venv and install requirements.txt first.'
    }
    $python = $command.Source
}

$logDirectory = Join-Path $projectRoot 'data\logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$stdout = Join-Path $logDirectory "startup_$stamp.out.log"
$stderr = Join-Path $logDirectory "startup_$stamp.err.log"

Start-Process -FilePath $python -ArgumentList ('"' + $launcher + '"') `
    -WorkingDirectory $projectRoot -WindowStyle Normal `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
