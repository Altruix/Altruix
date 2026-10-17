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
        "example": "apm_install https://github.com/username/XtraPlugins -sub media,lifestyle",
        "help": "Install external plugins with optional subcategory segregation and fast dependency resolution.",
        "user_args": [
            {
                "arg": "sub",
                "help": "Specify comma-separated subcategories to install (e.g. -sub media,lifestyle).",
                "requires_input": True,
            },
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
    raw = m.user_input.strip()

    # Parse subcategory flag: -sub cat1,cat2
    subcategories = None
    if "-sub " in raw:
        parts = raw.split("-sub ")
        raw = parts[0].strip()
        sub_arg = parts[1].strip().split()[0]
        subcategories = [s.strip() for s in sub_arg.split(",") if s.strip()]

    source = raw.strip()

    # Priority 1: Use modern PluginManager (APM v3)
    if Altruix.plugin_manager is not None:
        try:
            provider = "github"
            if source.startswith(("http://", "https://")) and "github.com" not in source:
                provider = "url"

            manifest = await Altruix.plugin_manager.install(
                source, provider=provider, subcategories=subcategories, msg=msg
            )
            if manifest:
                name = manifest.name
                author = manifest.author or "Unknown"
                version = manifest.version or "1.0.0"
                active_subs = manifest.active_subcategories

                subs_text = ""
                if active_subs:
                    subs_list = ", ".join([f"<code>{s}</code>" for s in active_subs])
                    subs_text = f"\n• <b>Active Subcategories:</b> {subs_list}"

                await msg.edit_msg(
                    f"✅ <b>Successfully installed plugin:</b> <code>{name}</code>\n"
                    f"• <b>Author:</b> {author}\n"
                    f"• <b>Version:</b> <code>{version}</code>"
                    f"{subs_text}"
                )

                if "ios" in m.user_args and packages_list:
                    doc_data = {"source": source, "subcategories": subcategories}
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
    ["apm_list", "apmlist", "plugins"],
    cmd_help={
        "help": "List all installed external plugins with version and active segregated subcategories.",
        "example": "apm_list",
    },
)
async def list_packages(c, m: Message):
    if not Altruix.plugin_manager:
        return await m.handle_message("❌ Plugin Manager not initialized.")

    installed = await Altruix.plugin_manager.list_installed()
    if not installed:
        return await m.handle_message("📦 <b>No external plugins currently installed.</b>\nInstall one via <code>.apm_install &lt;repo&gt;</code>.")

    lines = []
    for idx, p in enumerate(installed, 1):
        subs = p.active_subcategories
        subs_badge = f" [<code>{', '.join(subs)}</code>]" if subs else ""
        quarantine_badge = " ⚠️ <i>(Quarantined)</i>" if p.quarantined else ""
        lines.append(
            f"<b>{idx}.</b> <code>{p.name}</code> (v{p.version}) by <i>{p.author}</i>{quarantine_badge}\n"
            f"   • Source: <code>{p.source}</code>{subs_badge}"
        )

    report = (
        f"📦 <b>Installed Altruix External Plugins ({len(installed)}):</b>\n\n"
        + "\n\n".join(lines)
        + "\n\n<i>Manage subcategories via <code>.apm_sub &lt;plugin&gt;</code></i>"
    )
    await m.handle_message(report)


