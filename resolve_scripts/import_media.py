#!/usr/bin/env python3
"""Import exported bridge media into the current DaVinci Resolve Media Pool folder."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def get_resolve():
    try:
        import DaVinciResolveScript as dvr
    except ImportError as exc:
        raise RuntimeError(
            "Could not import DaVinciResolveScript. Run this from Resolve's scripting "
            "environment or configure Resolve's scripting module path."
        ) from exc

    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError("Could not connect to DaVinci Resolve.")
    return resolve


def import_paths(paths: list[Path]) -> int:
    valid_paths = [str(path.resolve()) for path in paths if path.exists()]
    missing = [str(path) for path in paths if not path.exists()]

    if missing:
        print("Missing paths:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)

    if not valid_paths:
        return 1

    resolve = get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    if project is None:
        raise RuntimeError("No current Resolve project.")

    media_pool = project.GetMediaPool()
    imported = media_pool.ImportMedia(valid_paths)
    print(f"Imported {len(imported or [])} item(s).")
    return 0 if imported else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Import media into Resolve's Media Pool.")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)
    return import_paths(args.paths)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
