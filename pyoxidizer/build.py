import os
import re
import subprocess
import sys
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


def compile_requirements(source_file, output_file):
    args = [
        source_file,
        f"--output-file={output_file}",
        "--resolver=backtracking",
        "--pip-args=--only-binary :all:",
        "--emit-options",
        "--annotate",
    ]
    print(
        "================================================================",
        file=sys.stderr,
    )
    print("pip-compile", *args, file=sys.stderr)
    subprocess.run(
        [sys.executable, "-m", "piptools", "compile", *args],
        check=True,
    )


def run_pyoxidizer(*args, vars=None, config=None):
    env = os.environ.copy()

    if config is not None:
        env["PYOXIDIZER_CONFIG"] = os.path.abspath(config)

    setvars = []
    if vars is not None:
        for key, value in vars.items():
            setvars.extend(["--var", key, value])

    print(
        "================================================================",
        file=sys.stderr,
    )
    print("pyoxidizer", *args, file=sys.stderr)
    subprocess.run(["pyoxidizer", *args, *setvars], env=env, check=True)


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


if __name__ == "__main__":
    main()
