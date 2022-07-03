# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from Main import Altruix
from pyrogram import Client
from Main.utils.paste import Paste
from Main.utils.helpers import random_hash
from Main.core.types.message import Message
from pyrogram.errors.exceptions.bad_request_400 import ChatSendInlineForbidden


___args__m = {"m": "prompts to choose a service from a menu"}

(
    ___args__m.update(_each, f"Pastes the output to {_each}")
    for _each in Paste().all_bins
)


@Altruix.register_on_cmd(
    ["paste"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "To paste the text to pastebin services.",
        "example": "paste",
        "user_args": ___args__m,
    },
)
async def paste(c: Client, m: Message):
    _m = await m.handle_message("PROCESSING")
    rm = m.reply_to_message
    if rm:
        msg = rm
        if msg.text:
            text = msg.text
        elif msg.document:
            file = await c.download_media(msg.document.file_id)
            with open(file, "rb") as f:
                text = f.read().decode()
        else:
            return await _m.edit_msg("`Reply to a valid text or file to paste!`")
    else:
        await m.edit_msg("Reply to a file or text to paste!")
        return
    if "-m" in m.user_args:
        _hash = random_hash()
        Altruix.local_db.add_to_col("paste", {_hash: text})
        try:
            results = await c.get_inline_bot_results(
                Altruix.bot_info.username, f"paste_menu:{_hash}"
            )
            await c.send_inline_bot_result(
                chat_id=m.chat.id,
                query_id=results.query_id,
                result_id=results.results[0].id,
                reply_to_message_id=rm.id if rm else None,
            )
            await m.delete_if_self()
        except ChatSendInlineForbidden:
            return await m.edit_msg(Altruix.get_string("INLINE_NOT_ALLOWED"))
    elif val := (set(m.user_args) & set(Paste().all_bins)):
        name, link = await Paste(text, service=val[0]).paste()
        try:
            results = await c.get_inline_bot_results(
                Altruix.bot_info.username, f"paste_url:{link}"
            )
            await c.send_inline_bot_result(
                chat_id=m.chat.id,
                query_id=results.query_id,
                result_id=results.results[0].id,
                reply_to_message_id=rm.id if rm else None,
            )
            await m.delete_if_self()
        except ChatSendInlineForbidden:
            await m.edit_msg(Altruix.get_string("PASTE_TEXT").format(name, link))
    else:
        name, link = await Paste(text).paste()
        await m.edit(
            Altruix.get_string("PASTE_TEXT").format(link, name),
            disable_web_page_preview=True,
        )
