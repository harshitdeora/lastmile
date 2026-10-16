$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
docker compose up -d falkordb
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop, then retry.' }
$env:PYTHONPATH = 'backend'
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { throw 'Create a Python 3.12 .venv and install backend/requirements.lock.txt first.' }
& '.\.venv\Scripts\python.exe' -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --workers 1
