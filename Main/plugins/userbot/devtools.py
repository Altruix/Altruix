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
from Main.core.types.client import AltruixTelegramClient as Client
from time import perf_counter as pc
from Main.core.config import TGLIMITS
from Main.core.types.message import Message
from Main.utils.dev_func import eval_py, exec_terminal


@Altruix.register_on_cmd(
    ["json"],
    cmd_help={
        "help": "Gets the json of the given message object.",
        "example": "json",
        "user_args": [
            {
                "arg": "p",
                "help": "Pastes the output to paste bin.",
                "requires_input": False,
            },
            {
                "arg": "f",
                "help": "Force sends the output as a file.",
                "requires_input": False,
            },
            {
                "arg": "s",
                "help": "Sends the output to log chat and deletes the command.",
                "requires_input": False,
            },
        ],
    },
)
async def get_json_message_handler(c: Client, m: Message):
    user_args = m.user_args
    msg_id = m.id
    rm = m.reply_to_message
    m_ = await m.handle_message("PROCESSING")
    target = rm or m
    jsonified = f"<pre>{str(target)}</pre>"
    cmd_ = "<b>jsonified</b>"
    await m_.edit_msg(
        jsonified,
        force_paste="p" in user_args,
        force_file=f"message.json;{cmd_}" if "f" in user_args else None,
        reply_to_message_id=msg_id,
    )


@Altruix.register_on_cmd(
    ["ex", "exec", "eval"],
    cmd_help={
        "help": "Executes the python snippet inside telegram.",
        "example": "eval print('Hello World!')",
        "user_args": [
            {
                "arg": "p",
                "help": "Pastes the output to paste bin.",
                "requires_input": False,
            },
            {
                "arg": "f",
                "help": "Force sends the output as a file.",
                "requires_input": False,
            },
            {
                "arg": "s",
                "help": "Sends the output to log chat and deletes the command.",
                "requires_input": False,
            },
        ],
    },
    just_exc=True,
)
async def evaluate_command_handler(c: Client, m: Message):
    msg_id = m.id
    m_ = await m.handle_message("PROCESSING")
    is_owner = (
        m.out
        or (getattr(m, "from_user", None) and getattr(m.from_user, "is_self", False))
        or (m.sender_id and m.sender_id == getattr(c.myself, "id", None))
    )
    if not is_owner:
        return await m_.edit_msg("❌ <b>Security Violation:</b> <code>Only the userbot owner can evaluate code.</code>")

    user_args = m.user_args
    cmd = m.raw_user_input
    if not cmd:
        await m_.edit_msg("INPUT_REQUIRED")
        return
    if "p" in user_args or "f" in user_args:
        cmd = (cmd.replace("-p", "").replace("-f", "")).strip()
    results = await eval_py(c, cmd, m)
    final_output = f"<b>INPUT:</b>\n<code>{cmd}</code>\n\n<b>OUTPUT</b>:\n<pre>{results.strip()}</pre>"
    cmd_ = "<b>Output Of Command</b>" if len(cmd) >= 1000 else f"<b>OUTPUT FOR COMMAND :</b> <code>{cmd}</code>"

    temp_dir = os.path.abspath("./temp")
    os.makedirs(temp_dir, exist_ok=True)
    if "s" in user_args and Altruix.log_chat:
        if "p" in user_args:
            service, url = await Paste(final_output).paste()
            msg = await c.send_message(Altruix.log_chat, f"{cmd_} \n<b>Pasted to {service}:</b> {url}", parse_mode="html")
        elif "f" in user_args or len(final_output) >= TGLIMITS.MESSAGE_TEXT:
            file_path = os.path.join(temp_dir, f"out_eval_{m.id}.txt")
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(final_output)
            msg = await c.send_file(Altruix.log_chat, file_path, caption=cmd_)
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            msg = await c.send_message(Altruix.log_chat, final_output, parse_mode="html")
        return await m.edit_msg("<b>OUTPUT sent to log chat!</b>")

    await m_.edit_msg(
        final_output,
        force_paste="p" in user_args,
        force_file=f"eval_output.txt;{cmd_}" if "f" in user_args else None,
        reply_to_message_id=msg_id,
    )


