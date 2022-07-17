# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import aiofiles
from Main import Altruix
from logging import info
from Main.utils.paste import Paste
from pyrogram import Client, enums
from time import perf_counter as pc
from Main.core.config import TGLIMITS
from Main.core.types.message import Message
from Main.utils.dev_func import eval_py, exec_terminal


@Altruix.register_on_cmd(
    ["json"],
    cmd_help={
        "help": "Gets the json of the given message object.",
        "example": "json",
        "user_args": {
            "p": "Pastes the output to pastebin.",
            "f": "Force sends the output as a file.",
            "s": "Sends the output to log chat.",
        },
    },
)
async def get_json(c: Client, m: Message):
    user_args = m.user_args
    msg_id = m.id
    rm = m.reply_to_message
    m_ = await m.handle_message("PROCESSING")
    jsonified = f"<code>{rm or m}</code>"
    cmd_ = "<b>jsonified</b>"
    await m_.edit_msg(
        jsonified,
        force_paste="_paste" in user_args,
        force_file=f"message.json;{cmd_}" if "-file" in user_args else None,
        reply_to_message_id=msg_id,
    )


@Altruix.register_on_cmd(
    ["ex", "exec", "eval"],
    cmd_help={
        "help": "Executes the python snippet inside telegram.",
        "example": "eval print('Hello World!')",
        "user_args": {
            "file": "Force sends the output as a file.",
            "paste": "Pastes the output to pastebin.",
        },
    },
    just_exc=True,
)
async def evaluate_command_handler(c: Client, m: Message):
    msg_id = m.id
    m_ = await m.handle_message("PROCESSING")
    user_args = m.user_args
    cmd = m.raw_user_input
    if not cmd:
        await m_.edit_msg("INPUT_REQUIRED")
        return
    if "-paste" in user_args or "-file" in user_args:
        cmd = (cmd.replace("-paste", "").replace("-file", "")).strip()
    results = await eval_py(c, cmd, m)
    final_output = f"<b>INPUT:</b>\n<code>{cmd}</code>\n\n<b>OUTPUT</b>:\n<code>{results.strip()}</code>"
    cmd_ = (
        "<b>Output Of Command</b>"
        if len(cmd) >= 1000
        else f"<b>OUTPUT FOR COMMAND :</b> <code>{cmd}</code>"
    )
    if "-s" in user_args and Altruix.log_chat:
        if "-paste" in user_args:
            url = await Paste(final_output).paste()
            msg = await c.send_message(
                Altruix.log_chat, f"{cmd_} \n<b>Pasted to :</b> {url}"
            )
        elif "-file" in user_args or len(final_output) >= TGLIMITS.MESSAGE_TEXT:
            file_path = f"out_bash_{m.id}.txt"
            async with aiofiles.open(file_path, "w") as f:
                await f.write(final_output)
            msg = await c.send_document(Altruix.log_chat, file_path, caption=cmd)
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            msg = await c.send_message(Altruix.log_chat, final_output)
        return await m.edit_msg(f"<b>OUTPUT :</b> <a href='{msg.link}'>VIEW</a>")
    await m_.edit_msg(
        final_output,
        force_paste="-paste" in user_args,
        force_file=f"eval_output.txt;{cmd_}" if "-file" in user_args else None,
        reply_to_message_id=msg_id,
    )


