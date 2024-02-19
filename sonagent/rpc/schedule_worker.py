import asyncio
import logging
from threading import Thread
from typing import TYPE_CHECKING, Any, Callable, Dict, List, TypedDict, Union


logger = logging.getLogger(__name__)


class ScheduleProcess:

    def __init__(self) -> None:
        
        self._running = False
        self._thread = None
        self._loop = None
        self._main_task = None
        self._sub_tasks = None

        self._schedule_config = {}
        self.enabled = True

        self.start()

    def start(self):
        """
        Start the main internal loop in another thread to run coroutines
        """
        if self._thread and self._loop:
            return

        logger.info("Starting ScheduleProcess")

        self._loop = asyncio.new_event_loop()
        self._thread = Thread(target=self._loop.run_forever)
        self._running = True
        self._thread.start()

        self._main_task = asyncio.run_coroutine_threadsafe(self._main(), loop=self._loop)

    async def _handle_producer_connection(self, param: {}, lock: asyncio.Lock):
        print("run handle ")
        pass

    async def _main(self):
        """
        The main task coroutine
        """
        lock = asyncio.Lock()

        try:
            # Create a connection to each producer
            self._sub_tasks = [
                self._loop.create_task(self._handle_producer_connection({}, lock))        
            ]

            await asyncio.gather(*self._sub_tasks)
        except asyncio.CancelledError:
            pass
        finally:
            # Stop the loop once we are done
            self._loop.stop()
