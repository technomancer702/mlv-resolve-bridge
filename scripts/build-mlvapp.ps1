param(
    [string]$Configuration = "release",
    [int]$Jobs = 4
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$QtBin = Join-Path $Root ".qt\6.5.3\mingw_64\bin"
$BuildDir = Join-Path $Root ".build\MLV-App"
$ProjectFile = Join-Path $Root "third_party\MLV-App\platform\qt\MLVApp.pro"

if (-not (Test-Path (Join-Path $QtBin "qmake.exe"))) {
    throw "Qt was not found at $QtBin. Install with: python -m aqt install-qt windows desktop 6.5.3 win64_mingw -O .qt -m qtmultimedia qt5compat"
}

$Make = Get-Command mingw32-make.exe -ErrorAction Stop

New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null

$originalPath = $env:Path
try {
    $paths = $env:Path -split ";" | Where-Object {
        $_ -and
        ($_ -notlike "C:\Program Files\Git\bin*") -and
        ($_ -notlike "C:\Program Files\Git\usr\bin*") -and
        ($_ -notlike "*\Git\bin*") -and
        ($_ -notlike "*\Git\usr\bin*")
    }
    $env:Path = "$QtBin;$($paths -join ';')"

    Push-Location $BuildDir
    try {
        & (Join-Path $QtBin "qmake.exe") $ProjectFile -spec win32-g++ "CONFIG+=$Configuration"
        & $Make.Source "-j$Jobs" "SHELL=cmd.exe"
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:Path = $originalPath
}
