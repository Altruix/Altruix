# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import re
import os
import asyncio
import logging
import contextlib
from dataclasses import dataclass
from Main.utils.suppress import suppress_error
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple, Union

from telethon import errors, utils
from telethon.tl.patched import Message as TelethonMessage
from telethon.tl.custom import Message as CustomMessage

logger = logging.getLogger("altruix.message")


class REGEX_STRINGS:
    ARGS_REGEX = r"(-[a-zA-Z0-9_]+)([0-9]*)$"


@dataclass
class Arg:
    key: str
    value: Optional[str] = None


class Args(list):
    def __init__(self, *args):
        super().__init__(args)

    def __contains__(self, key: object) -> bool:
        clean_key = str(key).lstrip("-")
        return any(x.key == clean_key or x.key == key or x.key.lstrip("-") == clean_key for x in self)

    def __getattr__(self, key: str) -> Any:
        clean_key = key.lstrip("-")
        for x in self:
            if x.key == clean_key or x.key == key:
                return x.value
        return None

    def get(self, key: str, default: Any = None) -> Any:
        val = getattr(self, key)
        return default if val is None else val


class ChatWrapper:
    """Convenience wrapper for Telethon chats matching Altruix interface."""

    def __init__(self, client: Any, chat_entity: Any, chat_id: Optional[int] = None):
        self._client = client
        self._entity = chat_entity
        cid = chat_id or getattr(chat_entity, "id", None)
        if not cid:
            from telethon.utils import get_peer_id
            try:
                cid = get_peer_id(chat_entity)
            except Exception:
                cid = getattr(chat_entity, "channel_id", None) or getattr(chat_entity, "user_id", None) or getattr(chat_entity, "chat_id", None) or 0
        self.id: int = int(cid) if cid is not None else 0
        self.title: str = getattr(chat_entity, "title", getattr(chat_entity, "first_name", "Chat"))
        self.username: Optional[str] = getattr(chat_entity, "username", None)

    @property
    def type(self) -> str:
        if hasattr(self._entity, "broadcast") and self._entity.broadcast:
            return "channel"
        if hasattr(self._entity, "megagroup") and self._entity.megagroup:
            return "supergroup"
        if hasattr(self._entity, "participants_count") or self.id < 0:
            return "group"
        return "private"

    @property
    def mention(self) -> str:
        if self.username:
            return f"@{self.username}"
        return f"<b>{self.title or 'Chat'}</b>"

    async def ban_member(self, user_id: Union[int, str], until_date=None) -> Any:
        return await self._client.ban_chat_member(self.id, user_id, until_date=until_date)

    async def unban_member(self, user_id: Union[int, str]) -> Any:
        return await self._client.unban_chat_member(self.id, user_id)


class UserWrapper:
    """Convenience wrapper for Telethon users matching Altruix interface."""

    def __init__(self, user_entity: Any):
        self._entity = user_entity
        self.id: int = getattr(user_entity, "id", 0)
        self.first_name: str = getattr(user_entity, "first_name", "") or ""
        self.last_name: Optional[str] = getattr(user_entity, "last_name", None)
        self.username: Optional[str] = getattr(user_entity, "username", None)
        self.is_self: bool = getattr(user_entity, "is_self", False)
        self.is_bot: bool = getattr(user_entity, "bot", False)
        self.bot: bool = self.is_bot
        self.type: str = "private"
        self.is_scam: bool = getattr(user_entity, "scam", False)
        self.is_verified: bool = getattr(user_entity, "verified", False)
        self.is_premium: bool = getattr(user_entity, "premium", False)
        self.is_mutual_contact: bool = getattr(user_entity, "mutual_contact", False)
        self.phone: Optional[str] = getattr(user_entity, "phone", None)

    @property
    def mention(self) -> str:
        if self.username:
            return f"@{self.username}"
        name = f"{self.first_name} {self.last_name}".strip() if self.last_name else self.first_name
        return f"<a href='tg://user?id={self.id}'>{name or 'User'}</a>"

    def __repr__(self) -> str:
        return f"<User id={self.id} name='{self.first_name}'>"


