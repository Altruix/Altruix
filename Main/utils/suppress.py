# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import inspect
import asyncio
import functools
import logging
from typing import Any, Callable, Optional, Tuple, Type, Union

logger = logging.getLogger("altruix.suppress")


class suppress_error:
    """
    Safe error suppression context manager and decorator.
    
    Acts like `contextlib.suppress(*exceptions)`, but provides informative logging
    instead of swallowing critical failures blindly, preserving debuggability
    across all Altruix modules and plugins.
    
    Usage:
        with suppress_error(msg="Deleting cache file"):
            os.remove(path)
            
        async with suppress_error(Exception, level=logging.WARNING, msg="Sending unafk notification"):
            await m.respond("I am back!")
            
        @suppress_error(log=True, msg="Failed to parse custom filter")
        def check_filter(event):
            ...
    """

    def __init__(
        self,
        *exceptions: Type[BaseException],
        log: bool = True,
        logger_instance: Optional[logging.Logger] = None,
        level: int = logging.DEBUG,
        msg: Optional[str] = None,
        raise_on: Optional[Tuple[Type[BaseException], ...]] = None,
    ):
        self.exceptions = exceptions or (Exception,)
        self.log = log
        self.logger = logger_instance or logger
        self.level = level
        self.msg = msg
        self.raise_on = raise_on or (KeyboardInterrupt, SystemExit, asyncio.CancelledError)

    def __enter__(self) -> "suppress_error":
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Any) -> bool:
        if exc_type is None:
            return False
        # Never suppress process termination or cancellation signals
        if issubclass(exc_type, self.raise_on):
            return False
        if issubclass(exc_type, self.exceptions):
            if self.log:
                prefix = f"[{self.msg}] " if self.msg else ""
                self.logger.log(
                    self.level,
                    f"{prefix}Suppressed {exc_type.__name__}: {exc_val}",
                    exc_info=bool(self.level >= logging.ERROR),
                )
            return True
        return False

    async def __aenter__(self) -> "suppress_error":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        return self.__exit__(exc_type, exc_val, exc_tb)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with self:
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with self:
                    return func(*args, **kwargs)
            return sync_wrapper


# Convenient aliases for natural imports
safe_suppress = suppress_error
suppress = suppress_error

__all__ = ["suppress_error", "safe_suppress", "suppress"]
