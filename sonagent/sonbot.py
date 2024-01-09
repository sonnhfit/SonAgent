import logging
import traceback
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from math import isclose
from threading import Lock
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

from sonagent.mixins import LoggingMixin
from sonagent.enums.enums import State
from sonagent.enums.rpcmessagetype import RPCMessageType
from sonagent.rpc import RPCManager
from sonagent.persistence.belief_models import Belief
                             

logger = logging.getLogger(__name__)


class SonBot(LoggingMixin):
    def __init__(self, config: dict) -> None:
        self.state = State.STOPPED

        self.config = config

        self.rpc: RPCManager = RPCManager(self)

        # Set initial bot state from config
        initial_state = self.config.get('initial_state')

        self.state = State[initial_state.upper()] if initial_state else State.STOPPED


    def cleanup(self) -> None:
        """
        Cleanup pending resources on an already stopped bot
        :return: None
        """
        logger.info('Cleaning up modules ...')
        try:
            # Wrap db activities in shutdown to avoid problems if database is gone,
            # and raises further exceptions.
            logger.info('Cleaning up process ...')
        except Exception as e:
            logger.warning(f'Exception during cleanup: {e.__class__.__name__} {e}')

        # finally:
        #     self.strategy.ft_bot_cleanup()

        # RPC cleanup 
        # self.rpc.cleanup()
        # if self.emc:
        #     self.emc.shutdown()

        # commit all changes to the database
        try:
            Belief.session.commit()
        except Exception:
            # Exeptions here will be happening if the db disappeared.
            # At which point we can no longer commit anyway.
            pass

    def startup(self) -> None:
        pass

    def process(self) -> None:
        # print("process")
        pass

    def process_stopped(self) -> None:
        """
        handle process stopped
        """
        pass

    def notify_status(self, msg: str, msg_type=RPCMessageType.STATUS) -> None:
        """
        Public method for users of this class (worker, etc.) to send notifications
        via RPC about changes in the bot status.
        """
        self.rpc.send_msg({
            'type': msg_type,
            'status': msg
        })

