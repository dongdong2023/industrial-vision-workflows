param(
    [Parameter(Mandatory = $true)][string]$Output,
    [string]$Python = "python"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
& $Python (Join-Path $PSScriptRoot "package.py") --output $Output
exit $LASTEXITCODE
