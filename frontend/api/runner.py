from collections.abc import Callable
from typing import Any

from nicegui import run

async def call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Call a function and handle exceptions."""
    return await run.io_bound(fn,*args, **kwargs)