param(
    [string]$ResolveUserSupportRoot = "$env:APPDATA\Blackmagic Design\DaVinci Resolve\Support",
    [string]$ResolveProgramDataRoot = "$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve",
    [ValidateSet("Comp", "Edit", "Color", "Deliver")]
    [string]$Category = "Edit"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ScriptSource = Join-Path $Root "resolve_scripts\mlv_app_resolve_bridge.py"
$LuaScriptSource = Join-Path $Root "resolve_scripts\MLVAppResolveBridge.lua"
$UserScriptTargetDir = Join-Path $ResolveUserSupportRoot "Fusion\Scripts\$Category"
$AllUsersScriptTargetDir = Join-Path $ResolveProgramDataRoot "Fusion\Scripts\$Category"

if (-not (Test-Path $ScriptSource)) {
    throw "Resolve script source not found: $ScriptSource"
}

if (-not (Test-Path $LuaScriptSource)) {
    throw "Resolve Lua script source not found: $LuaScriptSource"
}

foreach ($ScriptTargetDir in @($UserScriptTargetDir, $AllUsersScriptTargetDir)) {
    $ScriptTarget = Join-Path $ScriptTargetDir "MLV App Resolve Bridge.py"
    $LuaScriptTarget = Join-Path $ScriptTargetDir "MLVAppResolveBridge.lua"
    New-Item -ItemType Directory -Path $ScriptTargetDir -Force | Out-Null
    Copy-Item -LiteralPath $ScriptSource -Destination $ScriptTarget -Force
    Copy-Item -LiteralPath $LuaScriptSource -Destination $LuaScriptTarget -Force

    Write-Host "Installed Resolve script to $ScriptTarget"
    Write-Host "Installed Resolve Lua launcher to $LuaScriptTarget"
}
