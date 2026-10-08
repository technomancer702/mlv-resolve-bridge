# MLV-App Resolve Bridge

Prototype bridge for bringing Magic Lantern `.MLV` clips into DaVinci Resolve through a Resolve Workflow Integration panel.

This project is intended to be GPL-3.0-compatible so it can integrate with an MLV-App fork directly.

The target workflow:

1. Open `Workspace > Workflow Integrations > MLV-App Resolve Bridge`.
2. Drag `.MLV` clips onto the panel.
3. The bridge exports each clip through an MLV adapter, initially an external command.
4. The Resolve plugin imports the exported media into the current Media Pool bin.

## Why This Shape

Resolve does not natively decode Magic Lantern MLV. The bridge therefore has to create Resolve-readable media first, then import that media through Resolve's scripting API.

The initial implementation keeps the MLV conversion behind a configurable command template. That lets us prove the Resolve integration and caching flow before deciding whether to:

- call an existing MLV-App/MLV tool command,
- patch MLV-App to expose a stable headless exporter,
- or replace the adapter with a direct library integration.

## Recommended MVP

Use CinemaDNG folders as the first export target. They are large, but they preserve the raw-oriented workflow that Magic Lantern shooters usually want. ProRes/DNxHR export can be added as a faster editorial mode once the ingest loop works.

## Repository Layout

- `bridge/mlvapp_resolve_bridge.py` - command-line bridge/orchestrator.
- `bridge/config.example.json` - configurable export command template.
- `bridge/config.local-build.example.json` - local patched MLV-App export config.
- `bridge/config.local-smoke.example.json` - local smoke-test config that exports a bounded DNG sequence.
- `bridge/config.mlvapp-headless.example.json` - generic config for the MLV-App headless exporter.
- `docs/gpl-fork-strategy.md` - recommended fork/source dependency strategy.
- `docs/mlvapp-recon.md` - notes from inspecting MLV-App internals.
- `resolve_scripts/import_media.py` - standalone Resolve Python importer.
- `third_party/MLV-App` - MLV-App fork pinned to the `mlv-resolve-headless-export` branch.
- `workflow_plugin/com.codex.mlvappresolvebridge/` - Resolve Workflow Integration plugin scaffold.

## Current Status

The bridge now has a working local headless export path:

- the MLV-App fork builds on Windows with Qt 6.5.3/MinGW,
- `scripts/run-mlvapp-headless.ps1` launches the patched binary with the right runtime DLL order,
- `bridge/mlvapp_resolve_bridge.py` exports clips through the command-template adapter,
- and the bridge discovers the exported CinemaDNG sequence folder for Resolve import.

The sample clip in this checkout is missing its spanned `M06-1927.M00` continuation file, so a full export correctly fails near the end of the available `.MLV` data. Use `bridge/config.local-smoke.example.json` for repeatable local validation; it exports the first 12 frames and succeeds against the available sample file.

## MLV-App Fork Patch

This repo tracks the MLV-App fork as a submodule:

```powershell
git submodule update --init --recursive
```

The submodule points at:

```text
https://github.com/technomancer702/MLV-App.git
branch: mlv-resolve-headless-export
```

`patches/mlvapp-headless-export.patch` is kept as a portable patch artifact for review or re-application against upstream.

The patch adds this initial command shape:

```powershell
mlvapp --headless-export `
  --input C:\clips\A001.MLV `
  --output-dir D:\MLVBridgeCache\A001 `
  --codec cdng-fast `
  --cdng-naming resolve `
  --audio on `
  --max-frames 12
```

Supported codecs in the first patch:

- `cdng`
- `cdng-lossless`
- `cdng-fast`

`--max-frames` is optional. It is mainly useful for smoke tests and short proxy exports; omit it for full-clip export.

## Local Build

Install Qt into the workspace:

```powershell
python -m pip install --user aqtinstall
python -m aqt install-qt windows desktop 6.5.3 win64_mingw -O .qt -m qtmultimedia qt5compat
```

