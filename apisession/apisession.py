# APIO is a asynchronous aiohttp-based general purpose client
# with features for common API integration scenarios
from itertools import count
from typing import Optional, Union
import logging

import aiohttp
from aiohttp.client_exceptions import ClientPayloadError
from yarl import URL

logger = logging.getLogger(__name__)


class Retry:
    pass


class APISession:
    def __init__(
        self,
        name: str = 'default',
        url: Optional[Union[str, URL]] = None,
        middlewares: list = None,
        **kwargs
    ):
        self._name = name
        self._url = None if url is None else URL(url)
        self._session = aiohttp.ClientSession(**kwargs)

        _middlewares = middlewares or []

        self._request_handlers = [
            m.handle_request
            for m in _middlewares
            if hasattr(m, 'handle_request')
        ]
        self._response_handlers = [
            m.handle_response
            for m in _middlewares
            if hasattr(m, 'handle_response')
        ]

        for m in _middlewares:
            if hasattr(m, 'set_apisession'):
                m.set_apisession(self)

    async def get(self, url: Union[str, URL], **kwargs):
        return await self.request('GET', url, **kwargs)

    async def post(self, url: Union[str, URL], **kwargs):
        return await self.request('POST', url, **kwargs)

    async def request(self, method: str, url: Union[str, URL], **kwargs):
        '''Alias for ClientSession request:
            - Performs request on integration's client
            - Supports URLs relative to the integration's base URL
            - URL passed as first and only positional argument
            - Throttles requests according to `max_requests_per_minute`
        '''

        for attempt in count(1):
            request_url = (
                URL(url)
                if self._url is None
                else self._url.join(URL(url))
            )

            request = {
                'url': request_url,
                'method': method,
                **kwargs,
            }

            for handler in self._request_handlers:
                request = await handler(request)

            response = await self._session.request(**request)

            logger.debug(f'[{self._name}] Sent (attempt {attempt}): {request}')
            logger.debug(f'[{self._name}] Response: {response.status} {url}')
            logger.debug(f'[{self._name}] Headers received:', response.headers)

            for handler in self._response_handlers:
                response = await handler(response)
                if response is None:
                    return

            if response != Retry:
                break

            logger.info(f'Attempt {attempt} failed, will retry')

        try:
            logger.debug(
                '[{}] Body received: {}'
                .format(self._name, await response.text())
            )
        except UnicodeDecodeError:
            logger.debug(
                '[{}] Body received: {} bytes, non-utf8 data'.format(
                    self._name, len(await response.read())
                )
            )
        except ClientPayloadError:
            logger.warn(f'[{self._name}] Client Payload Error')

        return response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        return await self._session.close()
