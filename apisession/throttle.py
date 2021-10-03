import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Optional

from .callbacks import terminate_on_error

logger = logging.getLogger(__name__)


@dataclass
class Throttle:
    release_rate: int
    release_freq: timedelta
    initial: Optional[int] = None
    limit: Optional[int] = None
    _semaphore: asyncio.BoundedSemaphore = field(init=False, default=None)
    _task: asyncio.Task = field(init=False, default=None)
    _backlog_counter: int = 0

    def throttled(self):
        return self._semaphore and self._semaphore.locked()

    def set_apisession(self, apisession):
        if not self._task:
            self._task = asyncio.create_task(self.run())
            self._task.add_done_callback(terminate_on_error)

    async def run(self):
        '''Releases the Bounded Sempaphore that throttles requests
        at a defined rate
        '''

        limit = self.limit if self.limit is not None else self.release_rate

        self._semaphore = asyncio.BoundedSemaphore(limit)

        logger.info('Starting Throttle')
        pre_acquire = (limit - self.initial) if self.initial else 0
        for i in range(pre_acquire):
            await self._semaphore.acquire()

        while True:
            await asyncio.sleep(self.release_freq.total_seconds())

            if self.throttled():
                logger.info(f'Throttling - backlog = {self._backlog_counter}')

            for i in range(self.release_rate):
                try:
                    self._semaphore.release()
                except ValueError:
                    # Semaphore overflow
                    break

    async def handle_request(self, request: dict):
        if not self._semaphore:
            return request

        self._backlog_counter += 1
        await self._semaphore.acquire()
        self._backlog_counter -= 1
        return request
