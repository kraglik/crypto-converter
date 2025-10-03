import asyncio

import pytest
from converter.shared.utils.scheduler import FixedRateScheduler


@pytest.mark.asyncio
async def test_scheduler_run_without_jobs_returns_immediately():
    sched = FixedRateScheduler()

    await asyncio.wait_for(sched.run_until_shutdown(), timeout=1.0)
    await sched.shutdown()


@pytest.mark.asyncio
async def test_scheduler_prevents_scheduling_after_start():
    sched = FixedRateScheduler()

    async def noop():
        return

    sched.schedule(noop, 1, "job1")

    task = asyncio.create_task(sched.run_until_shutdown())

    await asyncio.sleep(0.05)

    with pytest.raises(RuntimeError):
        sched.schedule(noop, 1, "job2")

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
