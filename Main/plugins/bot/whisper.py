# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import uuid
from Main import Altruix
from Main.core.decorators import log_errors
from Main.utils.custom_filters import filters
from Main.plugins.userbot.channel_utils import digit_wrap
from telethon import custom


MSGS_DICT = {}


@Altruix.bot.on_inline_query(filters.regex(r"^whisper"))
@log_errors
async def whisper(c, iq):
    query = iq.text or ""
    if " " not in query:
        return
    text = (query.split("whisper ", 1)[1]).strip()
    if not text or "," not in text or (len(text.split(",", 1)) != 2):
        return
    _id = uuid.uuid1().int
    user, msg = text.split(",", 1)
    user = digit_wrap(user.strip())
    user_trail = user
    if isinstance(user, int):
        user_trail = f"[User](tg://user?id={user})"
    elif not str(user).startswith("@"):
        user_trail = f"@{user}"
    MSGS_DICT[int(_id)] = dict(user=user, msg=msg.strip())

    builder = iq.builder
    w_text = Altruix.get_string("WHISPER", user=user_trail) or f"<b>A Whisper Has Been Sent For {user_trail}</b>\nClick Below To Check Message!\n<i>Note: Only the recipient can open it!</i>"
    result = builder.article(
        title=f"Whisper to {user_trail}",
        text=w_text,
        parse_mode="html",
        buttons=[[custom.Button.inline("Show Message", f"whisper_{_id}".encode("utf-8"))]],
    )
    await iq.answer([result])


@Altruix.bot.on_callback_query(filters.regex(r"^whisper_(.*)"))
@log_errors
async def whisper_callback(c, cq):
    data_str = cq.data.decode("utf-8") if isinstance(cq.data, bytes) else str(cq.data)
    match = re.search(r"^whisper_(.*)", data_str)
    if not match:
        return
    _id = digit_wrap(match.group(1))
    if _id not in MSGS_DICT:
        return await cq.answer(Altruix.get_string("CACHE_LOST") or "Whisper expired or lost.", alert=True)
    msg_dict = MSGS_DICT[_id]
    user_id_or_username = digit_wrap(msg_dict.get("user"))
    MSG = msg_dict.get("msg")
    sender_id = cq.sender_id

    if sender_id in Altruix.auth_users:
        return await cq.answer(MSG, alert=True)
    if isinstance(user_id_or_username, int):
        if sender_id == int(user_id_or_username):
            return await cq.answer(MSG, alert=True)
    elif hasattr(cq, "sender") and getattr(cq.sender, "username", None):
        uname = cq.sender.username.lstrip("@")
        target_name = str(user_id_or_username).lstrip("@")
        if uname.lower() == target_name.lower():
            return await cq.answer(MSG, alert=True)
    await cq.answer(Altruix.get_string("WHISPER_INVALID_USER") or "You are not authorized to view this whisper.", alert=True)
