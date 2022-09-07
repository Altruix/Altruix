# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import re
import uuid
import psutil
import socket
import platform
import contextlib
from Main import Altruix
from Main.utils.essentials import Essentials
from telegraph import Telegraph, upload_file
from pyrogram.types.messages_and_media.message import Message


#telegraph = Telegraph()
#res = telegraph.create_account(short_name="Altruix")
#auth_url = res["auth_url"]


@Altruix.run_in_exc
def get_info():
    splatform = platform.system()
    platform_release = platform.release()
    platform_version = platform.version()
    architecture = platform.machine()
    hostname = socket.gethostname()
    ip_address = "Unable to fetch"
    mac_address = "Unable to fetch"
    with contextlib.suppress(Exception):
        ip_address = socket.gethostbyname(socket.gethostname())
    with contextlib.suppress(Exception):
        mac_address = ":".join(re.findall("..", "%012x" % uuid.getnode()))
    processor = platform.processor()
    ram = Essentials.humanbytes(round(psutil.virtual_memory().total))
    cpu_freq = psutil.cpu_freq().current
    if cpu_freq >= 1000:
        cpu_freq = f"{round(cpu_freq / 1000, 2)}GHz"
    else:
        cpu_freq = f"{round(cpu_freq, 2)}MHz"
    du = psutil.disk_usage(os.getcwd())
    psutil.disk_io_counters()
    disk = (
        f"{Essentials.humanbytes(du.used)}/{Essentials.humanbytes(du.total)}"
        f"({du.percent}%)"
    )
    cpu_len = len(psutil.Process().cpu_affinity())
    return (
        splatform,
        platform_release,
        platform_version,
        architecture,
        hostname,
        ip_address,
        mac_address,
        processor,
        ram,
        cpu_len,
        cpu_freq,
        disk,
    )


@Altruix.register_on_cmd(
    ["ubstat", "stat"],
    cmd_help={
        "help": "Get info about your machine.",
        "example": "ubstat",
    },
)
async def sTATS(c: Altruix, m: Message):
    msg = await m.handle_message("PROCESSING")
    ub_stat = tuple(await get_info())
    database_ = await Altruix.db._db_name.command("dbstats")
    s = ub_stat + (
        Essentials.humanbytes(database_["dataSize"]),
        Essentials.humanbytes(database_.get("storageSize")),
    )
    out_ = tuple(s)
    await msg.edit_msg("UBSTAT", string_args=out_)


#@Altruix.register_on_cmd(
#    ["telegraph", "tg"],
#    cmd_help={
#        "help": "upload files to telegraph",
#        "cmd_help": "telgraph <reply to media>",
#    },
#    requires_reply=True,
#)
#async def download_files_from_telegram(c, m):
#    msg = await m.handle_message("PROCESSING")
#    if not m.reply_to_message.media:
#        return await msg.edit_msg("REPLY_TO_FILE")
#    media = await m.reply_to_message.download()
#    media_url = upload_file(media)
#    await msg.edit(f"https://telegra.ph{media_url[0]}")
#    if os.path.exists(media):
#        os.remove(media)
#