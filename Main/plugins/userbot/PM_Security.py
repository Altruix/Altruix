# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


from Main import Altruix
from pyrogram.types import Message
from pyrogram import Client, filters
from ...core.types.message import Message


pm_permit_warning_cache = {}
__last_message_cache = {}
pm_permit_col = Altruix.db.make_collection("pm_permit")


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
    user_ = m.chat.id
    if await Altruix.config.get_pm_sts():
        await m.edit("<code>PM permit is disabled</code>")
        return

    if m.chat.type != "private":
        user_, _, is_channel = m.get_user
        if is_channel:
            return await msg.edit_msg("INVALID_USER")
    try:
        user_ = await c.get_users(user_)
    except Exception:
        user_ = None
    if not user_:
        return await msg.edit_msg("INVALID_USER")
    user_id = user_.id
    user_info = await pm_permit_col.find_one({"user_id": user_id})
    if not user_info:
        await pm_permit_col.insert_one({"user_id": user_id, "approved": True})
    else:
        if user_info.get("approved", False):
            await pm_permit_col.update_one(
                {"user_id": user_id}, {"$set": {"approved": True}}
            )
        else:
            return await msg.edit_msg("ALREADY_APPROVED")
    await msg.edit_msg("APPROVED", string_args=(user_.mention))


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
    user_ = m.chat.id
    if await Altruix.config.get_pm_sts():
        await c.send_message(
            Altruix.log_chat,
            f"**#DISSPROVE**\n\nStatus: `Can't Disapprove!`\n\n**Reason:** `PM Security is Disabled!`",
        )
        return

    if m.chat.type != "private":
        user_, _, is_channel = m.get_user
        if is_channel:
            return await msg.edit_msg("INVALID_USER")
    try:
        user_ = await c.get_users(user_)
    except Exception:
        user_ = None
    if not user_:
        return await msg.edit_msg("INVALID_USER")
    user_id = user_.id
    user_info = await pm_permit_col.find_one({"user_id": user_id})
    if not user_info:
        await pm_permit_col.insert_one(
            {
                "user_id": user_id,
                "approved": False,
                "action_user_id": c.myself.id,
                "is_global": False,
            }
        )
    else:
        if user_info.get("approved", False):
            return await msg.edit_msg("ALREADY_DISAPPROVED")
        else:
            await pm_permit_col.update_one(
                {"user_id": user_id}, {"$set": {"approved": False}}
            )
    await msg.edit_msg("DIS_APPROVED", string_args=(user_.mention))


# @Altruix.register_on_cmd(
#     "setpmpic",
#     bot_mode_unsupported=True,
#     cmd_help={
#         "help": "Sets the PM picture to be sent to the pms!",
#         "example": "setpmpic (reply to image)",
#     },
# )
# async def add_image_to_pm_permit(c: Client, m: Message):
#     msg = await m.handle_message("PROCESSING")
#     if await Altruix.config.get_pm_sts():
#         await c.send_message(
#             Altruix.log_chat,
#             f"**#Pm Picture**\n\nStatus: `Can't Set!`\n\n**Reason:** `PM Security is Disabled!`",
#         )
#         return

#     if m.user_args and "-default" in m.user_args:
#         CUSTOM_PM_MEDIA[c.myself.id] = None
#         await Altruix.config.del_env_from_db(f"PM_MEDIA_{c.myself.id}")
#         return await msg.edit_msg("DEFAULT_PM_PIC_SET_TO_DEFAULT")
#     if (not m.reply_to_message) and (not m.reply_to_message.media):
#         return await msg.edit_msg("INVALID_REPLY")
#     if not Altruix.log_chat:
#         return await msg.edit_msg("ERROR_404_NO_LOG_CHAT")
#     try:
#         media_id = await m.reply_to_message.copy(Altruix.log_chat)
#     except Exception as e:
#         return await msg.edit_msg("PM_MEDIA_SET_FAILED", string_args=(e))
#     await Altruix.config.sync_env_to_db(f"PM_MEDIA_{c.myself.id}", media_id.id)
#     CUSTOM_PM_MEDIA[c.myself.id] = media_id.id
#     if media_id.caption:
#         CUSTOM_PM_TEXT[c.myself.id] = media_id.caption
#         await Altruix.config.sync_env_to_db(f"PM_TEXT_{c.myself.id}", media_id.caption)
#     await msg.edit_msg("PM_SET_SUCCESSFULLY")


