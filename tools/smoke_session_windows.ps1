param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExecutable
)

$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sessionZip = Join-Path $repository "dist\LittleFoxWritingSession_Current.zip"
if (-not (Test-Path -LiteralPath $sessionZip -PathType Leaf)) {
    throw "Session ZIP was not built"
}

# Exercise the actual *extracted distribution*, not the repository's local
# installation. All page data below is fake, local and purpose-built.
$work = Join-Path $env:RUNNER_TEMP "littlefox-writing-session-smoke"
New-Item -ItemType Directory -Path $work -Force | Out-Null
Expand-Archive -LiteralPath $sessionZip -DestinationPath $work -Force
$setup = Join-Path $work "setup_session.ps1"
$probe = Join-Path $work ".venv\Scripts\littlefox-one-record-probe.exe"
$venvPython = Join-Path $work ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $setup -PathType Leaf)) {
    throw "Extracted ZIP lacks session setup script"
}
& $setup -PythonExecutable $PythonExecutable -NonInteractive
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "Session setup returned an error"
}
if (-not (Test-Path -LiteralPath $probe -PathType Leaf)) {
    throw "Session setup did not install the probe entry point"
}
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw "Extracted session dependencies failed pip check" }
& $probe --help | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Extracted probe CLI help failed" }

$chromeCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromeCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $chrome) { throw "Chrome not available on Windows CI runner" }

$fixture = Join-Path $work "synthetic-writing-detail.html"
@'
<!doctype html>
<html lang="en">
<body>
<div id="contents_0"><p>FAKE-SENTINEL-CONTENT-NOT-A-REAL-STUDENT</p></div>
<input id="writers_0" value="synthetic-student-role">
<input id="regdate_0" value="2099-01-01 synthetic">
</body>
</html>
'@ | Set-Content -LiteralPath $fixture -Encoding utf8
$profile = Join-Path $work "chrome-profile"
New-Item -ItemType Directory -Path $profile -Force | Out-Null
$url = ([uri]$fixture).AbsoluteUri
$process = $null

try {
    $process = Start-Process -FilePath $chrome -ArgumentList @(
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--remote-debugging-port=9222",
        "--user-data-dir=`"$profile`"",
        $url
    ) -PassThru

    $connected = $false
    for ($i = 0; $i -lt 25; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 1 -UseBasicParsing
            if ($response.StatusCode -eq 200) { $connected = $true; break }
        }
        catch { Start-Sleep -Seconds 1 }
    }
    if (-not $connected) { throw "Chrome local CDP preflight unavailable" }

    # Simulate the manager alongside the Writing detail target. Launch
    # Chrome with ONE URL (reliable in headless mode), then create a second
    # *synthetic* blank page using the local DevTools test endpoint.
    $extraTarget = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/new?about:blank" -Method Put -TimeoutSec 5
    if ($extraTarget.type -ne "page") {
        throw "Could not establish the synthetic manager-page target"
    }
    $targets = @(Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/list" -TimeoutSec 5)
    $pageTargets = @($targets | Where-Object { $_.type -eq "page" })
    if ($pageTargets.Count -lt 2) {
        throw "Synthetic multi-page CDP scenario was not established"
    }

    $raw = & $probe --cdp-endpoint "http://127.0.0.1:9222" | Out-String
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 3) { throw "Expected blocked read-only probe exit 3, got $exitCode" }
    $report = $raw | ConvertFrom-Json
    if (-not $report.attach_succeeded -or $report.matching_pages -ne 1 -or
        $report.source_state_count -ne 1 -or -not $report.writer_fields_complete -or
        -not $report.timestamp_fields_complete -or -not $report.source_html_complete -or
        $report.export_created -or $report.html_element_count -lt 1) {
        throw "Unexpected read-only synthetic CDP diagnostic result"
    }
    if ($report.blockers -notcontains "actor_mapping_unverified") {
        throw "Probe unexpectedly treated synthetic source as validated"
    }
    if ($raw -match "FAKE-SENTINEL|synthetic-student-role|2099-01-01") {
        throw "Probe leaked synthetic field contents"
    }
    Write-Host "PASS: extracted session ZIP installed, probe CLI works, local synthetic Chrome/CDP read succeeded with no export."
}
finally {
    if ($process) {
        try { & taskkill.exe /F /T /PID $process.Id 2>$null | Out-Null }
        catch { }
    }
}
