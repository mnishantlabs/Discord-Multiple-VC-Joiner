"""One long-lived asyncio loop owned by a dedicated thread.

This replaces the old ``_run_async`` helper that created a brand-new event
loop for every coroutine call. Creating a loop per call had two fatal
consequences for the voice feature:

* ``VoiceConnection.connect`` spawned a heartbeat task on loop A; when the
  calling loop was closed the heartbeat died and the gateway dropped the
  connection within a minute.
* ``disconnect`` ran on a *different* loop (B), cancelling a task that
  belonged to closed loop A (cross-loop cancellation → undefined behaviour).

With a single loop that lives for the whole process, persistent objects
(shared HTTP session, voice connections, heartbeats) stay on the loop that
created them and every operation is scheduled onto the same thread.
"""

import asyncio
import functools
import threading
from types import CoroutineType
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class AsyncBridge:
    """Runs an event loop on a background daemon thread and accepts work."""

    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._closed = False
        self._thread = threading.Thread(target=self._run, name="async-bridge", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            try:
                self._cancel_pending()
            finally:
                try:
                    asyncio.set_event_loop(None)
                finally:
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        task.cancel()
                    if self.loop.is_running() is False:
                        self.loop.close()

    def _cancel_pending(self) -> None:
        for task in asyncio.all_tasks(self.loop):
            task.cancel()

    def submit(self, coro: CoroutineType[Any, Any, T]) -> "asyncio.Future[T]":
        """Schedule *coro* on the loop; returns a concurrent Future."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def call_soon(self, fn: Callable[..., Any], *args: Any) -> None:
        """Schedule a plain callable on the loop thread."""
        self.loop.call_soon_threadsafe(fn, *args)

    def run_in_thread(self, fn: Callable[..., T], *args: Any) -> "asyncio.Future[T]":
        """Run a blocking function on the loop's default executor."""

        async def _wrapper() -> T:
            return await asyncio.to_thread(fn, *args)

        return self.submit(_wrapper())

    def shutdown(self, timeout: float = 3.0) -> None:
        """Cancel pending work and stop the loop. Safe to call once."""
        if self._closed:
            return
        self._closed = True

        def _stop() -> None:
            self.loop.stop()

        try:
            done = self.submit(self._drain())
            done.result(timeout=timeout)
        except Exception:
            self.call_soon(_stop)
        self._thread.join(timeout=timeout)

    async def _drain(self) -> None:
        tasks = [t for t in asyncio.all_tasks(self.loop)
                 if t is not asyncio.current_task()]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.loop.stop()


def call_after_callback(
    future: "asyncio.Future[T]",
    on_success: Callable[[T], None],
    on_error: Callable[[Exception], None],
) -> None:
    """Attach a callback that wraps ``future.result()`` into success/error."""
    future.add_done_callback(
        functools.partial(_dispatch, on_success=on_success, on_error=on_error)
    )


def _dispatch(done: "asyncio.Future[T]", on_success: Callable[[T], None],
              on_error: Callable[[Exception], None]) -> None:
    try:
        on_success(done.result())
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller's handler
        on_error(exc)