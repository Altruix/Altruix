# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import shutil
import logging
from traceback import format_exc
from Main import Altruix
from Main.core.apm import *
from Main.core.types.message import Message


packages_list = Altruix.db.make_collection("packages") if Altruix.db else None


@Altruix.register_on_cmd(
    ["apm_install", "apm"],
    cmd_help={
        "example": "apm_install https://github.com/username/my-altruix-plugin",
        "help": "Install external plugins or packages for Altruix from a GitHub repository or direct URL.",
        "user_args": [
            {
                "arg": "ios",
                "help": "Persist and install package on startup.",
                "requires_input": False,
            },
        ],
    },
    requires_input=True,
)
async def install_pack(c, m: Message):
    msg = await m.handle_message("PROCESSING")
    source = m.user_input.strip()

    # Priority 1: Use modern PluginManager (APM v2)
    if Altruix.plugin_manager is not None:
        try:
            provider = "github"
            if source.startswith(("http://", "https://")) and "github.com" not in source:
                provider = "url"
            manifest = await Altruix.plugin_manager.install(source, provider=provider, msg=msg)
            if manifest:
                name = manifest.name
                author = manifest.author or "Unknown"
                version = manifest.version or "1.0.0"
                await msg.edit_msg(
                    f"✅ <b>Successfully installed plugin:</b> <code>{name}</code>\n"
                    f"• <b>Author:</b> {author}\n"
                    f"• <b>Version:</b> <code>{version}</code>"
                )
                if "ios" in m.user_args and packages_list:
                    if pl := await packages_list.find_one({"_id": "APM"}):
                        await packages_list.update_one(
                            {"_id": "APM"}, {"$addToSet": {"installed_packages": source}}
                        )
                    else:
                        await packages_list.insert_one(
                            {"_id": "APM", "installed_packages": [source]}
                        )
                return
        except ValueError as e:
            return await msg.edit_msg(f"⚠️ {e}")
        except Exception as e:
            logging.error(format_exc())
            if source.startswith(("http://", "https://", "git@")) or "/" in source:
                return await msg.edit_msg(f"❌ <b>Installation Failed:</b> <code>{e}</code>")

    # Priority 2: Fallback to legacy APM client for bare package names
    apm_client = APM(Altruix)
    try:
        resp = await apm_client.install_package(source, msg)
    except Package404:
        return await msg.edit_msg("PACKAGE_NOT_FOUND")
    except AlreadyInstalled:
        return await msg.edit_msg("ALREADY_APM_INSTALLED", string_args=(source,))
    except Exception as e:
        logging.error(format_exc())
        return await msg.edit_msg("PLUGIN_INSTALL_ERROR", string_args=(e,))

    if os.path.exists("./Main/plugins/temp_app/"):
        shutil.rmtree("./Main/plugins/temp_app/")

    await msg.edit_msg(
        "INSTALLED_PACKAGE", string_args=(resp.Name, resp.developer, resp.version)
    )
    if "ios" in m.user_args and packages_list:
        if pl := await packages_list.find_one({"_id": "APM"}):
            await packages_list.update_one(
                {"_id": "APM"}, {"$addToSet": {"installed_packages": resp.Name}}
            )
        else:
            await packages_list.insert_one(
                {"_id": "APM", "installed_packages": [resp.Name]}
            )


@Altruix.register_on_cmd(
    ["apm_list", "apm_plugins"],
    cmd_help={
        "help": "List all installed external plugins.",
        "example": "apm_list",
    },
)
async def list_packs(c, m: Message):
    msg = await m.handle_message("PROCESSING")
    if Altruix.plugin_manager is not None:
        installed = await Altruix.plugin_manager.list_installed()
        if not installed:
            return await msg.edit_msg("ℹ️ No external plugins currently installed.")
        text = "<b>📦 Installed External Plugins:</b>\n\n"
        for p in installed:
            text += f"• <b>{p.name}</b> (v{p.version}) by <i>{p.author}</i>\n  Source: <code>{p.source}</code>\n"
        return await msg.edit_msg(text)
    return await msg.edit_msg("Plugin manager is not active.")


@Altruix.register_on_cmd(
    "apm_get",
    cmd_help={"example": "apm_get vcplayer", "help": "Get information about an APM package"},
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
    ["apm_rem", "apm_rm", "apm_uninstall"],
    cmd_help={
        "help": "Remove an installed external plugin or package",
        "example": "apm_rem my-plugin",
    },
    requires_input=True,
)
async def remove_pack(c, m: Message):
    msg = await m.handle_message("PROCESSING")
    pn = m.user_input.strip()

    # Check modern PluginManager first
    if Altruix.plugin_manager is not None and pn in Altruix.plugin_manager._installed:
        success = await Altruix.plugin_manager.uninstall(pn, msg=msg)
        if success:
            if packages_list:
                pk_ = await packages_list.find_one({"_id": "APM"})
                if pk_ and pk_.get("installed_packages"):
                    await packages_list.update_one(
                        {"_id": "APM"}, {"$pull": {"installed_packages": pn}}
                    )
            return await msg.edit_msg(f"🗑️ <b>Package uninstalled:</b> <code>{pn}</code>")

    # Fallback to legacy APM
    ac = APM(Altruix)
    if packages_list:
        pk_ = await packages_list.find_one({"_id": "APM"})
        if pk_ and pn in (pk_["installed_packages"] if pk_.get("installed_packages") else []):
            await packages_list.update_one(
                {"_id": "APM"}, {"$pull": {"installed_packages": pn}}
            )
    resp = await ac.uninstall_package(pn, msg)
    if resp is False:
        return await msg.edit_msg("PACKAGE_NOT_INSTALLED", string_args=(pn,))
    await msg.edit_msg("PACKAGE_REMOVED", string_args=(pn,))
