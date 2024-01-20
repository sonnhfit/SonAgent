# pragma pylint: disable=unused-argument, unused-variable, protected-access, invalid-name

"""
This module manage Telegram communication
"""
import asyncio
import json
import logging
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import partial, wraps
from html import escape
from itertools import chain
from math import isnan
from threading import Thread
from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional, Union


from telegram import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                      ReplyKeyboardMarkup, Update)
from telegram.constants import MessageLimit, ParseMode
from telegram.error import BadRequest, NetworkError, TelegramError
from telegram.ext import Application, CallbackContext, CallbackQueryHandler, CommandHandler, MessageHandler, ContextTypes
from telegram.helpers import escape_markdown
from telegram.ext import filters

from sonagent.exceptions import OperationalException
from sonagent.rpc import RPC, RPCException, RPCHandler
from sonagent.rpc.rpc_types import RPCSendMsg
from sonagent.enums import RPCMessageType
from sonagent.__init__ import __version__


logger = logging.getLogger(__name__)

logger.debug('Included module rpc.telegram ...')

MAX_MESSAGE_LENGTH = MessageLimit.MAX_TEXT_LENGTH


class Telegram(RPCHandler):
    def __init__(self, rpc: RPC, config: dict) -> None:
        """
        Init the Telegram call, and init the super class RPCHandler
        :param rpc: instance of RPC Helper class
        :param config: Configuration object
        :return: None
        """
        super().__init__(rpc, config)

        self._app: Application
        self._loop: asyncio.AbstractEventLoop
        self._init_keyboard()
        self._start_thread()

    def _start_thread(self):
        """
        Creates and starts the polling thread
        """
        self._thread = Thread(target=self._init, name='FTTelegram')
        self._thread.start()

    def _init_keyboard(self) -> None:
        """
        Validates the keyboard configuration from telegram config
        section.
        """
        self._keyboard: List[List[Union[str, KeyboardButton]]] = [
            ['/ibelieve', '/version', '/help']
        ]
        # do not allow commands with mandatory arguments and critical cmds
        # TODO: DRY! - its not good to list all valid cmds here. But otherwise
        #       this needs refactoring of the whole telegram module (same
        #       problem in _help()).
        valid_keys: List[str] = [
            r'/ibelieve',
            r'/help$', r'/version$'
        ]
        # Create keys for generation
        valid_keys_print = [k.replace('$', '') for k in valid_keys]

        # custom keyboard specified in config.json
        cust_keyboard = self._config['telegram'].get('keyboard', [])
        if cust_keyboard:
            combined = "(" + ")|(".join(valid_keys) + ")"
            # check for valid shortcuts
            invalid_keys = [b for b in chain.from_iterable(cust_keyboard)
                            if not re.match(combined, b)]
            if len(invalid_keys):
                err_msg = ('config.telegram.keyboard: Invalid commands for '
                           f'custom Telegram keyboard: {invalid_keys}'
                           f'\nvalid commands are: {valid_keys_print}')
                raise OperationalException(err_msg)
            else:
                self._keyboard = cust_keyboard
                logger.info('using custom keyboard from '
                            f'config.json: {self._keyboard}')

    def _init_telegram_app(self):
        return Application.builder().token(self._config['telegram']['token']).build()

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo the user message."""
        msg = update.message.text.replace('/sonagent', '')
        if len(msg) <= 0:
            msg = "Hello, I'm SonAgent"
        await update.message.reply_text(msg)

    def split_message_parts(self, msg: str) -> List[str]:
        """
        Split a message into parts of maximum length.
        :param msg: message to split
        :return: list of message parts
        """
        # Split message into parts of maximum length
        msg_parts = []
        while len(msg) > MAX_MESSAGE_LENGTH:
            msg_parts.append(msg[:MAX_MESSAGE_LENGTH])
            msg = msg[MAX_MESSAGE_LENGTH:]
        msg_parts.append(msg)
        return msg_parts

    async def echo_msg(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo the user message."""
        msg = update.message.text.replace('/sonagent', '')
        if len(msg) <= 0:
            msg = "Hello, I'm SonAgent"
        
        chat_result = await self._rpc.chat(msg)

        if len(chat_result) > MAX_MESSAGE_LENGTH:
            msg_parts = self.split_message_parts(chat_result)
            for msg_part in msg_parts:
                await update.message.reply_text(msg_part)
        await update.message.reply_text(chat_result)

    def _init(self) -> None:
        """
        Initializes this module with the given config,
        registers all known command handlers
        and starts polling for message updates
        Runs in a separate thread.
        """
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._app = self._init_telegram_app()

        # Register command handler and start telegram message polling
        handles = [
            CommandHandler('clear_chat', self._clear_short_term_memory),
            CommandHandler('reincarnate', self._reincarnate),
            CommandHandler('askme', self._askme),
            CommandHandler('ibelieve', self._ibelieve),
            CommandHandler('help', self._help),
            CommandHandler('version', self._version),
            CommandHandler('sonagent', self.echo),
        ]

        for handle in handles:
            self._app.add_handler(handle)
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo_msg))
        # self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_messages))

        logger.info(
            'rpc.telegram is listening for following commands'
        )
        self._loop.run_until_complete(self._startup_telegram())

    async def _startup_telegram(self) -> None:
        await self._app.initialize()
        await self._app.start()
        if self._app.updater:
            
            await self._app.updater.start_polling(
                bootstrap_retries=-1,
                timeout=20,
                # read_latency=60,  # Assumed transmission latency
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                #stop_signals=[],  # Necessary as we don't run on the main thread
            )

            while True:
                await asyncio.sleep(10)
                if not self._app.updater.running:
                    break

    async def _cleanup_telegram(self) -> None:
        if self._app.updater:
            await self._app.updater.stop()
        await self._app.stop()
        await self._app.shutdown()

    def cleanup(self) -> None:
        """
        Stops all running telegram threads.
        :return: None
        """
        # This can take up to `timeout` from the call to `start_polling`.
        asyncio.run_coroutine_threadsafe(self._cleanup_telegram(), self._loop)
        self._thread.join()

    def compose_message(self, msg: RPCSendMsg) -> Optional[str]:

        if msg['type'] == RPCMessageType.STATUS:
            message = f"*Status:* `{msg['status']}`"

        elif msg['type'] == RPCMessageType.WARNING:
            message = f"\N{WARNING SIGN} *Warning:* `{msg['status']}`"
        elif msg['type'] == RPCMessageType.EXCEPTION:
            # Errors will contain exceptions, which are wrapped in tripple ticks.
            message = f"\N{WARNING SIGN} *ERROR:* \n {msg['status']}"

        elif msg['type'] == RPCMessageType.STARTUP:
            message = f"{msg['status']}"
        else:
            logger.debug("Unknown message type: %s", msg['type'])
            return None
        return message
    
    def send_msg(self, msg: RPCSendMsg) -> None:
        """ Send a message to telegram channel """

        default_noti = 'on'

        msg_type = msg['type']
        noti = ''

        noti = self._config['telegram'] \
            .get('notification_settings', {}).get(str(msg_type), default_noti)

        if noti == 'off':
            logger.info(f"Notification '{msg_type}' not sent.")
            # Notification disabled
            return

        message = self.compose_message(deepcopy(msg))
        if message:
            asyncio.run_coroutine_threadsafe(
                self._send_msg(message, disable_notification=(noti == 'silent')),
                self._loop)

    async def _update_msg(self, query: CallbackQuery, msg: str, callback_path: str = "",
                          reload_able: bool = False, parse_mode: str = ParseMode.MARKDOWN) -> None:
        if reload_able:
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Refresh", callback_data=callback_path)],
            ])
        else:
            reply_markup = InlineKeyboardMarkup([[]])
        msg += f"\nUpdated: {datetime.now().ctime()}"
        if not query.message:
            return
        chat_id = query.message.chat_id
        message_id = query.message.message_id

        try:
            await self._app.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=msg,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except BadRequest as e:
            if 'not modified' in e.message.lower():
                pass
            else:
                logger.warning('TelegramError: %s', e.message)
        except TelegramError as telegram_err:
            logger.warning('TelegramError: %s! Giving up on that message.', telegram_err.message)

    async def _send_msg(self, msg: str, parse_mode: str = ParseMode.MARKDOWN,
                        disable_notification: bool = False,
                        keyboard: Optional[List[List[InlineKeyboardButton]]] = None,
                        callback_path: str = "",
                        reload_able: bool = False,
                        query: Optional[CallbackQuery] = None) -> None:
        """
        Send given markdown message
        :param msg: message
        :param bot: alternative bot
        :param parse_mode: telegram parse mode
        :return: None
        """
        reply_markup: Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]
        if query:
            await self._update_msg(query=query, msg=msg, parse_mode=parse_mode,
                                   callback_path=callback_path, reload_able=reload_able)
            return
        if reload_able and self._config['telegram'].get('reload', True):
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Refresh", callback_data=callback_path)]])
        else:
            if keyboard is not None:
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                reply_markup = ReplyKeyboardMarkup(self._keyboard, resize_keyboard=True)
        try:
            try:
                await self._app.bot.send_message(
                    self._config['telegram']['chat_id'],
                    text=msg,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    disable_notification=disable_notification,
                )
            except NetworkError as network_err:
                # Sometimes the telegram server resets the current connection,
                # if this is the case we send the message again.
                logger.warning(
                    'Telegram NetworkError: %s! Trying one more time.',
                    network_err.message
                )
                await self._app.bot.send_message(
                    self._config['telegram']['chat_id'],
                    text=msg,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    disable_notification=disable_notification,
                )
        except TelegramError as telegram_err:
            logger.warning(
                'TelegramError: %s! Giving up on that message.',
                telegram_err.message
            )

    async def _help(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /help.
        Show commands of the bot
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        print("help")
        message = (
            "_Bot Control_\n"
            "------------\n"
            "*/help:* `This help message`\n"
            "*/version:* `Show version`"
            )

        await self._send_msg(message, parse_mode=ParseMode.MARKDOWN)

    async def _version(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /version.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        version_string = f'*Version:* `{__version__}`'
        await self._send_msg(version_string)

    async def _ibelieve(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /ibelieve.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = "I believe in you!"
        msg = update.message.text.replace('/ibelieve', '')

        if len(msg) > 0:
            result = await self._rpc.ibelieve(msg)
        else:
            result = "What do you believe?"

        await update.message.reply_text(result)

    async def _askme(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /askme.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = "I believe in you!"
        msg = update.message.text.replace('/askme', '')
        if len(msg) <= 0:
            msg = "What do you ask me?"
        
        result = await self._rpc.askme(msg)
        await update.message.reply_text(result)

    async def _handle_messages(self, update: Update, context: CallbackContext)  -> None:
        # Lấy thông tin từ tin nhắn
        # message = update.message
        # chat_id = message.chat_id
        # text = message.text
        # Xử lý tin nhắn ở đây

        logger.info("--------- go here")
        # print(f"Received message '{text}' from chat {chat_id}")
        # logger.info(
        #     f"---- Received message '{text}' from chat {chat_id}"
        # )

    async def _reincarnate(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /reincarnate.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = await self._rpc.reincarnate()
        await update.message.reply_text(result)

    async def _clear_short_term_memory(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /clear_short_term_memory.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = await self._rpc.clear_short_term_memory()
        await update.message.reply_text(result)
