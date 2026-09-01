"""User-intent commands and keyboard shortcuts."""

from typing import Any, Callable

from utils.platform import MOD_CTRL

from controllers.commands import Commands, CommandContext
from controllers.shortcuts import SHORTCUTS, bind_shortcuts

__all__ = ["Commands", "CommandContext", "SHORTCUTS", "bind_shortcuts", "MOD_CTRL", "Callable", "Any"]