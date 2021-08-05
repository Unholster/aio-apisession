from aiohttp.web import Response
import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Debouncer:
    interval: timedelta
    statuses: List[int]
    _condition: asyncio.Condition = field(init=False)
    _task: asyncio.Task = field(init=False)

    def __post_init__(self):
        self._condition = asyncio.Condition()
        self._task = asyncio.create_task(self.run())

    async def handle_response(self, response: Response) -> Response:
        if response.status not in self.statuses:
            async with self._condition:
                self._condition.notify()
        return response

    def backing_off(self) -> bool:
        return self._condition.locked()

    async def run(self):
        interval_secs = self.interval.total_seconds()

        while True:
            async with self._condition:
                await self._condition.wait()
                logger.debug('Debounce - wait for {interval_secs} seconds')
                await asyncio.sleep(interval_secs)
