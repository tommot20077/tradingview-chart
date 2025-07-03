"""Main entry point for crypto_single application."""

import asyncio
import logging
from typing import NoReturn

logger = logging.getLogger(__name__)


async def main_async() -> None:
    """Async main function for the application."""
    logger.info("Starting crypto_single application...")

    # TODO: Initialize application components
    # - Load configuration
    # - Setup dependency injection container
    # - Initialize providers, storage, services
    # - Start API server
    # - Start background workers

    logger.info("crypto_single application started successfully")

    # Keep the application running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down crypto_single application...")


def main() -> NoReturn:
    """Main entry point for the application."""
    # Basic logging setup
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        raise SystemExit(0)
    except Exception as e:
        logger.error(f"Application failed with error: {e}")
        raise SystemExit(1)

    # This should never be reached, but satisfies mypy
    raise SystemExit(0)


if __name__ == "__main__":
    main()
