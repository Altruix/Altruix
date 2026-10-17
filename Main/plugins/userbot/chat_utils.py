# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
from Main import Altruix
from style import bullets
from Main.core.types.client import AltruixTelegramClient as Client
from Main.utils.paste import Paste
from Main.core.types.message import Message


b1 = bullets.get("bullet1", "•")
b2 = bullets.get("bullet2", "—")
b3 = bullets.get("bullet3", "▶")


@Altruix.register_on_cmd(
    ["setchattitle", "sct"],
    cmd_help={
        "help": "To change the title of the chat!",
        "example": "setchattitle <newtitle>",
    },
    group_only=True,
    requires_input=True,
)
async def set_chat_title_cmd_handler(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    title = m.user_input
    if len(title) >= 128:
        return await msg.edit_msg("TG_LIMIT_EXE", string_args=(128, "chat-title"))
    try:
        await c.set_chat_title(m.chat.id, title)
    except Exception as be:
        name, err = await Paste(str(be)).paste()
        return await msg.edit_msg("ERROR_", string_args=(name, err))
    await msg.edit_msg("CHAT_TITLE_CHANGED")


@Altruix.register_on_cmd(
    ["setchatpic", "scp"],
    cmd_help={"help": "To set current chat pic", "example": "setchatpic"},
    group_only=True,
)
async def set_chat_pic_cmd_handler(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if m.reply_to_message:
        reply = m.reply_to_message
        if not reply.file:
            return await msg.edit_msg("INVALID_REPLY")
        file_path = await reply.download_media("cache/")
        try:
            await c.set_chat_photo(m.chat.id, file_path)
            await msg.edit("<b>Chat photo updated!</b>", parse_mode="html")
        except Exception as be:
            name, err = await Paste(str(be)).paste()
            await msg.edit_msg("ERROR_", string_args=(name, err))
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
    else:
        await msg.edit_msg("REPLY_TO_MESSAGE")


@Altruix.register_on_cmd(
    ["delchatpic", "dcp"],
    cmd_help={
        "help": "To delete chat current pic",
        "example": "delchatpic",
    },
    group_only=True,
)
async def del_chat_pic_cmd_handler(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    try:
        await c.delete_chat_photo(m.chat.id)
    except Exception as be:
        name, err = await Paste(str(be)).paste()
        return await msg.edit_msg("ERROR_", string_args=(name, err))
    await msg.edit_msg("DELETED_CHAT_PIC")


@Altruix.register_on_cmd(
    ["chatinfo", "cinfo", "ci", "groupinfo", "ginfo", "gi"],
    cmd_help={
        "help": "To get chat info",
        "example": "chatinfo <chat id/chat username>",
    },
)
async def get_group_info_cmd_handler(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    chat_target = m.text.split(None, 1)[1] if m.user_input else m.chat.id
    if str(chat_target).lstrip("-").isdigit():
        chat_target = int(chat_target)

    try:
        ci = await c.get_entity(chat_target)
    except Exception as e:
        return await msg.edit(
            f"<code>Failed to fetch chat info.</code>\n\n<b>Traceback:</b>\n<code>{e}</code>",
            parse_mode="html",
        )

    title = getattr(ci, "title", getattr(ci, "first_name", "Chat"))
    username = getattr(ci, "username", None)
    chat_id = getattr(ci, "id", chat_target)

    ci_text = [
        f"{b3} <b>Chat-info of <i>{title}</i>:</b>\n\n",
        f"  {b1} <b>Username:</b> <code>@{username}</code>\n" if username else "",
        f"  {b1} <b>Chat ID:</b> <code>{chat_id}</code>\n",
        f"  {b1} <b>Participants:</b> <code>{getattr(ci, 'participants_count', 'Unknown')}</code>\n",
        f"  {b1} <b>Is Scam:</b> <i>{'Yes' if getattr(ci, 'scam', False) else 'No'}</i>\n",
        f"  {b1} <b>Is Verified:</b> <i>{'Yes' if getattr(ci, 'verified', False) else 'No'}</i>\n",
    ]

    try:
        photo = await c.download_profile_photo(ci)
        if photo:
            await msg.delete()
            await c.send_file(
                m.chat.id,
                photo,
                caption="".join(ci_text),
                reply_to=m.id,
                parse_mode="html",
            )
            if os.path.exists(photo):
                os.remove(photo)
            return
    except Exception:
        pass

    await msg.edit("".join(ci_text), parse_mode="html")
