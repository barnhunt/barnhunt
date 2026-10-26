# SPDX-FileCopyrightText: © 2017 Geoffrey T. Dairiki <dairiki@dairiki.org>
# SPDX-License-Identifier: GPL-3.0-only
from importlib import metadata

__all__ = ["__version__"]

__version__ = metadata.version(__name__)