# @Altruix.register_on_cmd(
#     ["setpmwarnlimit", "spwl"],
#     bot_mode_unsupported=True,
#     cmd_help={
#         "help": "Set your custom max PM warning limit!",
#         "example": "setpmwarnlimit 5",
#     },
# )
# async def setpmwlimit(c: Client, m: Message):
#     msg = m.handle_message("PROCESSING")
#     if await Altruix.config.get_pm_sts():
#         await c.send_message(
#             Altruix.log_chat,
#             f"**#Warn Limit**\n\nStatus: `Can't Set!`\n\n**Reason:** `PM Security is Disabled!`",
#         )
#         return

#     limit = str(m.user_input)
#     if not limit or not limit.isdigit() or (int(limit) <= 1):
#         return await msg.edit_msg("INVALID_LIMIT", string_args=(limit))
#     await Altruix.config.sync_env_to_db(f"PM_WARNS_COUNT_{c.myself.id}", int(limit))
#     PM_WARNS_DICT[c.myself.id] = int(limit)
#     await msg.edit_msg("LIMIT_SET", string_args=(limit))


# @Altruix.register_on_cmd(
#     ["setpmtext"],
#     bot_mode_unsupported=True,
#     cmd_help={
#         "help": "Sets the text to be sent in the PM!",
#         "example": "setpmtext Hello World!",
#     },
# )
# async def add_custom_text_to_pm_permit(c: Client, m: Message):
#     msg = await m.handle_message("PROCESSING")
#     if await Altruix.config.get_pm_sts():
#         await c.send_message(
#             Altruix.log_chat,
#             f"**#Pm Text**\n\nStatus: `Can't Set!`\n\n**Reason:** `PM Security is Disabled!`",
#         )
#         return

#     if m.user_args and "-default" in m.user_args:
#         CUSTOM_PM_TEXT[c.myself.id] = None
#         await Altruix.config.del_env_from_db(f"PM_TEXT_{c.myself.id}")
#         return await msg.edit_msg("DEFAULT_PM_TEXT_SET_TO_DEFAULT")
#     if not m.reply_to_message and not m.raw_user_input:
#         return await msg.edit_msg("INVALID_REPLY")
#     if m.reply_to_message and m.reply_to_message.text:
#         text = m.reply_to_message.text
#     elif m.reply_to_message and m.raw_user_input or not m.reply_to_message:
#         text = m.raw_user_input
#     elif m.reply_to_message.caption:
#         text = m.reply_to_message.caption
#     else:
#         return await msg.edit_msg("INVALID_REPLY")
#     await Altruix.config.sync_env_to_db(f"PM_TEXT_{c.myself.id}", text)
#     CUSTOM_PM_TEXT[c.myself.id] = text
#     await msg.edit_msg("PM_TEXT_INIT")


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
        await c.send_message(Altruix.log_chat, f"**#Pm Permit**\n\nStatus: `Disabled`")
        await m.reply_msg("Pm Security Status: `Disabled`")

    elif "y" in user_args:
        await Altruix.config.sync_env_to_db("PM_PERMIT", True)
        await c.send_message(Altruix.log_chat, f"**#Pm Permit**\n\nStatus: `Enabled`")
        await m.reply_msg("Pm Security Status: `Enabled`")
    else:
        await m.reply_msg(
            "Current PM security status: <code>{}</code>".format(
                "Enabled" if await Altruix.config.get_env("PM_PERMIT") else "Disabled"
            )
        )


@Altruix.on_message(
    filters.private & ~filters.group & ~filters.channel, 3, bot_mode_unsupported=True
)
async def pm_permit_new_message_listener_handler(c: Client, m: Message):
    if not await Altruix.config.get_pm_sts():
        return

    if (
        (not m)
        or (not m.from_user)
        or (m.from_user.is_contact)
        or (m.from_user.is_verified)
        or (m.from_user.is_bot)
    ):
        return

    if m.from_user.is_self or m.from_user.is_contact or m.from_user.is_bot:
        return
    pm_warns_count = int(pm_permit_warning_cache.get(c.myself.id, 3))
    if (
        pm_permit_warning_cache.get(int(m.from_user.id))
        and int(pm_permit_warning_cache[m.from_user.id]) >= pm_warns_count
    ):
        out = await m.reply_msg("PM_PERMIT_ALREADY_WARNED")
        del pm_permit_warning_cache[m.from_user.id]
        return await m.from_user.block()
    else:
        out = await m.reply_msg("<i>Hello there, This is an automated message. I'll respond soon.</i>")
    if m.from_user.id not in pm_permit_warning_cache:
        pm_permit_warning_cache[m.from_user.id] = 1
    else:
        pm_permit_warning_cache[m.from_user.id] += 1
    if m.from_user.id in __last_message_cache:
        await __last_message_cache[m.from_user.id]._delete()
    __last_message_cache[m.from_user.id] = out
