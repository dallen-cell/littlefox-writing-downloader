$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "Little Fox Writing - session computer setup"
Write-Host "==========================================="

# Follow the working Recordings session distribution. A reset session computer
# may have no Python installation; avoid the WindowsApps Store python.exe alias.
$python = $null
$known = @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)
foreach ($candidate in $known) {
    if (Test-Path $candidate) { $python = $candidate; break }
}

if (-not $python) {
    Write-Host "Installing Python 3.13.15 for the current user (no administrator account)..."
    $installer = Join-Path $env:TEMP "python-3.13.15-amd64.exe"
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.13.15/python-3.13.15-amd64.exe" -OutFile $installer
    $proc = Start-Process -FilePath $installer -ArgumentList @(
        "/quiet", "InstallAllUsers=0", "PrependPath=1",
        "Include_launcher=0", "Include_test=0"
    ) -Wait -PassThru
    if ($proc.ExitCode -ne 0) { throw "Python installer returned exit code $($proc.ExitCode)" }
    $python = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
    if (-not (Test-Path $python)) { throw "Python installed but expected user-local executable is missing" }
}

Write-Host "Using Python:"
& $python --version
if ($LASTEXITCODE -ne 0) { throw "Python is unavailable" }

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating session-local Python environment..."
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment setup failed" }
}
Write-Host "Installing Writing probe and Playwright 1.62.0..."
& ".\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -e ".[probe]" "playwright==1.62.0"
if ($LASTEXITCODE -ne 0) { throw "Writing probe installation failed" }

New-Item -ItemType Directory -Force -Path ".\chrome-profile" | Out-Null
& ".\.venv\Scripts\python.exe" -m compileall -q src
if ($LASTEXITCODE -ne 0) { throw "Source compilation failed" }

Write-Host ""
Write-Host "SESSION SETUP COMPLETE."
Write-Host "Next: run run_one_record_probe.cmd"
Read-Host "Press Enter to close"
