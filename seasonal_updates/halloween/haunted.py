"""Compatibility facade for Haunted Exploration 2.0.

The Haunted system used to live in this single module. The public helpers stay
available here so existing imports in Enceladus do not need to know about the
new internal package layout.
"""

from .haunted_system import *  # noqa: F401,F403
