# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import logging
from Main import Altruix
from ...core.apm import *


packages_list = Altruix.db.make_collection("packages")


@Altruix.register_on_cmd(
    "apm_install",
    cmd_help={
        "example": "apm_install vcplayer",
        "help": "install packages made for altruix.",
        "user_args": {"-ios": "install package on startup!"},
    },
    requires_input=True,
)
async def install_pack(c, m: Message):
    msg = await m.handle_message("PROCESSING")
    package_name = m.user_input
    apm_client = APM(Altruix)
    try:
        resp = await apm_client.install_package(package_name, msg)
    except Package404:
        return await msg.edit_msg("PACKAGE_NOT_FOUND")
    except AlreadyInstalled:
        return await msg.edit_msg("ALREADY_APM_INSTALLED", string_args=(package_name))
    except Exception as e:
        logging.error(format_exc())
        return await msg.edit_msg("PLUGIN_INSTALL_ERROR", string_args=(e))
    if os.path.exists("./Main/plugins/temp_app/"):
        shutil.rmtree("./Main/plugins/temp_app/")
    await msg.edit_msg(
        "INSTALLED_PACKAGE", string_args=(resp.Name, resp.developer, resp.version)
    )
    if "-ios" in m.user_args:
        if pl := await packages_list.find_one({"_id": "APM"}):
            if (
                pl
                and pl.get("installed_packages")
                and resp.Name in pl.get("installed_packages")
            ):
                return await msg.edit_msg("PACKAGE_ALREADY_IN_LIST")
            await packages_list.update_one(
                {"_id": "APM"}, {"$addToSet": {"installed_packages": resp.Name}}
            )
        else:
            await packages_list.insert_one(
                {"_id": "APM", "installed_packages": [resp.Name]}
            )


@Altruix.register_on_cmd(
    "apm_get",
    cmd_help={"example": "apm_get vcplayer", "help": "get information about a module"},
    requires_input=True,
)
async def get_pack(c, m: Message):
    msg = await m.handle_message("PROCESSING")
    pn = m.user_input
    apm_client = APM(Altruix)
    resp = await apm_client.get_package_info(pn)
    if not resp:
        return await msg.edit_msg("PACKAGE_NOT_FOUND")
    await m.edit_msg(
        "PACK_INFO",
        string_args=(
            resp.Name,
            resp.developer,
            resp.version,
            resp.description if getattr(resp, "description") else "No desc provided",
            resp.keywords if getattr(resp, "keywords") else "No keywords given",
        ),
    )


@Altruix.register_on_cmd(
    ["apm_rem", "apm_rm"],
    cmd_help={"help": "remove an installed package", "example": "apm_rem vcplayer"},
    requires_input=True,
)
async def remove_pack(c, m: Message):
    msg = await m.edit_msg("PROCESSING")
    pn = m.user_input
    ac = APM(Altruix)
    pk_ = await packages_list.find_one({"_id": "APM"})
    if (pk_) and (
        pn in (pk_["installed_packages"] if pk_.get("installed_packages") else [])
    ):
        await packages_list.update_one(
            {"_id": "APM"}, {"$pull": {"installed_packages": pn}}
        )
    resp = await ac.uninstall_package(pn, msg)
    if resp is False:
        return await msg.edit_msg("PACKAGE_NOT_INSTALLED", string_args=(pn))
    await msg.edit_msg("PACKAGE_REMOVED", string_args=(pn))
