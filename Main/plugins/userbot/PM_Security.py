# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import glob
import logging
from Main import Altruix
from ...core.config import Config
from pyrogram.types import Message
from pyrogram import Client, filters
from ...core.types.message import Message


APPROVED_DICT = Config.APPROVED_DICT or {}
CUSTOM_PM_MEDIA = Config.CUSTOM_PM_MEDIA
CUSTOM_PM_TEXT = Config.CUSTOM_PM_TEXT
PM_WARNS_DICT = Config.PM_WARNS_DICT
PM_WARNS_ACTIVE_CACHE = {}
LPM = {}


@Altruix.register_on_cmd(
    "approve",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Approves the targeted user!",
        "example": "approve @warner_stark",
    },
)
async def approve_user_pm_permit_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user_ = m.chat.id
    if not Altruix.Config.PM_ENABLE:
        logging.info("User DisAbled Pm-Permit.")
        return

    if m.chat.type != "private":
        user_, reason, is_channel = m.get_user
        if is_channel:
            return await msg.edit_msg("INVALID_USER")
    try:
        user_ = await c.get_users(user_)
    except Exception:
        user_ = None
    if not user_:
        return await msg.edit_msg("INVALID_USER")
    user_id = user_.id
    APPROVED_LIST = f"TO_PM_APPROVED_USERS_LIST_{c.myself.id}"
    get_approved = await Altruix.db.data_col.find_one(APPROVED_LIST)
    get_approved_ = []
    if get_approved:
        get_approved_ = get_approved.get("user_id")
        if not isinstance(get_approved_, list):
            get_approved_ = [get_approved_]
        APPROVED_DICT[c.myself.id] = get_approved_
    if (get_approved) and (user_id in get_approved_):
        return await msg.edit_msg("ALREADY_APPROVED")
    if APPROVED_DICT.get(c.myself.id):
        if user_id not in APPROVED_DICT[c.myself.id]:
            APPROVED_DICT[c.myself.id].append(user_id)
    else:
        APPROVED_DICT[c.myself.id] = [user_id]
    if not get_approved:
        await Altruix.db.data_col.insert_one(
            {"_id": APPROVED_LIST, "user_id": [user_id]}
        )
    else:
        await Altruix.db.data_col.update_one(
            {"_id": APPROVED_LIST}, {"$push": {"user_id": user_id}}
        )
    await msg.edit_msg("APPROVED", string_args=(user_.mention))


@Altruix.register_on_cmd(
    "disapprove",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Disapproves the targeted user!",
        "example": "disapprove @warner_stark",
    },
)
async def disapprove_user_pm_permit_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user_ = m.chat.id
    if not Altruix.config.PM_ENABLE:
        logging.info("User DisAbled Pm-Permit.")
        return

    if m.chat.type != "private":
        user_, reason, is_channel = m.get_user
        if is_channel:
            return await msg.edit_msg("INVALID_USER")
    try:
        user_ = await c.get_users(user_)
    except Exception:
        user_ = None
    if not user_:
        return await msg.edit_msg("INVALID_USER")
    user_id = user_.id
    APPROVED_LIST = f"TO_PM_APPROVED_USERS_LIST_{c.myself.id}"
    get_approved = await Altruix.db.data_col.find_one(APPROVED_LIST)
    if get_approved:
        get_approved_user_list = get_approved.get("user_id")
    else:
        return await msg.edit_msg("NOT_APPROVED")
    if not get_approved_user_list:
        return await msg.edit_msg("NOT_APPROVED")
    if (APPROVED_DICT.get(c.myself.id)) and (user_id in APPROVED_DICT[c.myself.id]):
        APPROVED_DICT[c.myself.id].remove(user_id)
    if user_id not in get_approved_user_list:
        return await msg.edit_msg("NOT_APPROVED")
    await Altruix.db.data_col.update_one(
        {"_id": APPROVED_LIST}, {"$pull": {"user_id": user_id}}
    )
    await msg.edit_msg("DIS_APPROVED", string_args=(user_.mention))