@Altruix.register_on_cmd(
    ["apm_sub", "apmsub", "subcategories"],
    cmd_help={
        "help": "Inspect segregated subcategories of an installed plugin and their enabled status.",
        "example": "apm_sub XtraPlugins",
    },
    requires_input=True,
)
async def list_plugin_subcategories(c, m: Message):
    if not Altruix.plugin_manager:
        return await m.handle_message("❌ Plugin Manager not initialized.")

    pname = m.user_input.strip()
    manifest = Altruix.plugin_manager._installed.get(pname)
    if not manifest:
        return await m.handle_message(f"❌ Plugin <code>{pname}</code> is not installed.")

    subs = manifest.subcategories
    if not subs:
        return await m.handle_message(f"ℹ️ Plugin <code>{pname}</code> is monolithic and has no segregated subcategories.")

    lines = []
    for sname, sdata in subs.items():
        is_active = sname in manifest.active_subcategories
        status_icon = "🟢 Active" if is_active else "⚪ Disabled"
        deps = sdata.get("dependencies", [])
        deps_str = f" | Deps: {', '.join(deps)}" if deps else " | Zero Deps"
        lines.append(
            f"• <b>{sdata.get('name', sname)}</b> (<code>{sname}</code>) - {status_icon}\n"
            f"  {sdata.get('file_count', 0)} files{deps_str}"
        )

    report = (
        f"🗂 <b>Subcategories for {manifest.name}:</b>\n\n"
        + "\n\n".join(lines)
        + "\n\n<b>Commands:</b>\n"
        f"• <code>.apm_enable {pname} &lt;category&gt;</code>\n"
        f"• <code>.apm_disable {pname} &lt;category&gt;</code>"
    )
    await m.handle_message(report)


@Altruix.register_on_cmd(
    ["apm_enable", "apmenable"],
    cmd_help={
        "help": "Enable and hot-load a segregated subcategory in an installed plugin.",
        "example": "apm_enable XtraPlugins media",
    },
    requires_input=True,
)
async def enable_subcategory_cmd(c, m: Message):
    if not Altruix.plugin_manager:
        return await m.handle_message("❌ Plugin Manager not initialized.")

    tokens = m.user_input.strip().split()
    if len(tokens) < 2:
        return await m.handle_message("⚠️ <b>Usage:</b> <code>.apm_enable &lt;plugin_name&gt; &lt;subcategory&gt;</code>")

    pname, sub = tokens[0], tokens[1].lower()
    success = await Altruix.plugin_manager.enable_subcategory(pname, sub)
    if success:
        await m.handle_message(f"✅ Subcategory <code>{sub}</code> in <b>{pname}</b> enabled and loaded!")
    else:
        await m.handle_message(f"❌ Failed to enable subcategory <code>{sub}</code>. Check plugin name and subcategories.")


@Altruix.register_on_cmd(
    ["apm_disable", "apmdisable"],
    cmd_help={
        "help": "Disable a segregated subcategory in an installed plugin without deleting files.",
        "example": "apm_disable XtraPlugins shopping",
    },
    requires_input=True,
)
async def disable_subcategory_cmd(c, m: Message):
    if not Altruix.plugin_manager:
        return await m.handle_message("❌ Plugin Manager not initialized.")

    tokens = m.user_input.strip().split()
    if len(tokens) < 2:
        return await m.handle_message("⚠️ <b>Usage:</b> <code>.apm_disable &lt;plugin_name&gt; &lt;subcategory&gt;</code>")

    pname, sub = tokens[0], tokens[1].lower()
    success = await Altruix.plugin_manager.disable_subcategory(pname, sub)
    if success:
        await m.handle_message(f"⚪ Subcategory <code>{sub}</code> in <b>{pname}</b> disabled. Restart Altruix to unload active handlers.")
    else:
        await m.handle_message(f"❌ Failed to disable subcategory <code>{sub}</code>.")


@Altruix.register_on_cmd(
    ["apm_doctor", "apmdoctor"],
    cmd_help={
        "help": "Diagnose the health of all installed plugins, verify Python imports, and detect missing packages.",
        "example": "apm_doctor",
    },
)
async def doctor_cmd(c, m: Message):
    if not Altruix.plugin_manager:
        return await m.handle_message("❌ Plugin Manager not initialized.")

    msg = await m.handle_message("🩺 Running APM health check across all plugins and Python environment...")
    doc = await Altruix.plugin_manager.doctor()

    total = doc["total_plugins"]
    healthy = len(doc["healthy"])
    issues = doc["issues"]

    status_icon = "🟢 Healthy" if not issues else "⚠️ Issues Found"

    issue_block = ""
    if issues:
        issue_lines = [f"  • {iss}" for iss in issues]
        issue_block = "\n\n<b>Detected Issues:</b>\n" + "\n".join(issue_lines) + "\n\n<i>Run <code>.apm_repair</code> to batch-install missing packages!</i>"

    report = (
        f"🩺 <b>APM Diagnostic Doctor Report</b>\n\n"
        f"• <b>Status:</b> {status_icon}\n"
        f"• <b>Plugins Inspected:</b> <code>{total}</code>\n"
        f"• <b>Fully Satisfied:</b> <code>{healthy}/{total}</code>"
        f"{issue_block}"
    )
    await msg.edit_msg(report)


