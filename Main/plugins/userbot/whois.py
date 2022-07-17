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
from pyrogram import Client
from Main.core.types.message import Message


b1 = bullets["bullet1"]
b2 = bullets["bullet2"]
b3 = bullets["bullet3"]

dc_id = {
    1: "Miami FL, USA",
    2: "Amsterdam, NL",
    3: "Miami FL, USA",
    4: "Amsterdam, NL",
    5: "Singapore, SG",
}


@Altruix.register_on_cmd(
    ["whois", "ui", "info", "userinfo", "uinfo"],
    cmd_help={
        "help": "To get a users info!",
        "example": "whois <reply/user id/username>",
    },
)
async def userinfo(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if m.reply_to_message:
        user = m.reply_to_message.from_user.id
    elif m.user_input:
        user = m.text.split(" ", 1)[1]
    else:
        return await msg.edit_msg("INVALID_USER")
    try:
        ui = await c.get_users(user)
    except Exception as e:
        return await msg.edit_msg("INVALID_USER_ERROR", string_args=(e))
    xio = f"{ui.dc_id} | {dc_id[ui.dc_id]}" if ui.dc_id else "Unknown"
    ui_text = [
        f"{b3} <b>User-info of <i>“{ui.mention}”</i> :</b>\n\n",
        f"  {b1} <b>Firstname : <i>{ui.first_name}</i></b>\n",
        f"  {b1} <b>Lastname : <i>{ui.last_name}</i></b>\n" if ui.last_name else "",
        (
            f"  {b1} <b>Username :</b> <code>@{ui.username}</code>\n"
            if ui.username
            else ""
        ),
        f"  {b1} <b>User ID :</b> <code>{ui.id}</code>\n",
        f"  {b2} <b>User DCID : <i>{xio}</i></b>\n",
        f"  {b2} <b>Premium User : <i>{ui.is_premium}</i></b>\n"
        f"  {b2} <b>Status : <i>{ui.status}</i></b>\n",
        f"  {b2} <b>Is Bot : <i>{'Yes' if ui.is_bot else 'No'}</i></b>\n",
        f"  {b2} <b>Is Scam : <i>{'Yes' if ui.is_scam else 'No'}</i></b>\n",
        f"  {b2} <b>Is Mutual : <i>{'Yes' if ui.is_mutual_contact else 'No'}</i></b>\n",
        f"  {b2} <b>Is Verified : <i>{'Yes' if ui.is_verified else 'No'}</i></b> \n",
        f"  {b2} <b>Common Chats Count : <i>{len(await ui.get_common_chats())}</i></b>",
    ]
    pic = ui.photo.big_file_id if ui.photo else None
    if pic is not None:
        await msg.delete()
        photo = await c.download_media(pic)
        await c.send_photo(
            chat_id=m.chat.id,
            photo=photo,
            caption="".join(ui_text),
            reply_to_message_id=m.id,
        )
        if os.path.exists(photo):
            os.remove(photo)
    else:
        await msg.edit("".join(ui_text))
