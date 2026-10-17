# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import os
from Main import Altruix
from Main.utils.paste import Paste
from Main.utils.custom_filters import filters
from Main.utils.essentials import Essentials
from Main.utils.helpers import arrange_buttons
from Main.core.decorators import log_errors, iuser_check
from telethon import custom


@Altruix.bot.on_message(filters.command("paste", "/"))
@log_errors
async def paste_bot_cmd_handler(_, m):
    if m.sender_id != Altruix.config.OWNER_ID:
        return
    text = None
    if m.reply_to_message:
        mess = m.reply_to_message
        if mess.text:
            text = mess.text
        elif mess.file:
            _file = await mess.download_media("temp/")
            with open(_file, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if os.path.exists(_file):
                os.remove(_file)
        elif mess.raw_text:
            text = mess.raw_text
    else:
        text = m.raw_user_input
    if not text:
        return await m.reply(Altruix.get_string("PASTE_SOURCE_NOT_PROVIDED") or "Please provide text or reply to a message to paste.")
    author_name = Altruix.ourselves[0].first_name if Altruix.ourselves else "Altruix"
    service, link = await Paste(text, author=author_name).paste()
    template = Altruix.get_string("PASTE_TEXT") or "Pasted to {1}: {0}"
    await m.reply(template.format(link, service), link_preview=False)


@Altruix.bot.on_callback_query(filters.regex(r"paste_to_(\w+)#(\w+)"))
@log_errors
@iuser_check
async def paste_cb_handler(_, cb):
    await cb.answer(
        Essentials.clean_html(Altruix.get_string("PLEASE_WAIT") or "Please wait..."),
        alert=True,
    )
    data_str = cb.data.decode("utf-8") if isinstance(cb.data, bytes) else str(cb.data)
    match = re.search(r"paste_to_(\w+)#(\w+)", data_str)
    if not match:
        return
    service = match.group(1)
    key = match.group(2)
    text = Altruix.local_db.get_from_col("paste", key)
    if not text:
        return await cb.edit(Altruix.get_string("DB_KEY_NOT_FOUND") or "Key not found in local DB.")
    author_name = Altruix.ourselves[0].first_name if Altruix.ourselves else "Altruix"
    service, link = await Paste(text, author=author_name, service=service).paste()
    template = Altruix.get_string("PASTE_TEXT") or "Pasted to {1}: {0}"
    await cb.edit(template.format(link, service), link_preview=False)


@Altruix.bot.on_inline_query(filters.regex(r"(paste_url:((?:(?:https?://)?[\w-]+(?:\.[\w-]+)+\.?(?::\d+)?(?:/\S*)?))|paste_menu:(\w+))"))
@log_errors
@iuser_check
async def paste_inline_handler(_, iq):
    builder = iq.builder
    query = iq.text or ""
    if "paste_menu:" in query:
        key = query.split("paste_menu:")[1].strip()
        all_bins = Paste().all_bins
        buttons = [
            custom.Button.inline(
                b.title(),
                f"paste_to_{b}#{key}".encode("utf-8"),
            )
            for b in all_bins
        ]
        grid = arrange_buttons(buttons, 2)
        result = builder.article(
            title="Paste Menu",
            description="Paste text to a specific bin",
            text="Which service would you like to use?",
            buttons=grid,
        )
        await iq.answer([result])
    elif "paste_url:" in query:
        url = query.split("paste_url:")[1].strip()
        template = Altruix.get_string("PASTE_TEXT") or "Pasted to {1}: {0}"
        result = builder.article(
            title=f"Paste {url}",
            description="Paste internal function",
            text=template.format(url, "bin"),
            buttons=[[custom.Button.url("URL", url)]],
        )
        await iq.answer([result])
