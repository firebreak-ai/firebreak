"""Settings for the kit's Python scripts: the environment first, then local/settings.env (see settings.example.env)."""
import os, pathlib

KIT = pathlib.Path(__file__).resolve().parent
LOCAL = KIT / "local"  # data and runs, ignored by git


def setting(name, default=""):
    if os.environ.get(name):
        return os.environ[name]
    f = LOCAL / "settings.env"
    for line in f.read_text().splitlines() if f.exists() else []:
        k, _, v = line.partition("=")
        if k.strip() == name:
            return v.strip()
    return default
