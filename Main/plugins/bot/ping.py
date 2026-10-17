# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import time
from Main import Altruix
from style import ping_format as pf
from Main.utils.custom_filters import filters
from Main.utils.essentials import Essentials
from Main.core.decorators import log_errors, iuser_check
from telethon import custom


@Altruix.bot.on_message(filters.command("ping", "/"))
@log_errors
async def ping_command_handler(c, m):
    if m.sender_id != Altruix.config.OWNER_ID:
        return
    start = time.perf_counter()
    await c.get_me()
    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    end = time.perf_counter()
    ms = round((end - start) * 1000, 2)
    template = Altruix.get_string("PING_TEXT") or "{0} Pong! {1} ms | {2} Uptime: {3}"
    text = template.format(pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime)
    buttons = [[custom.Button.inline(f"{pf['ping_emoji1']} Ping", b"ping")]]
    await m.reply(text, buttons=buttons, parse_mode="html")


@Altruix.bot.on_callback_query(filters.regex(r"^ping"))
@log_errors
async def ping_cb_handler(c, cb):
    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    start = time.perf_counter()
    await c.get_me()
    end = time.perf_counter()
    ms = round((end - start) * 1000, 2)
    template = Altruix.get_string("PING_TEXT") or "{0} Pong! {1} ms | {2} Uptime: {3}"
    text = template.format(pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime)
    await cb.answer(Essentials.clean_html(text), alert=True)
    buttons = [[custom.Button.inline(f"{pf['ping_emoji1']} Ping", b"ping")]]
    await cb.edit(text, buttons=buttons, parse_mode="html")


@Altruix.bot.on_inline_query(filters.regex(r"^ping"))
@log_errors
@iuser_check
async def ping_inline_handler(c, iq):
    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    start = time.perf_counter()
    await c.get_me()
    end = time.perf_counter()
    ms = round((end - start) * 1000, 2)
    builder = iq.builder
    result = builder.article(
        title=f"{pf['ping_emoji1']} Pong!",
        description=f"{ms} ms\n{uptime}",
        text=f"<b>{pf['ping_emoji1']} Pong!</b>\n<code>{ms} ms</code>\n<b>{pf['ping_emoji2']} Uptime:</b> <code>{uptime}</code>",
        parse_mode="html",
        buttons=[[custom.Button.inline(f"{pf['ping_emoji1']} Ping", b"ping")]],
    )
    await iq.answer([result])
