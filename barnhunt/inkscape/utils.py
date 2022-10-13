import shutil
from pathlib import Path
from subprocess import run


def get_user_data_directory(inkscape_command: str = "inkscape") -> Path:
    # FIXME: fallback to $XDG_CONFIG_HOME-based default (or whatever on Windows)
    # if `inkscape --user-data-directory` fails.
    inkscape = shutil.which(inkscape_command)
    if inkscape is None:
        raise FileNotFoundError(f"inkscape command {inkscape_command!r} not found")
    proc = run(
        (inkscape, "--user-data-directory"), capture_output=True, text=True, check=True
    )
    # Use final line: Inkscape 1.0 AppImage prints some initial cruft.
    _, _, user_data_dir = proc.stdout.strip().rpartition("\n")
    if not user_data_dir:
        raise ValueError("inkscape --user-data-directory gave no output")
    return Path(user_data_dir)
