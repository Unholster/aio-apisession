import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


def terminate_on_error(task: asyncio.Task) -> None:
    try:
        return task.result()
    except Exception:
        logger.exception('Task failed: %r', task)
        sys.exit(1)
