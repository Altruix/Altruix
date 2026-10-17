# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import re
import contextlib
from Main.utils.suppress import suppress_error
from typing import Any, Callable, List, Optional, Union


class Filter:
    """Composable filter object supporting &, |, ~ operators."""

    def __init__(self, check_func: Callable[[Any, Any], bool]):
        self.check_func = check_func

    async def __call__(self, client: Any, message: Any) -> bool:
        try:
            res = self.check_func(client, message)
        except TypeError:
            try:
                res = self.check_func(self, client, message)
            except TypeError:
                res = self.check_func(message)
        if hasattr(res, "__await__"):
            return await res
        return bool(res)

    def __and__(self, other: Filter) -> Filter:
        async def combined(c: Any, m: Any) -> bool:
            return (await self(c, m)) and (await other(c, m))
        return Filter(combined)

    def __or__(self, other: Filter) -> Filter:
        async def combined(c: Any, m: Any) -> bool:
            return (await self(c, m)) or (await other(c, m))
        return Filter(combined)

    def __invert__(self) -> Filter:
        async def inverted(c: Any, m: Any) -> bool:
            return not (await self(c, m))
        return Filter(inverted)


def create(check_func: Callable) -> Filter:
    return Filter(check_func)


class Filters:
    """Namespace of common filter builders for Telethon message events."""

    @staticmethod
    def command(commands: Union[str, List[str]], prefixes: Union[str, List[str]] = "/") -> Filter:
        if isinstance(commands, str):
            commands = [commands]
        if isinstance(prefixes, str):
            prefixes = list(prefixes)

        def check(client: Any, message: Any) -> bool:
            text = getattr(message, "text", None) or getattr(message, "raw_text", None) or getattr(message, "message", None) or ""
            if not text:
                return False
            first_word = text.split()[0].lower() if text.split() else ""
            if not first_word:
                return False
            for p in prefixes:
                for cmd in commands:
                    prefix_cmd = f"{p}{cmd}".lower()
                    if text.lower() == prefix_cmd or text.lower().startswith(f"{prefix_cmd} ") or text.lower().startswith(f"{prefix_cmd}\n"):
                        return True
                    if first_word.startswith(f"{prefix_cmd}@"):
                        bot_username = ""
                        if hasattr(client, "myself") and client.myself:
                            bot_username = (getattr(client.myself, "username", "") or "").lower()
                        elif hasattr(client, "get_me"):
                            import Main
                            bot_username = (getattr(getattr(Main.Altruix, "bot_info", None), "username", "") or "").lower()
                        at_target = first_word.split("@", 1)[1]
                        if not bot_username or at_target == bot_username:
                            return True
            return False

        return Filter(check)

    @staticmethod
    def regex(pattern: Union[str, re.Pattern], flags: int = 0) -> Filter:
        comp = re.compile(pattern, flags) if isinstance(pattern, str) else pattern

        def check(client: Any, message: Any) -> bool:
            # For callback query events, message.data is the button payload (bytes or str)
            data = getattr(message, "data", None)
            if data is not None:
                text = data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else str(data)
            else:
                text = (
                    getattr(message, "text", None)
                    or getattr(message, "raw_text", None)
                    or getattr(message, "message", None)
                )
                if isinstance(text, bytes):
                    text = text.decode("utf-8", errors="ignore")
                elif text is not None and not isinstance(text, str):
                    text = str(text)

            if text is None:
                return False
            match = comp.search(str(text))
            if match:
                with suppress_error(msg="setting matches on message"):
                    setattr(message, "matches", [match])
                    setattr(message, "pattern_match", match)
                return True
            return False

        return Filter(check)

    @staticmethod
    def user(users: Union[int, str, List[Union[int, str]]]) -> Filter:
        if isinstance(users, (int, str)):
            user_list = [int(users)] if str(users).lstrip("-").isdigit() else [users]
        else:
            user_list = [int(u) if str(u).lstrip("-").isdigit() else u for u in users]

        def check(client: Any, message: Any) -> bool:
            sender_id = getattr(message, "sender_id", None)
            if sender_id is not None and sender_id in user_list:
                return True
            sender = getattr(message, "from_user", None) or getattr(message, "sender", None)
            if sender:
                if getattr(sender, "id", None) in user_list:
                    return True
                if getattr(sender, "username", None) in user_list:
                    return True
            return False

        return Filter(check)

    @staticmethod
    def _private(client: Any, message: Any) -> bool:
        if hasattr(message, "is_private"):
            return bool(message.is_private)
        chat = getattr(message, "chat", None)
        return getattr(chat, "type", "") == "private"

    @staticmethod
    def _group(client: Any, message: Any) -> bool:
        if hasattr(message, "is_group"):
            return bool(message.is_group)
        chat = getattr(message, "chat", None)
        return getattr(chat, "type", "") in {"group", "supergroup"}

    @staticmethod
    def _channel(client: Any, message: Any) -> bool:
        if hasattr(message, "is_channel"):
            return bool(message.is_channel)
        chat = getattr(message, "chat", None)
        return getattr(chat, "type", "") == "channel"

    @staticmethod
    def _mentioned(client: Any, message: Any) -> bool:
        return bool(getattr(message, "mentioned", False))

    @staticmethod
    def _new_chat_members(client: Any, message: Any) -> bool:
        if getattr(message, "user_joined", False) or getattr(message, "user_added", False):
            return True
        action = getattr(message, "action", None)
        if action and type(action).__name__ in {"MessageActionChatAddUser", "MessageActionChatJoinedByLink"}:
            return True
        return False

    private = Filter(_private)
    group = Filter(_group)
    channel = Filter(_channel)
    mentioned = Filter(_mentioned)
    new_chat_members = Filter(_new_chat_members)
    all = Filter(lambda c, m: True)
    create = staticmethod(create)


