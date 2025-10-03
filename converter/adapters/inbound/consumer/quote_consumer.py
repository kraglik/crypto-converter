import asyncio

from tenacity import (
    AsyncRetrying,
    RetryCallState,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from converter.adapters.outbound.rate_source import RateBatch, RateSource
from converter.app.commands.store_quotes import (
    StoreQuotesCommand,
    StoreQuotesCommandHandler,
)
from converter.shared.logging import get_logger

logger = get_logger(__name__)


class QuoteConsumer:
    def __init__(
        self,
        rate_source: RateSource,
        handler: StoreQuotesCommandHandler,
    ) -> None:
        self._rate_source = rate_source
        self._handler = handler
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        logger.info("quote_consumer_starting")

        if self._shutdown_event.is_set():
            logger.info("shutdown_already_set")
            return

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=5, min=5, max=60),
                retry=retry_if_exception_type(Exception),
                before_sleep=self._log_retry,
            ):
                with attempt:
                    await self._run_consumer_loop()
                    break

        except RetryError as e:
            logger.error(
                "quote_consumer_max_retries_exceeded",
                error=str(e.last_attempt.exception()),
                exc_info=True,
            )
            raise

        except asyncio.CancelledError:
            logger.info("quote_consumer_cancelled")
            raise

        finally:
            logger.info("quote_consumer_stopped")

    async def _run_consumer_loop(self) -> None:
        try:
            await self._consume_stream()
        except Exception as e:
            logger.error("quote_consumer_stream_error", error=str(e), exc_info=True)
            raise

    async def _consume_stream(self) -> None:
        try:
            async for batch in self._rate_source.stream():
                if self._shutdown_event.is_set():
                    logger.info("shutdown_signal_received_breaking_stream")
                    break

                if not batch.quotes:
                    logger.debug("received_empty_batch_skipping")
                    continue

                await self._process_batch(batch)

        except asyncio.CancelledError:
            logger.info("consume_stream_cancelled")
            raise
        except Exception as e:
            logger.error("consume_stream_unexpected_error", error=str(e), exc_info=True)
            raise

    async def stop(self) -> None:
        if self._shutdown_event.is_set():
            return

        logger.info("quote_consumer_stopping")
        self._shutdown_event.set()

        await self._rate_source.close()

    async def _process_batch(self, batch: RateBatch) -> None:
        logger.debug("processing_batch", quote_count=len(batch.quotes))

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type(Exception),
            ):
                with attempt:
                    command = StoreQuotesCommand(quotes=batch.quotes)
                    result = await self._handler.handle(command)

                    logger.info(
                        "batch_processed",
                        received=result.total_received,
                    )

        except RetryError as e:
            logger.error(
                "batch_processing_failed_after_retries",
                error=str(e.last_attempt.exception()),
                quote_count=len(batch.quotes),
                exc_info=True,
            )

    @staticmethod
    def _log_retry(retry_state: RetryCallState) -> None:
        logger.warning(
            "quote_consumer_retrying",
            attempt=retry_state.attempt_number,
            wait_seconds=(
                retry_state.next_action.sleep if retry_state.next_action else 0
            ),
            error=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        )
