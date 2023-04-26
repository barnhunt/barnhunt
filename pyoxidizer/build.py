from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from itertools import chain
from pathlib import Path


def get_version():
    """Get the current version number."""
    proc = subprocess.run(
        ["pdm", "show", "--version"],
        capture_output=True,
        check=True,
        text=True,
    )
    return proc.stdout.strip()


def get_product_version(version):
    """Return a version number suitable for using for the WiX installer builder.

    WiX apparently only accepts version number consisting of between one and four
    dot-separated non-negative integers.

    Here we translate something like `v1.2.0rc5-14-gc920d76` to `1.2.0.5`.

    It's not perfect.
    """
    # strip any +local part and .dev suffix
    external_version, _, _ = version.partition("+")
    non_dev_version, _, _ = external_version.partition(".dev")
    nums = re.findall(r"\d+", non_dev_version)
    return ".".join(nums[:4])


def run(*cmd, extra_env=None):
    env = os.environ
    if extra_env is not None:
        env = {**env, **extra_env}

    print("================================================================")
    print(*cmd)
    subprocess.run(cmd, check=True, env=env, stderr=subprocess.STDOUT)


def compile_requirements(source_file, output_file):
    args = [
        source_file,
        f"--output-file={output_file}",
        "--resolver=backtracking",
        "--pip-args=--only-binary :all:",
        "--emit-options",
        "--annotate",
    ]

    run(sys.executable, "-m", "piptools", "compile", *args)


def run_pyoxidizer(*args, vars=None, config=None):
    env = {}
    if config is not None:
        env["PYOXIDIZER_CONFIG"] = os.path.abspath(config)

    setvars = []
    if vars is not None:
        for key, value in vars.items():
            setvars.extend(["--var", key, value])

    run("pyoxidizer", *args, *setvars, extra_env=env)


def copy_output(config=None):
    here = Path(config or __file__).parent
    build_path = here / "build"
    outputs = chain.from_iterable(
        build_path.glob(f"**/*install*/*.{ext}") for ext in ("exe", "msi", "app")
    )

    def dwim_build_target(path: Path) -> str | None:
        for part in reversed(path.parts):
            if re.match(r"(.*-){2}.", part):
                return part
        return None

    print("================================================================")
    for built in sorted(outputs, key=lambda path: path.stat().st_mtime):
        target = here / built.name
        build_target = dwim_build_target(built.relative_to(build_path))
        if build_target is not None:
            target = target.with_stem(f"{target.stem}-{build_target}")
        print(f"Copying {built} to {target}")
        shutil.copyfile(built, target)
    else:
        print("No output found!")


def main():
    here = Path(__file__).parent
    pyproject_toml = here / "../pyproject.toml"
    # we generate this from pyproject.toml
    requirements_txt = here / "requirements.txt"

    pyoxidizer_config = here / "pyoxidizer.bzl"

    version = get_version()
    product_version = get_product_version(version)
    barnhunt_version = f"{product_version} ({version})"

    print("barnhunt.__version__:", barnhunt_version)

    compile_requirements(pyproject_toml, requirements_txt)
    run_pyoxidizer(
        "build",
        *sys.argv[1:],
        config=pyoxidizer_config,
        vars={
            "barnhunt_version": barnhunt_version,
            "product_version": product_version,
            "requirements_txt": os.path.abspath(requirements_txt),
        },
    )
    copy_output(config=pyoxidizer_config)


if __name__ == "__main__":
    main()
