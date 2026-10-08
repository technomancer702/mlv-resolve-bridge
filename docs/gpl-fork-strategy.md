# GPL Fork Strategy

The project can be GPL-3.0-compatible. That means we can include, fork, patch, and redistribute MLV-App code as long as this project follows GPL-3.0 terms when distributing combined work.

## Recommendation

Use an MLV-App fork as a source dependency, not a one-time copied snapshot.

Preferred layout:

```text
mlv-resolve-bridge/
  bridge/
  workflow_plugin/
  third_party/
    MLV-App/              # git submodule pointing at our MLV-App fork
```

Why submodule/fork over copy-paste:

- We can pull upstream MLV-App fixes.
- Our headless-export changes remain reviewable as commits against MLV-App.
- Build instructions stay close to MLV-App's own Qt project.
- The bridge repo can package the exact fork revision it expects.

## Fork Roles

`mlv-resolve-bridge` owns:

- Resolve Workflow Integration UI.
- Drag/drop queue and job status.
- Calling the headless exporter.
- Export cache manifests.
- Resolve Media Pool import.

`MLV-App` fork owns:

- MLV decoding.
- Raw correction and image processing.
- CinemaDNG/ProRes/DNxHR/other exports.
- New headless export CLI mode.

## First MLV-App Fork Feature

Add a narrow, testable headless mode:

```text
mlvapp --headless-export --input clip.MLV --output-dir out --codec cdng-fast --cdng-naming resolve --audio on
```

The first implementation should support only:

- one input clip at a time,
- CinemaDNG fast-pass,
- Resolve-style CinemaDNG naming,
- optional WAV audio export,
- non-interactive stderr errors,
- deterministic process exit code.

After that works, add batch inputs and rendered formats.

An initial patch lives at:

```text
patches/mlvapp-headless-export.patch
```

## Bridge Contract

The bridge should treat the exporter as a command-line program with this contract:

- Exit `0` only when export completed.
- Write output media under the requested output directory.
- Never show blocking UI in headless mode.
- Print human-readable progress to stdout/stderr.
- Optionally write a JSON manifest later.

The bridge already discovers output assets by extension, so the first exporter does not need to emit JSON.

## Licensing Notes

When we distribute this as a combined app or installer, include:

- this project's GPL-3.0 license text,
- MLV-App's license and copyright notices,
- source code or a written source offer as required by GPL-3.0,
- build instructions for the shipped binaries.

Keeping the bridge and MLV-App fork as separate repos is still fine under GPL; the important thing is that the distributed combined work remains GPL-compliant.
