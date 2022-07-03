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
from Main import Altruix
from typing import Union
from Main.core.config import Config
from pyrogram import Client, filters
from pyrogram.types import Chat, Message
from ...core.types.message import Message as MMessage
from pyrogram.errors.exceptions.forbidden_403 import ChatAdminRequired
from pyrogram.errors.exceptions.bad_request_400 import (
    PeerIdInvalid, UsernameInvalid)


auto_post_db = Altruix.db.make_collection("auto_post_s")
auto_post_cache = Config.AUTOPOST_CACHE


def digit_wrap(digit_: str) -> Union[str, int]:
    try:
        return int(digit_)
    except ValueError:
        return digit_


@Altruix.register_on_cmd(
    "transfer",
    cmd_help={
        "help": "Transfer channel contents from one to another",
        "example": "transfer @warner_stark @tenet",
    },
    requires_input=True,
)
async def fast_transfer(c: Client, m: Union[Message, MMessage]):
    _m: Message = await m.handle_message("PROCESSING")
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
        async for message_ in c.get_chat_history(from_transfer):
            if message_.service:
                continue
            if "-onlyimg" in _args_m and not message_.photo:
                continue
            if "-onlyvid" in _args_m and not message_.video:
                continue
            if "-onlyaud" in _args_m and not message_.audio:
                continue
            if "-onlydoc" in _args_m and not message_.document:
                continue
            if "-onlytxt" in _args_m and not message_.text:
                continue
            if "-onlygif" in _args_m and not message_.animation:
                continue
            if "-onlysticker" in _args_m and not message_.sticker:
                continue
            if "-onlyvoice" in _args_m and not message_.voice:
                continue
            if "-onlycontact" in _args_m and not message_.contact:
                continue
            try:
                await message_.copy(transfer_to)
                await asyncio.sleep(random.randint(1, 3))
                count_of_ss += 1
            except ChatAdminRequired:
                return await _m.edit_msg("CHAT_ADMIN_REQUIRED")
            except UsernameInvalid:
                return await _m.edit_msg("INVALID_CHAT_ID")
            except PeerIdInvalid:
                return await _m.edit_msg("INVALID_CHAT_ID")
            except Exception as e:
                try:
                    await _m.edit_msg(f"<code>{message_.id}</code>: <code>{e}</code>")
                except Exception:
                    logging.error(e)
                continue
    except Exception as e:
        return await _m.edit_msg("FAILED_TRANSFER", string_args=(str(e)))
    await _m.edit_msg(
        "TRANSFER_SUCCESS", string_args=(from_transfer, transfer_to, count_of_ss)
    )


@Altruix.register_on_cmd(
    "add_autopost",
    cmd_help={
        "help": "Adds an auto post to the database!",
        "example": "add_autopost -100xxxx",
    },
    requires_input=True,
)
async def add_autopost_func(c: Client, m: Union[Message, MMessage]):
    msg_ = await m.handle_message("PROCESSING")
    if m.chat.type == "private":
        return await m.edit_msg("INVALID_CHAT_ID")
    chat_ = digit_wrap(m.user_input)
    try:
        chat_obj: Chat = await c.get_group(chat_)
    except Exception:
        return await msg_.edit_msg("AUTOPOST_FAILED_CINVALID", string_args=(chat_))
    if chat_obj.type == "private":
        return await m.edit_msg("INVALID_CHAT_ID")
    if await auto_post_db.find_one(
        {"client_id": c.myself.id, "from_chat": m.chat.id, "to_chat": chat_obj.id}
    ):
        return await msg_.edit_msg("ALREADY_AUTOPOST")
    await auto_post_db.insert_one(
        {"client_id": c.myself.id, "from_chat": m.chat.id, "to_chat": chat_obj.id}
    )
    if c.myself.id not in auto_post_cache:
        auto_post_cache[c.myself.id] = {}
    if auto_post_cache[c.myself.id].get(m.chat.id):
        auto_post_cache[c.myself.id][m.chat.id].append(chat_obj.id)
    else:
        auto_post_cache[c.myself.id][m.chat.id] = [chat_obj.id]
    await msg_.edit_msg("AUTOPOST_ADDED")


@Altruix.register_on_cmd(
    "rm_autopost",
    cmd_help={
        "help": "removes an auto post to the database!",
        "example": "rm_autopost -100xxxx",
    },
    requires_input=True,
)
async def rm_autopost_func(c: Client, m: Union[Message, MMessage]):
    msg_ = await m.handle_message("PROCESSING")
    if m.chat.type == "private":
        return await m.edit_msg("INVALID_CHAT_ID")
    chat_ = m.user_input
    try:
        chat_obj = await c.get_group(chat_)
    except Exception:
        return await msg_.edit_msg("AUTOPOST_FAILED_CINVALID", string_args=(chat_))
    if not (
        await auto_post_db.find_one(
            {"client_id": c.myself.id, "from_chat": m.chat.id, "to_chat": chat_obj.id}
        )
    ):
        return await msg_.edit_msg("NOT_IN_AUTOPOST")
    await auto_post_db.delete_one(
        {"client_id": c.myself.id, "from_chat": m.chat.id, "to_chat": chat_obj.id}
    )
    if (
        auto_post_cache.get(c.myself.id)
        and auto_post_cache.get(c.myself.id).get(m.chat.id)
        and chat_obj.id in auto_post_cache.get(c.myself.id).get(m.chat.id)
    ):
        auto_post_cache[c.myself.id][m.chat.id].remove(chat_obj.id)
    await msg_.edit_msg("AUTOPOST_REMOVED")


@Altruix.on_message(~filters.private & ~filters.via_bot, 5)
async def auto_poster(c, m: Union[Message, MMessage]):
    if not auto_post_cache.get(c.myself.id) or not auto_post_cache.get(c.myself.id).get(
        m.chat.id
    ):
        return
    for chat in auto_post_cache.get(c.myself.id).get(m.chat.id):
        try:
            await m.copy(chat)
        except ChatAdminRequired:
            logging.critical(
                f"You are not an admin for {chat}. removing chat from database to avoid mass errors."
            )
            await auto_post_db.delete_one(
                {"client_id": c.myself.id, "from_chat": m.chat.id, "to_chat": chat}
            )
            auto_post_cache[c.myself.id][m.chat.id].remove(chat)
        except Exception:
            Altruix.log()
        continue
