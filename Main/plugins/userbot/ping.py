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
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.utils.essentials import Essentials
from Main.core.decorators import inline_check


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
                "requires_input": False,
            },
        ],
    },
)
async def ping_ub_cmd(c: Client, m: Message):
    user_args = m.user_args
    start = time.perf_counter()
    await c.get_me()
    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    end = time.perf_counter()
    ms = round((end - start) * 1000, 2)
    template = Altruix.get_string("PING_TEXT") or "{0} Pong! {1} ms | {2} Uptime: {3}"
    await m.handle_message(
        template.format(pf["ping_emoji1"], ms, pf["ping_emoji2"], uptime)
    )