@Altruix.register_on_cmd(
    ["apm_repair", "apmrepair", "apmfix"],
    cmd_help={
        "help": "Batch-install any missing dependencies across all installed plugins without restarting the bot.",
        "example": "apm_repair",
    },
)
async def repair_cmd(c, m: Message):
    if not Altruix.plugin_manager:
        return await m.handle_message("❌ Plugin Manager not initialized.")

    msg = await m.handle_message("🔧 Scanning and resolving missing plugin dependencies...")
    repaired, failed = await Altruix.plugin_manager.repair(msg)

    if repaired == 0 and failed == 0:
        return await msg.edit_msg("✅ <b>Everything is in order:</b> No missing dependencies detected across any plugins.")

    if failed == 0:
        await msg.edit_msg(f"✅ <b>Repair Complete:</b> Successfully installed <code>{repaired}</code> missing package(s)!")
    else:
        await msg.edit_msg(f"⚠️ <b>Partial Repair:</b> Installed {repaired} package(s), but {failed} package(s) encountered installation errors.")


@Altruix.register_on_cmd(
    ["apm_uninstall", "unapm"],
    cmd_help={
        "example": "apm_uninstall my_plugin",
        "help": "Uninstall an external plugin and remove all files.",
    },
    requires_input=True,
)
async def uninstall_pack(c, m: Message):
    msg = await m.handle_message("PROCESSING")
    pn = m.user_input.strip()

    if Altruix.plugin_manager is not None:
        try:
            success = await Altruix.plugin_manager.uninstall(pn, msg=msg)
            if success:
                if packages_list:
                    await packages_list.update_one(
                        {"_id": "APM"}, {"$pull": {"installed_packages": pn}}
                    )
                return await msg.edit_msg(f"🗑️ Plugin <code>{pn}</code> uninstalled successfully.")
            return await msg.edit_msg(f"❌ Plugin <code>{pn}</code> is not installed.")
        except Exception as e:
            return await msg.edit_msg(f"❌ Uninstall failed: <code>{e}</code>")

    # Legacy fallback
    apm_client = APM(Altruix)
    try:
        resp = await apm_client.uninstall_package(pn)
        if packages_list:
            await packages_list.update_one(
                {"_id": "APM"}, {"$pull": {"installed_packages": pn}}
            )
        await msg.edit_msg(resp)
    except Exception as e:
        await msg.edit_msg(f"❌ Error: <code>{e}</code>")


@Altruix.register_on_cmd(
    ["apm_update", "updateapm"],
    cmd_help={
        "example": "apm_update my_plugin",
        "help": "Update an installed plugin to its latest version.",
    },
    requires_input=True,
)
async def update_pack(c, m: Message):
    msg = await m.handle_message("PROCESSING")
    pn = m.user_input.strip()

    if Altruix.plugin_manager is not None:
        try:
            manifest = await Altruix.plugin_manager.update(pn, msg=msg)
            if manifest:
                return await msg.edit_msg(
                    f"✅ Plugin <code>{pn}</code> updated successfully to version <code>{manifest.version}</code>."
                )
            return await msg.edit_msg(f"❌ Could not update plugin <code>{pn}</code>.")
        except Exception as e:
            return await msg.edit_msg(f"❌ Update error: <code>{e}</code>")

    apm_client = APM(Altruix)
    try:
        resp = await apm_client.update_package(pn, msg)
        await msg.edit_msg(resp)
    except Exception as e:
        await msg.edit_msg(f"❌ Error: <code>{e}</code>")
