[CmdletBinding()]
param(
    [switch]$Coverage
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$VirtualPython = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Description,

        [Parameter(Mandatory)]
        [scriptblock]$Command
    )

    Write-Host "`n==> $Description" -ForegroundColor Cyan
    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path $VirtualPython)) {
    throw "The test environment is missing. Run .\scripts\prepare-tests.ps1 first."
}

& $VirtualPython -c "import pytest, pytest_cov, yaml, yamllint" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Test dependencies are missing. Run .\scripts\prepare-tests.ps1 first."
}

Push-Location $RepositoryRoot
try {
    Invoke-CheckedCommand "Validate YAML" {
        & $VirtualPython -m yamllint -c .yamllint .
    }

    Invoke-CheckedCommand "Check Markdown trailing whitespace" {
        $Failures = [System.Collections.Generic.List[string]]::new()

        Get-ChildItem -Path $RepositoryRoot -Filter "*.md" -File -Recurse |
            Where-Object { $_.FullName -notmatch "[\\/]\.git[\\/]" } |
            ForEach-Object {
                $MarkdownFile = $_
                $RelativePath = [System.IO.Path]::GetRelativePath(
                    $RepositoryRoot,
                    $MarkdownFile.FullName
                )
                $LineNumber = 0

                Get-Content -LiteralPath $MarkdownFile.FullName |
                    ForEach-Object {
                        $LineNumber++
                        if ($_ -match "[ `t]+$") {
                            $Failures.Add(
                                "${RelativePath}:${LineNumber}: trailing whitespace"
                            )
                        }
                    }
            }

        if ($Failures.Count -gt 0) {
            $Failures | ForEach-Object { Write-Host $_ -ForegroundColor Red }
            throw "Markdown trailing-whitespace check failed."
        }
    }

    $PytestArguments = @("-m", "pytest", "-v")
    if ($Coverage) {
        $PytestArguments += @("--cov", "--cov-report=term-missing")
    }

    Invoke-CheckedCommand "Run test suite" {
        & $VirtualPython @PytestArguments
    }
}
finally {
    Pop-Location
}

Write-Host "`nAll checks passed." -ForegroundColor Green
