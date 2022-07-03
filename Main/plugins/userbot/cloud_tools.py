# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from Main import Altruix
from style import bullets
from pyrogram import Client
from os.path import isdir, exists, isfile
from ...utils.essentials import Essentials
from Main.core.types.message import Message
from os import stat, rmdir, remove as rm, listdir as ls


b1 = bullets["bullet1"]
b2 = bullets["bullet2"]
b3 = bullets["bullet3"]


def readable(data):
    return Essentials.humanbytes(data)


@Altruix.register_on_cmd(
    ["listdir", "list", "ls", "ld"],
    cmd_help={
        "help": "Lists given directory given as input.",
        "example": "ls Main/plugins/userbot",
    },
)
async def listdir_cmd_handler(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    input_ = m.raw_user_input
    if input_:
        if not exists(input_):
            return await msg.edit(
                f"<b>Directory,</b> <code>{input_}</code> <b>doesn't exist.</b>"
            )
        if isfile(input_):
            return await msg.edit(
                f"<code>{input_}</code> <b>is a file not a directory.</b>"
            )
    files = []
    folders = []
    lists = sorted(ls(input_))
    length = len(lists)
    if length == 0:
        return await msg.edit(f"<code>{input_}</code> <b>is an empty folder.</b>")
    for i in lists:
        j = i
        if input_:
            j = f"{input_}/{i}"
        if isdir(j):
            folders.append(f"<code>  {b1} {i}</code>")
        if isfile(j):
            files.append(f"<code>  {b2} {i} ({readable(stat(j).st_size)})</code>")
    if not input_:
        input_ = "Altruix"
    output_ = f"<b>Files and Folders in</b> <code>{input_}</code> (<code>{length}</code>) <b>are :</b> \n\n"
    output_ += (
        f"<code>{b3}</code> <i><b>Folders</b></i> (<code>{len(folders)}</code>):\n"
    )
    output_ += ("\n").join(folders)
    output_ += "\n\n"
    output_ += f"<code>{b3}</code> <i><b>Files</b></i> (<code>{len(files)}</code>):\n"
    output_ += ("\n").join(files)
    del (files, folders)
    if input_ and input_.startswith("/"):
        output_ += (
            f"\n\n<b>Note:</b> <code>{input_}</code> <b>is a parent directory.</b>"
        )
    await msg.edit(f"{output_}")


@Altruix.register_on_cmd(
    ["remove", "rm"],
    cmd_help={
        "help": "Removes given directory or file from the system.",
        "example": "rm -a |*.log",
        "user_args": {
            "d": "to remove a directory from the system.",
            "a": "to remove files of the same type from a directory.",
        },
    },
    requires_input=True,
)
async def remove_cmd_handler(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    input_ = m.raw_user_input
    u_input = m.user_input
    if user_args := m.user_args:
        if "-d" in user_args:
            try:
                if not exists(u_input):
                    return await msg.edit(
                        f"<b>Directory,</b> <code>{u_input}</code> <b>doesn't exist.</b>"
                    )
                elif isfile(u_input):
                    await msg.edit(
                        f"<code>{u_input}</code> <b>is a file not a directory.</b>"
                    )
                else:
                    rmdir(u_input)
                    await msg.edit(
                        f"<b>Folder,</b> <code>{u_input}</code> <b>has been removed successfully.</b>"
                    )
            except OSError as traceback:
                return await msg.edit(
                    f"<b>Unable to delete</b>, <code>{u_input}</code>.\n\n<i><b><u>Traceback:</u></b></i>\n\n<code>{traceback}</code>"
                )
        elif "-a" in user_args:
            if "|*." not in u_input:
                return await msg.edit_msg("INVALID_INPUT")
            data = u_input.split("*")
            if data[0] == "|" or data[1] == ".":
                return await msg.edit_msg("INVALID_INPUT")
            data[0] = data[0].replace("|", "")
            if not exists(data[0]):
                return await msg.edit(
                    f"<b>Directory,</b> <code>{data[0]}</code> <b>doesn't exist.</b>"
                )
            elif isfile(data[0]):
                await msg.edit(f"<code>{data}</code> <b>is a file not a directory.</b>")
            else:
                lists = sorted(ls(data[0]))
                count = 0
                for i in lists:
                    if isfile(f"{data[0]}/{i}") and i.endswith(data[1]):
                        rm(f"{data[0]}/{i}")
                        count += 1
                await msg.edit(
                    f"<b>Removed all files ending with</b> <code>{data[1]}</code> <b>in</b> <code>{data[0]}</code> <b>(</b><code>{count}</code><b>).</b>"
                )

    elif not exists(input_):
        return await msg.edit(
            f"<b>File,</b> <code>{input_}</code> <b>doesn't exist.</b>"
        )
    elif isdir(input_):
        await msg.edit(f"<code>{input_}</code> <b>is a directory not a file.</b>")
    else:
        rm(input_)
        await msg.edit(
            f"<b>File,</b> <code>{input_}</code> <b>has been removed successfully.</b>"
        )
