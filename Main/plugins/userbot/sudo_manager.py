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
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message


b4 = bullets.get("bullet4", "•")
b5 = bullets.get("bullet5", "├")
b6 = bullets.get("bullet6", "│")
b7 = bullets.get("bullet7", "└")


def bulletify(u_):
    out = "<b>Sudo Users :</b> \n"
    len_ = len(u_)
    if len_ == 1:
        mention = getattr(u_[0], "mention", str(u_[0].id))
        return f"{out}\n{b6}{b4} {mention}"
    if len_ == 2:
        m0 = getattr(u_[0], "mention", str(u_[0].id))
        m1 = getattr(u_[1], "mention", str(u_[1].id))
        return f"{out}\n{b5}{b4} {m0}\n{b7}{b4} {m1}"
    for i in enumerate(u_):
        m_curr = getattr(i[1], "mention", str(i[1].id))
        if i[0] == 0:
            out += f"\n{b5}{b4} {m_curr}"
        elif i[0] == len_ - 1:
            out += f"\n{b7}{b4} {m_curr}"
        else:
            out += f"\n{b6}{b4} {m_curr}"
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
        input_ = [x.strip() for x in input_.split(",") if x.strip()]
    else:
        input_ = [input_]
    await Altruix.config.sync_env_to_db("DISABLED_SUDO_CMD_LIST", input_, push_=True)
    current = getattr(Altruix, "disabled_sudo_plugin_list", [])
    Altruix.disabled_sudo_plugin_list = list(dict.fromkeys([*current, *[x.lower() for x in input_]]))
    await msg.edit_msg("DISABLED_SUDO_CMD", string_args=(str(input_),))


@Altruix.register_on_cmd(
    "rmdfs",
    cmd_help={"help": "Disabled cmds from sudo users", "example": "rmdfs eval"},
    requires_input=True,
)
async def remove_disabled_ps_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    input_ = m.user_input.strip()
    if "," in input_:
        input_ = [x.strip() for x in input_.split(",") if x.strip()]
    else:
        input_ = [input_]
    Altruix.disabled_sudo_plugin_list = await Altruix.config.unsync_env_to_db(
        "DISABLED_SUDO_CMD_LIST", input_
    )
    Altruix.disabled_sudo_plugin_list = [str(item).strip().lower() for item in Altruix.disabled_sudo_plugin_list]
    await msg.edit_msg("UNDISABLED_SUDO_CMD", string_args=(str(input_),))


@Altruix.register_on_cmd(
    "addsudo",
    cmd_help={
        "help": "Add a user to sudo list",
        "example": "addsudo @username",
    },
)
async def add_sudo_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user, _, is_channel = m.get_user
    if not user or is_channel:
        return await msg.edit_msg("INVALID_USER")
    target_id = None
    mention_str = None
    try:
        user_ent = await c.get_users(user)
        target_id = user_ent.id
        mention_str = getattr(user_ent, "mention", str(target_id))
    except Exception:
        if isinstance(user, int):
            target_id = user
            mention_str = str(user)
        else:
            return await msg.edit_msg("INVALID_USER")

    sudo_list = await Altruix.config.get_sudo()
    if target_id in sudo_list:
        return await msg.edit_msg("ALREADY_IN_SUDO")
    await Altruix.config.add_sudo(target_id)
    await msg.edit_msg("ADDED_SUDO", string_args=(mention_str,))


@Altruix.register_on_cmd(
    "rmsudo",
    cmd_help={
        "help": "Remove sudo from sudo list",
        "example": "rmsudo @username",
        "user_args": [
            {
                "arg": "a",
                "help": "Removes all sudos from the db.",
                "requires_input": False,
            },
        ],
    },
)
async def rm_sudo_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    user, _, is_channel = m.get_user
    acg = await Altruix.config.get_sudo()
    user_args = m.user_args
    if "a" in user_args:
        count = 0
        lacg = len(acg)
        for i in acg:
            try:
                await Altruix.config.del_sudo(i)
                count += 1
            except Exception:
                pass
        return await msg.edit_msg("DEL_SUDO_A", string_args=(count, lacg))

    if not user or is_channel:
        return await msg.edit_msg("INVALID_USER")

    target_id = None
    mention_str = None
    try:
        user_ent = await c.get_users(user)
        target_id = user_ent.id
        mention_str = getattr(user_ent, "mention", str(target_id))
    except Exception:
        if isinstance(user, int):
            target_id = user
            mention_str = str(user)
        else:
            return await msg.edit_msg("INVALID_USER")

    if target_id not in acg:
        return await msg.edit_msg("NOT_IN_SUDO")
    await Altruix.config.del_sudo(target_id)
    await msg.edit_msg("DEL_SUDO", string_args=(mention_str,))


@Altruix.register_on_cmd(
    "listsudo", cmd_help={"help": "list all sudo users!", "example": "listsudo"}
)
async def list_sudo_func(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    users_ = await Altruix.config.get_sudo()
    if not users_:
        return await msg.edit_msg("NO_SUDO_LIST")
    user_ = []
    for i in users_:
        try:
            user_.append(await c.get_users(int(i)))
        except Exception:
            user_.append(type("DummyUser", (), {"id": int(i), "mention": f"<code>{i}</code>"}))
    if not user_:
        return await msg.edit_msg("NO_SUDO_LIST")

    await msg.edit_msg(bulletify(user_))
