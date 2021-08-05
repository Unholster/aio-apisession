import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class Throttle:
    release_rate: int
    release_freq: timedelta
    _semaphore: asyncio.BoundedSemaphore = field(init=False)
    _task: asyncio.Task = field(init=False)

    def __post_init__(self):
        self._semaphore = asyncio.BoundedSemaphore(self.release_rate)
        self._task = asyncio.create_task(self.run())

    def throttled(self):
        return self._semaphore.locked()

    async def run(self):
        '''Releases the Bounded Sempaphore that throttles requests
        at a defined rate
        '''
        while True:
            await asyncio.sleep(self.release_freq)
            for i in range(self.release_rate):
                self._semaphore.release()

    async def handle_request(self, request: dict):
        await self._semaphore.acquire()
        return request
