# ORIGAMI local sandbox launcher (Windows PowerShell)
# Creates/uses .venv, installs UI extras, starts Streamlit + static web demos.

param(
    [int]$Port = 8501,
    [int]$StaticPort = 8080,
    [switch]$SkipInstall,
    [switch]$NoStatic
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== ORIGAMI Sandbox ===" -ForegroundColor Cyan
Write-Host "Repo: $Root"

$pyLauncher = "$env:LocalAppData\Programs\Python\Python312\python.exe"
if (-not (Test-Path $pyLauncher)) {
    $pyLauncher = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $pyLauncher) {
    throw "Python 3.12 not found. Install Python 3.12+ and retry."
}

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating .venv ..."
    & $pyLauncher -m venv .venv
}
$Python = $venvPython
$Streamlit = Join-Path $Root ".venv\Scripts\streamlit.exe"

# Skip Streamlit first-run email prompt (local empty credentials; not committed)
$credDir = Join-Path $Root ".streamlit"
$credFile = Join-Path $credDir "credentials.toml"
if (-not (Test-Path $credFile)) {
    New-Item -ItemType Directory -Force -Path $credDir | Out-Null
    Set-Content -Path $credFile -Value "[general]`nemail = `"`"`n" -Encoding UTF8
}

if (-not $SkipInstall) {
    Write-Host "Installing ORIGAMI editable with [ui,dev] ..."
    & $Python -m pip install -U pip setuptools wheel | Out-Null
    & $Python -m pip install -e ".[ui,dev]"
}

Write-Host ""
Write-Host "Local URLs:" -ForegroundColor Green
Write-Host "  Streamlit UI : http://localhost:$Port"
if (-not $NoStatic) {
    Write-Host "  Static demos : http://localhost:$StaticPort/"
    Write-Host "  CTPR optimizer: http://localhost:$StaticPort/ctpr_scaffold_optimizer.html"
}
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

# Static file server for web/ (GitLab Pages content) in background
$staticJob = $null
if (-not $NoStatic) {
    $staticJob = Start-Job -ScriptBlock {
        param($Root, $Python, $StaticPort)
        Set-Location (Join-Path $Root "web")
        & $Python -m http.server $StaticPort --bind 127.0.0.1
    } -ArgumentList $Root, $Python, $StaticPort
}

try {
    & $Python -m streamlit run (Join-Path $Root "app.py") `
        --server.port $Port `
        --server.address 127.0.0.1 `
        --server.headless true `
        --browser.gatherUsageStats false
}
finally {
    if ($staticJob) {
        Stop-Job $staticJob -ErrorAction SilentlyContinue
        Remove-Job $staticJob -Force -ErrorAction SilentlyContinue
    }
}
