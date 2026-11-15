param(
    [switch]$Setup,
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

function Get-SystemPython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Command = "py"; Arguments = @("-3") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Command = "python"; Arguments = @() }
    }
    throw "Python 3 is not installed. Install it from https://www.python.org/downloads/ and run this script again."
}

function Test-Python($path) {
    if (-not (Test-Path $path)) { return $false }
    & $path --version 2>$null
    return $LASTEXITCODE -eq 0
}

Set-Location $projectRoot

# Ensure .env exists from .env.example
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

if ($Setup) {
    $systemPython = Get-SystemPython
    if (Test-Path $venvPath) {
        Remove-Item -LiteralPath $venvPath -Recurse -Force
    }
    Write-Host "Creating Python virtual environment in .venv..."
    & $systemPython.Command @($systemPython.Arguments + @("-m", "venv", ".venv"))
    & $venvPython -m pip install --upgrade pip
    Write-Host "Installing dependencies from requirements.txt..."
    & $venvPython -m pip install -r requirements.txt

    # Handle Windows Application Control / AppLocker by enabling pure-Python SQLAlchemy
    Get-ChildItem -Path "$venvPath\Lib\site-packages\sqlalchemy" -Recurse -Filter "*.pyd" -ErrorAction SilentlyContinue | ForEach-Object {
        Rename-Item $_.FullName "$($_.Name).disabled" -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Initializing SQLite database and importing places..."
    & $venvPython -m flask --app run init-db
    & $venvPython -m flask --app run import-places
    Write-Host "Setup completed successfully."
}

if (-not (Test-Python $venvPython)) {
    throw "The local environment is missing or invalid. Run: .\run_local.ps1 -Setup"
}

Write-Host "Starting Mood application on http://127.0.0.1:$Port ..."
& $venvPython -m flask --app run run --port $Port
