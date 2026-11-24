$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:Path = "C:\Program Files\nodejs;" + $env:Path
Start-Process -FilePath "py" -ArgumentList "-3","-m","uvicorn","app.main:app","--app-dir","$root\backend","--host","127.0.0.1","--port","8000" -WorkingDirectory $root
Set-Location "$root\frontend"
npm run dev -- --host 127.0.0.1 --port 5173
