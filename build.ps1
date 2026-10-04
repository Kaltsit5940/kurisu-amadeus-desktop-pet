param([string]$Python = '')
$ErrorActionPreference = 'Stop'
$taskVenv = Join-Path $PSScriptRoot '.venv'
$taskPython = Join-Path $taskVenv 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    if ($Python) {
        & $Python -m venv $taskVenv
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.13 -m venv $taskVenv
    } else {
        & python -m venv $taskVenv
    }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python virtual environment' }
}
& $taskPython -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'Could not install build dependencies' }
$taskOutput = Join-Path $PSScriptRoot 'dist'
New-Item -ItemType Directory -Force -Path $taskOutput | Out-Null
& $taskPython -m PyInstaller --noconfirm --onefile --windowed --exclude-module numpy --name KurisuAmadeusPet --add-data "$(Join-Path $PSScriptRoot 'assets');assets" --icon (Join-Path $PSScriptRoot 'assets/kurisu.ico') --distpath $taskOutput --workpath (Join-Path $PSScriptRoot 'build') --specpath $PSScriptRoot (Join-Path $PSScriptRoot 'pet.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
