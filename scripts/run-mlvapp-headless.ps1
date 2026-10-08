param(
    [Parameter(Mandatory=$true)]
    [Alias("Input")]
    [string]$InputPath,

    [Parameter(Mandatory=$true)]
    [string]$OutputDir,

    [string]$Codec = "cdng-fast",
    [ValidateSet("default", "resolve")]
    [string]$CdngNaming = "resolve",
    [ValidateSet("on", "off")]
    [string]$Audio = "on",
    [int]$MaxFrames = 0
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Exe = Join-Path $Root ".build\MLV-App\release\MLVApp.exe"
$QtBin = Join-Path $Root ".qt\6.5.3\mingw_64\bin"

if (-not (Test-Path $Exe)) {
    throw "MLVApp.exe was not found at $Exe. Build it with scripts\build-mlvapp.ps1."
}

function ConvertTo-ProcessArgument {
    param([string]$Value)

    if ($Value -notmatch '[\s"]') {
        return $Value
    }

    return '"' + ($Value -replace '"', '\"') + '"'
}

$MingwBin = Split-Path (Get-Command g++.exe -ErrorAction Stop).Source
$originalPath = $env:Path
try {
    # Put the compiler runtime before Qt's bundled MinGW runtime. This build uses the local compiler.
    $env:Path = "$MingwBin;$QtBin;$originalPath"
    $arguments = @(
        "--headless-export",
        "--input", $InputPath,
        "--output-dir", $OutputDir,
        "--codec", $Codec,
        "--cdng-naming", $CdngNaming,
        "--audio", $Audio
    )

    if ($MaxFrames -gt 0) {
        $arguments += @("--max-frames", $MaxFrames.ToString())
    }

    $arguments = $arguments | ForEach-Object { ConvertTo-ProcessArgument $_ }

    $process = Start-Process -FilePath $Exe -ArgumentList $arguments -NoNewWindow -Wait -PassThru
    exit $process.ExitCode
}
finally {
    $env:Path = $originalPath
}