class Message(TelethonMessage):
    """
    Subclassed Telethon Message containing Altruix convenience properties and methods.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reply_to_cached: Optional[Message] = None
        self._sender_cached: Optional[UserWrapper] = None
        self._chat_cached: Optional[ChatWrapper] = None

    @property
    def client(self) -> Any:
        return getattr(self, "_client", None)

    @client.setter
    def client(self, val: Any) -> None:
        self._client = val

    @property
    def sender_id(self) -> Optional[int]:
        if hasattr(self, "_sender_id_override"):
            return self._sender_id_override
        try:
            return super().sender_id
        except Exception:
            return None

    @sender_id.setter
    def sender_id(self, val: Optional[int]) -> None:
        self._sender_id_override = val

    @property
    def chat_id(self) -> Optional[int]:
        if hasattr(self, "_chat_id_override"):
            return self._chat_id_override
        try:
            return super().chat_id
        except Exception:
            return None

    @chat_id.setter
    def chat_id(self, val: Optional[int]) -> None:
        self._chat_id_override = val

    @property
    def text(self) -> Optional[str]:
        val = getattr(self, "_text", None)
        if val is not None:
            return val
        return getattr(self, "message", None)

    @text.setter
    def text(self, val: Optional[str]) -> None:
        self._text = val
        self.message = val

    @property
    def is_private(self) -> bool:
        if hasattr(self, "_is_private_override"):
            return self._is_private_override
        try:
            return super().is_private
        except Exception:
            return False

    @is_private.setter
    def is_private(self, val: bool) -> None:
        self._is_private_override = val

    @property
    def is_group(self) -> bool:
        if hasattr(self, "_is_group_override"):
            return self._is_group_override
        try:
            return super().is_group
        except Exception:
            return False

    @is_group.setter
    def is_group(self, val: bool) -> None:
        self._is_group_override = val

    @property
    def is_channel(self) -> bool:
        if hasattr(self, "_is_channel_override"):
            return self._is_channel_override
        try:
            return super().is_channel
        except Exception:
            return False

    @is_channel.setter
    def is_channel(self, val: bool) -> None:
        self._is_channel_override = val

    @property
    def reply_to_msg_id(self) -> Optional[int]:
        if hasattr(self, "_reply_to_msg_id_override"):
            return self._reply_to_msg_id_override
        try:
            return super().reply_to_msg_id
        except Exception:
            return None

    @reply_to_msg_id.setter
    def reply_to_msg_id(self, val: Optional[int]) -> None:
        self._reply_to_msg_id_override = val

    @property
    def reply_to_top_id(self) -> Optional[int]:
        if hasattr(self, "_reply_to_top_id_override"):
            return self._reply_to_top_id_override
        reply_to = getattr(self, "reply_to", None)
        return getattr(reply_to, "reply_to_top_id", None)

    @reply_to_top_id.setter
    def reply_to_top_id(self, val: Optional[int]) -> None:
        self._reply_to_top_id_override = val

    @property
    def reply_to_message(self) -> Optional[Message]:
        cached = getattr(self, "_reply_to_cached", None)
        if cached is not None:
            return cached
        internal = getattr(self, "_reply_message", None)
        if internal is not None:
            cl = getattr(self, "client", None) or getattr(self, "_client", None)
            enriched = enrich_message(internal, cl)
            self._reply_to_cached = enriched
            return enriched
        return None

    @reply_to_message.setter
    def reply_to_message(self, val: Any) -> None:
        self._reply_to_cached = val

    async def get_reply_message(self) -> Optional[Message]:
        cached = getattr(self, "_reply_to_cached", None)
        if cached is not None:
            return cached
        reply = None
        cl = getattr(self, "client", None) or getattr(self, "_client", None)
        if cl and self.reply_to_msg_id:
            chat_target = getattr(self, "input_chat", None) or self.chat_id
            try:
                reply = await cl.get_messages(chat_target, ids=self.reply_to_msg_id)
            except Exception:
                pass
        if not reply:
            try:
                reply = await super().get_reply_message()
            except Exception:
                pass
        if reply:
            enriched = enrich_message(reply, cl)
            self._reply_to_cached = enriched
            return enriched
        return None

    @property
    def from_user(self) -> Optional[UserWrapper]:
        cached = getattr(self, "_sender_cached", None)
        if cached:
            return cached
        sender = getattr(self, "sender", None)
        if sender:
            self._sender_cached = UserWrapper(sender)
            return self._sender_cached
        if self.sender_id:
            from telethon import types as _types
            dummy = _types.User(id=self.sender_id)
            self._sender_cached = UserWrapper(dummy)
            return self._sender_cached
        return None

    @property
    def chat(self) -> ChatWrapper:
        cached = getattr(self, "_chat_cached", None)
        if cached:
            return cached
        chat_ent = getattr(self, "_chat", None) or getattr(self, "input_chat", None) or self
        self._chat_cached = ChatWrapper(self.client, chat_ent, chat_id=self.chat_id)
        return self._chat_cached

    @property
    def new_chat_members(self) -> List[UserWrapper]:
        if hasattr(self, "_new_chat_members_cached"):
            return self._new_chat_members_cached
        res: List[UserWrapper] = []
        action = getattr(self, "action", None)
        if action and hasattr(action, "users"):
            for u in action.users:
                res.append(UserWrapper(u) if not isinstance(u, UserWrapper) else u)
        elif getattr(self, "user_added", False) or getattr(self, "user_joined", False):
            sender = getattr(self, "sender", None) or getattr(self, "from_user", None)
            if sender:
                res.append(sender if isinstance(sender, UserWrapper) else UserWrapper(sender))
        self._new_chat_members_cached = res
        return res

    @property
    def command_(self) -> Optional[str]:
        text = self.text or getattr(self, "raw_text", None) or getattr(self, "message", None) or ""
        if not text:
            return None
        try:
            return text.split()[0][1:].strip()
        except Exception:
            return None

    @property
    def raw_user_input(self) -> Optional[str]:
        msg = self.text or getattr(self, "raw_text", None) or getattr(self, "message", None) or ""
        if not msg:
            return None
        if " " in msg:
            return msg[msg.find(" ") + 1:].strip()
        return None

    @property
    def user_args(self) -> Args:
        if hasattr(self, "_user_args_override"):
            return self._user_args_override
        raw_user_input = self.raw_user_input
        if not raw_user_input:
            return Args()
        user_args = Args()
        matches = re.findall(r"-([a-zA-Z0-9_-]+)(?:\s+([^-][^\s]*))?", raw_user_input)
        for match in matches:
            arg_name = match[0]
            arg_val = match[1] if len(match) > 1 and match[1] else None
            user_args.append(Arg(arg_name, arg_val))
        return user_args

    @user_args.setter
    def user_args(self, val: Any) -> None:
        if isinstance(val, (list, tuple)):
            clean_args = Args()
            for v in val:
                if isinstance(v, Arg):
                    clean_args.append(v)
                elif isinstance(v, str):
                    clean_args.append(Arg(v.lstrip("-")))
            self._user_args_override = clean_args
        else:
            self._user_args_override = val

    @property
    def user_input(self) -> Optional[str]:
        if hasattr(self, "_user_input_override"):
            return self._user_input_override
        text_to_return = self.text
        if text_to_return is None or " " not in text_to_return:
            return None
        s_text = text_to_return.split(" ", 1)[1]
        final_text = s_text.split(" ")
        final_text_ = []
        for ft in final_text:
            if not ft.startswith("-"):
                final_text_.append(ft)
        res = " ".join(final_text_).strip()
        return res if res else None

    @user_input.setter
    def user_input(self, val: Optional[str]) -> None:
        self._user_input_override = val

    def strip_args(self, text_to_return: Optional[str]) -> Optional[str]:
        if text_to_return is None:
            return None
        words = text_to_return.split()
        return " ".join([w for w in words if not w.startswith("-")]).strip() or None

    async def handle_message(self, text: str, **kwargs) -> Any:
        """Edit message if sent by self/userbot, or reply if from sudo/bot."""
        import Main
        altruix = Main.Altruix
        sudo_users = getattr(altruix.config, "SUDO_USERS", [])
        is_bot = getattr(altruix, "bot_info", None) and getattr(self.client, "myself", None) and (
            self.client.myself.id == altruix.bot_info.id
        )

        sender_id = self.sender_id
        if is_bot or (sender_id and sender_id in sudo_users and not self.out):
            if self.reply_to_message:
                res = await self.reply_to_message.reply_msg(text, **kwargs)
            else:
                res = await self.reply_msg(text, **kwargs)
        else:
            res = await self.edit_msg(text, **kwargs)
        enriched = enrich_message(res, self.client)
        self._last_handled_msg = enriched
        return enriched

    async def edit_msg(
        self,
        text: str,
        force_paste: bool = False,
        force_file: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        del_in: Optional[int] = None,
        **args,
    ) -> Any:
        import Main
        from Main.utils.paste import Paste
        from Main.utils.essentials import Essentials
        from Main.utils.file_helpers import make_file_from_text

        altruix = Main.Altruix
        s_args = args.pop("string_args", None)
        if s_args is None and "args" in args:
            s_args = args.pop("args")

        str_val = altruix.get_string(text, string_args=s_args)
        if str_val is not None:
            text = str_val
        elif s_args is not None:
            with suppress_error(msg="edit_msg string formatting"):
                text = text.format(*s_args) if isinstance(s_args, (list, tuple)) else text.format(s_args)

        if force_paste:
            text_clean = Essentials.md_to_text(text)
            service, paste_link = await Paste(text_clean).paste()
            p_text = f"<b>OUTPUT ({service.title()}):</b> <a href='{paste_link}'>PREVIEW</a>"
            res = await self.edit(p_text, parse_mode="html", link_preview=False)
            enriched = enrich_message(res, self.client)
            self._last_handled_msg = enriched
            return enriched

        if force_file:
            caption = None
            if ";" in force_file:
                force_file, caption = force_file.split(";", 1)
            suffix = ".txt"
            if "." in force_file:
                force_file, ext = force_file.split(".", 1)
                suffix = f".{ext}"
            text_clean = Essentials.md_to_text(text)
            file_path = await make_file_from_text(text_clean, file_name=force_file, file_suffix=suffix)
            try:
                await self.delete()
                res = await self.client.send_file(
                    self.chat_id,
                    file_path,
                    caption=caption,
                    reply_to=reply_to_message_id or self.id,
                )
                enriched = enrich_message(res, self.client)
                self._last_handled_msg = enriched
                return enriched
            finally:
                if os.path.exists(file_path):
                    with suppress_error(msg="cleaning edit_msg force_file"):
                        os.remove(file_path)

        try:
            msg = await self.edit(text, parse_mode="html", link_preview=False)
        except errors.MessageTooLongError:
            text_clean = Essentials.md_to_text(text)
            service, paste_link = await Paste(text_clean).paste()
            p_text = f"<b>OUTPUT ({service.title()}):</b> <a href='{paste_link}'>PREVIEW</a>"
            msg = await self.edit(p_text, parse_mode="html", link_preview=False)
        except errors.MessageNotModifiedError:
            msg = self

        if del_in and isinstance(del_in, int):
            await asyncio.sleep(del_in)
            with suppress_error(msg="edit_msg auto delete"):
                await msg.delete()
        enriched = enrich_message(msg, self.client)
        self._last_handled_msg = enriched
        return enriched

    async def reply_msg(
        self,
        text: str,
        force_paste: bool = False,
        force_file: Optional[str] = None,
        del_in: Optional[int] = None,
        **args,
    ) -> Any:
        import Main
        from Main.utils.paste import Paste
        from Main.utils.essentials import Essentials
        from Main.utils.file_helpers import make_file_from_text

        altruix = Main.Altruix
        s_args = args.pop("string_args", None)
        if s_args is None and "args" in args:
            s_args = args.pop("args")

        str_val = altruix.get_string(text, string_args=s_args)
        if str_val is not None:
            text = str_val
        elif s_args is not None:
            with suppress_error(msg="reply_msg string formatting"):
                text = text.format(*s_args) if isinstance(s_args, (list, tuple)) else text.format(s_args)

        if force_paste:
            text_clean = Essentials.md_to_text(text)
            service, paste_link = await Paste(text_clean).paste()
            p_text = f"<b>OUTPUT ({service.title()}):</b> <a href='{paste_link}'>PREVIEW</a>"
            return await self.reply(p_text, parse_mode="html", link_preview=False)

        if force_file:
            caption = None
            if ";" in force_file:
                force_file, caption = force_file.split(";", 1)
            suffix = ".txt"
            if "." in force_file:
                force_file, ext = force_file.split(".", 1)
                suffix = f".{ext}"
            text_clean = Essentials.md_to_text(text)
            file_path = await make_file_from_text(text_clean, file_name=force_file, file_suffix=suffix)
            try:
                return await self.client.send_file(
                    self.chat_id,
                    file_path,
                    caption=caption,
                    reply_to=self.id,
                )
            finally:
                if os.path.exists(file_path):
                    with suppress_error(msg="cleaning reply_msg force_file"):
                        os.remove(file_path)

        try:
            msg = await self.reply(text, parse_mode="html", link_preview=False)
        except errors.MessageTooLongError:
            text_clean = Essentials.md_to_text(text)
            service, paste_link = await Paste(text_clean).paste()
            p_text = f"<b>OUTPUT ({service.title()}):</b> <a href='{paste_link}'>PREVIEW</a>"
            msg = await self.reply(p_text, parse_mode="html", link_preview=False)

        if del_in and isinstance(del_in, int):
            await asyncio.sleep(del_in)
            with suppress_error(msg="reply_msg auto delete"):
                await msg.delete()
        return enrich_message(msg, self.client)

    async def delete_msg(self, *args, **kwargs) -> Any:
        """Compatibility alias for delete() ensuring plugins calling delete_msg() succeed."""
        try:
            return await self.delete(*args, **kwargs)
        except Exception:
            return None

    async def reply_file(
        self,
        file_path: str,
        caption: Optional[str] = None,
        thumb: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        send_msg_if_file_invalid: bool = False,
        **kwargs,
    ) -> Any:
        kwargs.pop("quote", None)
        reply_to = reply_to_message_id or self.id
        try:
            res = await self.client.send_file(
                self.chat_id,
                file_path,
                caption=caption,
                thumb=thumb,
                reply_to=reply_to,
                parse_mode="html",
                **kwargs,
            )
            return enrich_message(res, self.client)
        except Exception as e:
            if send_msg_if_file_invalid and caption:
                return await self.reply_msg(caption)
            raise

    async def reply_voice(self, file_path: str, caption: Optional[str] = None, **kwargs) -> Any:
        kwargs.pop("quote", None)
        res = await self.client.send_file(
            self.chat_id,
            file_path,
            voice_note=True,
            caption=caption,
            reply_to=self.id,
            parse_mode="html",
            **kwargs,
        )
        return enrich_message(res, self.client)

    async def reply_document(self, file_path: str, caption: Optional[str] = None, **kwargs) -> Any:
        kwargs.pop("quote", None)
        res = await self.client.send_file(
            self.chat_id,
            file_path,
            force_document=True,
            caption=caption,
            reply_to=self.id,
            parse_mode="html",
            **kwargs,
        )
        return enrich_message(res, self.client)

    async def delete_if_self(self, **kwargs) -> Any:
        if self.out or (self.from_user and self.from_user.is_self):
            with suppress_error(msg="delete_if_self"):
                return await self.delete()

    async def delete_if_sudo(self, **kwargs) -> Any:
        import Main
        sudo = getattr(Main.Altruix.config, "SUDO_USERS", [])
        if self.out or (self.from_user and self.from_user.is_self):
            return
        if self.sender_id and self.sender_id in sudo:
            with suppress_error(msg="delete_if_sudo"):
                return await self.delete()

    @property
    def get_user(self) -> Tuple[Optional[Union[int, str]], Optional[str], Optional[bool]]:
        """Extract user, reason, is_channel."""
        text = self.user_input
        asplit = text.split(" ", 1) if text else None
        user_s = None
        reason_ = None
        is_channel = False

        if self.reply_to_message:
            reply = self.reply_to_message
            if reply.sender_id:
                user_s = reply.sender_id
            reason_ = text or None
        elif asplit and len(asplit[0]) > 0:
            target = asplit[0]
            user_s = int(target) if target.lstrip("-").isdigit() else target
            if len(asplit) == 2:
                reason_ = asplit[1]

        reason_ = self.strip_args(reason_) if reason_ else None
        return user_s, reason_, is_channel

    @property
    def extract_time(self) -> Tuple[Optional[datetime], Optional[str]]:
        msg_t = self.raw_user_input
        if not msg_t:
            return None, None
        match = re.search(r"-t(\d+)([mhd])", msg_t)
        if not match:
            return None, None
        num = int(match.group(1))
        unit = match.group(2)
        if unit == "d":
            sec = num * 86400
        elif unit == "h":
            sec = num * 3600
        elif unit == "m":
            sec = num * 60
        else:
            return None, None
        until = datetime.now(timezone.utc) + timedelta(seconds=sec)
        return until, f"{num}{unit}"

    async def copy(
        self,
        chat_id: Union[int, str],
        caption: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """Copy this message to another chat."""
        text = caption if caption is not None else (self.text or self.message or "")
        client = getattr(self, "client", None)
        if not client:
            import Main
            client = Main.Altruix.clients[0] if Main.Altruix.clients else None
        if not client:
            raise RuntimeError("No client available to copy message")

        if self.media:
            return await client.send_file(
                chat_id,
                file=self.media,
                caption=text,
                reply_to=reply_to_message_id,
            )
        return await client.send_message(
            chat_id,
            message=text,
            reply_to=reply_to_message_id,
        )



def enrich_message(event_or_message: Any, client: Any = None) -> Any:
    """Enrich a Telethon message or event with Altruix properties."""
    if event_or_message is None:
        return None
    if isinstance(event_or_message, (TelethonMessage, CustomMessage)):
        target = event_or_message
    elif hasattr(event_or_message, "message") and isinstance(event_or_message.message, (TelethonMessage, CustomMessage)):
        target = event_or_message.message
    else:
        target = event_or_message

    if isinstance(target, (TelethonMessage, CustomMessage)) and not isinstance(target, Message):
        with suppress_error(msg="enrich_message set __class__"):
            target.__class__ = Message

    cl = client or getattr(target, "_client", None) or getattr(event_or_message, "_client", None)
    if cl is not None:
        with suppress_error(msg="enrich_message set target _client"):
            target._client = cl
        with suppress_error(msg="enrich_message set event _client"):
            event_or_message._client = cl

    if hasattr(target, "_sender_cached") and getattr(target, "_sender_cached", None) is None:
        target._sender_cached = None
    if hasattr(target, "_chat_cached") and getattr(target, "_chat_cached", None) is None:
        target._chat_cached = None
    if hasattr(target, "_reply_to_cached") and getattr(target, "_reply_to_cached", None) is None:
        target._reply_to_cached = None
    return target


# Patch Altruix helper methods and properties onto Telethon message classes so raw instances also have them
for _cls in (TelethonMessage, CustomMessage):
    for _name in (
        "edit_msg", "reply_msg", "handle_message", "reply_file", "reply_voice",
        "reply_document", "delete_if_self", "delete_if_sudo", "user_args",
        "user_input", "raw_user_input", "command_", "from_user", "chat",
        "new_chat_members", "get_user", "extract_time", "copy", "strip_args",
        "chat_id", "sender_id", "reply_to_message", "get_reply_message", "reply_to_top_id", "reply_to_msg_id",
        "is_private", "is_group", "is_channel",
    ):
        _val = getattr(Message, _name, None)
        if _val is not None and not hasattr(_cls, _name):
            try:
                setattr(_cls, _name, _val)
            except Exception:
                pass
