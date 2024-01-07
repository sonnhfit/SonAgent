import logging
import time
import traceback
from os import getpid
from typing import Any, Callable, Dict, Optional


import sdnotify

from sonagent import __version__
from sonagent.sonbot import SonBot
from sonagent.enums import State

logger = logging.getLogger(__name__)


class Worker:
    
    def __init__(self, args: Dict[str, Any], config: Optional[dict] = None) -> None:
        """
        Init all variables and objects the bot needs to work
        """
        logger.info(f"Starting worker {__version__}")

        self._args = args
        self._config = config
        self._init(False)

        self._heartbeat_msg: float = 0

        # Tell systemd that we completed initialization phase
        self._notify("READY=1")

    def _init(self, reconfig: bool) -> None:
        
        # Init the instance of the bot
        self.sonbot = SonBot(self._config)

        self._sd_notify = sdnotify.SystemdNotifier() if \
            self._config.get('internals', {}).get('sd_notify', False) else None

    def _notify(self, message: str) -> None:
        """
        Removes the need to verify in all occurrences if sd_notify is enabled
        :param message: Message to send to systemd if it's enabled.
        """
        if self._sd_notify:
            logger.debug(f"sd_notify: {message}")
            self._sd_notify.notify(message)

    def run(self) -> None:
        state = None
        while True:
            state = self._worker(old_state=state)
            if state == State.RELOAD_CONFIG:
                self._reconfigure()

    @staticmethod
    def _sleep(sleep_duration: float) -> None:
        """Local sleep method - to improve testability"""
        time.sleep(sleep_duration)

    def _reconfigure(self) -> None:
        """
        Cleans up current freqtradebot instance, reloads the configuration and
        replaces it with the new instance
        """
        # Tell systemd that we initiated reconfiguration
        self._notify("RELOADING=1")

        # Clean up current freqtrade modules
        self.sonbot.cleanup()

        # Load and validate config and create new instance of the bot
        self._init(True)

        self.sonbot.notify_status('config reloaded')

        # Tell systemd that we completed reconfiguration
        self._notify("READY=1")

    def exit(self) -> None:
        # Tell systemd that we are exiting now
        self._notify("STOPPING=1")

        if self.sonbot:
            self.sonbot.notify_status('process died')
            self.sonbot.cleanup()