filters = Filters()


def user_filters(cmd: Union[str, List[str]], disable_sudo: bool = False) -> Filter:
    """Filter that matches self user commands and sudo commands."""
    if isinstance(cmd, str):
        cmd = [cmd]
    cmd_set = {c.lower() for c in cmd}

    async def check(client: Any, message: Any) -> bool:
        text = getattr(message, "text", None) or getattr(message, "raw_text", None) or getattr(message, "message", None) or ""
        if not text or not isinstance(text, str) or len(text) < 2:
            return False

        import Main
        altruix = Main.Altruix
        user_prefix = getattr(altruix, "user_command_handler", ".") or "."
        sudo_prefix = getattr(altruix, "sudo_cmd_handler", "!") or "!"

        first_char = text[0]
        if first_char != user_prefix and first_char != sudo_prefix:
            return False

        first_token = text.split(None, 1)[0]
        if len(first_token) < 2:
            return False

        prefix = first_token[0]
        command_name = first_token[1:].lower()
        if command_name not in cmd_set:
            return False

        if prefix == user_prefix:
            is_self = getattr(message, "out", False)
            if not is_self and hasattr(message, "from_user") and message.from_user:
                is_self = getattr(message.from_user, "is_self", False)
            if not is_self and hasattr(client, "myself") and client.myself:
                sender_id = getattr(message, "sender_id", None)
                if sender_id and sender_id == client.myself.id:
                    is_self = True
            return is_self

        if prefix == sudo_prefix and not disable_sudo:
            sender_id = getattr(message, "sender_id", None)
            sudo_users = getattr(altruix.config, "SUDO_USERS", []) or []
            if not sender_id or sender_id not in sudo_users:
                return False

            disabled = getattr(altruix, "disabled_sudo_plugin_list", []) or []
            if isinstance(disabled, str):
                disabled_set = {x.strip().lower() for x in disabled.split(",") if x.strip()}
            else:
                disabled_set = {str(x).strip().lower() for x in disabled}
            return command_name not in disabled_set

        return False

    return Filter(check)
