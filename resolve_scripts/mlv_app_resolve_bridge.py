#!/usr/bin/env python3
"""Resolve Scripts-menu fallback for exporting MLV clips and importing DNG sequences."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback


DEFAULT_REPO_ROOT = r"F:\Coding Projects\mlvapp-resolve-bridge"
DEFAULT_CONFIG = os.path.join(DEFAULT_REPO_ROOT, "bridge", "config.local-smoke.example.json")
WIN_ID = "com.codex.mlvappresolvebridge.script"


def get_resolve_object():
    if "resolve" in globals() and hasattr(resolve, "GetProjectManager"):
        return resolve

    import DaVinciResolveScript as dvr_script

    instance = dvr_script.scriptapp("Resolve")
    if instance is None:
        raise RuntimeError("Could not connect to DaVinci Resolve.")
    return instance


def dng_sequence_import_info(asset_path: str) -> dict[str, object]:
    path = Path(asset_path)
    directory = path if path.is_dir() else path.parent
    groups: dict[tuple[str, int, str], list[int]] = {}

    if not directory.exists():
        return {"FilePath": asset_path}

    for candidate in directory.iterdir():
        match = re.match(r"^(.*?)(\d+)(\.[dD][nN][gG])$", candidate.name)
        if not match:
            continue
        key = (match.group(1), len(match.group(2)), match.group(3))
        groups.setdefault(key, []).append(int(match.group(2)))

    if not groups:
        return {"FilePath": asset_path}

    (prefix, width, extension), frames = max(groups.items(), key=lambda item: len(item[1]))
    return {
        "FilePath": str(directory / f"{prefix}%0{width}d{extension}"),
        "StartIndex": min(frames),
        "EndIndex": max(frames),
    }


def request_mlv_files() -> list[str]:
    selected = fusion.RequestFile("", "", {"FReqB_Multi": True})
    if not selected:
        return []

    raw = eval(str(selected), {"__builtins__": {}})
    parent = raw.pop("Path", "")
    return [
        os.path.join(parent, child)
        for child in raw.values()
        if str(child).lower().endswith(".mlv")
    ]


class BridgeWindow:
    def __init__(self):
        self.ui = fusion.UIManager
        self.dispatcher = bmd.UIDispatcher(self.ui)
        self.resolve = get_resolve_object()
        self.paths: list[str] = []
        self.items = None
        self.window = None

    def build(self):
        existing = self.ui.FindWindow(WIN_ID)
        if existing:
            existing.Show()
            existing.Raise()
            return None

        self.window = self.dispatcher.AddWindow(
            {
                "ID": WIN_ID,
                "Geometry": [120, 120, 760, 560],
                "WindowTitle": "MLV-App Resolve Bridge",
            },
            self.ui.VGroup({"Spacing": 8}, [
                self.ui.Label({
                    "Text": "MLV-App Resolve Bridge",
                    "Weight": 0,
                    "Font": self.ui.Font({"Family": "Helvetica", "PointSize": 16, "Bold": True}),
                }),
                self.ui.HGroup({"Weight": 0}, [
                    self.ui.Label({"Text": "Python", "Weight": 0.12}),
                    self.ui.LineEdit({"ID": "python", "Text": "python", "Weight": 0.88}),
                ]),
                self.ui.HGroup({"Weight": 0}, [
                    self.ui.Label({"Text": "Repo", "Weight": 0.12}),
                    self.ui.LineEdit({"ID": "repo_root", "Text": DEFAULT_REPO_ROOT, "Weight": 0.88}),
                ]),
                self.ui.HGroup({"Weight": 0}, [
                    self.ui.Label({"Text": "Config", "Weight": 0.12}),
                    self.ui.LineEdit({"ID": "config", "Text": DEFAULT_CONFIG, "Weight": 0.88}),
                ]),
                self.ui.HGroup({"Weight": 0}, [
                    self.ui.Button({"ID": "add", "Text": "Add MLV Clips...", "Weight": 0.18}),
                    self.ui.Button({"ID": "clear", "Text": "Clear", "Weight": 0.10}),
                    self.ui.Button({"ID": "run", "Text": "Export and Import", "Weight": 0.18}),
                    self.ui.HGap(0, 0.54),
                ]),
                self.ui.Label({"Text": "Queue", "Weight": 0}),
                self.ui.TextEdit({"ID": "queue", "ReadOnly": True, "Weight": 0.35}),
                self.ui.Label({"Text": "Log", "Weight": 0}),
                self.ui.TextEdit({"ID": "log", "ReadOnly": True, "Weight": 0.65}),
            ]),
        )

        self.items = self.window.GetItems()
        self.window.On[WIN_ID].Close = self.close
        self.window.On["add"].Clicked = self.add_clips
        self.window.On["clear"].Clicked = self.clear
        self.window.On["run"].Clicked = self.export_and_import
        return self.window

    def log(self, message: str):
        current = self.items["log"].PlainText or ""
        self.items["log"].PlainText = f"{current}{message}\n"

    def render_queue(self):
        self.items["queue"].PlainText = "\n".join(self.paths)

    def add_clips(self, _event):
        self.paths = list(dict.fromkeys([*self.paths, *request_mlv_files()]))
        self.render_queue()

    def clear(self, _event):
        self.paths.clear()
        self.items["queue"].PlainText = ""
        self.items["log"].PlainText = ""

    def bridge_command(self) -> list[str]:
        repo_root = self.items["repo_root"].Text
        config = self.items["config"].Text
        python = self.items["python"].Text or "python"
        return [
            python,
            os.path.join(repo_root, "bridge", "mlvapp_resolve_bridge.py"),
            "--config",
            config,
            *self.paths,
        ]

    def export_and_import(self, _event):
        if not self.paths:
            self.log("No MLV clips selected.")
            return

        try:
            repo_root = self.items["repo_root"].Text
            command = self.bridge_command()
            self.log(f"Exporting {len(self.paths)} clip(s)...")
            completed = subprocess.run(
                command,
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            if completed.stderr:
                self.log(completed.stderr.strip())
            payload = json.loads(completed.stdout)
            if completed.returncode != 0:
                self.log(f"Bridge exited with code {completed.returncode}.")

            assets = [
                asset
                for result in payload.get("results", [])
                for asset in result.get("assets", [])
            ]
            if not assets:
                self.log("No exported assets were discovered.")
                return

            project = self.resolve.GetProjectManager().GetCurrentProject()
            if project is None:
                self.log("No current Resolve project.")
                return

            media_pool = project.GetMediaPool()
            self.resolve.OpenPage("media")
            clip_infos = [dng_sequence_import_info(asset) for asset in assets]
            imported = media_pool.ImportMedia(clip_infos)
            for info in clip_infos:
                suffix = ""
                if "StartIndex" in info:
                    suffix = f" [{info['StartIndex']}-{info['EndIndex']}]"
                self.log(f"Resolve import: {info['FilePath']}{suffix}")
            self.log(f"Imported {len(imported or [])} item(s).")
        except Exception:
            self.log(traceback.format_exc())

    def close(self, _event):
        self.dispatcher.ExitLoop()

    def run(self):
        window = self.build()
        if window is None:
            return
        window.Show()
        self.dispatcher.RunLoop()


BridgeWindow().run()
