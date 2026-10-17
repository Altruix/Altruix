# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import time
import uuid
from typing import Dict, Any, Optional
from Main import Altruix
from Main.core.decorators import log_errors
from Main.utils.custom_filters import filters
from Main.utils.suppress import suppress_error
from Main.plugins.userbot.channel_utils import digit_wrap
from telethon import custom

# In-memory fast cache (backed by database)
MSGS_DICT: Dict[str, Dict[str, Any]] = {}
WHISPER_MAX_TTL = 86400  # 1 day max TTL in seconds


@Altruix.bot.on_inline_query(filters.regex(r"^whisper"))
@log_errors
async def whisper(c, iq):
    query = iq.text or ""
    if " " not in query:
        return
    text = (query.split("whisper ", 1)[1]).strip()
    if not text or "," not in text or (len(text.split(",", 1)) != 2):
        return

    _id = str(uuid.uuid4().hex[:16])
    user, msg = text.split(",", 1)
    user = digit_wrap(user.strip())
    user_trail = user
    if isinstance(user, int):
        user_trail = f"[User](tg://user?id={user})"
    elif not str(user).startswith("@"):
        user_trail = f"@{user}"

    now = time.time()
    expires_at = now + WHISPER_MAX_TTL
    whisper_data = {
        "_id": _id,
        "user": user,
        "msg": msg.strip(),
        "sender_id": getattr(iq, "sender_id", None),
        "created_at": now,
        "expires_at": expires_at,
    }

    # Fast memory cache
    MSGS_DICT[_id] = whisper_data

    # Multi-Database Persistence (SQLite / Postgres / Mongo)
    if Altruix.db is not None:
        with suppress_error(msg="Persisting whisper to DB"):
            await Altruix.db["WHISPERS"].insert_one(dict(whisper_data))

    builder = iq.builder
    w_text = Altruix.get_string("WHISPER", user=user_trail) or (
        f"<b>A Whisper Has Been Sent For {user_trail}</b>\n"
        "Click Below To Check Message!\n"
        "<i>Note: Only the recipient (or sender) can open it! (Expires in 24 hours)</i>"
    )
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
    _id = str(match.group(1))

    # 1. Fetch from memory or fallback to database
    msg_dict = MSGS_DICT.get(_id)
    if not msg_dict and Altruix.db is not None:
        try:
            msg_dict = await Altruix.db["WHISPERS"].find_one({"_id": _id})
            if msg_dict:
                MSGS_DICT[_id] = msg_dict
        except Exception:
            pass

    if not msg_dict:
        return await cq.answer(Altruix.get_string("CACHE_LOST") or "Whisper expired or not found.", alert=True)

    # 2. Check 1-Day TTL expiration
    expires_at = msg_dict.get("expires_at", 0)
    now = time.time()
    if expires_at and now > expires_at:
        MSGS_DICT.pop(_id, None)
        if Altruix.db is not None:
            with suppress_error():
                await Altruix.db["WHISPERS"].delete_one({"_id": _id})
        return await cq.answer("⏳ This whisper has expired (max 1 day TTL).", alert=True)

    user_id_or_username = digit_wrap(msg_dict.get("user"))
    MSG = msg_dict.get("msg")
    sender_id = cq.sender_id
    creator_id = msg_dict.get("sender_id")

    # 3. Access authorization check
    if sender_id in Altruix.auth_users or (creator_id and sender_id == creator_id):
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
