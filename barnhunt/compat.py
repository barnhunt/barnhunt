try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap  # noqa: F401