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
- `bridge/config.mlvapp-headless.example.json` - target config for the planned MLV-App headless exporter.
- `docs/gpl-fork-strategy.md` - recommended fork/source dependency strategy.
- `docs/mlvapp-recon.md` - notes from inspecting MLV-App internals.
- `resolve_scripts/import_media.py` - standalone Resolve Python importer.
- `workflow_plugin/com.codex.mlvappresolvebridge/` - Resolve Workflow Integration plugin scaffold.

## Current Status

This is a scaffold. The MLV-App source has been inspected locally, and the current Qt app opens clips from command-line arguments but does not expose a ready-made headless export command. See `docs/mlvapp-recon.md` for the relevant MLV-App functions and likely patch path.

`patches/mlvapp-headless-export.patch` adds the first narrow headless exporter prototype to MLV-App. The Python bridge already supports a command-template adapter, so once a patched MLV-App binary is available, the Resolve ingest loop can stay stable.

The recommended path is to maintain an MLV-App fork as a source dependency and add a narrow headless export mode there. See `docs/gpl-fork-strategy.md`.

## MLV-App Fork Patch

Apply the patch to your MLV-App fork:

```powershell
git clone https://github.com/ilia3101/MLV-App.git third_party\MLV-App
git -C third_party\MLV-App apply ..\..\patches\mlvapp-headless-export.patch
```

After you create a GitHub fork of MLV-App, change `origin` in `third_party\MLV-App` to your fork URL and push a branch for this work.

The patch adds this initial command shape:

```powershell
mlvapp --headless-export `
  --input C:\clips\A001.MLV `
  --output-dir D:\MLVBridgeCache\A001 `
  --codec cdng-fast `
  --cdng-naming resolve `
  --audio on
```

Supported codecs in the first patch:

- `cdng`
- `cdng-lossless`
- `cdng-fast`

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

Copy `workflow_plugin/com.codex.mlvappresolvebridge` into Resolve's Workflow Integration Plugins directory.

Windows:

```text
%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Workflow Integration Plugins\
```

macOS:

```text
/Library/Application Support/Blackmagic Design/DaVinci Resolve/Workflow Integration Plugins/
```

Then copy the current `WorkflowIntegration.node` from Resolve's Developer examples into the plugin folder. Resolve's docs say that native module lives beside its sample plugin, and it should match the installed Resolve version.

When the panel opens, set `Bridge repo root` to this checkout:

```text
F:\Coding Projects\mlvapp-resolve-bridge
```

## Notes

- Workflow Integration plugins are a DaVinci Resolve Studio feature.
- Resolve Workflow Integration plugins are supported on Windows and macOS; scripts are the cross-platform fallback.
- MLV-App is GPL-3.0 licensed. Keeping it as a separate external executable is the cleanest early prototype boundary; embedding or linking its code would have licensing consequences for this project.
