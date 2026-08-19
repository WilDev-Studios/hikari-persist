from __future__ import annotations

from hikaripersist import (
    __hikari_version__,
    __version__,
)
from importlib.metadata import version
from typing import TYPE_CHECKING

import logging

if TYPE_CHECKING:
    from hikari import GatewayBot

logger: logging.Logger = logging.getLogger("persist.ux")

async def check_updates(bot: GatewayBot) -> None:
    session = bot.rest._client_session

    try:
        async with session.get("https://pypi.org/pypi/hikari-persist/json") as response:
            latest: str = (await response.json())["info"]["version"]
    except Exception:
        logger.warning("Unable to fetch latest `hikari-persist` version from PyPI")
        return

    if latest == __version__:
        return

    logger.info(
        f"Update available for hikari-persist: {__version__} -> {latest}; "
        "consider updating for latest features, bug fixes, and hikari compatibility"
    )

def verify_compatibility() -> None:
    current: str = version("hikari")
    if current == __hikari_version__:
        return

    error: str = f"hikari-persist {__version__} requires hikari {__hikari_version__}, not {current}"
    logger.error(error)
    raise ImportError(error)
