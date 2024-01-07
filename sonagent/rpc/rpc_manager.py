"""
This module contains class to manage RPC communications (Telegram, API, ...)
"""
import logging
from collections import deque
from typing import List

from sonagent.enums import RPCMessageType
from sonagent.rpc import RPC, RPCHandler
from sonagent.rpc.rpc_types import RPCSendMsg


logger = logging.getLogger(__name__)


class RPCManager:
    def __init__(self, sonagent) -> None:
        self.registered_modules: List[RPCHandler] = []
        self._rpc = RPC(sonagent)
        config = sonagent.config


    def send_msg(self, msg: RPCSendMsg) -> None:
        """
        Send given message to all registered rpc modules.
        A message consists of one or more key value pairs of strings.
        e.g.:
        {
            'status': 'stopping bot'
        }
        """

        logger.info('Sending rpc message: %s', msg)
        for mod in self.registered_modules:
            logger.debug('Forwarding message to rpc.%s', mod.name)
            try:
                mod.send_msg(msg)
            except NotImplementedError:
                logger.error(f"Message type '{msg['type']}' not implemented by handler {mod.name}.")
            except Exception:
                logger.exception('Exception occurred within RPC module %s', mod.name)

    



