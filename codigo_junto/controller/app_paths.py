import os
import sys
from pathlib import Path


def application_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_path(*parts):
    bundle_dir = getattr(sys, '_MEIPASS', None)
    base = Path(bundle_dir) if bundle_dir else application_dir()
    return base.joinpath(*parts)


def user_data_dir():
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home())
    return base / 'GestionInstitucional'
