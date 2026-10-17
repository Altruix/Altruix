# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import glob
import time
from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.utils.essentials import Essentials


@Altruix.register_on_cmd(
    "alive",
    cmd_help={"help": "Checks Alive status of UB", "example": "alive"},
)
async def alive(c: Client, m: Message):
    version = Altruix.__version__
    uptime = Essentials.get_readable_time(time.time() - Altruix.start_time)
    path_ = "./cache/alive.*"
    files = glob.glob(path_)
    file = files[0] if files else ""
    template = Altruix.get_string("ALIVE_TEXT") or "<b>Altruix Userbot (Telethon) is Alive!</b>\nVersion: <code>{0}</code>\nUptime: <code>{1}</code>"
    text = template.format(version, uptime)
    if os.path.exists(file):
        await m.reply_file(file, caption=text)
        return await m.delete_if_self()
    await m.handle_message(text)
