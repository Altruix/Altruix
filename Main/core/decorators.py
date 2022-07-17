# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import traceback
from Main import Altruix
from typing import Union
from functools import wraps
from Main.internals.set_inline import set_inline_in_botfather
from pyrogram.types import Message, InlineQuery, CallbackQuery
from pyrogram import Client, StopPropagation, ContinuePropagation
from pyrogram.errors import (
    MessageEmpty, MessageIdInvalid, BotInlineDisabled, MessageNotModified,
    UserNotParticipant)


def inline_check(func):
    @wraps(func)
    async def check_inline(c: Client, m: Message, *args, **kwargs):
        try:
            return await func(c, m)
        except BotInlineDisabled:
            status = await m.handle_message("INLINE_DISABLED")
            await set_inline_in_botfather(c)
            await status.delete()
            return await func(c, m)

    return check_inline


def check_perm(perm_type, return_perm=False):
    def check_perm_s(func):
        async def perm_check(client, m):
            if m.chat.type in ["bot", "private"]:
                return await func(client, m)
            if isinstance(perm_type, list):
                s = {}
                for i in perm_type:
                    s[perm_type] = await client.check_my_perm(m, i)[0]
                if all(element is False for element in s.values()):
                    return await func(client, m)
                not_true_ = [str(v) for v in s.values() if v is False]
                not_true_m = "".join(f"{i} " for i in not_true_)
                return await m.handle_message(
                    "ADMIN_ACTION_FAILED", string_args=(not_true_m)
                )
            else:
                perm_result = await client.check_my_perm(m, perm_type)
                if return_perm:
                    return (
                        await func(client, m, perm_result[1])
                        if perm_result[0]
                        else await m.handle_message(
                            "ADMIN_ACTION_FAILED", string_args=(perm_type)
                        )
                    )
                return (
                    await func(client, m)
                    if perm_result[0]
                    else await m.handle_message(
                        "ADMIN_ACTION_FAILED", string_args=(perm_type)
                    )
                )

        return perm_check

    return check_perm_s


def iuser_check(func):
    """Allow only authorized users to send a callback query or inline query."""

    async def wrapper(client, update: Union[CallbackQuery, InlineQuery]):
        users = Altruix.auth_users
        if update.from_user and update.from_user.id in users:
            try:
                return await func(client, update)
            except MessageNotModified:
                await update.answer("🤔🧐😳🙄😬🤭😶‍🌫️")
        elif isinstance(update, CallbackQuery):
            await update.answer(
                "You are not authorized to use me.",
                cache_time=0,
                show_alert=True,
            )
        else:
            await update.answer(
                [],
                cache_time=0,
                is_personal=True,
                switch_pm_text="You are not authorized to use me.",
                switch_pm_parameter="auth",
            )

    return wrapper


def log_errors(func):
    """Log exceptions."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except StopPropagation as e:
            raise StopPropagation from e
        except (
            MessageNotModified,
            MessageIdInvalid,
            UserNotParticipant,
            MessageEmpty,
        ):
            pass
        except ContinuePropagation as e:
            raise ContinuePropagation from e
        except Exception as _be:
            try:
                await Altruix.bot.send_message(
                    Altruix.log_chat or Altruix.config.OWNER_ID,
                    f"<b>AN ERROR OCCURRED:</b>\nException: <i>{_be}</i>\nOccurred in: <code>{func.__name__}</code>\n\n<code>{traceback.format_exc()}</code>",
                )
            except Exception as e:
                raise _be from e

    return wrapper
