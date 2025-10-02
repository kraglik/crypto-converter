import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from converter.shared.logging import get_logger

logger = get_logger(__name__)


class FixedRateScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._started = False

    def schedule(
        self,
        coro_func: Callable[[], Awaitable[None]],
        interval_seconds: int,
        name: str,
    ) -> None:
        """
        Schedule a coroutine to run at fixed intervals.

        :param coro_func: Async function to run periodically
        :param interval_seconds: Interval between executions, in seconds
        :param name: Task name, primarily for logging and identification
        """
        if self._started:
            raise RuntimeError("Cannot schedule tasks after scheduler has started")

        async def _safe_execution() -> None:
            try:
                await coro_func()
            except Exception as e:
                logger.error(
                    "scheduled_task_failed", task_name=name, error=str(e), exc_info=True
                )

        self._scheduler.add_job(
            _safe_execution,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=name,
            name=name,
            max_instances=1,  # I'd rather not poll Binance too many times in parallel
            replace_existing=True,
        )

        logger.info("task_scheduled", task_name=name, interval_seconds=interval_seconds)

    async def run_until_shutdown(self) -> None:
        if not self._scheduler.get_jobs():
            logger.warning("no_tasks_scheduled")
            return

        self._started = True
        self._scheduler.start()

        logger.info("scheduler_started", job_count=len(self._scheduler.get_jobs()))

        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("scheduler_cancelled")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        if not self._started:
            return

        logger.info("scheduler_shutting_down")
        self._scheduler.shutdown(wait=True)
        logger.info("scheduler_shutdown_complete")

    def get_job_info(self) -> list[dict[str, Any]]:
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time,
            }
            for job in self._scheduler.get_jobs()
        ]
