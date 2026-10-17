# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import random
import asyncio
import logging
import contextlib
from Main import Altruix
from Main.utils.suppress import suppress_error
from typing import Union, Any
from Main.core.config import Config
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from telethon import errors


logger = logging.getLogger("altruix.channel_utils")


def digit_wrap(digit_: Any) -> Union[str, int]:
    try:
        val = str(digit_).strip()
        if val.lstrip("-").isdigit():
            return int(val)
        return digit_
    except Exception:
        return digit_


@Altruix.register_on_cmd(
    "transfer",
    cmd_help={
        "help": "Transfer channel contents from one to another",
        "example": "transfer @source_channel @target_channel",
    },
    requires_input=True,
)
async def fast_transfer(c: Client, m: Message):
    _m = await m.handle_message("PROCESSING")
    input_ = m.user_input.strip().split(" ", 1)
    if len(input_) == 1:
        transfer_to = digit_wrap(m.chat.id)
        from_transfer = digit_wrap(input_[0])
    else:
        from_transfer = digit_wrap(input_[0])
        transfer_to = digit_wrap(input_[1])
    _args_m = m.user_args
    if from_transfer == transfer_to:
        return await _m.edit_msg("ILLEGAL_TRANSFER")

    count_of_ss = 0
    try:
        async for message_ in c.iter_messages(from_transfer):
            if not message_ or getattr(message_, "action", None):
                continue
            if "-onlyimg" in _args_m and not message_.photo:
                continue
            if "-onlyvid" in _args_m and not message_.video:
                continue
            if "-onlydoc" in _args_m and not message_.document:
                continue
            if "-onlytxt" in _args_m and not message_.text:
                continue
            try:
                await c.send_message(transfer_to, message_)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                count_of_ss += 1
            except errors.ChatAdminRequiredError:
                return await _m.edit_msg("CHAT_ADMIN_REQUIRED")
            except (errors.UsernameInvalidError, errors.PeerIdInvalidError):
                return await _m.edit_msg("INVALID_CHAT_ID")
            except Exception as e:
                logger.error(f"Error copying message {message_.id}: {e}")
                continue
    except Exception as e:
        return await _m.edit_msg("FAILED_TRANSFER", string_args=(str(e),))

    await _m.edit_msg(
        "TRANSFER_SUCCESS", string_args=(str(from_transfer), str(transfer_to), count_of_ss)
    )


@Altruix.register_on_cmd(
    "add_autopost",
    cmd_help={
        "help": "Adds an auto post to the database!",
        "example": "add_autopost -100xxxx",
    },
    requires_input=True,
)
async def add_autopost_func(c: Client, m: Message):
    msg_ = await m.handle_message("PROCESSING")
    if getattr(m, "is_private", False) or getattr(m.chat, "type", "") == "private":
        return await m.edit_msg("INVALID_CHAT_ID")
    chat_ = digit_wrap(m.user_input)
    try:
        chat_obj = await c.get_entity(chat_)
    except Exception:
        return await msg_.edit_msg("AUTOPOST_FAILED_CINVALID", string_args=(str(chat_),))

    if Altruix.db is None:
        return await msg_.edit_msg("No database connected.")

    auto_post_db = Altruix.db.make_collection("auto_post_s")
    target_id = getattr(chat_obj, "id", chat_)
    curr_chat_id = m.chat_id or getattr(m.chat, "id", None)
    if await auto_post_db.find_one(
        {"client_id": c.myself.id, "from_chat": curr_chat_id, "to_chat": target_id}
    ):
        return await msg_.edit_msg("ALREADY_AUTOPOST")

    await auto_post_db.insert_one(
        {"client_id": c.myself.id, "from_chat": curr_chat_id, "to_chat": target_id}
    )
    if c.myself.id not in Config.AUTOPOST_CACHE:
        Config.AUTOPOST_CACHE[c.myself.id] = {}
    if Config.AUTOPOST_CACHE[c.myself.id].get(curr_chat_id):
        Config.AUTOPOST_CACHE[c.myself.id][curr_chat_id].append(target_id)
    else:
        Config.AUTOPOST_CACHE[c.myself.id][curr_chat_id] = [target_id]
    await msg_.edit_msg("AUTOPOST_ADDED")


@Altruix.register_on_cmd(
    "rm_autopost",
    cmd_help={
        "help": "Removes an auto post from the database!",
        "example": "rm_autopost -100xxxx",
    },
    requires_input=True,
)
async def rm_autopost_func(c: Client, m: Message):
    msg_ = await m.handle_message("PROCESSING")
    chat_ = digit_wrap(m.user_input)
    if Altruix.db is None:
        return await msg_.edit_msg("No database connected.")
    curr_chat_id = m.chat_id or getattr(m.chat, "id", None)
    auto_post_db = Altruix.db.make_collection("auto_post_s")
    await auto_post_db.delete_one({"client_id": c.myself.id, "from_chat": curr_chat_id, "to_chat": chat_})
    if c.myself.id in Config.AUTOPOST_CACHE and curr_chat_id in Config.AUTOPOST_CACHE[c.myself.id]:
        with suppress_error(ValueError, msg="Removing chat from AUTOPOST_CACHE"):
            Config.AUTOPOST_CACHE[c.myself.id][curr_chat_id].remove(chat_)
    await msg_.edit_msg("AUTOPOST_REMOVED")