@Altruix.register_on_cmd(
    "setpmpic",
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Sets the PM picture to be sent to the pms!",
        "example": "setpmpic (reply to image)",
    },
)
async def add_image_to_pm_permit(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if not Altruix.config.PM_ENABLE:
        logging.info("User DisAbled Pm-Permit.")
        return

    if m.user_args and "-default" in m.user_args:
        CUSTOM_PM_MEDIA[c.myself.id] = None
        await Altruix.config.del_env_from_db(f"PM_MEDIA_{c.myself.id}")
        return await msg.edit_msg("DEFAULT_PM_PIC_SET_TO_DEFAULT")
    if (not m.reply_to_message) and (not m.reply_to_message.media):
        return await msg.edit_msg("INVALID_REPLY")
    if not Altruix.log_chat:
        return await msg.edit_msg("ERROR_404_NO_LOG_CHAT")
    try:
        media_id = await m.reply_to_message.copy(Altruix.log_chat)
    except Exception as e:
        return await msg.edit_msg("PM_MEDIA_SET_FAILED", string_args=(e))
    await Altruix.config.sync_env_to_db(f"PM_MEDIA_{c.myself.id}", media_id.id)
    CUSTOM_PM_MEDIA[c.myself.id] = media_id.id
    if media_id.caption:
        CUSTOM_PM_TEXT[c.myself.id] = media_id.caption
        await Altruix.config.sync_env_to_db(f"PM_TEXT_{c.myself.id}", media_id.caption)
    await msg.edit_msg("PM_SET_SUCCESSFULLY")


@Altruix.register_on_cmd(
    ["setpmwarnlimit", "spwl"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Set your custom max PM warning limit!",
        "example": "setpmwarnlimit 5",
    },
)
async def setpmwlimit(c: Client, m: Message):
    msg = m.handle_message("PROCESSING")
    if not Altruix.config.PM_ENABLE:
        logging.info("User DisAbled Pm-Permit.")
        return

    limit = str(m.user_input)
    if not limit or not limit.isdigit() or (int(limit) <= 1):
        return await msg.edit_msg("INVALID_LIMIT", string_args=(limit))
    await Altruix.config.sync_env_to_db(f"PM_WARNS_COUNT_{c.myself.id}", int(limit))
    PM_WARNS_DICT[c.myself.id] = int(limit)
    await msg.edit_msg("LIMIT_SET", string_args=(limit))


@Altruix.register_on_cmd(
    ["setpmtext"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Sets the text to be sent in the PM!",
        "example": "setpmtext Hello World!",
    },
)
async def add_custom_text_to_pm_permit(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if not Altruix.config.PM_ENABLE:
        logging.info("User DisAbled Pm-Permit.")
        return

    if m.user_args and "-default" in m.user_args:
        CUSTOM_PM_TEXT[c.myself.id] = None
        await Altruix.config.del_env_from_db(f"PM_TEXT_{c.myself.id}")
        return await msg.edit_msg("DEFAULT_PM_TEXT_SET_TO_DEFAULT")
    if not m.reply_to_message and not m.raw_user_input:
        return await msg.edit_msg("INVALID_REPLY")
    if m.reply_to_message and m.reply_to_message.text:
        text = m.reply_to_message.text
    elif m.reply_to_message and m.raw_user_input or not m.reply_to_message:
        text = m.raw_user_input
    elif m.reply_to_message.caption:
        text = m.reply_to_message.caption
    else:
        return await msg.edit_msg("INVALID_REPLY")
    await Altruix.config.sync_env_to_db(f"PM_TEXT_{c.myself.id}", text)
    CUSTOM_PM_TEXT[c.myself.id] = text
    await msg.edit_msg("PM_TEXT_INIT")


@Altruix.on_message(
    filters.private & ~filters.group & ~filters.channel, 3, bot_mode_unsupported=True
)
async def pm_permit_(c: Client, m: Message):
    if not Altruix.config.PM_ENABLE:
        logging.info("User DisAbled Pm-Permit.")
        return

    if (
        (not m)
        or (not m.from_user)
        or (m.from_user.is_contact)
        or (m.from_user.is_verified)
        or (m.from_user.is_bot)
    ):
        return
    if APPROVED_DICT.get(c.myself.id) and m.from_user.id in APPROVED_DICT[c.myself.id]:
        return
    if m.from_user.is_self or m.from_user.is_contact or m.from_user.is_bot:
        return
    pm_warns_count = int(PM_WARNS_DICT.get(c.myself.id) or 3)
    if (
        PM_WARNS_ACTIVE_CACHE.get(int(m.from_user.id))
        and int(PM_WARNS_ACTIVE_CACHE[m.from_user.id]) >= pm_warns_count
    ):
        await m.reply_msg("PM_PERMIT_ALREADY_WARNED")
        del PM_WARNS_ACTIVE_CACHE[m.from_user.id]
        return await m.from_user.block()
    media_ = CUSTOM_PM_MEDIA.get(c.myself.id)
    text_ = CUSTOM_PM_TEXT.get(c.myself.id)
    id_msg = m.id
    if text_:
        text_ = text_.format(
            user_id=m.from_user.id,
            mention=m.from_user.mention,
            user_name=m.from_user.username,
            max_warns=pm_warns_count,
            warns=PM_WARNS_ACTIVE_CACHE[m.from_user.id]
            if PM_WARNS_ACTIVE_CACHE.get(m.from_user.id)
            else 1,
            mymention=c.myself.mention,
        )
    if media_ and Altruix.log_chat:
        dtext = Altruix.config.DEFAULT_PM_TEXT.format(
            user_id=m.from_user.id,
            mention=m.from_user.mention,
            user_name=m.from_user.username,
            max_warns=pm_warns_count,
            warns=PM_WARNS_ACTIVE_CACHE[m.from_user.id]
            if PM_WARNS_ACTIVE_CACHE.get(m.from_user.id)
            else 1,
            mymention=c.myself.mention,
        )
        out = await c.copy_message(
            m.chat.id,
            Altruix.log_chat,
            int(media_),
            text_ or dtext,
            reply_to_message_id=id_msg,
        )
    elif text_:
        out = await m.reply(text_, quote=True)
    else:
        path_ = "./custom_files/pmpermit.*"
        photo_ = (
            glob.glob(path_)[0] if glob.glob(path_) else Altruix.config.DEFAULT_PM_IMAGE
        )
        text_ = Altruix.config.DEFAULT_PM_TEXT.format(
            user_id=m.from_user.id,
            mention=m.from_user.mention,
            user_name=m.from_user.username,
            max_warns=pm_warns_count,
            warns=PM_WARNS_ACTIVE_CACHE[m.from_user.id]
            if PM_WARNS_ACTIVE_CACHE.get(m.from_user.id)
            else 1,
            mymention=c.myself.mention,
        )
        out = await m.reply_file(photo_, caption=text_, quote=True)
    if m.from_user.id not in PM_WARNS_ACTIVE_CACHE:
        PM_WARNS_ACTIVE_CACHE[m.from_user.id] = 1
    else:
        PM_WARNS_ACTIVE_CACHE[m.from_user.id] += 1
    if m.from_user.id in LPM:
        await LPM[m.from_user.id]._delete()
    LPM[m.from_user.id] = out
