param(
    [string]$ResolveUserSupportRoot = "$env:APPDATA\Blackmagic Design\DaVinci Resolve\Support",
    [ValidateSet("Comp", "Edit", "Color", "Deliver")]
    [string]$Category = "Edit"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ScriptSource = Join-Path $Root "resolve_scripts\mlv_app_resolve_bridge.py"
$ScriptTargetDir = Join-Path $ResolveUserSupportRoot "Fusion\Scripts\$Category"
$ScriptTarget = Join-Path $ScriptTargetDir "MLV App Resolve Bridge.py"

if (-not (Test-Path $ScriptSource)) {
    throw "Resolve script source not found: $ScriptSource"
}

New-Item -ItemType Directory -Path $ScriptTargetDir -Force | Out-Null
Copy-Item -LiteralPath $ScriptSource -Destination $ScriptTarget -Force

Write-Host "Installed Resolve script to $ScriptTarget"
