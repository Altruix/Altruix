# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import contextlib
from Main import Altruix
from Main.utils.suppress import suppress_error
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.utils.custom_filters import filters
from telethon import functions


pm_permit_warning_cache = {}
__last_message_cache = {}


@Altruix.register_on_cmd(
    "approve",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Approves the targeted user!",
        "example": "approve @username",
    },
)
async def approve_user_pm_permit_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user_ = m.chat_id or getattr(m.chat, "id", None)
    if not await Altruix.config.get_pm_sts():
        return await m.edit("<code>PM permit is disabled</code>", parse_mode="html")

    if not (getattr(m, "is_private", False) or getattr(m.chat, "type", "") == "private"):
        user_, _, is_channel = m.get_user
        if is_channel or not user_:
            return await msg.edit_msg("INVALID_USER")

    try:
        user_obj = await c.get_users(user_)
    except Exception:
        user_obj = None

    if not user_obj:
        return await msg.edit_msg("INVALID_USER")

    user_id = user_obj.id
    if Altruix.db is not None:
        pm_permit_col = Altruix.db.make_collection("pm_permit")
        user_info = await pm_permit_col.find_one({"user_id": user_id})
        if not user_info:
            await pm_permit_col.insert_one({"user_id": user_id, "approved": True})
        else:
            if user_info.get("approved", False):
                return await msg.edit_msg("ALREADY_APPROVED")
            await pm_permit_col.update_one({"user_id": user_id}, {"$set": {"approved": True}})

    mention = getattr(user_obj, "mention", str(user_id))
    await msg.edit_msg("APPROVED", string_args=(mention,))


@Altruix.register_on_cmd(
    "disapprove",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Disapproves the targeted user!",
        "example": "disapprove @username",
    },
)
async def disapprove_user_pm_permit_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user_ = m.chat_id or getattr(m.chat, "id", None)
    if not await Altruix.config.get_pm_sts():
        if Altruix.log_chat:
            await c.send_message(
                Altruix.log_chat,
                "**#DISAPPROVE**\n\nStatus: `Can't Disapprove!`\n\n**Reason:** `PM Security is Disabled!`",
            )
        return

    if not (getattr(m, "is_private", False) or getattr(m.chat, "type", "") == "private"):
        user_, _, is_channel = m.get_user
        if is_channel or not user_:
            return await msg.edit_msg("INVALID_USER")

    try:
        user_obj = await c.get_users(user_)
    except Exception:
        user_obj = None

    if not user_obj:
        return await msg.edit_msg("INVALID_USER")

    user_id = user_obj.id
    if Altruix.db is not None:
        pm_permit_col = Altruix.db.make_collection("pm_permit")
        await pm_permit_col.update_one({"user_id": user_id}, {"$set": {"approved": False}}, upsert=True)

    mention = getattr(user_obj, "mention", str(user_id))
    await msg.edit_msg("DIS_APPROVED", string_args=(mention,))


@Altruix.register_on_cmd(
    "pmpermit",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Changes Status Of PM Permit",
        "example": "pmpermit -y or -n",
        "user_args": [
            {"arg": "y", "help": "Enables Pm Permit.", "requires_input": False},
            {"arg": "n", "help": "Disables Pm Permit.", "requires_input": False},
        ],
    },
)
async def pm_permit_command_handler(c: Client, m: Message):
    user_args = m.user_args
    if "n" in user_args:
        await Altruix.config.sync_env_to_db("PM_PERMIT", False)
        if Altruix.log_chat:
            await c.send_message(Altruix.log_chat, "**#Pm Permit**\n\nStatus: `Disabled`")
        await m.reply_msg("Pm Security Status: `Disabled`")
    elif "y" in user_args:
        await Altruix.config.sync_env_to_db("PM_PERMIT", True)
        if Altruix.log_chat:
            await c.send_message(Altruix.log_chat, "**#Pm Permit**\n\nStatus: `Enabled`")
        await m.reply_msg("Pm Security Status: `Enabled`")
    else:
        status_enabled = await Altruix.config.get_pm_sts()
        await m.reply_msg(f"Current PM security status: <code>{'Enabled' if status_enabled else 'Disabled'}</code>")


@Altruix.on_message(
    filters.private & ~filters.group & ~filters.channel,
    group=3,
    bot_mode_unsupported=True,
)
async def pm_permit_new_message_listener_handler(c: Client, m: Message):
    if not await Altruix.config.get_pm_sts():
        return

    sender = getattr(m, "from_user", None) or getattr(m, "sender", None)
    sender_id = getattr(sender, "id", None) or m.sender_id
    if not m or not sender_id or m.out or getattr(sender, "is_self", False) or getattr(sender, "is_bot", False):
        return

    user_id = sender_id
    if Altruix.db is not None:
        pm_permit_col = Altruix.db.make_collection("pm_permit")
        user_info = await pm_permit_col.find_one({"user_id": user_id})
        if user_info and user_info.get("approved", False):
            return

    pm_warns_count = 3
    current_warns = pm_permit_warning_cache.get(user_id, 0)
    if current_warns >= pm_warns_count:
        await m.reply_msg("PM_PERMIT_ALREADY_WARNED")
        with suppress_error(msg="Blocking user on max PM warns"):
            del pm_permit_warning_cache[user_id]
            input_peer = await c.get_input_entity(user_id)
            await c(functions.contacts.BlockRequest(id=input_peer))
        return

    out = await m.reply_msg("<i>Hello there, This is an automated message. I'll respond soon.</i>")
    pm_permit_warning_cache[user_id] = current_warns + 1

    if user_id in __last_message_cache:
        with suppress_error(msg="Deleting previous PM permit warning"):
            await __last_message_cache[user_id].delete()
    __last_message_cache[user_id] = out
