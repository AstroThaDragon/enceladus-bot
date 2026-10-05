"""Compatibility entry point for Enceladus economy.

The economy implementation is modularized under :mod:`economy_system` while
this file preserves the existing ``economy`` cog-loading path.
"""

from economy_system.cog import Economy, setup
from economy_system.data import *
from economy_system.shop.views import *