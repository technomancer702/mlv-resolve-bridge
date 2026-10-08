#!/usr/bin/env python3
"""Export MLV clips through a configurable adapter and report Resolve-importable assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Any


DEFAULT_ASSET_EXTENSIONS = {".mov", ".mxf", ".avi", ".dng", ".wav"}
LOG_TAIL_CHARS = 1200


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def stable_clip_id(path: Path) -> str:
    stat = path.stat()
    payload = f"{path.resolve()}|{stat.st_size}|{int(stat.st_mtime)}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:12]


def expand_command(template: list[str], values: dict[str, str]) -> list[str]:
    return [part.format(**values) for part in template]


def discover_assets(output_dir: Path, extensions: set[str]) -> list[Path]:
    if not output_dir.exists():
        return []

    assets: list[Path] = []
    for candidate in output_dir.rglob("*"):
        if candidate.is_file() and candidate.suffix.lower() in extensions:
            assets.append(candidate)

    dng_parents = sorted({path.parent for path in assets if path.suffix.lower() == ".dng"})
    non_dng_assets = [path for path in assets if path.suffix.lower() != ".dng"]
    return [*dng_parents, *non_dng_assets]


def tail_text(value: str, max_chars: int = LOG_TAIL_CHARS) -> str:
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def write_text_log(path: Path, value: str) -> str | None:
    if not value:
        return None
    path.write_text(value, encoding="utf-8", errors="replace")
    return str(path.resolve())


def resolve_import_info(asset: Path) -> tuple[str, str, int | None, int | None]:
    if asset.suffix.lower() != ".dng" and not asset.is_dir():
        return ("file", str(asset.resolve()), None, None)

    directory = asset if asset.is_dir() else asset.parent
    groups: dict[tuple[str, int, str], list[int]] = {}
    for candidate in directory.iterdir() if directory.exists() else []:
        match = re.match(r"^(.*?)(\d+)(\.[dD][nN][gG])$", candidate.name)
        if not match:
            continue
        key = (match.group(1), len(match.group(2)), match.group(3))
        groups.setdefault(key, []).append(int(match.group(2)))

    if not groups:
        return ("file", str(asset.resolve()), None, None)

    (prefix, width, extension), frames = max(groups.items(), key=lambda item: len(item[1]))
    pattern = str((directory / f"{prefix}%0{width}d{extension}").resolve())
    return ("sequence", pattern, min(frames), max(frames))


def print_resolve_import_list(results: list[dict[str, Any]]) -> None:
    for result in results:
        for asset in result.get("assets", []):
            kind, path, start, end = resolve_import_info(Path(asset))
            print(
                "\t".join(
                    [
                        kind,
                        path,
                        "" if start is None else str(start),
                        "" if end is None else str(end),
                    ]
                )
            )


def export_clip(
    clip_path: Path,
    output_root: Path,
    command_template: list[str],
    asset_extensions: set[str],
    dry_run: bool,
) -> dict[str, Any]:
    if clip_path.suffix.lower() != ".mlv":
        raise ValueError(f"Expected an .MLV file, got: {clip_path}")
    if not clip_path.exists():
        raise FileNotFoundError(clip_path)

    clip_id = stable_clip_id(clip_path)
    output_dir = output_root / f"{clip_path.stem}_{clip_id}"
    output_file = output_dir / f"{clip_path.stem}.mov"
    values = {
        "input": str(clip_path.resolve()),
        "output_dir": str(output_dir.resolve()),
        "output_file": str(output_file.resolve()),
        "repo_root": str(Path(__file__).resolve().parents[1]),
        "stem": clip_path.stem,
    }
    command = expand_command(command_template, values)

    result: dict[str, Any] = {
        "input": str(clip_path.resolve()),
        "output_dir": str(output_dir.resolve()),
        "command": command,
        "dry_run": dry_run,
        "returncode": None,
        "assets": [],
        "stdout_tail": "",
        "stderr_tail": "",
    }

    if dry_run:
        return result

    output_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    result["returncode"] = completed.returncode
    result["stdout_tail"] = tail_text(completed.stdout)
    result["stderr_tail"] = tail_text(completed.stderr)
    result["stdout_log"] = write_text_log(output_dir / "mlvapp.stdout.log", completed.stdout)
    result["stderr_log"] = write_text_log(output_dir / "mlvapp.stderr.log", completed.stderr)

    assets = discover_assets(output_dir, asset_extensions)
    result["assets"] = [str(path.resolve()) for path in assets]

    manifest_path = output_dir / "mlv-resolve-bridge.json"
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export MLV clips for Resolve import.")
    parser.add_argument("clips", nargs="+", type=Path, help="One or more .MLV files.")
    parser.add_argument("--config", type=Path, help="Bridge config JSON.")
    parser.add_argument("--output-root", type=Path, help="Export cache root.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    parser.add_argument(
        "--resolve-import-list",
        action="store_true",
        help="Print tab-separated Resolve import entries instead of JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_config(args.config)

    output_root = args.output_root or Path(config.get("output_root", "exports"))
    asset_extensions = {
        ext.lower()
        for ext in config.get("asset_extensions", sorted(DEFAULT_ASSET_EXTENSIONS))
    }
    command_template = config.get("export_command")
    if not isinstance(command_template, list) or not command_template:
        print("config.export_command must be a non-empty list", file=sys.stderr)
        return 2

    results = []
    for clip in args.clips:
        try:
            results.append(
                export_clip(
                    clip,
                    output_root,
                    command_template,
                    asset_extensions,
                    args.dry_run,
                )
            )
        except Exception as exc:
            results.append({"input": str(clip), "error": str(exc), "assets": []})

    if args.resolve_import_list:
        print_resolve_import_list(results)
    else:
        print(json.dumps({"results": results}, indent=2))
    failed = [
        item
        for item in results
        if item.get("error") or (item.get("returncode") not in (None, 0))
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
