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
from pyrogram import Client, filters
from pyrogram.raw.functions import Ping
from Main.core.decorators import iuser_check
from Main.utils.essentials import Essentials
from pyrogram.types import (
    Message, InlineQuery, CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle)


@Altruix.bot.on_message(
    filters.command("ping", "/") & filters.user(Altruix.config.OWNER_ID)
)
async def restart_command_handler(c: Client, m: Message):
    start = time.perf_counter()
    await c.invoke(Ping(ping_id=9999999))
    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    end = time.perf_counter()
    ms = round((end - start) * 1000, 2)
    await m.edit(
        Altruix.get_string("PING_TEXT").format(
            pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"{pf['ping_emoji1']} Ping", "ping")]]
        ),
    )


@Altruix.bot.on_callback_query(filters.regex("^ping"))
async def ping_cb_handler(c: Client, cb: CallbackQuery):
    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    start = time.perf_counter()
    await c.invoke(Ping(ping_id=9999999))
    end = time.perf_counter()
    ms = round((end - start) * 1000, 2)
    text = Altruix.get_string("PING_TEXT").format(
        pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime
    )
    await cb.answer(Essentials.clean_html(text), show_alert=True)
    await cb.edit_message_text(
        Altruix.get_string(
            "PING_TEXT", args=(pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime)
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"{pf['ping_emoji1']} Ping", "ping")]]
        ),
    )


@Altruix.bot.on_inline_query(filters.regex("^ping"))
@iuser_check
async def ping_inline_handler(c: Client, iq: InlineQuery):
    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    start = time.perf_counter()
    await c.invoke(Ping(ping_id=9999999))
    end = time.perf_counter()
    ms = round((end - start) * 1000, 2)
    await iq.answer(
        [
            InlineQueryResultArticle(
                id=1,
                title=f"{pf['ping_emoji1']} Pong!",
                description=f"{ms} ms\n{uptime}",
                input_message_content=InputTextMessageContent(
                    "<b>{} Pong!</b>\n<code>{} ms</code>\n<b>{} Uptime:</b> <code>{}</code>".format(
                        pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime
                    )
                ),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(f"{pf['ping_emoji1']} Ping", "ping")]]
                ),
            )
        ],
        cache_time=0,
        is_personal=True,
        switch_pm_text=f"{pf['ping_emoji1']} Ping",
        switch_pm_parameter="ping",
    )
