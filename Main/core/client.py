# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import os
import re
import sys
import glob
import html
import time
import yaml
import signal
import shlex
import random
import shutil
import asyncio
import inspect
import logging
import aiofiles
import importlib
import traceback
import contextlib
import multiprocessing
from pathlib import Path
from functools import wraps
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
import telethon
from telethon import events, errors, functions, types
from telethon.sessions import StringSession, MemorySession
from cachetools import TTLCache

from Main.core.apm import APM
from Main.core.cache import Cache
from Main.utils.paste import Paste
from ..utils._updater import Updater
from .config import Config, BaseConfig
from ..utils.suppress import suppress_error, safe_suppress, suppress
from .database import MongoDB, LocalDatabase, create_database
from .plugin_manager import PluginManager
from .types.client import AltruixTelegramClient
from .types.message import Message, enrich_message
from ..utils.custom_filters import user_filters, filters as default_filters, Filter
from ..utils.startup_helpers import concatenate
from Main.utils.heroku_ import prepare_heroku_url
from ..utils.multi_lang_helpers import get_all_files_in_path
from ..utils.command import resolve_command

logger = logging.getLogger("Altruix")


class BotWrapper:
    """Wrapper around assistant bot client providing decorator event handling."""

    def __init__(self, altruix_client: AltruixClient):
        self._altruix = altruix_client

    def __getattr__(self, name: str) -> Any:
        if self._altruix._raw_bot is not None:
            return getattr(self._altruix._raw_bot, name)
        raise AttributeError(f"'BotWrapper' has no attribute '{name}' (bot not initialized yet)")

    def on_message(self, custom_filter: Optional[Any] = None, pattern: Optional[Any] = None, *args, **kwargs):
        if pattern is not None:
            regex_filter = default_filters.regex(pattern)
            custom_filter = (custom_filter & regex_filter) if custom_filter is not None else regex_filter
        elif isinstance(custom_filter, (str, re.Pattern)):
            custom_filter = default_filters.regex(custom_filter)

        def decorator(func: Callable):
            self._altruix._pending_bot_handlers.append(("message", custom_filter, func))
            if self._altruix._raw_bot is not None:
                self._altruix._register_bot_handler("message", custom_filter, func)
            return func
        return decorator

    def on_callback_query(self, custom_filter: Optional[Any] = None, pattern: Optional[Any] = None, *args, **kwargs):
        if pattern is not None:
            regex_filter = default_filters.regex(pattern)
            custom_filter = (custom_filter & regex_filter) if custom_filter is not None else regex_filter
        elif isinstance(custom_filter, (str, re.Pattern)):
            custom_filter = default_filters.regex(custom_filter)

        def decorator(func: Callable):
            self._altruix._pending_bot_handlers.append(("callback_query", custom_filter, func))
            if self._altruix._raw_bot is not None:
                self._altruix._register_bot_handler("callback_query", custom_filter, func)
            return func
        return decorator

    def on_inline_query(self, custom_filter: Optional[Any] = None, pattern: Optional[Any] = None, *args, **kwargs):
        if pattern is not None:
            regex_filter = default_filters.regex(pattern)
            custom_filter = (custom_filter & regex_filter) if custom_filter is not None else regex_filter
        elif isinstance(custom_filter, (str, re.Pattern)):
            custom_filter = default_filters.regex(custom_filter)

        def decorator(func: Callable):
            self._altruix._pending_bot_handlers.append(("inline_query", custom_filter, func))
            if self._altruix._raw_bot is not None:
                self._altruix._register_bot_handler("inline_query", custom_filter, func)
            return func
        return decorator

    def on(self, event: Any = None):
        def decorator(func: Callable):
            self._altruix._pending_bot_handlers.append(("telethon_event", event, func))
            if self._altruix._raw_bot is not None:
                self._altruix._register_bot_handler("telethon_event", event, func)
            return func
        return decorator


