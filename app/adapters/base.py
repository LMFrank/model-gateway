from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass


class AdapterError(Exception):
    pass


class ProviderConnectionError(AdapterError):
    """Provider connection failed before an upstream response was available."""


@dataclass(slots=True)
class StreamHandle:
    iterator: AsyncIterator[bytes]
    close: Callable[[], Awaitable[None]]
