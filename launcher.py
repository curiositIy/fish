import argparse
import asyncio
import logging.handlers
import os
import sys
import tomllib

import aiohttp
from discord import gateway
from core import Fishie
from utils import Config, base_header, create_pool, identify_mobile

gateway.DiscordWebSocket.identify = identify_mobile


async def start(testing: bool):
    logger = logging.getLogger("fishie")
    logger.setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.INFO)

    handlers = [
        logging.handlers.RotatingFileHandler(
            filename="discord.log",
            encoding="utf-8",
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=5,  # Rotate through 5 files
        ),
        logging.StreamHandler(sys.stdout),
    ]

    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
    )

    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    with open("config.toml", "rb") as fileObj:
        config: Config = Config(**tomllib.load(fileObj))

    jsk_envs = [
        "JISHAKU_RETAIN",
        "JISHAKU_HIDE",
        "JISHAKU_NO_DM_TRACEBACK",
        "JISHAKU_NO_UNDERSCORE",
        "JISHAKU_FORCE_PAGINATOR",
    ]

    for env in jsk_envs:
        os.environ[env] = "True"

    pool = await create_pool(config["databases"]["psql_testing" if testing else "psql"])
    logger.info("Connected to Postgres")

    async with (
        aiohttp.ClientSession(headers=base_header) as session,
        Fishie(
            config=config, logger=logger, pool=pool, session=session, testing=testing
        ) as bot,
    ):
        await bot.start(
            config["tokens"]["testing_bot"] if testing else config["tokens"]["bot"]
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--testing", "-t", required=False, default=False, type=bool)

    parsed = parser.parse_args()

    asyncio.run(start(parsed.testing))
