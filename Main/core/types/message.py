# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import asyncio
import contextlib
from Main import Altruix
from typing import Tuple, Union
from dataclasses import dataclass
from Main.utils.paste import Paste
from datetime import datetime, timedelta
from pyrogram.utils import zero_datetime
from pyrogram.errors import MessageTooLong
from Main.utils.essentials import Essentials
from ...utils.startup_helpers import monkeypatch
from pyrogram.types import Message as RawMessage
from Main.utils.file_helpers import make_file_from_text


class REGEX_STRINGS(object):
    ARGS_REGEX = r"(-[a-zA-Z]+)([0-9]*)$"


@dataclass
class Arg:
    key: str
    value: str


class Args(list):
    def __init__(self, *args):
        super(Args, self).__init__(args)

    def __contains__(self, key):
        return key in [x.key for x in self]

    def __getattr__(self, key):
        return {x.key: x.value for x in self}.get(key)


@monkeypatch(RawMessage)
class Message:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def reply_file(
        self,
        file_path: str,
        thumb=None,
        quote=None,
        reply_to_message_id=None,
        send_msg_if_file_invalid=False,
        *args,
        **kwargs,
    ):
        if quote is None:
            quote = self.chat.type != "private"

        if reply_to_message_id is None and quote:
            reply_to_message_id = self.id
        if send_msg_if_file_invalid and (kwargs.get("caption")):
            try:
                return await self._client.send_file(
                    self.chat.id,
                    file_path,
                    thumb=thumb,
                    reply_to_message_id=reply_to_message_id,
                    *args,
                    **kwargs,
                )
            except Exception:
                Altruix.log()
                return await self.reply(kwargs.get("caption"))
        return await self._client.send_file(
            self.chat.id,
            file_path,
            thumb=thumb,
            reply_to_message_id=reply_to_message_id,
            *args,
            **kwargs,
        )

    @property
    def command_(self):
        try:
            self.text.split()[0][
                1:
            ].strip() if self.text and " " in self.text else self.text[1:].strip()
        except (IndexError or AttributeError):
            return None

    @property
    def user_args(self) -> Args[Arg]:
        raw_user_input = self.raw_user_input
        if raw_user_input is None:
            return []
        user_args: Args[Arg] = Args()
        matches = re.findall(r"-(\w+ ?.*?(?=-)|\w+)?|\w+", raw_user_input)
        for match in matches:
            if not match:
                continue
            splitted = match.split(" ", 1)
            arg_name = splitted[0]
            arg_value = None
            if len(splitted) > 1:
                arg_value = splitted[1]
            user_args.append(Arg(arg_name, arg_value))
        return user_args

    async def edit_msg(
        self,
        text,
        force_paste=False,
        force_file=None,
        reply_to_message_id=None,
        ttwp=None,
        del_in=None,
        **args,
    ):
        headers = ttwp or "<b>OUTPUT</b>"
        reply_to_message_id = reply_to_message_id or self.id
        if txt := Altruix.get_string(text):
            if "string_args" in args:
                s_args = args.get("string_args")
                del args["string_args"]
                text = Altruix.get_string(text, s_args)
            else:
                text = txt
        if force_paste:
            text = Essentials.md_to_text(text)
            service, paste_link = await Paste(text).paste()
            _p = f"{headers.format(service.title())} : <b><a href='{paste_link}'>PREVIEW</a></b>"
            return await self.edit(_p, disable_web_page_preview=True, **args)
        if force_file:
            if ";" in force_file:
                force_file, caption = force_file.split(";", 1)
            force_file, file_suffix = force_file.split(".", 1)
            text = Essentials.md_to_text(text)
            file_ = await make_file_from_text(
                text, file_name=force_file, file_suffix=file_suffix
            )
            return await asyncio.gather(
                self.delete(),
                self._client.send_document(
                    self.chat.id,
                    file_,
                    reply_to_message_id=reply_to_message_id,
                    caption=caption,
                    **args,
                ),
            )
        try:
            msg_ = await self.edit(text, **args)
        except MessageTooLong:
            text = Essentials.md_to_text(text)
            service, paste_link = await Paste(text).paste()
            _p = f"{headers.format(service.title())} : <b><a href='{paste_link}'>PREVIEW</a></b>"
            msg_ = await self.edit(_p, disable_web_page_preview=True, **args)
        if del_in and isinstance(del_in, int):
            await asyncio.sleep(del_in)
            await msg_.delete()
        return msg_

    async def _delete(self, *args, **kwargs):
        with contextlib.suppress(Exception):
            await self.delete(*args, **kwargs)
        return self

    async def reply_msg(
        self,
        text,
        force_paste=False,
        force_file=None,
        ttwp=None,
        del_in=None,
        **args,
    ):
        headers = ttwp or "<b>OUTPUT</b>"
        if txt := Altruix.get_string(text):
            if "string_args" in args:
                s_args = args.get("string_args")
                del args["string_args"]
                text = Altruix.get_string(text, s_args)
            else:
                text = txt
        if force_paste:
            text = Essentials.md_to_text(text)
            service, paste_link = await Paste(text).paste()
            _p = f"{headers.format(service.title())} : <b><a href='{paste_link}'>PREVIEW</a></b>"
            return await self.reply(
                _p, quote=True, disable_web_page_preview=True, **args
            )
        if force_file:
            if ";" in force_file:
                force_file, caption = force_file.split(";", 1)
            force_file, file_suffix = force_file.split(".", 1)
            text = Essentials.md_to_text(text)
            file_ = await make_file_from_text(
                text, file_name=force_file, file_suffix=file_suffix
            )
            return await self.reply_document(file_, quote=True, caption=caption, **args)
        try:
            msg_ = await self.reply(text, quote=True, **args)
        except MessageTooLong:
            text = Essentials.md_to_text(text)
            service, paste_link = await Paste(text).paste()
            _p = f"{headers.format(service.title())} : <b><a href='{paste_link}'>PREVIEW</a></b>"
            msg_ = await self.reply(_p, disable_web_page_preview=True, **args)
        if del_in and isinstance(del_in, int):
            await asyncio.sleep(del_in)
            await msg_.delete()
        return msg_

    async def handle_message(self, text_, **kwargs):
        sudo_users = Altruix.config.SUDO_USERS
        if self._client.myself.id == Altruix.bot_info.id:
            return await self.reply_msg(text_, **kwargs)
        if not self:
            return await self.edit_msg(text_, **kwargs)
        if not self.from_user or not self.from_user.id:
            return await self.edit_msg(text_, **kwargs)
        if int(self.from_user.id) in sudo_users:
            if self.reply_to_message:
                return await self.reply_to_message.reply_msg(text_, **kwargs)
            return await self.reply_msg(text_, **kwargs)
        return await self.edit_msg(text_, **kwargs)

    async def delete_if_self(self, **kwargs):
        if self.from_user and self.from_user.is_self or self.outgoing:
            return await self.delete(**kwargs)

    async def delete_if_sudo(self, **kwargs):
        sudo_ = Altruix.config.SUDO_USERS
        if self.from_user and self.from_user.is_self:
            return
        if self.from_user and self.from_user.id in sudo_:
            return await self.delete(**kwargs)

    @property
    def user_input(self):
        text_to_return = self.text
        if text_to_return is None:
            return text_to_return
        if " " in text_to_return:
            s_text = text_to_return.split(" ", 1)[1]
            final_text = s_text.split(" ")
            final_text_ = ""
            for ft in final_text:
                stripContext = re.sub(REGEX_STRINGS.ARGS_REGEX, "", ft)
                if stripContext != "":
                    final_text_ += f"{stripContext} "
            ft = final_text_.strip()
            return ft

    def strip_args(self, text_to_return):
        if text_to_return is None:
            return text_to_return
        if " " in text_to_return:
            s_text = text_to_return.split(" ", 1)[1]
            final_text = s_text.split(" ")
            final_text_ = ""
            for ft in final_text:
                stripContext = re.sub(REGEX_STRINGS.ARGS_REGEX, "", ft)
                if stripContext != "":
                    final_text_ += f"{stripContext} "
            return final_text_

    @property
    def raw_user_input(self):
        msg = self.text
        if not msg:
            return None
        if " " in msg:
            return msg[msg.find(" ") + 1 :]

    async def edit_and_del(self, text, del_in=5, **args):
        _m_ = await self.edit(text, **args)
        await asyncio.sleep(del_in)
        await _m_.delete()

    @property
    def get_user(self) -> Union[Tuple[Union[int, str]], None]:
        """Extract User for that event
        Returns:
            Union[Tuple[Union[int, str]], None]: Returns User Object and String (Reason)
        """
        text = self.user_input
        asplit = None if text is None else text.split(" ", 1)
        user_s = None
        reason_ = None
        is_chnnl = None
        if self.reply_to_message:
            if self.reply_to_message.from_user:
                user_s = self.reply_to_message.from_user.id
                is_chnnl = False
            if (
                not self.reply_to_message.from_user
                and self.reply_to_message.sender_chat.id
            ):
                user_s = self.reply_to_message.sender_chat.id
                is_chnnl = True
            reason_ = text or None
        elif asplit is None:
            return None, None, None
        elif len(asplit[0]) > 0:
            if self.entities:
                if len(self.entities) == 1:
                    required_entity = self.entities[0]
                    if required_entity.type == "text_mention":
                        user_s = int(required_entity.user.id)
                    else:
                        user_s = int(asplit[0]) if asplit[0].isdigit() else asplit[0]
            else:
                user_s = int(asplit[0]) if asplit[0].isdigit() else asplit[0]
            is_chnnl = False
            if len(asplit) == 2:
                reason_ = asplit[1]
        reason_ = self.strip_args(reason_) if reason_ else None
        return user_s, reason_, is_chnnl

    @property
    def extract_time(self):
        msg_t = self.raw_user_input
        arg_regex = r"-t(\d+)(m|d|h)"
        if msg_t is None:
            return zero_datetime(), None
        time_val = str(
            (
                re.match(arg_regex, str(msg_t))[0].split("-t")[1]
                if re.match(arg_regex, str(msg_t))
                else 0
            )
        )
        if not any(time_val.endswith(unit) for unit in ("m", "h", "d")):
            return zero_datetime(), None
        unit = time_val[-1]
        time_num = time_val[:-1]
        if not time_num.isdigit():
            return zero_datetime(), None
        if unit == "d":
            bantime = int(time_num) * (24 * 60 * 60)
        elif unit == "h":
            bantime = int(time_num) * (60 * 60)
        elif unit == "m":
            bantime = int(time_num) * 60
        return int(datetime.now() + timedelta(seconds=bantime)), time_val
