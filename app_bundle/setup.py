from pathlib import Path

from setuptools import setup

import objc._objc
import zlib


if not hasattr(zlib, "__file__"):
    zlib.__file__ = objc._objc.__file__


ROOT = Path(__file__).resolve().parents[1]
APP = [str(ROOT / "src" / "todo_tracker" / "menubar.py")]
DATA_FILES = [str(ROOT / "assets" / "icon.png")]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": str(ROOT / "assets" / "icon.png"),
    "packages": ["todo_tracker", "rumps", "sqlalchemy", "AppKit", "Foundation", "objc"],
    "plist": {
        "CFBundleName": "TodoTracker",
        "CFBundleDisplayName": "TodoTracker",
        "CFBundleIdentifier": "local.todo-tracker",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
}


setup(
    name="TodoTracker",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    package_dir={"": str(ROOT / "src")},
    packages=["todo_tracker"],
)
