param(
    # Used only for offline Windows CI or an explicit local Python selection.
    # Normal session users can continue to run setup_session.cmd unchanged.
    [string]$PythonExecutable = "",
    [switch]$NonInteractive,
    [switch]$ForceBootstrap,
    [string]$BootstrapTarget = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if ($ForceBootstrap -and $PythonExecutable) {
    throw "Cannot combine -ForceBootstrap with -PythonExecutable"
}
if ($BootstrapTarget -and -not $ForceBootstrap) {
    throw "-BootstrapTarget is only valid with -ForceBootstrap"
}

Write-Host ""
Write-Host "Little Fox Writing - session computer setup"
Write-Host "==========================================="

# Follow the working Recordings session distribution. A reset session computer
# may have no Python installation; avoid the WindowsApps Store python.exe alias.
$python = $null
if ($PythonExecutable) {
    if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
        throw "Provided Python executable does not exist"
    }
    $python = (Resolve-Path -LiteralPath $PythonExecutable).Path
}
$known = @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)
if (-not $python -and -not $ForceBootstrap) {
    foreach ($candidate in $known) {
        if (Test-Path $candidate) { $python = $candidate; break }
    }
}

if (-not $python) {
    Write-Host "Installing Python 3.13.15 for the current user (no administrator account)..."
    $installer = Join-Path $env:TEMP "python-3.13.15-amd64.exe"
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.13.15/python-3.13.15-amd64.exe" -OutFile $installer

    # Pinned Python.org 3.13.15 Windows 64-bit SHA-256 (official release page).
    $expectedHash = "edec09c4853aeae9ac36efb8c9f95b6b8e2fee65eee56d9767a8b7c69c574403"
    $actualHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $expectedHash) {
        throw "Python installer checksum verification failed"
    }

    $target = if ($BootstrapTarget) {
        [System.IO.Path]::GetFullPath($BootstrapTarget)
    } else {
        Join-Path $env:LOCALAPPDATA "Programs\Python\Python313"
    }
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    $arguments = @(
        "/quiet", "InstallAllUsers=0", "PrependPath=0",
        "Include_launcher=0", "Include_test=0",
        "TargetDir=`"$target`""
    )
    $proc = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
    if ($proc.ExitCode -ne 0) { throw "Python installer returned exit code $($proc.ExitCode)" }
    $python = Join-Path $target "python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "Python installer completed without the required user-local executable"
    }
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
if (-not $NonInteractive) {
    Read-Host "Press Enter to close" | Out-Null
}
