# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from Main import Altruix
from ..utils._updater import *
from Main.core.types.message import Message


@Altruix.register_on_cmd(
    "update",
    cmd_help={
        "help": "Updates your userbot bot.",
        "example": "update",
        "user_args": {"-changelog": "Generate and shows changelog."},
    },
)
async def update(client, message: Message):
    msg = await message.handle_message("PROCESSING")
    updater_ = Updater(
        repo=Altruix.config.REPO, branch="main", app_url=Altruix.app_url_
    )
    await msg.edit_msg("UPDATING")
    repo = await updater_.init_repo()
    if "-changelog" in message.user_args:
        repo = await updater_.init_repo()
        if cl := await updater_.gen_changelog(repo, message, Altruix.config.REPO):
            cl = f"<b>Change-log for AltruiX <i>v{Altruix.__version__}</i></b> \n{cl}"
        else:
            cl = "NO_CHANGES"
        await msg.edit_msg(cl)
    uprem = await updater_.create_remote_and_fetch(repo)
    if Altruix.app_url_:
        await updater_.update_remotely_heroku(uprem, repo, msg)
    else:
        await updater_.update_locally(uprem, repo, msg)
    return await msg.edit_msg("UPDATER_SUCCESS", string_args=(Altruix.__version__))
