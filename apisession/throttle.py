import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging

from .callbacks import terminate_on_error

logger = logging.getLogger(__name__)


@dataclass
class Throttle:
    release_rate: int
    release_freq: timedelta
    _semaphore: asyncio.BoundedSemaphore = field(init=False)
    _task: asyncio.Task = field(init=False, default=None)

    def __post_init__(self):
        self._semaphore = asyncio.BoundedSemaphore(self.release_rate)

    def throttled(self):
        return self._semaphore.locked()

    def set_apisession(self, apisession):
        if not self._task:
            self._task = asyncio.create_task(self.run())
            self._task.add_done_callback(terminate_on_error)

    async def run(self):
        '''Releases the Bounded Sempaphore that throttles requests
        at a defined rate
        '''

        logger.info('Starting Throttle')
        while True:
            await asyncio.sleep(self.release_freq.total_seconds())
            for i in range(self.release_rate):
                try:
                    self._semaphore.release()
                except ValueError:
                    # Semaphore overflow
                    break

    async def handle_request(self, request: dict):
        if self.throttled():
            logger.info('Throttling {}'.format(request.get('url')))

        await self._semaphore.acquire()
        return request
