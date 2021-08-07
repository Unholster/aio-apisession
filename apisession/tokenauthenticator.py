import asyncio
from dataclasses import dataclass, field, InitVar
from datetime import timedelta
import logging
from typing import Optional

from .apisession import APISession
from .callbacks import terminate_on_error

logger = logging.getLogger(__name__)

STATE = 0
SESSION = 1


@dataclass
class TokenAuthenticator:
    private_key: str
    get_token: callable
    request_handler: callable
    refresh_interval: timedelta
    initial_state: InitVar[Optional[dict]]
    _mutable: list = field(default_factory=lambda: [None, None])
    _task: asyncio.Task = field(init=False, default=None)

    def __post_init__(self, initial_state: dict):
        self._mutable[STATE] = {
            'token': None,
            **(initial_state or {}),
        }

    def set_apisession(self, apisession: APISession):
        self._mutable[SESSION] = apisession
        if not self._task:
            self._task = asyncio.create_task(self.run())
            self._task.add_done_callback(terminate_on_error)

    async def run(self):
        logger.info('Starting TokenAuthenticator')
        while True:
            logger.info('Refreshing token')
            try:
                self._mutable[STATE] = await self.get_token(
                    api=self._mutable[SESSION],
                    **{
                        **self._mutable[STATE],
                        'private_key': self.private_key,
                    },
                )
                logger.info('Token refreshed')
            except Exception:
                logger.exception('Token refresh failed')

            await asyncio.sleep(self.refresh_interval.total_seconds())

    def get(self, key: str):
        '''Retrieves a value from the state'''
        return self._mutable[STATE].get(key)

    async def handle_request(self, request: dict) -> dict:
        return self.request_handler(
            token=self.get('token'),
            request=request
        )
