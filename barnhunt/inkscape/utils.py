import logging
import os
import shutil
import sys
from pathlib import Path
from subprocess import run


log = logging.getLogger()


def get_user_data_directory(inkscape_command: str = "inkscape") -> Path:
    """Attempt to determine Inkscape’s user profile directory in various ways."""
    try:
        return _user_data_directory(inkscape_command)
    except Exception as exc:
        log.warning("failed to query inkscape for profile directory: %s", exc)
        return get_default_user_data_directory()


def _user_data_directory(inkscape_command: str = "inkscape") -> Path:
    """Run ``inkscape --user-data-directory`` to determine path to profile directory."""
    inkscape = shutil.which(inkscape_command)
    if inkscape is None:
        raise FileNotFoundError(f"command {inkscape_command!r} not found")
    cmd = (inkscape, "--user-data-directory")
    proc = run(cmd, capture_output=True, text=True, check=True)
    # Use final line: Inkscape 1.0 AppImage prints some initial cruft.
    _, _, user_data_dir = proc.stdout.strip().rpartition("\n")
    if not user_data_dir:
        raise ValueError(f"{' '.join(cmd)!r} did not produce any output")
    return Path(user_data_dir)


def get_default_user_data_directory() -> Path:
    """Attempt to determine Inkscape’s user profile directory
    from the environment.

    This attempts to duplicate the way that Inkscape itself deduces the
    user profile directory.
    """
    # Get the base configuration directory used by Inkscape.
    #
    # On Windows this appears to be %APPDATA% (typically
    # C:\Users\UserName\AppData\Roaming).
    #
    # On POSIX systems this is $XDG_CONFIG_HOME (default ~/.config).
    if sys.platform == "win32":
        config_home = Path(_get_appdata())
    elif "XDG_CONFIG_HOME" in os.environ:
        config_home = Path(os.environ["XDG_CONFIG_HOME"])
    else:
        config_home = Path.home() / ".config"

    return config_home / "inkscape"


def _get_appdata() -> str:
    """Get path to the Windows %APPDATA% directory."""
    from ctypes import c_int, create_unicode_buffer
    from ctypes import windll  # type: ignore[attr-defined]
    from ctypes.wintypes import DWORD, HANDLE, HWND, MAX_PATH

    CSIDL_APPDATA = 26

    path_buf = create_unicode_buffer(MAX_PATH)
    result = windll.shell32.SHGetFolderPathW(
        HWND(), c_int(CSIDL_APPDATA), HANDLE(), DWORD(), path_buf
    )
    if result != 0:
        raise RuntimeError(  # pragma: NO COVER
            f"ctypes call to SHGetFolderPathW failed ({result})"
        )
    return path_buf.value
