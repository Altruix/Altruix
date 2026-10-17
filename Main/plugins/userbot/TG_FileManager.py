# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import time
from Main import Altruix
from Main.core.types.message import Message
from Main.utils.essentials import Essentials


@Altruix.register_on_cmd(
    ["download"],
    cmd_help={"help": "Download files from telegram", "example": "download"},
    requires_reply=True,
)
async def download_files_from_telegram(c, m: Message):
    msg = await m.handle_message("PROCESSING")
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm or not rm.file:
        return await msg.edit_msg("REPLY_TO_FILE")
    input_ = m.user_input
    user_args = m.user_args
    start_time = time.time()
    downloads_path = "./temp/thumb.jpg" if "-sethumb" in user_args else "./temp/downloads/"
    if not os.path.exists(downloads_path):
        os.makedirs(downloads_path, exist_ok=True)

    target_file = (downloads_path + (input_ or "")) if not downloads_path.endswith(".jpg") else downloads_path
    file_ = await rm.download_media(file=target_file)
    end_time = round(time.time() - start_time, 2)
    await msg.edit_msg("FILE_DOWNLOADED", string_args=(file_, end_time))


@Altruix.register_on_cmd(
    ["upload"],
    cmd_help={"help": "Upload files to telegram", "example": "upload Altruix.log"},
    requires_input=True,
)
async def upload_files_to_telegram(c, m: Message):
    start_time = time.time()
    msg = await m.handle_message("PROCESSING")
    input_ = m.user_input.strip()
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    msg_id = rm.id if rm else m.id
    thumb = "./temp/thumb.jpg" if os.path.exists("./temp/thumb.jpg") else ("./cache/thumb.jpg" if os.path.exists("./cache/thumb.jpg") else None)
    if not os.path.exists(input_) or not os.path.isfile(input_):
        return await msg.edit_msg("404_FILE_NOT_FOUND")

    chat_target = m.chat_id or (getattr(m.chat, "id", None))
    await c.send_file(
        chat_target,
        input_,
        thumb=thumb,
        reply_to=msg_id,
    )
    time_taken = round(time.time() - start_time, 2)
    file_size = Essentials.humanbytes(os.stat(input_).st_size)
    await msg.edit_msg("FILE_UPLOAD", string_args=(input_, file_size, time_taken))
