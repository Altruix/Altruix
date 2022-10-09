# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import time
from Main import Altruix
from pyrogram import Client
from style import ping_format as pf
from pyrogram.raw.functions import Ping
from Main.core.types.message import Message
from Main.utils.essentials import Essentials
from Main.core.decorators import inline_check
from pyrogram.errors import ChatSendInlineForbidden


@Altruix.register_on_cmd(
    ["ping", "pong"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Ping userbot",
        "example": "ping",
        "user_args": [
                        {
                "arg": "c",
                "help": "show the ping output as a regular text edit.",
                "requires_input": False
            },
],
    },
)
@inline_check
async def ping_ub_cmd(c: Client, m: Message):
    user_args = m.user_args
    if "c" not in user_args:
        rm = m.reply_to_message
        try:
            results = await c.get_inline_bot_results(Altruix.bot_info.username, "ping")
            await c.send_inline_bot_result(
                chat_id=m.chat.id,
                query_id=results.query_id,
                result_id=results.results[0].id,
                reply_to_message_id=rm.id if rm else m.id,
            )
            await m.delete_if_self()
        except ChatSendInlineForbidden:
            start = time.perf_counter()
            await c.invoke(Ping(ping_id=9999999))
            uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
            end = time.perf_counter()
            ms = round((end - start) * 1000, 2)
            await m.handle_message(
                "PING_TEXT",
                string_args=(pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime),
            )

    else:
        start = time.perf_counter()
        await c.invoke(Ping(ping_id=9999999))
        uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
        end = time.perf_counter()
        ms = round((end - start) * 1000, 2)
        await m.handle_message(
            "PING_TEXT", string_args=(pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime)
        )
