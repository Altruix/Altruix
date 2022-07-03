# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import time
import logging
from Main import Altruix
from functools import wraps
from pyrogram import Client, filters
from Main.core.types.message import Message
from Main.plugins.userbot.channel_utils import digit_wrap


gban_db = Altruix.db.make_collection("Gbans")
USER_CHAT_CACHE = []


@Altruix.register_on_cmd(
    ["gban"], cmd_help={"help": "To globally ban a user", "example": "gban <userid>"}
)
async def gban(c: Client, m: Message):
    start_time = time.time()
    msg = await m.handle_message("PROCESSING")
    my_id = c.myself.id
    gbanned_users = [user async for user in gban_db.find({"client_id": my_id})]
    user_ids, reason, is_chnnl = m.get_user
    if is_chnnl:
        return await msg.edit_msg("INVALID_USER")
    if isinstance(digit_wrap(user_ids), int):
        user_id = int(user_ids)
        user_mention = f"[User](tg://user?id={user_ids})"
    else:
        try:
            user_obj = await c.get_users(user_ids)
            user_id, user_mention = user_obj.id, user_obj.mention
        except Exception:
            Altruix.log(level=40)
            return await msg.edit_msg("INVALID_USER")
    if user_id == my_id:
        return await msg.edit_msg("BAN_MYSELF_NOT_ALLOWDED")
    reason = reason or "NR"
    if user_id in gbanned_users:
        return await msg.edit_msg("ALREADY_GBANNED")
    await gban_db.insert_one(
        {"user_id": int(user_id), "reason": reason, "client_id": my_id}
    )
    if "--no-cache" not in m.user_args:
        chats = USER_CHAT_CACHE or await c.fetch_chats()
    else:
        chats = await c.fetch_chats()
    if len(chats) == 0:
        return await msg.edit_msg("NOT_ADMIN_IN_ANY_CHAT", user_mention)
    err = 0
    for chat in chats:
        try:
            await c.ban_chat_member(chat, int(user_id))
        except Exception:
            err += 1
    await msg.edit_msg(
            "GBANNED",
            string_args=(
                user_mention,
                (len(chats) - err),
                round(time.time() - start_time, 2),
            ),
        )


@Altruix.register_on_cmd(
    ["ungban"], cmd_help={"help": "To globally unban a user", "example": "ungban <userid>"}
)
async def ungban(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    my_id = c.myself.id
    user_ids, reason, is_chnnl = m.get_user
    if is_chnnl:
        return msg.edit_msg("INVALID_USER")
    if isinstance(digit_wrap(user_ids), int):
        user_id = int(user_ids)
        user_mention = f"[User](tg://user?id={user_ids})"
    else:
        try:
            user_obj = await c.get_users(user_ids)
            user_id, user_mention = user_obj.id, user_obj.mention
        except Exception:
            Altruix.log(level=40)
            return await msg.edit_msg("INVALID_USER")
    check = await gban_db.find_one({"user_id": int(user_id), "client_id": my_id})
    if not check:
        return await msg.edit_msg("USER_NOT_GBANNED")
    await gban_db.delete_one({"user_id": int(user_id), "client_id": my_id})
    if "--no-cache" not in m.user_args:
        chats = USER_CHAT_CACHE or await c.fetch_chats()
    else:
        chats = await c.fetch_chats()
    if len(chats) == 0:
        return await msg.edit_msg("NOT_ADMIN_IN_ANY_CHAT", user_mention)
    err = 0
    for chat in chats:
        try:
            await c.unban_chat_member(chat, int(user_id))
        except Exception:
            err += 1
    await msg.edit_msg(
            "UNGBANNED",
            string_args=(user_mention, err, len(chats), (len(chats) - err)),
        )

GBANNED_CACHE = {}

async def check_gbanned(user_, my_id):
    if GBANNED_CACHE.get(my_id) and user_ in GBANNED_CACHE.get(my_id):
        return True
    _checks_ = await gban_db.find_one({"user_id": user_, "client_id": my_id})
    check_result = bool(_checks_)
    if check_result:
        if my_id not in GBANNED_CACHE:
            GBANNED_CACHE[my_id] = []
        GBANNED_CACHE[my_id].append(user_)
    return bool(_checks_)

def is_gbanned(func):
    @wraps(func)
    async def is_g_banned(c, m):
        my_id = c.myself.id
        if m and m.from_user and m.from_user.id:
            user_ = int(m.from_user.id)
            if await check_gbanned(user_, my_id):
                return await func(c, m)
        return False
    return is_g_banned

@Altruix.on_message((filters.group | filters.channel) & ~filters.private, group=2)
@is_gbanned
async def gwatch_(c: Client, m: Message):
    user_id = int(m.from_user.id)
    try:
        await c.kick_chat_member(m.chat.id, user_id)
    except Exception as e:
        return Altruix.log(
            f"ERROR : Unable to kick gbanned user! \nError : [{e}]", level=logging.DEBUG
        )
    if await Altruix.config.get_env("ENABLE_GLOGS") and Altruix.log_chat:
        chat_ = m.chat.username or m.chat.id
        gbanned_ = await Altruix.get_string(
            "GBANNED_USER_JOINED", args=(m.from_user.mention, chat_, m.id)
        )
        await c.send_message(Altruix.log_chat, gbanned_)