@Altruix.register_on_cmd(
    ["term", "terminal", "run", "bash"],
    just_exc=True,
    cmd_help={
        "help": "Executes command in terminal.",
        "example": "term echo Hello World!",
        "user_args": {
            "file": "Force sends the output as a file.",
            "paste": "Pastes the output to pastebin.",
        },
    },
)
async def terminal(c: Client, m: Message):
    user_args = m.user_args
    bash_code = m.raw_user_input
    if not bash_code:
        return await m.handle_message("TERM_INPUT_REQUIRED")
    ms_id = m.id
    m = await m.handle_message("CMD_RUNNING")
    if "-paste" in user_args or "-file" in user_args:
        bash_code = (bash_code.replace("-paste", "").replace("-file", "")).strip()
    success, output, return_code = await exec_terminal(bash_code)
    out_text = f"<b>Input</b>\n<code>{bash_code}</code>"
    _out_text = out_text
    _out_text += f'\n\n<b>{Altruix.get_string("OUTPUT")}</b>\n<code>{output or Altruix.get_string("NO_OUTPUT")}</code>\n'
    _out_text += "<b>Status</b>: "
    _out_text += "<i>Success</i> " if success else "<i>Failed</i> "
    _out_text += f"(<code>{return_code}</code>)"
    ttwp = out_text if len(out_text) <= 3999 else None
    caption_ = out_text if len(out_text) <= 9999 else "<b>OUTPUT OF CMD EXECUTED</b>"
    if "-s" in user_args and Altruix.log_chat:
        if "-paste" in user_args:
            url = await Paste(_out_text).paste()
            msg = await c.send_message(
                Altruix.log_chat, f"{caption_} \n<b>Pasted to :</b> {url}"
            )
        elif "-file" in user_args or len(out_text) >= TGLIMITS.MESSAGE_TEXT:
            file_path = f"out_bash_{m.id}.txt"
            async with aiofiles.open(file_path, "w") as f:
                await f.write(_out_text)
            msg = await c.send_document(Altruix.log_chat, file_path, caption=caption_)
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            msg = await c.send_message(Altruix.log_chat, _out_text)
        return await m.edit_msg(f"<b>OUTPUT :</b> <a href='{msg.link}'>VIEW</a>")
    return await m.edit_msg(
        _out_text,
        force_paste="-paste" in user_args,
        force_file=f"bash_output.txt;{caption_}" if "-file" in user_args else None,
        reply_to_message_id=ms_id,
        ttwp=ttwp,
    )


async def paste_logs(log_path):
    async with aiofiles.open(log_path, mode="r") as f:
        file_c = await f.read()
        name, link = await Paste(file_c).paste()
    return f"<b>LOGS HAS BEEN PASTED TO {name.upper()}</b> : [View]({link})"


@Altruix.register_on_cmd(
    "logs",
    cmd_help={
        "help": "Retrieve logs of the bot.",
        "example": "logs",
        "user_args": {
            "paste": "Pastes logs to a pastebin.",
            "s": "Silently sends logs to log chat.",
            "r": "Resets logs.",
        },
    },
)
async def logs(c: Client, m: Message):
    log_file_ = "altruix.log"
    start = pc()
    log__args_ = m.user_args
    MSG = await m.handle_message("PROCESSING")
    if not os.path.exists(log_file_):
        with open(log_file_, "w") as log_file:
            log_file.write("A log file has been created!")
        info("A log file has been created!")
        return await MSG.edit_msg("ERROR_404_NO_LOG_FILE")
    file_size_ = os.stat(log_file_).st_size
    if file_size_ == 0:
        return await MSG.edit_msg("ERROR_404_NO_LOG_FILE")
    if "-r" in log__args_:
        with open(log_file_, "w") as log_file:
            log_file.write("")
        info("Logs have been reset!")
        return await MSG.edit_msg("LOGS_RESET")
    if "-s" in log__args_ and Altruix.log_chat:
        msg = (
            await c.send_document(
                Altruix.log_chat,
                log_file_,
                file_name="AltruiX_logs.txt",
                caption="LOGS of your Altruix Userbot.",
            )
            if "_paste" not in log__args_
            else await c.send_message(Altruix.log_chat, (await paste_logs(log_file_)))
        )
        return await MSG.edit_msg(
            f"**LOGS HERE :** [VIEW]({msg.link})", parse_mode=enums.ParseMode.MARKDOWN
        )
    if "_paste" in log__args_:
        return await MSG.edit_msg(await paste_logs(log_file_))
    msg = await c.send_document(
        m.chat.id,
        log_file_,
        reply_to_message_id=m.id,
        file_name="AltruiX_logs.txt",
    )
    end = pc()
    time_taken = round(end - start, 2)
    await MSG.delete()
    await msg.edit_msg(f"Retrieved logs in <code>{time_taken}</code>s.")
