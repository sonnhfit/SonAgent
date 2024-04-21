import logging
import time
from typing import Any, Dict, Optional

from requests import RequestException, post

from sonagent.enums import RPCMessageType
from sonagent.rpc import RPC, RPCHandler
from sonagent.rpc.rpc_types import RPCSendMsg

logger = logging.getLogger(__name__)

logger.debug('import module rpc.webhook ...')


class Webhook(RPCHandler):

    def __init__(self, rpc: RPC, config: dict) -> None:
        """
        Init the Webhook class, and init the super class RPCHandler
        :param rpc: instance of RPC Helper class
        :param config: Configuration object
        :return: None
        """
        super().__init__(rpc, config)

        self._url = self._config['webhook']['url']
        self._format = self._config['webhook'].get('format', 'json')
        self._retries = self._config['webhook'].get('retries', 0)
        self._retry_delay = self._config['webhook'].get('retry_delay', 0.1)
        self._timeout = self._config['webhook'].get('timeout', 10)

    def cleanup(self) -> None:
        """
        Cleanup pending module resources.
        This will do nothing for webhooks, they will simply not be called anymore
        """
        pass

    def _get_value_dict(self, msg: RPCSendMsg) -> Optional[Dict[str, Any]]:
        whconfig = self._config['webhook']
        if msg['type'].value in whconfig:
            # Explicit types should have priority
            valuedict = whconfig.get(msg['type'].value)
        # Deprecated 2022.10 - only keep generic method.
        elif msg['type'] in [RPCMessageType.CHAT]:
            valuedict = whconfig.get('chat')
        elif msg['type'] in (RPCMessageType.STATUS,
                             RPCMessageType.STARTUP,
                             RPCMessageType.EXCEPTION,
                             RPCMessageType.WARNING):
            valuedict = whconfig.get('webhookstatus')

        return valuedict

    def send_msg(self, msg: RPCSendMsg) -> None:
        """ Send a message to telegram channel """
        if msg['type'] == RPCMessageType.CHAT:
            try:

                valuedict = self._get_value_dict(msg)

                if not valuedict:
                    logger.debug("Message type '%s' not configured for webhooks", msg['type'])
                    return

                payload = {key: value.format(**msg) for (key, value) in valuedict.items()}
                self._send_msg(payload)
            except KeyError as exc:
                logger.exception("Problem calling Webhook. Please check your webhook configuration. "
                                "Exception: %s", exc)

    def _send_msg(self, payload: dict) -> None:
        """do the actual call to the webhook"""

        success = False
        attempts = 0
        while not success and attempts <= self._retries:
            if attempts:
                if self._retry_delay:
                    time.sleep(self._retry_delay)
                logger.info("Retrying webhook...")

            attempts += 1

            try:
                if self._format == 'json':
                    response = post(self._url, json=payload, timeout=self._timeout)
                elif self._format == 'raw':
                    response = post(self._url, data=payload['data'],
                                    headers={'Content-Type': 'text/plain'},
                                    timeout=self._timeout)
                else:
                    raise NotImplementedError(f'Unknown format: {self._format}')

                response.raise_for_status()
                success = True

            except RequestException as exc:
                logger.warning("Could not call webhook url. Exception: %s", exc)
