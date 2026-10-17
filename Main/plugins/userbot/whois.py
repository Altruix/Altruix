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
from Main.core.types.message import Message


b1 = bullets.get("bullet1", "•")
b2 = bullets.get("bullet2", "—")
b3 = bullets.get("bullet3", "▶")


@Altruix.register_on_cmd(
    ["whois", "ui", "info", "userinfo", "uinfo"],
    cmd_help={
        "help": "To get user info!",
        "example": "whois <reply/user id/username>",
    },
)
async def userinfo(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    reply_msg = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if reply_msg and reply_msg.sender_id:
        user = reply_msg.sender_id
    elif m.user_input:
        target = m.user_input.strip()
        user = int(target) if target.lstrip("-").isdigit() else target
    else:
        user = "me"

    try:
        ui = await c.get_entity(user)
    except Exception as e:
        return await msg.edit_msg("INVALID_USER_ERROR", string_args=(str(e),))

    first_name = getattr(ui, "first_name", "") or ""
    last_name = getattr(ui, "last_name", "") or ""
    username = getattr(ui, "username", None)
    user_id = getattr(ui, "id", user)
    mention = f"@{username}" if username else f"<a href='tg://user?id={user_id}'>{first_name}</a>"

    ui_text = [
        f"{b3} <b>User-info of <i>{mention}</i>:</b>\n\n",
        f"  {b1} <b>First name:</b> <i>{first_name}</i>\n",
        f"  {b1} <b>Last name:</b> <i>{last_name}</i>\n" if last_name else "",
        f"  {b1} <b>Username:</b> <code>@{username}</code>\n" if username else "",
        f"  {b1} <b>User ID:</b> <code>{user_id}</code>\n",
        f"  {b2} <b>Is Bot:</b> <i>{'Yes' if getattr(ui, 'bot', False) else 'No'}</i>\n",
        f"  {b2} <b>Is Scam:</b> <i>{'Yes' if getattr(ui, 'scam', False) else 'No'}</i>\n",
        f"  {b2} <b>Is Verified:</b> <i>{'Yes' if getattr(ui, 'verified', False) else 'No'}</i>\n",
        f"  {b2} <b>Is Premium:</b> <i>{'Yes' if getattr(ui, 'premium', False) else 'No'}</i>\n",
    ]

    chat_target = m.chat_id or (getattr(m.chat, "id", None))
    try:
        photo = await c.download_profile_photo(ui)
        if photo and chat_target:
            try:
                await c.send_file(
                    chat_target,
                    photo,
                    caption="".join(ui_text),
                    reply_to=m.id,
                    parse_mode="html",
                )
                await msg.delete()
                return
            finally:
                if os.path.exists(photo):
                    os.remove(photo)
    except Exception:
        pass

    await msg.edit_msg("".join(ui_text))
