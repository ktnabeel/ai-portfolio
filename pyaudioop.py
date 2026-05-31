"""Compatibility shim for Python 3.13 Spaces builds.

Gradio pulls in :mod:`pydub`, which expects an ``audioop``-compatible module
on Python versions where the stdlib module is absent. The pure-Python fallback
already ships inside pydub, so this shim simply re-exports it.
"""

from __future__ import annotations

from pydub.pyaudioop import *  # noqa: F401,F403

