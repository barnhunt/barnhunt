import fileinput
import pkgutil
import re
import sys
from importlib import import_module
from pathlib import Path

INF = float("inf")


def module_size(module_info: pkgutil.ModuleInfo) -> float:
    module = module_info.name
    if re.search(r"\b(test|__main__)\b", module):
        return INF
    if module in {"idlelib.idle", "this", "antigravity"}:
        return INF
    try:
        mod = import_module(module)
    except (AssertionError, ImportError, LookupError):
        return INF
    mod_file = getattr(mod, "__file__", None)
    if mod_file is None:
        return 0                # builtin
    mod_path = Path(mod_file)
    mod_path.name.startswith("__init__.")
    if not module_info.ispkg:
        return mod_path.stat().st_size
    return sum(
        p.stat().st_size for p in mod_path.parent.glob("**/*")
        if p.is_file()
    )


def human(size: float) -> str:
    if size is INF:
        return "-"
    for suffix, divisor in [
        ("G", 1024 ** 3),
        ("M", 1024 ** 2),
        ("K", 1024 ** 1),
    ]:
        fmt = f"{size / divisor:.1f}{suffix}"
        if not fmt.startswith("0"):
            return fmt
    return f"{size}b"


def main() -> None:
    required_modules = set()

    if len(sys.argv) > 1:
        for line in fileinput.input(files=sys.argv[1:]):
            module = line.strip()
            if module and not module.startswith("#"):
                required_modules.add(module)

    seen: set[str] = set()
    unused_module_info: list[pkgutil.ModuleInfo] = []
    for module_info in sorted(pkgutil.walk_packages(), key=lambda m: m.name.count(".")):
        module = module_info.name
        if module in required_modules:
            continue
        parts = module.split(".")
        if seen.isdisjoint(".".join(parts[:n]) for n in range(1, len(parts))):
            seen.add(module)
            unused_module_info.append(module_info)

    total = 0
    total_skipped = 0
    for module_info in sorted(unused_module_info, key=module_size, reverse=True):
        # FIXME: Omit some of PIL?
        top, sep, _ = module_info.name.partition(".")
        skip = sep and top not in {"lxml", "logging", "http", "json"}
        size = module_size(module_info)
        skip = skip or size < 8196
        if size is not INF:
            if skip:
                total_skipped += int(size)
            else:
                total += int(size)
        line = (
            f"{module_info.name:<20s} "
            f"{human(size):6s} {human(total):6s} {human(total_skipped):6s}"
        )
        if skip:
            line = "#" + line
        print(line)


if __name__ == "__main__":
    main()
