# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from os import remove
import os
from Main import Altruix
from style import bullets
from pyrogram import Client
from Main.utils.paste import Paste
from Main.core.types.message import Message


b1 = bullets["bullet1"]
b2 = bullets["bullet2"]
b3 = bullets["bullet3"]


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
        name, err = await Paste(be).paste()
        return await msg.edit_msg("ERROR_", sting_args=(name, err))
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
        if not reply.media:
            
            return await msg.edit_msg("INVALID_REPLY")
        if reply.photo:
            file = reply.photo.file_id
        elif reply.video:
            file = await reply.download()
        else:
            return await msg.edit_msg("INVALID_REPLY")
        try:
            await c.set_chat_photo(m.chat.id, file)
        except Exception as be:
            name, err = await Paste(be).paste()
            await msg.edit_msg(
                Altruix.get_string("ERROR_"), string_args=(name, err)
            )
        return os.remove(file) if os.path.exists(file) else 'ok'
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
        name, err = await Paste(be).paste()
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
    chat_id = m.text.split(None, 1)[1] if m.user_input else m.chat.id
    try:
        ci = await c.get_group(chat_id)
    except Exception as e:
        return await msg.edit(
            f"<code>Failed to fetch chat info.</code>\n\n<b><u>Traceback</u> :</b>\n\n<code>{e}</code>"
        )

    ci_text = [
        f"{b3} <b>Chat-info of <i>“{ci.title}”</i> :</b>\n\n",
        f"  {b1} <b>Username :</b> <code>@{ci.username}</code>\n"
        if ci.username is not None
        else "",
        f"  {b1} <b>Chat ID :</b> <code>{ci.id}</code>\n",
        f"  {b1} <b>Chat DCID : <i>{ci.dc_id}</i></b>\n",
        f"  {b1} <b>Participants :</b> <code>{ci.members_count}</code>\n",
        f"  {b1} <b>Is Scam : <i>{'Yes' if ci.is_scam else 'No'}</i></b>\n",
        f"  {b1} <b>Is Support : <i>{'Yes' if (ci.is_support or m.chat.id == -1001596389253) else 'No'}</i></b>\n"
        f"  {b1} <b>Is Verified : <i>{'Yes' if (ci.is_verified or m.chat.id == -1001596389253) else 'No'}</i></b>\n",
        f"  {b1} <b>Chat Type : <i>{ci.type}</i></b>\n",
        f"  {b1} <b>Chat Description :</b>\n\n<code>{ci.description}</code>"
        if ci.description is not None
        else "",
    ]

    pic = ci.photo.big_file_id if ci.photo else None
    if pic is not None:
        photo = await c.download_media(pic)
        await c.send_photo(
            msg.chat.id,
            photo,
            caption="".join(ci_text),
            reply_to_message_id=m.id,
        )
        remove(photo)
        await msg.delete()
        return
    else:
        await msg.edit("".join(ci_text))
