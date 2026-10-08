# MLV-App Recon

Source inspected locally at:

```text
.external/MLV-App
```

Reference commit:

```text
e25c1fa0c707f8d79d9b9561045883e58d265eea
e25c1fa 2026-09-20 Fix rcd and dcb debayer for export
```

The clone is intentionally ignored by git. Treat it as reference source unless we explicitly decide to fork MLV-App.

## What Matters For The Bridge

MLV-App's Qt app currently supports opening a clip from the command line, but not exporting one headlessly.

Relevant files:

- `.external/MLV-App/platform/qt/main.cpp`
- `.external/MLV-App/platform/qt/MainWindow.cpp`
- `.external/MLV-App/platform/qt/MainWindow.h`
- `.external/MLV-App/platform/qt/ExportSettingsDialog.h`
- `.external/MLV-App/src/dng/dng.c`

Useful symbols:

- `MainWindow::MainWindow(int &argc, char **argv, ...)` opens `argv[1]` if it is `.mlv` or `.masxml`.
- `MainWindow::openMlvSet(QStringList list)` imports dropped/opened `.mlv` and `.mcraw` files.
- `MainWindow::addClipToExportQueue(int row, QString fileName)` snapshots a clip receipt into `m_exportQueue`.
- `MainWindow::exportHandler()` opens queued clips and dispatches to the right export path.
- `MainWindow::startExportCdng(QString fileName)` writes CinemaDNG folders and optional WAV audio.
- `startExportPipe(...)` handles ffmpeg-backed rendered exports such as ProRes/DNxHR/H.264.

## Export Constants

From `ExportSettingsDialog.h`:

- `CODEC_PRORES422PROXY = 0`
- `CODEC_PRORES422LT = 1`
- `CODEC_PRORES422ST = 2`
- `CODEC_PRORES422HQ = 3`
- `CODEC_PRORES4444 = 4`
- `CODEC_CDNG = 6`
- `CODEC_CDNG_LOSSLESS = 7`
- `CODEC_CDNG_FAST = 8`
- `CODEC_DNXHD = 19`
- `CODEC_DNXHR = 20`
- `CODEC_CDNG_RESOLVE = 1`

## Best Integration Path

The cleanest bridge is probably a tiny MLV-App headless export mode, added upstream or maintained in a small fork:

```text
mlvapp --headless-export --input clip.MLV --output-dir out --codec cdng-fast --cdng-naming resolve
```

Internally that mode can reuse the existing Qt export queue:

1. Construct `QApplication` as today.
2. Parse headless arguments before showing `MainWindow`.
3. Import/open one or more clips.
4. Set export codec/profile options.
5. Push receipts with `addClipToExportQueue`.
6. Run `exportHandler`.
7. Quit on `exportReady` when the queue is empty.

For a minimal first patch, target CinemaDNG only. It already has a direct export path through `startExportCdng`, does not require an ffmpeg pipe, and can emit Resolve-style naming with `CODEC_CDNG_RESOLVE`.

## Why Not Embed MLV-App Yet

MLV-App is GPL-3.0. Keeping it as an external executable gives this bridge a clear process boundary while we prove the Resolve workflow. If we later link to or embed MLV-App code, this project needs to be treated as GPL-compatible.

## Near-Term Tasks

1. Initialize this local checkout against `https://github.com/technomancer702/mlv-resolve-bridge`.
2. Decide whether to prototype headless export in an MLV-App fork or first use a separate command-line MLV converter.
3. Extend `bridge/config.example.json` with a concrete preset once the exporter command exists.
4. Update the Workflow Integration UI to expose `cdng-fast`, `cdng-lossless`, and `prores/dnxhr` presets.
