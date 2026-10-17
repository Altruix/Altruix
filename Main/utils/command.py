"""Resolve Python and pip commands to the active environment."""

from __future__ import annotations

import os
import sys
from typing import List


def resolve_command(args: List[str]) -> List[str]:
    if not args:
        return args

    executable = os.path.basename(args[0]).lower()
    python_names = {"python", "python.exe", "python3", "python3.exe", "py", "py.exe", "py3", "py3.exe"}
    pip_names = {"pip", "pip.exe", "pip3", "pip3.exe"}

    if executable in pip_names:
        return [sys.executable, "-m", "pip", *args[1:]]
    if executable in python_names or executable.startswith("python3."):
        rest = args[1:]
        if executable in {"py", "py.exe", "py3", "py3.exe"} and rest:
            if rest[0] == "-3" or rest[0].startswith("-3."):
                rest = rest[1:]
        return [sys.executable, *rest]
    return args
