# pragma pylint: disable=unused-argument, unused-variable, protected-access, invalid-name

"""
This module manage Telegram communication
"""
import asyncio
import logging
import re
from copy import deepcopy
from datetime import datetime
from itertools import chain
from threading import Thread
from typing import List, Optional, Union

from telegram import (CallbackQuery, InlineKeyboardButton,
                      InlineKeyboardMarkup, KeyboardButton,
                      ReplyKeyboardMarkup, Update)
from telegram.constants import MessageLimit, ParseMode
from telegram.error import BadRequest, NetworkError, TelegramError
from telegram.ext import (Application, CallbackContext, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from sonagent.__init__ import __version__
from sonagent.enums import RPCMessageType
from sonagent.exceptions import OperationalException
from sonagent.rpc import RPC, RPCHandler
from sonagent.rpc.rpc_types import RPCSendMsg

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
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
            ['/ibelieve', '/mode', '/show_mode', '/sum', '/version', '/help']
        ]
        # do not allow commands with mandatory arguments and critical cmds
        # TODO: DRY! - its not good to list all valid cmds here. But otherwise
        #       this needs refactoring of the whole telegram module (same
        #       problem in _help()).
        valid_keys: List[str] = [
            r'/ibelieve', r'/show_mode$', r'/mode', r'/sum$', r'/show_skills$',
            r'/reload_skills$', r'/remove_skill', r'/show_schedule$',
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
        logger.info(f"telegram chat_result: {chat_result}")

        if len(chat_result) > MAX_MESSAGE_LENGTH:
            msg_parts = self.split_message_parts(chat_result)
            for msg_part in msg_parts:
                # await update.message.reply_text(msg_part)
                await self._send_msg(msg_part, parse_mode=ParseMode.MARKDOWN)
        else:
            await self._send_msg(chat_result, parse_mode=ParseMode.MARKDOWN)
        # await update.message.reply_text(chat_result)
        # await self._send_msg(chat_result, parse_mode=ParseMode.MARKDOWN)

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
            CommandHandler('show_plan', self._show_plan),
            CommandHandler('planning', self._planning),
            CommandHandler('clear_chat', self._clear_short_term_memory),
            CommandHandler('reincarnate', self._reincarnate),
            CommandHandler('askme', self._askme),
            CommandHandler('ibelieve', self._ibelieve),
            CommandHandler('show_mode', self._show_mode),
            CommandHandler('sum', self._summerize_dialog),
            CommandHandler('show_skills', self._show_skills),
            CommandHandler('show_schedule', self._show_schedule),
            CommandHandler('reload_skills', self._reload_skills),
            CommandHandler('remove_skill', self._remove_skill),
            CommandHandler('mode', self._mode),
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
        elif msg['type'] == RPCMessageType.CHAT:
            message = msg['message']
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
        logger.info(f"Sending message: {message}")
        if message:
            asyncio.run_coroutine_threadsafe(
                self._send_msg(message, parse_mode=ParseMode.MARKDOWN),
                self._loop)
        # self._send_msg(message, disable_notification=(noti == 'silent')),

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
    
    async def _show_skills(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /show_skills.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = await self._rpc.show_skills()
        if result is None or len(result) == 0:
            result = "Agent doesn't have any available skills."
        await update.message.reply_text(result)

    async def _show_schedule(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /show_schedule.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = await self._rpc.show_schedule()
        await self._send_msg(result, parse_mode=ParseMode.MARKDOWN)
        # await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _reload_skills(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /reload_skills.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = await self._rpc.reload_skills()
        await update.message.reply_text(result)

    async def _remove_skill(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /remove_skill.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """

        result = "remove your ai skill!"

        skill_name = update.message.text.replace('/remove_skill', '')

        if len(skill_name) > 0:
            result = await self._rpc.remove_skill(skill_name=skill_name.strip())
        else:
            result = "What skill you want to remove?"

        # result = "remove your ai skill!"

        await update.message.reply_text(result)

    async def _show_mode(self, update: Update, context: CallbackContext) -> None:
            """
            Handler for /_show_mode.
            :param bot: telegram bot
            :param update: message update
            :return: None
            """
            result = await self._rpc.show_mode()
            await update.message.reply_text(result)

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

    async def _mode(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /ibelieve.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = ""
        msg = update.message.text.replace('/mode', '')

        if len(msg) > 0:
            result = await self._rpc.mode(msg.strip())
        else:
            result = "You need give a mode like: chat, coding"

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

    async def _planning(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /planning.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        msg = update.message.text.replace('/planning', '')
        if len(msg) <= 0:
            msg = "What do you want to plan?"
        
        result = await self._rpc.planning(msg)
        await update.message.reply_text(result)

    async def _show_plan(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /show_plan.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """

        result = await self._rpc.show_plan()
        await update.message.reply_text(result)

    async def _summerize_dialog(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /summerize_dialog.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = await self._rpc.summerize_dialog()
        await update.message.reply_text(result)
