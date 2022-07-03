# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

"""
A-Z for sudo users!
"""

from Main import Altruix
from style import bullets
from pyrogram import Client
from ...core.types.message import Message


b4 = bullets["bullet4"]
b5 = bullets["bullet5"]
b6 = bullets["bullet6"]
b7 = bullets["bullet7"]


def bulletify(u_):
    out = "<b>Sudo Users :</b> \n"
    len_ = len(u_)
    if len_ == 1:
        return f"{out}\n{b6}{b4} {u_[0].mention}"
    if len_ == 2:
        return f"{out}\n{b5}{b4} {u_[0].mention}\n{b7}{b4} {u_[1].mention}"
    for i in enumerate(u_):
        if i[0] == 0:
            out += f"\n{b5}{b4} {i[1].mention}"
        elif i[0] == len_ - 1:
            out += f"\n{b7}{b4} {i[1].mention}"
        else:
            out += f"\n{b6}{b4} {i[1].mention}"
    return out


@Altruix.register_on_cmd(
    "dpfs",
    cmd_help={"help": "Disabled cmds for sudo users!", "example": "dpfs eval"},
    requires_input=True,
)
async def disabled_ps_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    input_ = m.user_input.strip()
    if "," in input_:
        input_ = input_.split(",").strip()
    await Altruix.config.sync_env_to_db("DISABLED_SUDO_CMD_LIST", input_, push_=True)
    await msg.edit_msg("DISABLED_SUDO_CMD", string_args=(input_))


@Altruix.register_on_cmd(
    "rmdfs",
    cmd_help={"help": "Disabled cmds from sudo users", "example": "dpfs eval"},
    requires_input=True,
)
async def remove_disabled_ps_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    input_ = m.user_input.strip()
    if "," in input_:
        input_ = input_.split(",")
    await Altruix.config.unsync_env_to_db("DISABLED_SUDO_CMD_LIST", input_)
    await msg.edit_msg("UNDISABLED_SUDO_CMD", string_args=(input_))


@Altruix.register_on_cmd(
    "addsudo",
    cmd_help={
        "help": "Add a user to sudo list, requires restart once done!",
        "example": "addsudo @warner_stark",
    },
)
async def add_sudo_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user, reason, is_channel = m.get_user
    if not user or is_channel:
        return await msg.edit_msg("INVALID_USER")
    try:
        user_id = await c.get_users(user)
    except Exception:
        return await msg.edit_msg("INVALID_USER")
    if user_id.id in (await Altruix.config.get_sudo()):
        return await msg.edit_msg("ALREADY_IN_SUDO")
    await Altruix.config.add_sudo(user_id.id)
    await msg.edit_msg("ADDED_SUDO", string_args=(user_id.mention))


@Altruix.register_on_cmd(
    "rmsudo",
    cmd_help={
        "help": "remove sudo from sudo list, requires a restart to reflect the changes",
        "example": "rmsudo @warner_stark",
    },
)
async def add_sudo_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user, _, is_channel = m.get_user
    if not user or is_channel:
        return await msg.edit_msg("INVALID_USER")
    try:
        user_id = await c.get_users(user)
    except Exception:
        return await msg.edit_msg("INVALID_USER")
    if user_id.id not in (await Altruix.config.get_sudo()):
        return await msg.edit_msg("NOT_IN_SUDO")
    await Altruix.config.del_sudo(user_id.id)
    await msg.edit_msg("DEL_SUDO", string_args=(user_id.mention))


@Altruix.register_on_cmd(
    "listsudo", cmd_help={"help": "list all sudo users!", "example": "listsudo"}
)
async def add_sudo_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    users_ = await Altruix.config.get_sudo()
    if not users_:
        return await msg.edit_msg("NO_SUDO_LIST")
    user_ = []
    for i in users_:
        try:
            user_.append(await c.get_users(int(i)))
        except Exception:
            continue
    if not user_:
        return await msg.edit_msg("NO_SUDO_LIST")

    await msg.edit_msg(bulletify(user_))