Build the patched MLV-App:

```powershell
.\scripts\build-mlvapp.ps1
```

Run a headless export:

```powershell
.\scripts\run-mlvapp-headless.ps1 -Input C:\clips\A001.MLV -OutputDir D:\MLVBridgeCache\A001
```

Use the local build from the bridge:

```powershell
python bridge\mlvapp_resolve_bridge.py --config bridge\config.local-build.example.json C:\clips\A001.MLV
```

Run the smoke config against a sample clip:

```powershell
python bridge\mlvapp_resolve_bridge.py --config bridge\config.local-smoke.example.json "sample mlv footage\M06-1927.MLV"
```

The smoke run should return `returncode: 0`, one exported DNG-sequence folder in `assets`, and 12 `.dng` files under `.build\smoke-exports`.

## Local CLI Smoke Test

Copy the example config and edit `export_command`:

```powershell
Copy-Item bridge\config.example.json bridge\config.local.json
python bridge\mlvapp_resolve_bridge.py --config bridge\config.local.json --dry-run C:\clips\A001.MLV
```

Run without `--dry-run` once the command template is real:

```powershell
python bridge\mlvapp_resolve_bridge.py --config bridge\config.local.json C:\clips\A001.MLV
```

The bridge prints JSON describing exported paths. The Workflow Integration panel consumes that JSON and passes the paths to Resolve.

## Resolve Plugin Install

Workflow Integration plugins require DaVinci Resolve Studio. If you are using the free Resolve build, skip to **Resolve Free Script Install** below.

Install the workflow plugin:

```powershell
.\scripts\install-resolve-plugin.ps1
```

The script copies `workflow_plugin/com.codex.mlvappresolvebridge` into Resolve's Workflow Integration Plugins directory and adds the version-matched `WorkflowIntegration.node` from Resolve's Developer examples.

Windows:

```text
%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Plugins\
```

macOS:

```text
/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/
```

Restart Resolve after installing or updating the plugin. Open:

```text
Workspace > Workflow Integrations > MLV-App Resolve Bridge
```

The panel defaults to this checkout and the local smoke config:

```text
F:\Coding Projects\mlvapp-resolve-bridge
```

```text
F:\Coding Projects\mlvapp-resolve-bridge\bridge\config.local-smoke.example.json
```

That smoke config exports 12 DNG frames so the included incomplete sample clip can be imported into Resolve. For full clips with all spanned `.M00`, `.M01`, etc. files present, switch `Config JSON` to:

```text
F:\Coding Projects\mlvapp-resolve-bridge\bridge\config.local-build.example.json
```

## Resolve Free Script Install

The free Resolve build can use the normal Scripts menu path when local scripting is available. Install the fallback script:

```powershell
.\scripts\install-resolve-script.ps1
```

The installer copies both a Python script and a Lua launcher to the user scripts folder and the all-users `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Edit` folder, because Resolve builds differ in which location and language they enumerate. Restart Resolve after installing or updating the script. Open:

```text
Workspace > Scripts > Edit > MLVAppResolveBridge
```

The Lua menu entry opens a file picker, exports the selected `.MLV`, and imports the returned DNG sequence into the current Media Pool. The Python UI script, when visible as `MLV App Resolve Bridge`, provides the same flow with a small window. Both use the same local smoke config by default:

```text
F:\Coding Projects\mlvapp-resolve-bridge\bridge\config.local-smoke.example.json
```

For complete clips with all spanned files present, switch the `Config` field to:

```text
F:\Coding Projects\mlvapp-resolve-bridge\bridge\config.local-build.example.json
```

## Notes

- Workflow Integration plugins are a DaVinci Resolve Studio feature.
- Resolve Workflow Integration plugins are supported on Windows and macOS; scripts are the cross-platform fallback.
- MLV-App is GPL-3.0 licensed. Keeping it as a separate external executable is the cleanest early prototype boundary; embedding or linking its code would have licensing consequences for this project.
