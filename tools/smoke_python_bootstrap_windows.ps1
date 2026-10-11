param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$zip = Join-Path $repoRoot "dist\LittleFoxWritingSession_Current.zip"
if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) {
    throw "Session ZIP missing for isolated Python bootstrap smoke test"
}
$root = Join-Path $env:RUNNER_TEMP "lf-writing-bootstrap-test"
$unpacked = Join-Path $root "package"
$target = Join-Path $root "user-python313"
New-Item -ItemType Directory -Force -Path $root | Out-Null
Expand-Archive -LiteralPath $zip -DestinationPath $unpacked -Force

# Exercise the Python installer branch even though this GitHub runner already
# has Python from setup-python. Installation is isolated, non-admin, and uses
# the exact bundled session setup script.
& (Join-Path $unpacked "setup_session.ps1") -ForceBootstrap -BootstrapTarget $target -NonInteractive
if (-not $?) { throw "Bundled bootstrap setup failed" }

$installed = Join-Path $target "python.exe"
$session = Join-Path $unpacked ".venv\Scripts\python.exe"
$probe = Join-Path $unpacked ".venv\Scripts\littlefox-one-record-probe.exe"
foreach ($file in @($installed, $session, $probe)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Bootstrap did not create an expected Python or probe executable"
    }
}
& $installed -c "import sys; assert sys.version_info[:2] == (3,13)"
if ($LASTEXITCODE -ne 0) { throw "Bootstrapped Python interpreter invalid" }
& $session -m pip check
if ($LASTEXITCODE -ne 0) { throw "Bootstrap session dependencies failed" }
& $probe --help | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Bootstrap probe executable failed" }

Write-Host "PASS: bundled session setup downloaded/verified/installed user-local Python and launched its isolated Python and probe."