@Altruix.register_on_cmd(
    ["term", "terminal", "run", "bash"],
    just_exc=True,
    cmd_help={
        "help": "Executes command in terminal.",
        "example": "term echo Hello World!",
        "user_args": [
            {
                "arg": "p",
                "help": "Pastes the output to paste bin.",
                "requires_input": False,
            },
            {
                "arg": "f",
                "help": "Force sends the output as a file.",
                "requires_input": False,
            },
            {
                "arg": "s",
                "help": "Sends the output to log chat and deletes the command.",
                "requires_input": False,
            },
        ],
    },
)
async def terminal(c: Client, m: Message):
    is_owner = (
        m.out
        or (getattr(m, "from_user", None) and getattr(m.from_user, "is_self", False))
        or (m.sender_id and m.sender_id == getattr(c.myself, "id", None))
    )
    if not is_owner:
        return await m.handle_message("❌ <b>Security Violation:</b> <code>Only the userbot owner can execute terminal commands.</code>")

    user_args = m.user_args
    bash_code = m.raw_user_input
    if not bash_code:
        return await m.handle_message("TERM_INPUT_REQUIRED")
    ms_id = m.id
    m_ = await m.handle_message("CMD_RUNNING")
    if "p" in user_args or "f" in user_args:
        bash_code = (bash_code.replace("-p", "").replace("-f", "")).strip()
    success, output, return_code = await exec_terminal(bash_code)
    out_text = f"<b>Input:</b>\n<code>{bash_code}</code>"
    out_text += f'\n\n<b>{Altruix.get_string("OUTPUT") or "Output"}:</b>\n<pre>{output or Altruix.get_string("NO_OUTPUT") or "No output"}</pre>\n'
    out_text += f"<b>Status:</b> <i>{'Success' if success else 'Failed'}</i> (<code>{return_code}</code>)"
    caption_ = "<b>OUTPUT OF CMD EXECUTED</b>"

    temp_dir = os.path.abspath("./temp")
    os.makedirs(temp_dir, exist_ok=True)
    if "s" in user_args and Altruix.log_chat:
        if "p" in user_args:
            service, url = await Paste(out_text).paste()
            await c.send_message(Altruix.log_chat, f"{caption_} \n<b>Pasted to {service}:</b> {url}", parse_mode="html")
        elif "f" in user_args or len(out_text) >= TGLIMITS.MESSAGE_TEXT:
            file_path = os.path.join(temp_dir, f"out_bash_{m.id}.txt")
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(out_text)
            await c.send_file(Altruix.log_chat, file_path, caption=caption_)
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await c.send_message(Altruix.log_chat, out_text, parse_mode="html")
        return await m_.edit_msg("<b>OUTPUT sent to log chat!</b>")

    return await m_.edit_msg(
        out_text,
        force_paste="p" in user_args,
        force_file=f"bash_output.txt;{caption_}" if "f" in user_args else None,
        reply_to_message_id=ms_id,
    )


async def paste_logs(log_path: str) -> str:
    async with aiofiles.open(log_path, mode="r", encoding="utf-8", errors="ignore") as f:
        file_c = await f.read()
        name, link = await Paste(file_c).paste()
    return f"<b>LOGS PASTED TO {name.upper()}:</b> <a href='{link}'>View</a>"


@Altruix.register_on_cmd(
    "logs",
    cmd_help={
        "help": "Retrieve logs of the bot.",
        "example": "logs",
        "user_args": [
            {
                "arg": "p",
                "help": "Pastes the logs to paste bin.",
                "requires_input": False,
            },
            {
                "arg": "s",
                "help": "Silently sends logs to log chat.",
                "requires_input": False,
            },
            {"arg": "r", "help": "Resets logs.", "requires_input": False},
        ],
    },
)
async def logs(c: Client, m: Message):
    log_file_ = "altruix.log"
    start = pc()
    log__args_ = m.user_args
    MSG = await m.handle_message("PROCESSING")
    if not os.path.exists(log_file_):
        with open(log_file_, "w", encoding="utf-8") as lf:
            lf.write("Altruix log initialized.\n")
        return await MSG.edit_msg("ERROR_404_NO_LOG_FILE")

    if os.stat(log_file_).st_size == 0:
        return await MSG.edit_msg("ERROR_404_NO_LOG_FILE")

    if "r" in log__args_:
        with open(log_file_, "w", encoding="utf-8") as lf:
            lf.write("")
        return await MSG.edit_msg("LOGS_RESET")

    if "s" in log__args_ and Altruix.log_chat:
        if "p" not in log__args_:
            await c.send_file(Altruix.log_chat, log_file_, caption="Altruix Logs")
        else:
            await c.send_message(Altruix.log_chat, await paste_logs(log_file_), parse_mode="html")
        return await MSG.edit_msg("<b>Logs sent to log chat!</b>")

    if "p" in log__args_:
        return await MSG.edit_msg(await paste_logs(log_file_))

    await MSG.delete()
    end = pc()
    time_taken = round(end - start, 2)
    await c.send_file(
        m.chat.id,
        log_file_,
        caption=f"Retrieved logs in <code>{time_taken}s</code>.",
        reply_to=m.id,
        parse_mode="html",
    )
