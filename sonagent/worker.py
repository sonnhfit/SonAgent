import logging
import time
import traceback
from os import getpid
from typing import Any, Callable, Dict, Optional


import sdnotify

from sonagent import __version__
from sonagent.sonbot import SonBot

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

