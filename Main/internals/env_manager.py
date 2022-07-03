# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from Main import Altruix
from Main.core.types.message import Message


@Altruix.register_on_cmd(
    "addenv",
    cmd_help={
        "help": "Adds Env to database!",
        "example": "addenv env_varname env_value",
    },
    requires_input=True,
)
async def add_env_cmd_handler(c: Altruix, m: Message):
    ms = await m.handle_message("PROCESSING")
    input_ = m.user_input
    if " " not in input_:
        return await ms.edit_msg("PROPER_INPUT_REQ")
    env_key, value = input_.split(" ", maxsplit=1)
    await Altruix.config.sync_env_to_db(env_key, value)
    await ms.edit_msg("ENV_ADDED", string_args=(env_key, value))


@Altruix.register_on_cmd(
    "delenv",
    cmd_help={
        "help": "Deletes env from database!",
        "example": "delenv env_varname",
    },
    requires_input=True,
)
async def del_env_cmd_handler(c: Altruix, m: Message):
    ms = await m.handle_message("PROCESSING")
    input_ = m.user_input
    if not await Altruix.config.get_env(input_):
        return await ms.edit_msg("NO_ENV_FOUND", string_args=(input))
    await Altruix.config.del_env_from_db(input_)
    await ms.edit_msg("ENV_DELETED", string_args=(input_))


@Altruix.register_on_cmd(
    "getenv",
    cmd_help={"help": "Gets env from database!", "example": "getenv env_varname"},
    requires_input=True,
)
async def get_env_cmd_handler(c: Altruix, m: Message):
    ms = await m.handle_message("PROCESSING")
    input_ = m.user_input
    value = await Altruix.config.get_env(input_)
    if not value:
        return await ms.edit_msg("NO_ENV_FOUND", string_args=(input))
    await ms.edit_msg("ENV_VALUE", string_args=(input_, value))
