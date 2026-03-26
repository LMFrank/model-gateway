from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass


class AdapterError(Exception):
    pass


@dataclass(slots=True)
class StreamHandle:
    iterator: AsyncIterator[bytes]
    close: Callable[[], Awaitable[None]]
