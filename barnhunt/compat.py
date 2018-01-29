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
