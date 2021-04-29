from contextlib import asynccontextmanager
from asyncio import get_event_loop
from threading import Lock
from collections import defaultdict


@asynccontextmanager
async def async_lock(lock):
    loop = get_event_loop()
    await loop.run_in_executor(None, lock.acquire)
    try:
        yield  # the lock is held
    finally:
        lock.release()


class Counter:

    def __init__(self):
        self._lock = Lock()
        self._value = 0

    @property
    def value(self):
        return self._value

    async def increment(self):
        async with async_lock(self._lock):
            self._value += 1

    def decrement(self):
        with self._lock:
            self._value -= 1


viewers = defaultdict(Counter)
