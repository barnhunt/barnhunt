from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from packaging.version import Version
from pdm.backend.hooks import Context

PROJECT_ROOT = Path(__file__).parent


################################################################
#
# Generate dynamic README
#


def pdm_build_initialize(context: Context) -> None:
    """Generate README by concatenating README.md and CHANGES.md"""
    metadata = context.config.metadata
    if "readme" in metadata.get("dynamic", []):
        metadata["dynamic"].remove("readme")
        metadata["readme"] = {
            "text": compute_readme(context.root),
            "content-type": "text/markdown",
        }


def compute_readme(root: Path) -> str:
    readme = root / "README.md"
    changes = root / "CHANGES.md"
    return "\n".join(
        file.read_text("utf-8").rstrip() + "\n" for file in (readme, changes)
    )


################################################################
#
# Helpers for running pyoxidizer
#
#


def get_dist_version() -> str:
    """Get the current distribution version number."""
    proc = subprocess.run(
        ["pdm", "show", "--version"],
        capture_output=True,
        check=True,
        text=True,
    )
    return proc.stdout.strip()


def get_product_version(dist_version: str) -> str:
    """Return a version number suitable for using for the WiX installer builder.

    WiX apparently only accepts version number consisting of between one and four
    dot-separated non-negative integers.

    Here we return <major>.<minor>.<micro>.<build>, where normally <build>
    is taken from $GITHUB_RUN_NUMBER, guaranteed increasing run number for the
    workflow.

    """
    version = Version(dist_version)
    build_number = os.environ.get(
        "BARNHUNT_BUILD_NUMBER", os.environ.get("GITHUB_RUN_NUMBER")
    )
    if build_number is not None:
        build = int(build_number)
        assert build >= 0
        return f"{version.major}.{version.minor}.{version.micro}.{build}"
    return f"{version.major}.{version.minor}.{version.micro}"


def oxidize() -> None:
    """Run `pyoxidizer build [args]` with some approriate settings."""
    dist_version = get_dist_version()
    product_version = get_product_version(dist_version)
    # This is what goes into `barnhunt.__version__`
    barnhunt_version = f"{product_version} ({dist_version})"

    cmd: list[str | Path]
    cmd = ["pyoxidizer", "build", *sys.argv[1:]]
    cmd.extend(["--path", PROJECT_ROOT / "pyoxidizer"])
    cmd.extend(["--var", "product_version", product_version])
    cmd.extend(["--var", "barnhunt_version", barnhunt_version])
    print(*cmd)

    subprocess.run(
        cmd,
        check=True,
        stderr=subprocess.STDOUT,
    )


def copy_output() -> None:
    """Copy pyoxidizer out from deep in the build tree to the pyoxidizer directory.

    This also mangles the names of the files copied to add the target-triple.
    """
    cwd = PROJECT_ROOT
    dest_path = PROJECT_ROOT / "pyoxidizer"
    build_path = PROJECT_ROOT / "pyoxidizer/build"

    outputs = [
        path
        for path in build_path.glob("*/*/*/*")
        if path.is_file() and path.suffix in {".msi", ".exe", ".app", ""}
    ]

    print("================================================================")
    seen = set()
    for built in sorted(outputs, key=lambda path: path.stat().st_mtime, reverse=True):
        # output is in e.g:
        #    build/<target-triple>/{debug|release}/<build-target>/*.msi
        target_triple = built.parts[-4]
        dest = dest_path / f"{built.stem}-{target_triple}{built.suffix}"
        if dest not in seen:
            print(f"Copying {built.relative_to(cwd)} to {dest.relative_to(cwd)}")
            shutil.copyfile(built, dest)
            seen.add(dest)
    if len(seen) == 0:
        print("No output found!")
