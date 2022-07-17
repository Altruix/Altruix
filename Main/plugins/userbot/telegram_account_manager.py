# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
from os import remove
from Main import Altruix
from pyrogram import Client
from Main.core.types.message import Message
from pyrogram.raw.types import Authorization
from pyrogram.raw.functions.account import CheckUsername, GetAuthorizations


@Altruix.register_on_cmd(
    ["set", "modify"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "To change your different settings of account",
        "example": "set -f <newname>",
        "user_args": {
            "f": "To change your first name.",
            "l": "To change your last name.",
            "b": "To change your bio.",
            "p": "To set your new profile pic.",
            "s": "To get account sessions.",
            "u": "To change your username.",
        },
    },
)
async def set(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    args = m.user_args
    if not args:
        return await m.handle_message("INPUT_REQUIRED")
    if "-f" in args:
        if not m.user_input:
            return await msg.edit("INPUT_REQUIRED")
        fname = m.text.split(None, 2)[2]
        await c.update_profile(first_name=fname)
        await m.handle_message(Altruix.get_string("CHANGE").format("FirstName", fname))
    elif "-l" in args:
        if not m.user_input:
            return await msg.edit("INPUT_REQUIRED")
        lname = m.text.split(None, 2)[2]
        await c.update_profile(last_name=lname)
        await m.handle_message(Altruix.get_string("CHANGE").format("LastName", lname))
    elif "-b" in args:
        if not m.user_input:
            return await msg.edit("INPUT_REQUIRED")
        bio = m.text.split(None, 2)[2]
        await c.update_profile(bio=bio)
        await m.handle_message(Altruix.get_string("CHANGE").format("Bio", bio))
    elif "-u" in args:
        if not m.user_input:
            return await msg.edit("INPUT_REQUIRED")
        uname = m.text.split(None, 2)[2].replace("@", "")
        check = await c.invoke(CheckUsername(username=uname))
        if not check:
            return await m.handle_message(
                Altruix.get_string("USERNAME_TAKEN").format(f"@{uname}")
            )
        await c.set_username(uname)
        await m.handle_message(Altruix.get_string("CHANGE").format("Username", uname))
    elif "-p" in args:
        if not m.reply_to_message:
            return await m.handle_message("REPLY_REQUIRED")
        reply = m.reply_to_message
        if not reply.photo:
            return await msg.edit("REPLY_PHOTO")
        pic = await c.download_media(reply.photo.file_id)
        await c.set_profile_photo(photo=pic)
        await m.handle_message("CHNG_PHOTO")
        if os.path.exists(pic):
            remove(pic)
    elif "-s" in args:
        sessions = (await c.invoke(GetAuthorizations())).authorizations
        text_ = f"<b>Sessions :</b> ({len(sessions)}) \n\n"
        for session in sessions:
            session: Authorization = session
            text_ += f"> <b>Device :</b> <code>{session.device_model} {session.platform} V{session.system_version}</code> \n<b>App :</b> <code>{session.app_name} V{session.app_version}</code> \n<b>Region :</b> <code>{session.country} - {session.region} ({session.ip})</code> \n\n"
        await m.handle_message(text_)
