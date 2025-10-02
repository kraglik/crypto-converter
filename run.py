import asyncio
import signal
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from contextlib import suppress
from functools import partial

from converter.shared.config import get_settings
from converter.shared.di import get_container
from converter.shared.logging import configure_logging, get_logger

settings = get_settings()

configure_logging(
    log_level=settings.LOG_LEVEL,
    json_logs=settings.JSON_LOGS
)

logger = get_logger(__name__)


def setup_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Crypto Converter App Entrypoint",
        formatter_class=RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    api_parser = subparsers.add_parser("api", help="Run the FastAPI web server.")
    api_parser.set_defaults(func=run_api)

    consumer_parser = subparsers.add_parser(
        "consumer",
        aliases=["quote-consumer"],
        help="Run the background quote consumer."
    )
    consumer_parser.set_defaults(func=run_consumer)

    return parser


def run_api(args) -> None:
    import uvicorn
    from converter.adapters.inbound.api.app import app

    logger.info(
        "api_starting",
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL
    )

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )


async def run_consumer_async(args) -> None:
    container = get_container(app_type="consumer")

    consumer = container.quote_consumer()
    logger.info("quote_consumer_initialized")

    stop_event = asyncio.Event()

    def initiate_shutdown(sig: signal.Signals) -> None:
        logger.info("shutdown_signal_received", signal=sig.name)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            partial(initiate_shutdown, sig)
        )
        logger.debug("signal_handler_registered", signal=sig.name)

    consumer_task = asyncio.create_task(consumer.start(), name="quote_consumer_loop")
    logger.info("quote_consumer_started")

    await stop_event.wait()

    logger.info("quote_consumer_stopping")
    await consumer.stop()

    with suppress(asyncio.CancelledError):
        await consumer_task

    try:
        redis_client = container.redis_client()
        await redis_client.aclose()
        logger.info("redis_closed")
    except Exception as e:
        logger.warning("redis_close_error", error=str(e))

    try:
        engine = container.db_engine()
        await engine.dispose()
        logger.info("database_engine_disposed")
    except Exception as e:
        logger.warning("engine_dispose_error", error=str(e))

    logger.info("quote_consumer_stopped")


def run_consumer(args) -> None:
    try:
        asyncio.run(run_consumer_async(args))
    except KeyboardInterrupt:
        logger.info("consumer_interrupted")


def main() -> None:
    parser = setup_arg_parser()
    args = parser.parse_args()

    logger.info("command_starting", command=args.command)

    try:
        args.func(args)
    except Exception as e:
        logger.error(
            "command_failed",
            command=args.command,
            error=str(e),
            exc_info=True
        )
        sys.exit(1)

    logger.info("command_completed", command=args.command)
    sys.exit(0)


if __name__ == "__main__":
    main()
