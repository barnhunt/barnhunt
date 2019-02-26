import sys

# FIXME: unused?
try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap  # noqa: F401

try:
    import enum
except ImportError:
    enum = None
if not hasattr(enum, 'Flag'):
    # python < 3.6
    import aenum as enum

if sys.version_info >= (3, 5):
    import pathlib              # pragma: no cover
else:
    # 3.4 has pathlib, but its Path.mkdir() does not support the
    # not_exist argument
    import pathlib2 as pathlib  # noqa: F401
