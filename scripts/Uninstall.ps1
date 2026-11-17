param(
    [Parameter(Mandatory = $true)][string]$Project,
    [string]$Python = "python"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ExtensionRoot = Split-Path -Parent $PSScriptRoot
& $Python (Join-Path $ExtensionRoot "ivw.py") uninstall --project $Project
exit $LASTEXITCODE
