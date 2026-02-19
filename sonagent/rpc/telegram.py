# pragma pylint: disable=unused-argument, unused-variable, protected-access, invalid-name

"""
This module manage Telegram communication
"""
import asyncio
import html
import logging
import re
from copy import deepcopy
from datetime import datetime
from itertools import chain
from threading import Thread
from typing import List, Optional, Union

from tabulate import tabulate
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


def preprocess_markdown_message(message: str) -> str:
    """
    Preprocess message to fix common Markdown parsing issues before sending to Telegram.
    
    This function fixes:
    - Unclosed backticks (inline code)
    - Unclosed code blocks (```)
    - Unmatched square brackets
    - Unpaired asterisks (causing bold/italic parsing issues)
    - Underscores in words (causing italic parsing issues)
    - Other special characters that could cause parse errors
    
    :param message: The raw message to preprocess
    :return: Preprocessed message safe for Telegram Markdown parsing
    """
    if not message:
        return message
    
    result = message
    
    # Fix unclosed code blocks (```)
    code_block_count = result.count('```')
    if code_block_count % 2 == 1:
        result += '\n```'
    
    # Fix unclosed inline code (`)
    # Find all backtick pairs and mark unclosed ones
    in_code = False
    processed_chars = []
    for char in result:
        if char == '`':
            in_code = not in_code
            processed_chars.append(char)
        else:
            processed_chars.append(char)
    
    # If we end with an unclosed backtick, add a closing one
    if in_code:
        result = ''.join(processed_chars) + '`'
    
    # Fix unmatched square brackets that could be interpreted as links
    # Count opening and closing brackets
    open_brackets = result.count('[')
    close_brackets = result.count(']')
    
    if open_brackets > close_brackets:
        result += ']' * (open_brackets - close_brackets)
    
    # Fix unpaired asterisks - escape lone asterisks that could cause bold/italic issues
    # Count asterisks and escape unpaired ones
    asterisk_count = result.count('*')
    if asterisk_count % 2 == 1:
        # Find the last asterisk and escape it
        last_asterisk_pos = result.rfind('*')
        if last_asterisk_pos != -1:
            result = result[:last_asterisk_pos] + '\\*' + result[last_asterisk_pos + 1:]
    
    # Escape underscores and asterisks that are not in code blocks or already escaped
    lines = result.split('\n')
    processed_lines = []
    
    for line in lines:
        # Skip if line is inside a code block
        if '```' in line:
            processed_lines.append(line)
            continue
        
        # Process the line
        processed_line = ''
        i = 0
        while i < len(line):
            # Skip escaped characters
            if line[i] == '\\' and i + 1 < len(line):
                processed_line += line[i:i+2]
                i += 2
                continue
            
            # Check for backticks - skip processing inside code
            if line[i] == '`':
                processed_line += line[i]
                i += 1
                # Find the end of this code section
                while i < len(line) and line[i] != '`':
                    processed_line += line[i]
                    i += 1
                if i < len(line):
                    processed_line += line[i]
                    i += 1
                continue
            
            # Handle asterisks - escape lone asterisks
            if line[i] == '*':
                # Check if this is likely part of a pair
                # Look ahead and behind to see if there's another asterisk
                prev_char = processed_line[-1] if processed_line else ' '
                next_char = line[i + 1] if i + 1 < len(line) else ' '
                
                # If it's a single asterisk not part of a pair, escape it
                # Simple heuristic: if not surrounded by asterisks, escape
                if prev_char != '*' and next_char != '*':
                    processed_line += '\\*'
                else:
                    processed_line += line[i]
            
            # Escape underscores that are not in code blocks or already escaped
            elif line[i] == '_':
                # Check if this is likely a variable/identifier (inside word)
                prev_char = processed_line[-1] if processed_line else ' '
                next_char = line[i + 1] if i + 1 < len(line) else ' '
                
                if prev_char.isalnum() and next_char.isalnum():
                    # This is like a_variable - escape the underscore
                    processed_line += '\\_'
                elif prev_char == ' ' and next_char.isalnum():
                    # This is like _variable - escape
                    processed_line += '\\_'
                elif prev_char.isalnum() and next_char == ' ':
                    # This is like variable_ - escape
                    processed_line += '\\_'
                else:
                    processed_line += line[i]
            else:
                processed_line += line[i]
            i += 1
        
        processed_lines.append(processed_line)
    
    result = '\n'.join(processed_lines)
    
    # Final cleanup: escape parentheses that could be interpreted as part of links
    # Telegram Markdown links use [text](url), so unpaired parentheses can cause issues
    open_paren = result.count('(')
    close_paren = result.count(')')
    if open_paren > close_paren:
        # Add missing closing parentheses
        result += ')' * (open_paren - close_paren)
    
    return result


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
            ['/show_tasks', '/version', '/help']
        ]
        # do not allow commands with mandatory arguments and critical cmds
        # TODO: DRY! - its not good to list all valid cmds here. But otherwise
        #       this needs refactoring of the whole telegram module (same
        #       problem in _help()).
        valid_keys: List[str] = [
            r'/show_skills$',
            r'/reload_skills$', r'/remove_skill', r'/show_tasks$', r'/env$',
            r'/add_env', r'/remove_env', r'/reload_env',
             r'/show_tools$', r'/reload_tools$', r'/execute_tool',
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
        
        logger.info(f"[Telegram] Received message: {msg[:100]}...")
        try:
            await self._rpc.chat(msg)
            logger.debug("[Telegram] Message processed successfully")
        except Exception as e:
            logger.error(f"[Telegram] Error processing message: {e}", exc_info=True)
            # Try to send error message back to user
            try:
                error_msg = f"Sorry, an error occurred while processing your message: {str(e)[:200]}"
                await update.message.reply_text(error_msg)
            except Exception as reply_error:
                logger.error(f"[Telegram] Failed to send error message to user: {reply_error}")

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
            CommandHandler('show_skills', self._show_skills),
            CommandHandler('show_tasks', self._show_task),
            CommandHandler('env', self._env),
            CommandHandler('add_env', self._add_env),
            CommandHandler('remove_env', self._remove_env),
            CommandHandler('reload_skills', self._reload_skills),
            CommandHandler('reload_env', self._reload_env),
            CommandHandler('remove_skill', self._remove_skill),
            CommandHandler('show_tools', self._show_tools),
            CommandHandler('reload_tools', self._reload_tools),
            CommandHandler('execute_tool', self._execute_tool),
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
        
        # Preprocess message to fix Markdown parsing issues
        if message:
            message = preprocess_markdown_message(message)
        
        logger.info(f"Sending message: {message}")
        if message:
            if len(message) > MAX_MESSAGE_LENGTH:
                msg_parts = self.split_message_parts(message)
                for msg_part in msg_parts:
                    # Also preprocess each part
                    processed_part = preprocess_markdown_message(msg_part)
                    asyncio.run_coroutine_threadsafe(
                        self._send_msg(processed_part, parse_mode=ParseMode.MARKDOWN),
                        self._loop
                    )
            else:
                asyncio.run_coroutine_threadsafe(
                    self._send_msg(message, parse_mode=ParseMode.MARKDOWN),
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
            "*/show_tasks:* `Show all tasks with details`\n"
            "*/clear_chat:* `Clear chat`\n"
            "*/show_skills:* `Show skills`\n"
            "*/reload_skills:* `Reload skills`\n"
            "*/remove_skill:* `Remove skill`\n"
            "*/env:* `Environment`\n"
            "*/add_env:* `Add environment`\n"
            "*/remove_env:* `Remove environment`\n"
            "*/help:* `This help message`\n"
            "*/version:* `Show version`\n\n"
            "_Tool Management_\n"
            "----------------\n"
            "*/show_tools:* `Show all loaded tools from user_data/tools/`\n"
            "*/reload_tools:* `Force reload all tools from directory`\n"
            "*/execute_tool <tool_name> [args]:* `Execute a specific tool with optional JSON arguments`\n\n"

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
    
    async def _env(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /env.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = await self._rpc.show_env()
        head = ['Key', 'Value', 'Description']
        logger.info(result)
        message = tabulate(result, headers=head, tablefmt='simple')

        await self._send_msg(f"<pre>{message}</pre>", parse_mode=ParseMode.HTML)
        # await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _reload_env(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /reload_env.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = await self._rpc.reload_env()
        await update.message.reply_text(result)

    async def _add_env(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /add_env.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = "Add your environment!"
        msg = update.message.text.replace('/add_env', '')

        logger.info(msg)

        if len(msg) > 0:
            try:
                msg_param = msg.strip().split(' ')
                key = msg_param[0].strip()
                value = msg_param[1].strip()
                description = msg_param[2].strip()
                result = await self._rpc.add_env(key, value, description)
            except Exception as e:
                result = "Wrong format. Please use /add_env key value description"
                logger.error(e)
        else:
            result = "What environment you want to add?"

        await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)

    async def _remove_env(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /remove_env.
        Show version information
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        result = "remove your environment!"

        env_name = update.message.text.replace('/remove_env', '')

        if len(env_name) > 0:
            result = await self._rpc.remove_env(env_name=env_name.strip())
        else:
            result = "What environment you want to remove?"

        # result = "remove your ai skill!"

        await update.message.reply_text(result)
    
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

    async def _show_tasks(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /show_tasks.
        Show current tasks
        :param update: message update
        :param context: callback context
        :return: None
        """
        result = await self._rpc.get_tasks()
        await self._send_msg(result, parse_mode=ParseMode.MARKDOWN)

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

    async def _show_task(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /show_task.
        Show detailed task information using the Task model.
        Similar to show_plan but shows all tasks with more details.
        :param bot: telegram bot
        :param update: message update
        :return: None
        """

        result = await self._rpc.show_task()
        await self._send_msg(result, parse_mode=ParseMode.MARKDOWN)

    async def _show_tools(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /show_tools.
        Show all loaded tools from the ToolRegistry.
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        logger.info("[Telegram] Showing tools")
        try:
            result = await self._rpc.show_tools()
            await self._send_msg(result, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            error_msg = f"Error showing tools: {str(e)[:200]}"
            logger.error(f"[Telegram] Error in _show_tools: {e}", exc_info=True)
            await update.message.reply_text(error_msg)

    async def _reload_tools(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /reload_tools.
        Force reload all tools from the tools directory.
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        logger.info("[Telegram] Reloading tools")
        try:
            result = await self._rpc.reload_tools()
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            error_msg = f"Error reloading tools: {str(e)[:200]}"
            logger.error(f"[Telegram] Error in _reload_tools: {e}", exc_info=True)
            await update.message.reply_text(error_msg)

    async def _execute_tool(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for /execute_tool.
        Execute a specific tool with arguments.
        :param bot: telegram bot
        :param update: message update
        :return: None
        """
        logger.info("[Telegram] Executing tool")
        
        # Get the full message text
        full_text = update.message.text
        
        # Remove command and get arguments
        args_text = full_text.replace('/execute_tool', '').strip()
        
        if not args_text:
            # No arguments provided
            await update.message.reply_text(
                "Usage: /execute_tool <tool_name> [json_arguments]\n"
                "Example: /execute_tool greet_user {\"name\": \"John\"}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Parse tool name and arguments
        try:
            # Split by space to get tool name and JSON args
            parts = args_text.split(' ', 1)
            tool_name = parts[0].strip()
            
            # Check if there are JSON arguments
            if len(parts) > 1:
                json_args = parts[1].strip()
                # Try to parse JSON to validate
                import json
                try:
                    json.loads(json_args)
                    # Arguments are valid JSON
                    tool_args = json_args
                except json.JSONDecodeError:
                    # Arguments are not valid JSON, treat as plain text
                    tool_args = json.dumps({"arg": json_args})
            else:
                tool_args = ""
            
            logger.info(f"[Telegram] Executing tool: {tool_name} with args: {tool_args[:100]}...")
            
            # Call RPC to execute tool
            result = await self._rpc.execute_tool(tool_name, tool_args)
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            error_msg = f"Error executing tool: {str(e)[:200]}"
            logger.error(f"[Telegram] Error in _execute_tool: {e}", exc_info=True)
            await update.message.reply_text(error_msg)
