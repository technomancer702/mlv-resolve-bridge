param(
    [string]$ResolveSupportRoot = "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PluginId = "com.codex.mlvappresolvebridge"
$SourcePlugin = Join-Path $Root "workflow_plugin\$PluginId"
$PluginRoot = Join-Path $ResolveSupportRoot "Workflow Integration Plugins"
$TargetPlugin = Join-Path $PluginRoot $PluginId
$WorkflowNode = Join-Path $ResolveSupportRoot "Developer\Workflow Integrations\Examples\SamplePlugin\WorkflowIntegration.node"

if (-not (Test-Path $SourcePlugin)) {
    throw "Plugin source folder not found: $SourcePlugin"
}

if (-not (Test-Path $WorkflowNode)) {
    throw "WorkflowIntegration.node not found: $WorkflowNode"
}

New-Item -ItemType Directory -Path $PluginRoot -Force | Out-Null
New-Item -ItemType Directory -Path $TargetPlugin -Force | Out-Null

Copy-Item -Path (Join-Path $SourcePlugin "*") -Destination $TargetPlugin -Recurse -Force
Copy-Item -LiteralPath $WorkflowNode -Destination (Join-Path $TargetPlugin "WorkflowIntegration.node") -Force
Remove-Item -LiteralPath (Join-Path $TargetPlugin "package.js") -Force -ErrorAction SilentlyContinue

Write-Host "Installed $PluginId to $TargetPlugin"
