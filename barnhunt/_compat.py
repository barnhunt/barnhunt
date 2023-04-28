import sys

if sys.version_info < (3, 10):
    import importlib_metadata
else:
    from importlib import metadata as importlib_metadata

if sys.version_info < (3, 8):
    from typing_extensions import Final
    from typing_extensions import Literal
    from typing_extensions import Protocol
else:
    from typing import Final
    from typing import Literal
    from typing import Protocol


if sys.version_info < (3, 10):
    from typing_extensions import TypeGuard
else:
    from typing import TypeGuard

__all__ = ["importlib_metadata", "Final", "Literal", "Protocol", "TypeGuard"]
