$ErrorActionPreference = "Stop"

# LadderIQ's authoritative working folder and Git repository.
# $PSScriptRoot resolves to the folder containing this script, which should be:
# C:\Users\mcdph\OneDrive\03 - LadderIQ Platform\04 - Development
$ExpectedRoot = "C:\Users\mcdph\OneDrive\03 - LadderIQ Platform\04 - Development"
$ProjectRoot = $PSScriptRoot

if ([System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\\') -ne [System.IO.Path]::GetFullPath($ExpectedRoot).TrimEnd('\\')) {
    Write-Warning "This package is running from: $ProjectRoot"
    Write-Warning "The intended LadderIQ root is: $ExpectedRoot"
    Write-Warning "Move/extract the package to the intended root before using it as the production copy."
}

Set-Location $ProjectRoot
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " LadderIQ - Generate and Publish" -ForegroundColor Cyan
Write-Host " Root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Invoke-PythonStep {
    param(
        [Parameter(Mandatory=$true)][string]$Script,
        [Parameter(Mandatory=$true)][string]$Description,
        [switch]$Optional
    )

    if (-not (Test-Path (Join-Path $ProjectRoot $Script))) {
        if ($Optional) {
            Write-Warning "$Description skipped because $Script was not found."
            return
        }
        throw "Required file not found: $Script"
    }

    Write-Host "[LadderIQ] $Description..." -ForegroundColor Yellow
    & python (Join-Path $ProjectRoot $Script)
    if ($LASTEXITCODE -ne 0) {
        if ($Optional) {
            Write-Warning "$Description failed. Continuing with the latest saved leadership scores."
            return
        }
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

# Import the newest Fidelity exports found under the LadderIQ root/data folders.
Invoke-PythonStep -Script "import_fidelity_csv.py" -Description "Importing Fidelity account history"
Invoke-PythonStep -Script "import_positions.py" -Description "Importing Fidelity positions"

# This step may require internet access and the yfinance package.
Invoke-PythonStep -Script "leadership_scanner.py" -Description "Refreshing leadership scores" -Optional

# Generate reports/latestladder.html plus compatibility copies.
Invoke-PythonStep -Script "build_ladder.py" -Description "Building the Daily Investment Playbook"

$ReportPath = Join-Path $ProjectRoot "reports\latestladder.html"
if (-not (Test-Path $ReportPath)) {
    throw "Build completed without creating the expected report: $ReportPath"
}

Write-Host "[LadderIQ] Report generated successfully." -ForegroundColor Green
Start-Process $ReportPath

# Publish only when this root folder has been initialized as a Git repository.
if (Test-Path (Join-Path $ProjectRoot ".git")) {
    Write-Host "[GitHub] Checking for changes..." -ForegroundColor Yellow
    & git add --all
    if ($LASTEXITCODE -ne 0) { throw "git add failed." }

    $changes = & git status --porcelain
    if ($LASTEXITCODE -ne 0) { throw "git status failed." }

    if ($changes) {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
        & git commit -m "LadderIQ automated refresh $stamp"
        if ($LASTEXITCODE -ne 0) { throw "git commit failed." }

        & git push
        if ($LASTEXITCODE -ne 0) { throw "git push failed. Check GitHub authentication and the configured remote." }

        Write-Host "[GitHub] Changes committed and pushed." -ForegroundColor Green
    }
    else {
        Write-Host "[GitHub] No file changes detected; nothing to publish." -ForegroundColor DarkGray
    }
}
else {
    Write-Warning "GitHub publishing skipped because $ProjectRoot is not yet a Git repository."
    Write-Warning "Complete the one-time GitHub setup in README.md, then double-click Generate_LadderIQ.bat again."
}

Write-Host ""
Write-Host "LadderIQ generation finished." -ForegroundColor Green