class AltruixClient:
    def __init__(self, *args, **kwargs) -> None:
        self.ourselves: List[types.User] = []
        self.bot_info: Optional[types.User] = None
        self._raw_bot: Optional[AltruixTelegramClient] = None
        self.bot: BotWrapper = BotWrapper(self)
        self.clients: List[AltruixTelegramClient] = []
        self.cmd_list: Dict[str, List[Dict[str, Any]]] = {}
        self.all_lang_strings: Dict[str, Any] = {}
        self.__version__ = "0.2.0"
        self.selected_lang = "english"
        self.local_lang_file = str(Path(__file__).resolve().parents[1] / "localization")
        self.start_time = time.time()
        self.app_url_ = None
        self.disabled_sudo_plugin_list: List[str] = []
        self.SELF_PERMISSION_CACHE = TTLCache(99999, ttl=60 * 60, timer=time.perf_counter)
        self.loaded_bot_cmds = False
        self.cmd_list_s: List[str] = []
        self.training_wheels_protocol = False
        self._init_logger()

        self.local_db = LocalDatabase()
        self.executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() * 5)
        self._mongo_db: Optional[MongoDB] = None
        self.config: Config = Config(self.local_db.env_col, executor=self.executor)
        self.log_chat = None
        self.main_plugins: set[str] = set()
        self.extra_plugins: set[str] = set()
        self.plugin_categories: Dict[str, str] = {}
        self._command_help_message_data: Dict[str, str] = {}
        self._pending_handlers: List[Dict[str, Any]] = []
        self._pending_bot_handlers: List[Tuple[str, Optional[Filter], Callable]] = []
        self.sudo_cmd_handler = getattr(self.config, "SUDO_CMD_HANDLER", "!") or "!"
        self.user_command_handler = getattr(self.config, "CMD_HANDLER", ".") or "."
        self.bot_command_handler = getattr(self.config, "BOT_CMD_HANDLER", "/") or "/"
        self.bot_mode = getattr(self.config, "BOT_MODE", False)
        self.plugin_manager: Optional[PluginManager] = None  # initialized after setup
        self._stop_event: Optional[asyncio.Event] = None
        self._restart_requested = False
        self._http: Optional[httpx.AsyncClient] = None
        self.suppress = suppress_error
        self.suppress_error = suppress_error
        self.safe_suppress = suppress_error
        self.setup_localization_sync()

    @property
    def db(self) -> Union[MongoDB, LocalDatabase]:
        if self._mongo_db is not None:
            return self._mongo_db
        return self.local_db

    @db.setter
    def db(self, val: Optional[MongoDB]) -> None:
        self._mongo_db = val

    def _init_logger(self) -> None:
        logging.getLogger("telethon").setLevel(logging.WARNING)
        logging.basicConfig(
            level=logging.INFO,
            datefmt="[%d/%m/%Y %H:%M:%S]",
            format="%(asctime)s - [Altruix] >> %(levelname)s << %(message)s",
            handlers=[logging.FileHandler("altruix.log"), logging.StreamHandler()],
        )
        self.log("Initialized Logger successfully!")

    @staticmethod
    def log(
        message: Optional[str] = None,
        level: int = logging.INFO,
        logger: logging.Logger = logging.getLogger("Altruix"),
    ) -> Optional[str]:
        msg = message or traceback.format_exc()
        logger.log(level, msg)
        return msg

    @property
    def banner(self) -> str:
        return f"""
     _    _ _              _
    / \\  | | |_ _ __ _   _(_)_  __
   / _ \\ | | __| '__| | | | \\ \\/ /
  / ___ \\| | |_| |  | |_| | |>  <
 /_/   \\_\\_|\\__|_|   \\__,_|_/_/\\_\\

 (C) Project-Altruix (Telethon Edition) 2021-{datetime.today().year}
        """

    @property
    def ax(self) -> Optional[AltruixTelegramClient]:
        return random.choice(self.clients) if self.clients else None

    @property
    def auth_users(self) -> List[int]:
        users = set(getattr(self.config, "SUDO_USERS", []))
        if getattr(self.config, "OWNER_ID", None):
            with contextlib.suppress(Exception):
                users.add(int(self.config.OWNER_ID))
        for acc in self.ourselves:
            if hasattr(acc, "id"):
                users.add(int(acc.id))
        for cl in self.clients:
            if hasattr(cl, "myself") and cl.myself and hasattr(cl.myself, "id"):
                users.add(int(cl.myself.id))
        return list(users)

    async def resolve_dns(self) -> None:
        try:
            import dns.resolver
            try:
                dns.resolver.resolve("www.google.com")
            except Exception:
                self.log("Resolving DNS. Setting to : 8.8.8.8")
                dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
                dns.resolver.default_resolver.nameservers = ["8.8.8.8"]
        except ImportError:
            pass

    async def _db_setup(self) -> None:
        with contextlib.suppress(Exception):
            await self.update_on_startup()
        await self.resolve_dns()
        if self.config.DB_URI:
            try:
                self.db = create_database(self.config.DB_URI, db_name=self.config.DB_NAME or "Altruix")
                backend_name = type(self.db).__name__
                self.log(f"Initialized Database ({backend_name}) successfully!")
                if not await self.db.ping():
                    raise ConnectionError(f"{backend_name} did not respond to the ping command")
                self.log(f"Pinged {backend_name} successfully!")
            except Exception as e:
                self.log(f"Database connection failed: {e}. Falling back to local storage.", level=logging.WARNING)
                self.db = None
        else:
            self.log("No DB_URI provided. Running with local configuration.", level=logging.INFO)
        self.app_url_ = await prepare_heroku_url()

    def run_in_exc(self, func_: Callable) -> Callable:
        @wraps(func_)
        async def wrapper(*args, **kwargs):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self.executor, lambda: func_(*args, **kwargs))
        return wrapper

    def setup_localization_sync(self) -> None:
        all_files = get_all_files_in_path(self.local_lang_file)
        for filepath in all_files:
            if not str(filepath).endswith((".yaml", ".yml")):
                continue
            with open(filepath, encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue
                language_to_load = data.get("language")
                if language_to_load and language_to_load != "template":
                    self.all_lang_strings[language_to_load] = data
        self.selected_lang = self.selected_lang if self.selected_lang in self.all_lang_strings else "english"

    async def setup_localization(self) -> None:
        lang = await self.config.get_env("UB_LANG") if hasattr(self.config, "get_env") else None
        selected_lang = lang.lower() if lang else "english"
        self.setup_localization_sync()
        if selected_lang in self.all_lang_strings:
            self.selected_lang = selected_lang
        else:
            self.selected_lang = "english"
        self.log("Localization setup complete!")

    def get_string(self, keyword: str, *args: Any, string_args: Any = None, **kwargs: Any) -> Optional[str]:
        # Lookup in selected language, fallback to english
        str_ing = None
        for lang_name in (self.selected_lang, "english"):
            lang_dict = self.all_lang_strings.get(lang_name)
            if lang_dict and isinstance(lang_dict, dict) and keyword in lang_dict:
                str_ing = lang_dict[keyword]
                break

        if str_ing is None or not isinstance(str_ing, str):
            return str_ing

        fmt_args = string_args if string_args is not None else (args if args else None)
        if fmt_args is not None or kwargs:
            try:
                if fmt_args is not None and kwargs:
                    return str_ing.format(*fmt_args, **kwargs) if isinstance(fmt_args, (list, tuple)) else str_ing.format(fmt_args, **kwargs)
                elif fmt_args is not None:
                    return str_ing.format(*fmt_args) if isinstance(fmt_args, (list, tuple)) else str_ing.format(fmt_args)
                elif kwargs:
                    return str_ing.format(**kwargs)
            except Exception:
                return str_ing
        return str_ing

    def on_message(self, custom_filters: Any = None, group: int = 1, bot_mode_unsupported: bool = False):
        def decorator(func: Callable):
            handler_info = {
                "type": "custom",
                "filter": custom_filters,
                "func": func,
                "group": group,
                "bot_mode_unsupported": bot_mode_unsupported,
            }
            self._pending_handlers.append(handler_info)
            for client in self.clients:
                self._attach_handler_to_client(client, handler_info)
            if self.bot_mode and not bot_mode_unsupported and self._raw_bot is not None:
                self._attach_handler_to_client(self._raw_bot, handler_info)
            return func
        return decorator

    def register_on_cmd(
        self,
        cmd: Union[str, List[str]],
        cmd_help: dict = {},
        pm_only: bool = False,
        group_only: bool = False,
        channel_only: bool = False,
        just_exc: bool = False,
        requires_input: bool = False,
        requires_reply: bool = False,
        bot_mode_unsupported: bool = False,
        group: int = 1,
        disallow_if_sender_is_channel: bool = False,
    ):
        if isinstance(cmd, str):
            cmd = [cmd]
        self.cmd_list_s.extend(cmd)
        previous_stack_frame = inspect.stack()[1]
        file_name = os.path.basename(previous_stack_frame.filename.replace(".py", ""))
        self.add_help_to_command_list(
            commands=cmd,
            file_name=file_name,
            help_map=cmd_help,
            requires_input=requires_input,
            requires_reply=requires_reply,
            group_only=group_only,
            channel_only=channel_only,
            private_only=pm_only,
            bot_mode_unsupported=bot_mode_unsupported,
        )

        def decorator(func: Callable):
            handler_info = {
                "type": "cmd",
                "cmd": cmd,
                "func": func,
                "file_name": file_name,
                "pm_only": pm_only,
                "group_only": group_only,
                "channel_only": channel_only,
                "just_exc": just_exc,
                "requires_input": requires_input,
                "requires_reply": requires_reply,
                "bot_mode_unsupported": bot_mode_unsupported,
                "group": group,
                "disallow_if_sender_is_channel": disallow_if_sender_is_channel,
            }
            self._pending_handlers.append(handler_info)
            for client in self.clients:
                self._attach_handler_to_client(client, handler_info)
            if not bot_mode_unsupported and self._raw_bot is not None:
                self._attach_handler_to_client(self._raw_bot, handler_info)
            return func

        return decorator

    def _attach_handler_to_client(self, client: AltruixTelegramClient, handler_info: Dict[str, Any]) -> None:
        h_type = handler_info["type"]
        func = handler_info["func"]

        if h_type == "cmd":
            cmd = handler_info["cmd"]
            cmd_aliases = [cmd] if isinstance(cmd, str) else cmd

            if not hasattr(client, "_cmd_handlers_map"):
                client._cmd_handlers_map = {}

            for alias in cmd_aliases:
                client._cmd_handlers_map[str(alias).strip().lower()] = handler_info

            if not getattr(client, "_cmd_router_attached", False):
                client._cmd_router_attached = True

                async def cmd_router_callback(event: events.NewMessage.Event):
                    raw_text = getattr(event, "raw_text", None) or getattr(event, "message", None) or ""
                    if not raw_text or not isinstance(raw_text, str):
                        return

                    is_bot_client = hasattr(client, "myself") and bool(getattr(client.myself, "bot", False))

                    user_p = getattr(self, "user_command_handler", ".") or "."
                    sudo_p = getattr(self, "sudo_cmd_handler", "!") or "!"
                    bot_p = getattr(self, "bot_command_handler", "/") or "/"

                    first_char = raw_text[0]
                    valid_prefixes = (bot_p, "/") if is_bot_client else (user_p, sudo_p)
                    if first_char not in valid_prefixes:
                        return

                    parts = raw_text.split(None, 1)
                    if not parts or len(parts[0]) <= 1:
                        return

                    prefix = parts[0][0]
                    cmd_raw = parts[0][1:].lower()
                    if "@" in cmd_raw:
                        cmd_name, at_target = cmd_raw.split("@", 1)
                        if is_bot_client and hasattr(client, "myself") and client.myself:
                            bot_user = (getattr(client.myself, "username", "") or "").lower()
                            if at_target != bot_user:
                                return
                    else:
                        cmd_name = cmd_raw

                    handler_entry = client._cmd_handlers_map.get(cmd_name)
                    if not handler_entry:
                        return

                    sender_id = getattr(event, "sender_id", None)
                    sudo_users = getattr(self.config, "SUDO_USERS", []) or []

                    if is_bot_client:
                        # Security: only owner and authorized sudo users may execute bot commands
                        owner_id = getattr(self.config, "OWNER_ID", None)
                        is_owner = False
                        if owner_id and sender_id == owner_id:
                            is_owner = True
                        elif hasattr(self, "ourselves"):
                            for acc in self.ourselves:
                                if hasattr(acc, "id") and sender_id == acc.id:
                                    is_owner = True
                                    break

                        is_sudo = bool(sender_id and sender_id in sudo_users)

                        if not is_owner and not is_sudo:
                            return

                        # Sudo user restrictions:
                        if is_sudo and not is_owner:
                            # 1. Check disabled sudo plugins / commands
                            disabled = getattr(self, "disabled_sudo_plugin_list", []) or []
                            if isinstance(disabled, (list, tuple, set)) and cmd_name in {str(x).lower() for x in disabled}:
                                return
                            owner_only_cmds = {
                                "apm", "apmpanel", "apm_install", "apm_uninstall", "unapm",
                                "apm_update", "updateapm", "apm_sub", "apmsub", "subcategories",
                                "apm_enable", "apmenable", "apm_disable", "apmdisable",
                                "apm_doctor", "apmdoctor", "apm_repair", "apmrepair", "apmfix",
                                "eval", "exec", "bash", "sh", "terminal", "py", "install",
                                "addsudo", "rmsudo", "dpfs", "rmdfs",
                                "restart", "reload", "shutdown", "update", "add_session", "session", "token",
                            }
                            if cmd_name in owner_only_cmds or handler_entry.get("file_name") in owner_only_cmds:
                                return
                    else:
                        is_self = getattr(event, "out", False)
                        if not is_self and hasattr(client, "myself") and client.myself:
                            if getattr(event, "sender_id", None) == client.myself.id:
                                is_self = True

                        if prefix == user_p:
                            if not is_self:
                                return
                        elif prefix == sudo_p:
                            if not sender_id or sender_id not in sudo_users:
                                return
                            owner_only_cmds = {
                                "apm", "apmpanel", "apm_install", "apm_uninstall", "unapm",
                                "apm_update", "updateapm", "apm_sub", "apmsub", "subcategories",
                                "apm_enable", "apmenable", "apm_disable", "apmdisable",
                                "apm_doctor", "apmdoctor", "apm_repair", "apmrepair", "apmfix",
                                "eval", "exec", "bash", "sh", "terminal", "py", "install",
                                "addsudo", "rmsudo", "dpfs", "rmdfs",
                                "restart", "reload", "shutdown", "update", "add_session", "session", "token",
                            }
                            if cmd_name in owner_only_cmds or handler_entry.get("file_name") in owner_only_cmds:
                                return
                            disabled = getattr(self, "disabled_sudo_plugin_list", []) or []
                            if isinstance(disabled, (list, tuple, set)) and cmd_name in {str(x).lower() for x in disabled}:
                                return
                        else:
                            return

                    message = enrich_message(event, client)

                    requires_input = handler_entry["requires_input"]
                    requires_reply = handler_entry["requires_reply"]
                    group_only = handler_entry["group_only"]
                    channel_only = handler_entry["channel_only"]
                    pm_only = handler_entry["pm_only"]
                    just_exc = handler_entry["just_exc"]
                    file_name = handler_entry["file_name"]
                    cmd_list = handler_entry["cmd"]
                    h_func = handler_entry["func"]

                    if message.is_reply or message.reply_to_msg_id:
                        with suppress_error(msg="Fetching replied message"):
                            reply = None
                            if hasattr(message, "get_reply_message"):
                                reply = await message.get_reply_message()
                            if not reply and hasattr(event, "message") and hasattr(event.message, "get_reply_message"):
                                reply = await event.message.get_reply_message()
                            if not reply and message.reply_to_msg_id:
                                chat_target = getattr(message, "input_chat", None) or getattr(event, "input_chat", None) or message.chat_id
                                reply = await client.get_messages(chat_target, ids=message.reply_to_msg_id)
                            if reply:
                                message.reply_to_message = enrich_message(reply, client)

                    chat_type = getattr(message.chat, "type", "")
                    user_inp = message.user_input
                    if requires_input and not user_inp:
                        return await message.handle_message("INPUT_REQUIRED")
                    if requires_reply and not message.reply_to_message:
                        return await message.handle_message("REPLY_REQUIRED")
                    if group_only and chat_type not in {"supergroup", "group"}:
                        return await message.handle_message("GROUP_ONLY")
                    if channel_only and chat_type != "channel":
                        return await message.handle_message("CHANNEL_ONLY")
                    if pm_only and chat_type != "private":
                        return await message.handle_message("PM_ONLY")

                    if just_exc:
                        await h_func(client, message)
                    else:
                        try:
                            await h_func(client, message)
                        except errors.MessageNotModifiedError:
                            pass
                        except Exception as exc:
                            tb = traceback.format_exc()
                            cmd_str = cmd_list[0] if isinstance(cmd_list, list) else cmd_list
                            logger.error(f"[{file_name}] Unhandled exception in '{cmd_str}':\n{tb}")
                            err_name = exc.__class__.__name__
                            err_detail = str(exc) or err_name
                            err_text = f"❌ <b>Error ({file_name}):</b> <code>{html.escape(err_detail[:300])}</code>"
                            last_msg = getattr(message, "_last_handled_msg", None)
                            if last_msg is not None:
                                with suppress_error(msg="Update processing message on failure"):
                                    await last_msg.edit_msg(err_text)
                            else:
                                with suppress_error(msg="Send error notice on failure"):
                                    await message.handle_message(err_text)
                            await self.send_error(client, cmd_list, tb, file_name=file_name)

                client.add_event_handler(cmd_router_callback, events.NewMessage())

        elif h_type == "custom":
            cust_filter = handler_info["filter"]

            async def custom_callback(event: events.NewMessage.Event):
                message = enrich_message(event, client)
                if cust_filter is not None:
                    if hasattr(cust_filter, "__call__"):
                        try:
                            passes = await cust_filter(client, message)
                        except Exception as exc:
                            logger.error(f"Custom filter error: {exc}\n{traceback.format_exc()}")
                            return
                        if not passes:
                            return

                if message.is_reply or message.reply_to_msg_id:
                    with suppress_error(msg="Fetching replied message in custom handler"):
                        reply = None
                        if hasattr(message, "get_reply_message"):
                            reply = await message.get_reply_message()
                        if not reply and hasattr(event, "message") and hasattr(event.message, "get_reply_message"):
                            reply = await event.message.get_reply_message()
                        if not reply and message.reply_to_msg_id:
                            chat_target = getattr(message, "input_chat", None) or getattr(event, "input_chat", None) or message.chat_id
                            reply = await client.get_messages(chat_target, ids=message.reply_to_msg_id)
                        if reply:
                            message.reply_to_message = enrich_message(reply, client)

                try:
                    await func(client, message)
                except Exception as exc:
                    logger.error(f"Custom handler exception in '{getattr(func, '__name__', 'func')}':\n{traceback.format_exc()}")

            client.add_event_handler(custom_callback, events.NewMessage())

    def _register_bot_handler(self, handler_type: str, custom_filter: Optional[Filter], func: Callable) -> None:
        if self._raw_bot is None:
            return

        if handler_type == "message":
            async def cb(event: events.NewMessage.Event):
                msg = enrich_message(event, self._raw_bot)
                if custom_filter is not None:
                    try:
                        if not await custom_filter(self._raw_bot, msg):
                            return
                    except Exception as exc:
                        logger.error(f"Bot filter error: {exc}\n{traceback.format_exc()}")
                        return

                if msg.is_reply or msg.reply_to_msg_id:
                    with suppress_error(msg="Fetching replied message in bot handler"):
                        reply = None
                        if hasattr(msg, "get_reply_message"):
                            reply = await msg.get_reply_message()
                        if not reply and hasattr(event, "message") and hasattr(event.message, "get_reply_message"):
                            reply = await event.message.get_reply_message()
                        if not reply and msg.reply_to_msg_id:
                            chat_target = getattr(msg, "input_chat", None) or getattr(event, "input_chat", None) or msg.chat_id
                            reply = await self._raw_bot.get_messages(chat_target, ids=msg.reply_to_msg_id)
                        if reply:
                            msg.reply_to_message = enrich_message(reply, self._raw_bot)

                try:
                    await func(self._raw_bot, msg)
                except Exception as exc:
                    logger.error(f"Bot handler exception in '{getattr(func, '__name__', 'func')}':\n{traceback.format_exc()}")
            self._raw_bot.add_event_handler(cb, events.NewMessage())

        elif handler_type == "callback_query":
            async def cq_cb(event: events.CallbackQuery.Event):
                setattr(event, "from_user", types.User(id=event.sender_id) if event.sender_id else None)
                if custom_filter is not None and not await custom_filter(self._raw_bot, event):
                    return
                try:
                    sig = inspect.signature(func)
                    if len(sig.parameters) == 1:
                        await func(event)
                    else:
                        await func(self._raw_bot, event)
                except (TypeError, ValueError):
                    try:
                        await func(self._raw_bot, event)
                    except TypeError:
                        await func(event)
            self._raw_bot.add_event_handler(cq_cb, events.CallbackQuery())

        elif handler_type == "inline_query":
            async def iq_cb(event: events.InlineQuery.Event):
                setattr(event, "from_user", types.User(id=event.sender_id) if event.sender_id else None)
                if custom_filter is not None and not await custom_filter(self._raw_bot, event):
                    return
                try:
                    sig = inspect.signature(func)
                    if len(sig.parameters) == 1:
                        await func(event)
                    else:
                        await func(self._raw_bot, event)
                except (TypeError, ValueError):
                    try:
                        await func(self._raw_bot, event)
                    except TypeError:
                        await func(event)
            self._raw_bot.add_event_handler(iq_cb, events.InlineQuery())

        elif handler_type == "telethon_event":
            self._raw_bot.add_event_handler(func, custom_filter)

    def add_help_to_command_list(
        self,
        commands: Union[List[str], str],
        file_name: str,
        help_map: dict,
        requires_input: bool,
        requires_reply: bool,
        group_only: bool,
        channel_only: bool,
        private_only: bool,
        bot_mode_unsupported: bool = False,
    ) -> None:
        example = html.escape(str(help_map.get("example", "No example available")))
        help_text = html.escape(str(help_map.get("help", "Sorry, No help available for this command")))
        user_args = help_map.get("user_args")
        if isinstance(commands, str):
            commands = [commands]
        data = {
            "commands": commands,
            "help": help_text,
            "example": example,
            "user_args": user_args,
            "requires_input": requires_input,
            "requires_reply": requires_reply,
            "group_only": group_only,
            "channel_only": channel_only,
            "private_only": private_only,
            "bot_mode_unsupported": bot_mode_unsupported,
        }
        if file_name not in self.cmd_list:
            self.cmd_list[file_name] = [data]
        elif commands[0] not in [x.get("commands", [""])[0] for x in self.cmd_list[file_name]]:
            self.cmd_list[file_name].append(data)

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=20.0, http2=True)
        return self._http

    async def update_cache(self) -> None:
        if self.db is not None:
            cache = Cache(self.config, self.db, self.clients)
            await cache.update_all()

    async def _setup(self, restart: bool = False, *args, **kwargs) -> None:
        if not os.path.isdir("cache"):
            os.mkdir("cache")
        await self._db_setup()
        env_col = self.db.env_col if self.db is not None else self.local_db.env_col
        self.config = Config(env_col, executor=self.executor)
        await self.config.init_db_vars()
        await self.setup_localization()
        self.sudo_cmd_handler = await self.config.get_env("SUDO_CMD_HANDLER") or "!"
        self.user_command_handler = await self.config.get_env("CMD_HANDLER") or "."
        disabled_sudo = await self.config.get_env("DISABLED_SUDO_CMD_LIST", []) or []
        if isinstance(disabled_sudo, str):
            disabled_sudo = [item.strip() for item in disabled_sudo.split(",") if item.strip()]
        self.disabled_sudo_plugin_list = [str(item).strip().lower() for item in disabled_sudo]
        self.log_chat = self.config.digit_wrap(await self.config.get_env("LOG_CHAT_ID"))
        self.bot_mode = str(await self.config.get_env("BOT_MODE")).lower() in {"yes", "true", "enable", "1"}
        # Initialize plugin manager
        self.plugin_manager = PluginManager(self)
        if not restart:
            await self.initialize_telegram_sessions(*args, **kwargs)
        await self.update_cache()

    async def initialize_telegram_sessions(self, *args, **kwargs) -> None:
        api_id = getattr(self.config, "API_ID", None)
        api_hash = getattr(self.config, "API_HASH", None)
        bot_token = getattr(self.config, "BOT_TOKEN", None)

        if not api_id or not api_hash:
            self.log("API_ID or API_HASH missing in config.", level=logging.WARNING)
            self.training_wheels_protocol = True
            return

        if bot_token:
            try:
                self._raw_bot = AltruixTelegramClient(MemorySession(), api_id=api_id, api_hash=api_hash)
                await self._raw_bot.start(bot_token=bot_token)
                self.bot_info = await self._raw_bot.get_me()
                self._raw_bot.myself = self.bot_info
                self.log(f"Assistant : Logged in as @{getattr(self.bot_info, 'username', 'Unknown')}")
                for h_type, cust_filter, func in self._pending_bot_handlers:
                    self._register_bot_handler(h_type, cust_filter, func)
                for h_info in self._pending_handlers:
                    if not h_info.get("bot_mode_unsupported"):
                        self._attach_handler_to_client(self._raw_bot, h_info)
            except Exception as e:
                self.log(f"Failed to start assistant bot: {e}", level=logging.ERROR)

        string_sessions = getattr(self.config, "SESSIONS", [])
        if not string_sessions and self.config and hasattr(self.config, "get_env_from_db"):
            string_sessions = await self.config.get_env_from_db("SESSIONS") or []

        if not string_sessions:
            self.training_wheels_protocol = True
            self.log("No User Session found; userbot features will run in TWP mode.", level=logging.WARNING)
        else:
            self.log("User Sessions found, connecting via Telethon StringSession...")
            for idx, session_str in enumerate(string_sessions):
                try:
                    c = AltruixTelegramClient(
                        StringSession(session_str),
                        api_id=api_id,
                        api_hash=api_hash,
                    )
                    await c.start()
                    c.myself = await c.get_me()
                    self.clients.append(c)
                    if self.config.OWNER_ID and c.myself.id != self.config.OWNER_ID:
                        self.ourselves.append(c.myself)
                    for h_info in self._pending_handlers:
                        self._attach_handler_to_client(c, h_info)
                    self.log(f"[{idx + 1}/{len(string_sessions)}] User session loaded: {getattr(c.myself, 'first_name', '')}")
                except Exception as err:
                    self.log(f"Failed loading session {idx + 1}: {err}", level=logging.ERROR)

    async def add_session(self, session: str, status: Optional[Any] = None) -> Optional[AltruixTelegramClient]:
        await self.config.add_element_to_list("SESSIONS", session)
        self.config.append_session(session)
        api_id = self.config.API_ID
        api_hash = self.config.API_HASH
        app = AltruixTelegramClient(StringSession(session), api_id=api_id, api_hash=api_hash)
        await app.start()
        app.myself = await app.get_me()
        self.clients.append(app)
        if self.config.OWNER_ID and app.myself.id != self.config.OWNER_ID:
            self.ourselves.append(app.myself)
        for h_info in self._pending_handlers:
            self._attach_handler_to_client(app, h_info)
        self.training_wheels_protocol = False
        self.log(f"User session added successfully: {getattr(app.myself, 'first_name', '')}")
        if status:
            with contextlib.suppress(Exception):
                await status.edit("<b>Account successfully added!</b>", parse_mode="html")
        return app

    async def custom_log(self, msg: str, level: int = logging.INFO, p_msg: Any = None) -> Any:
        self.log(msg, level)
        if p_msg and hasattr(p_msg, "edit_msg"):
            return await p_msg.edit_msg(msg.strip())

    async def reboot(
        self,
        soft: bool = False,
        last_msg: Any = None,
        power_hard: bool = False,
        **kwargs: Any,
    ) -> None:
        """Request a clean process restart after disconnecting active clients."""
        self._restart_requested = True
        if last_msg is not None and hasattr(last_msg, "edit_msg"):
            with contextlib.suppress(Exception):
                await last_msg.edit_msg("Restarting Altruix…")
        if self._stop_event is None:
            raise RuntimeError("Altruix is not running; restart can only be requested while it is active")
        self._stop_event.set()

    async def _restart(self, **kwargs: Any) -> None:
        """Compatibility entry point used by the updater."""
        await self.reboot(**kwargs)

    async def load_from_directory(self, path_pattern: str, log: bool = True, msg: Any = None, category: Optional[str] = None) -> None:
        helper_scripts = glob.glob(path_pattern, recursive=True)
        if not helper_scripts:
            return
        clean_pat = path_pattern.replace("\\", "/").lower()
        if category:
            cat = category
        elif any(k in clean_pat for k in ("plugins/userbot", "plugins/bot", "internals", "utils")):
            cat = "main"
        else:
            cat = "loaded"

        for file_path in helper_scripts:
            path_obj = Path(file_path)
            plugin_name = path_obj.stem
            if plugin_name == "__init__":
                continue
            p_name = plugin_name.lower()
            self.plugin_categories[p_name] = cat
            if cat == "main":
                self.main_plugins.add(p_name)
                self.extra_plugins.discard(p_name)
            else:
                self.extra_plugins.add(p_name)
                self.main_plugins.discard(p_name)

            module_name = f"Main.{path_obj.parent.name}.{plugin_name}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                mod.Altruix = self
                mod.bot = self.bot
                mod.telethon = telethon
                mod.Client = AltruixTelegramClient
                mod.filters = default_filters
                mod.suppress_error = suppress_error
                mod.safe_suppress = safe_suppress
                mod.suppress = suppress
                sys.modules[module_name] = mod
                try:
                    spec.loader.exec_module(mod)
                    if log:
                        self.log(f"Loaded plugin: {plugin_name}")
                except Exception as err:
                    sys.modules.pop(module_name, None)
                    self.log(f"Failed to load plugin {plugin_name}: {err}", level=logging.ERROR)

    async def load_all_modules(self) -> None:
        await self.load_from_directory("Main/utils/*.py", log=False)
        await self.load_from_directory("Main/internals/*.py", log=False)
        self.log("All internal modules loaded.")
        await self.load_from_directory("Main/plugins/bot/*.py", log=True)
        await self.load_from_directory("Main/plugins/userbot/*.py", log=True)
        # Load externally installed plugins respecting segregation & quarantine status
        if self.plugin_manager and self.plugin_manager._installed:
            for pname, manifest in self.plugin_manager._installed.items():
                if manifest.enabled and not manifest.quarantined:
                    pdir = self.plugin_manager.PLUGIN_DIR / pname
                    if pdir.is_dir():
                        await self.plugin_manager._load_plugin_modules(manifest, pdir)
                    elif (self.plugin_manager.PLUGIN_DIR / f"{pname}.py").exists():
                        await self.load_from_directory(str(self.plugin_manager.PLUGIN_DIR / f"{pname}.py"), log=True)
        else:
            await self.load_from_directory("Main/plugins/external/**/*.py", log=True)

        # Auto-sync extra plugin repos from GitHub if configured
        load_xtra = os.environ.get("LOAD_XTRA_PLUGINS", "").strip().lower() in ("true", "1", "yes", "enable")
        if not load_xtra and self.config and hasattr(self.config, "LOAD_XTRA_PLUGINS"):
            load_xtra = bool(self.config.LOAD_XTRA_PLUGINS)
        if load_xtra:
            try:
                from Main.core.apm_env_setup import sync_xtra_plugins_repos
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, sync_xtra_plugins_repos)
            except Exception as e:
                self.log(f"Error syncing extra plugins: {e}", level=logging.WARNING)

        # Auto-load workspace development & extra plugin suites if present locally
        suites = {"XtraPlugins", "XtraPluginsAI"}
        configured_repos = os.environ.get("XTRA_PLUGINS_REPOS", "")
        if configured_repos:
            for r in re.split(r"[\s,;]+", configured_repos):
                r_name = r.rstrip("/").split("/")[-1].replace(".git", "")
                if r_name:
                    suites.add(r_name)

        for suite in suites:
            candidates = [Path(f"./{suite}"), Path(f"./plug/{suite}")]
            for suite_dir in candidates:
                if suite_dir.is_dir() and not (self.plugin_manager and suite in self.plugin_manager._installed):
                    await self.load_from_directory(f"{suite_dir.as_posix()}/*.py", log=True)
                    await self.load_from_directory(f"{suite_dir.as_posix()}/**/*.py", log=True)

        self.prepare_help()
        self.log("All plugins loaded.")

    def prepare_help(self) -> None:
        self._command_help_message_data.clear()
        owner_only_cmds = {
            "apm", "apmpanel", "apm_install", "apm_uninstall", "unapm",
            "apm_update", "updateapm", "apm_sub", "apmsub", "subcategories",
            "apm_enable", "apmenable", "apm_disable", "apmdisable",
            "apm_doctor", "apmdoctor", "apm_repair", "apmrepair", "apmfix",
            "eval", "exec", "bash", "sh", "terminal", "py", "install",
            "addsudo", "rmsudo", "dpfs", "rmdfs",
            "restart", "reload", "shutdown", "update", "add_session", "session", "token",
        }
        disabled_sudo = set(str(x).lower() for x in (getattr(self, "disabled_sudo_plugin_list", []) or []))

        for plugin_name, commands_data in self.cmd_list.items():
            p_name = plugin_name.lower()
            self._command_help_message_data[p_name] = ""
            for cmd_info in commands_data:
                cmds: List[str] = cmd_info.get("commands", ["???"])
                h_text = cmd_info.get("help", "")
                ex_text = cmd_info.get("example", "")
                user_args = cmd_info.get("user_args", [])
                bot_unsupported = cmd_info.get("bot_mode_unsupported", False)
                p_only = cmd_info.get("private_only", False)
                g_only = cmd_info.get("group_only", False)
                c_only = cmd_info.get("channel_only", False)
                r_reply = cmd_info.get("requires_reply", False)
                r_input = cmd_info.get("requires_input", False)

                bot_status = "👤 Userbot Only" if bot_unsupported else "🤖 Bot & Userbot"

                is_owner_only = any(c.lower() in owner_only_cmds for c in cmds) or (p_name in owner_only_cmds)
                is_sudo_disabled = any(c.lower() in disabled_sudo for c in cmds) or (p_name in disabled_sudo)
                if is_owner_only:
                    sudo_status = "👑 Owner Only (Sudo Blocked)"
                elif is_sudo_disabled:
                    sudo_status = "🚫 Sudo Disabled"
                else:
                    sudo_status = "🛡️ Sudo Allowed"

                if p_only:
                    scope = "💬 PM Only"
                elif g_only:
                    scope = "👥 Groups Only"
                elif c_only:
                    scope = "📢 Channels Only"
                else:
                    scope = "🌐 All Chats"

                self._command_help_message_data[p_name] += "\n<b>Command:</b> "
                for c in cmds:
                    self._command_help_message_data[p_name] += f"<code>{self.user_command_handler}{c}</code> / "
                self._command_help_message_data[p_name] = self._command_help_message_data[p_name].rstrip("/ ") + "\n"
                self._command_help_message_data[p_name] += f"<b>Help:</b> <i>{h_text}</i>\n"
                self._command_help_message_data[p_name] += f"<b>Mode:</b> {bot_status}  |  <b>Sudo:</b> {sudo_status}\n"
                self._command_help_message_data[p_name] += f"<b>Scope:</b> {scope}"
                reqs = []
                if r_reply:
                    reqs.append("↩️ Reply Needed")
                if r_input:
                    reqs.append("✍️ Input Needed")
                if reqs:
                    self._command_help_message_data[p_name] += f" (<i>{', '.join(reqs)}</i>)"
                self._command_help_message_data[p_name] += "\n"

                if ex_text:
                    self._command_help_message_data[p_name] += f"<b>Example:</b> <code>{self.user_command_handler}{ex_text}</code>\n"
                if user_args:
                    self._command_help_message_data[p_name] += "<b>Flags:</b>\n"
                    for arg in user_args:
                        arg_name = arg.get("arg", "")
                        arg_help = arg.get("help", "")
                        req = " <i>[input required]</i>" if arg.get("requires_input", False) else ""
                        self._command_help_message_data[p_name] += f"  • <code>-{arg_name}</code>: {arg_help}{req}\n"

    def get_plugin_category(self, plugin_name: str) -> str:
        p_name = plugin_name.lower()
        if p_name in self.extra_plugins:
            return "loaded"
        if p_name in self.main_plugins:
            return "main"
        return self.plugin_categories.get(p_name, "main")

    def get_plugins_by_category(self) -> Tuple[List[str], List[str]]:
        main_list: List[str] = []
        loaded_list: List[str] = []
        for p in sorted(self._command_help_message_data.keys()):
            if self.get_plugin_category(p) == "loaded":
                loaded_list.append(p)
            else:
                main_list.append(p)
        return main_list, loaded_list

    async def send_error(
        self,
        client: AltruixTelegramClient,
        cmd: Union[str, List[str]],
        error: str,
        file_name: str,
        **args,
    ) -> Any:
        chat_id = self.log_chat
        if not chat_id:
            logger.info("log_chat is not configured; error recorded only in console logs.")
            return
        cmd_str = cmd[0] if isinstance(cmd, list) else cmd
        txt = (
            f"<b>ERROR OCCURRED:</b>\n"
            f"Command: <code>{self.user_command_handler}{cmd_str}</code>\n"
            f"Plugin: <code>{file_name}</code>\n\n"
            f"<pre>{error}</pre>"
        )
        try:
            return await client.send_message(chat_id, txt, parse_mode="html")
        except Exception as e:
            logger.warning(f"Failed to send direct error to log_chat: {e}")
            try:
                service, paste_link = await Paste(error).paste()
                fallback = f"<b>ERROR:</b> <a href='{paste_link}'>{service}</a>"
                return await client.send_message(chat_id, fallback, parse_mode="html")
            except Exception as e2:
                logger.error(f"Failed to send paste link to log_chat: {e2}")

    async def update_on_startup(self) -> None:
        if getattr(self.config, "UPDATE_ON_STARTUP", False):
            updater_ = Updater(repo=self.config.REPO, branch="main", app_url=self.app_url_)
            with contextlib.suppress(Exception):
                repo = await updater_.init_repo()
                up_rem = await updater_.create_remote_and_fetch(repo)
                await updater_.update_locally(up_rem, repo, None, self, True)

    async def run_cmd_async(self, cmd: str) -> Tuple[str, str, int, int]:
        args = resolve_command(shlex.split(cmd))
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        return out.decode("utf-8").strip(), err.decode("utf-8").strip(), proc.returncode or 0, proc.pid

    async def _run(self) -> None:
        await self._setup()
        await self.load_all_modules()
        print(self.banner)
        self.log(f"Altruix v{self.__version__} successfully initialized with Telethon v{telethon.__version__}!")

        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()
        self._stop_event = stop_event

        def _shutdown_signal_handler(sig: int) -> None:
            self.log(f"Received signal {sig}, initiating graceful shutdown...")
            stop_event.set()

        with contextlib.suppress(NotImplementedError):
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, _shutdown_signal_handler, sig)

        tasks = []
        if self._raw_bot is not None:
            tasks.append(asyncio.ensure_future(self._raw_bot.run_until_disconnected()))
        for c in self.clients:
            tasks.append(asyncio.ensure_future(c.run_until_disconnected()))

        if not tasks:
            self.log("No active clients or bot — nothing to run.", level=logging.WARNING)
            if self.plugin_manager is not None:
                with contextlib.suppress(Exception):
                    await self.plugin_manager._http.aclose()
            if self.db is not None and hasattr(self.db, "close"):
                with contextlib.suppress(Exception):
                    self.db.close()
            self.executor.shutdown(wait=False)
            self._stop_event = None
            return

        # Stop on the first disconnect or shutdown request. Cancel the other
        # waiters before disconnecting clients so shutdown cannot deadlock.
        stop_task = asyncio.create_task(stop_event.wait())
        wait_tasks = [*tasks, stop_task]
        done, pending = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)
        await asyncio.gather(*done, return_exceptions=True)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        # Graceful teardown
        self.log("Shutting down — disconnecting clients...")
        for c in self.clients:
            with contextlib.suppress(Exception):
                await c.disconnect()
        if self._raw_bot is not None:
            with contextlib.suppress(Exception):
                await self._raw_bot.disconnect()
        if self.plugin_manager is not None:
            with contextlib.suppress(Exception):
                await self.plugin_manager._http.aclose()
        if self._http is not None and not self._http.is_closed:
            with contextlib.suppress(Exception):
                await self._http.aclose()
        if hasattr(self, "db") and self.db is not None and hasattr(self.db, "close"):
            self.db.close()
        self.executor.shutdown(wait=False)
        self._stop_event = None
        self.log("Altruix has exited cleanly.")

    def run(self) -> None:
        asyncio.run(self._run())
        if self._restart_requested:
            self._restart_requested = False
            if Path(sys.argv[0]).name == "__main__.py" and Path(sys.argv[0]).parent.name == "Main":
                restart_args = [sys.executable, "-m", "Main", *sys.argv[1:]]
            else:
                restart_args = [sys.executable, *sys.argv]
            os.execv(sys.executable, restart_args)
