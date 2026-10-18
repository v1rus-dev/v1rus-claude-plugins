#!/usr/bin/env python3
"""Copy the canonical rules engine (plugins/v1rus-core/hooks) into every plugin."""
import pathlib
import shutil

root = pathlib.Path(__file__).resolve().parent.parent
src = root / "plugins/v1rus-core/hooks"
for plugin in sorted((root / "plugins").iterdir()):
    dst = plugin / "hooks"
    if plugin.name == "v1rus-core" or not plugin.is_dir():
        continue
    dst.mkdir(exist_ok=True)
    for name in ("v1rus_rules.py", "hooks.json"):
        shutil.copyfile(src / name, dst / name)
    print("synced", plugin.name)
