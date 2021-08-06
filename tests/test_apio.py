import asyncio
from datetime import timedelta
import pytest
from apisession import (
    APISession,
    Throttle,
    Debouncer,
)


@pytest.fixture
async def url(aiohttp_raw_server):
    from aiohttp import web

    async def handler(request):
        requested_status = int(request.path.strip('/'))
        return web.Response(
            status=requested_status,
        )

    server = await aiohttp_raw_server(handler)
    return f'http://{server.host}:{server.port}'


@pytest.fixture
async def slumber(monkeypatch):
    condition = asyncio.Condition()
    true_sleep = asyncio.sleep

    class Slumber:
        sleeping = False

        @staticmethod
        async def sleep(secs):
            return await true_sleep(secs)

        @staticmethod
        async def wake():
            async with condition:
                return condition.notify()

    async def fake_sleep(secs):
        async with condition:
            await condition.wait()

    monkeypatch.setattr(asyncio, 'sleep', fake_sleep)
    yield Slumber


async def test_throttle(slumber, url):
    throttle = Throttle(
        release_rate=3,
        release_freq=timedelta(seconds=0.1),
    )

    async with APISession(
        url=url,
        middlewares=[throttle]
    ) as session:
        assert not throttle.throttled()

        await session.get('200')
        assert not throttle.throttled()

        await session.get('200')
        await session.get('200')
        assert throttle.throttled()

        throttled_request = asyncio.create_task(session.get('200'))
        assert not throttled_request.done()
        assert throttle.throttled()

        await slumber.wake()
        await throttled_request
        assert not throttle.throttled()


async def test_debouncer(slumber, url):
    debouncer = Debouncer(
        interval=timedelta(seconds=10),
        statuses=[429],
    )

    async with APISession(
        url=url,
        middlewares=[debouncer]
    ) as session:
        await session.get('200')
        assert not debouncer.backing_off()

        await session.get('429')
        await slumber.sleep(0)

        assert debouncer.backing_off()

        await slumber.wake()
        await slumber.sleep(0)
        assert not debouncer.backing_off()
