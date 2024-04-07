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

        # Enable telegram
        if config.get('telegram', {}).get('enabled', False):
            logger.info('Enabling rpc.telegram ...')
            from sonagent.rpc.telegram import Telegram
            self.registered_modules.append(Telegram(self._rpc, config))

        # Enable local rest api server for cmd line control
        if config.get('api_server', {}).get('enabled', False):
            logger.info('Enabling rpc.api_server')
            from sonagent.rpc.api_server import ApiServer
            apiserver = ApiServer(config)
            apiserver.add_rpc_handler(self._rpc)
            self.registered_modules.append(apiserver)

        if config.get('webhook', {}).get('enabled', False):
            logger.info('Enabling webhook ...')
            from sonagent.rpc.webhook import Webhook
            self.registered_modules.append(Webhook(self._rpc, config))


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
            logger.info('Forwarding message to rpc.%s', mod.name)
            try:
                mod.send_msg(msg)
            except NotImplementedError:
                logger.error(f"Message type '{msg['type']}' not implemented by handler {mod.name}.")
            except Exception:
                logger.exception('Exception occurred within RPC module %s', mod.name)

    



