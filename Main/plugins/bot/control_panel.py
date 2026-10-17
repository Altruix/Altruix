# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import time
import psutil
from telethon import custom
from Main import Altruix
from Main.utils.custom_filters import filters
from Main.utils.inline_helper import is_owner, is_owner_cb


def _get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for i in range(len(time_list)):
        time_list[i] = str(time_list[i]) + time_suffix_list[i]
    if len(time_list) == 4:
        ping_time += f"{time_list.pop()}, "
    time_list.reverse()
    ping_time += ":".join(time_list)
    return ping_time or "0s"


async def _render_main_panel():
    uptime = _get_readable_time(int(time.time() - getattr(Altruix, "start_time", time.time())))
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent

    db_obj = getattr(Altruix, "db", None)
    if db_obj is None:
        db_type = "🔴 None"
    else:
        cls_name = db_obj.__class__.__name__
        if "Mongo" in cls_name:
            db_type = "🟢 MongoDB (NoSQL)"
        elif "SQL" in cls_name:
            dialect = getattr(db_obj, "dialect", "sql").title()
            db_type = f"🟢 SQL ({dialect})"
        elif "Local" in cls_name:
            db_type = "🟡 Local JSON"
        elif "Redis" in cls_name:
            db_type = "🟢 Redis"
        else:
            db_type = f"🟢 {cls_name}"

    pm_sts = await Altruix.config.get_pm_sts()
    pm_badge = "🟢 Enabled" if pm_sts else "🔴 Disabled"

    clients_count = len(getattr(Altruix, "clients", []))
    prefix = getattr(Altruix, "user_command_handler", ".")
    ver = getattr(Altruix, "__version__", "0.2.0")

    text = (
        f"⚡ <b>Altruix Control Center v{ver}</b>\n\n"
        f"• <b>Status:</b> 🟢 Operational\n"
        f"• <b>Uptime:</b> <code>{uptime}</code>\n"
        f"• <b>Clients Active:</b> <code>{clients_count} session(s)</code>\n"
        f"• <b>Database:</b> <code>{db_type}</code>\n"
        f"• <b>Prefix Handler:</b> <code>{prefix}</code>\n"
        f"• <b>PM Security:</b> {pm_badge}\n"
        f"• <b>CPU:</b> <code>{cpu_usage}%</code> | <b>RAM:</b> <code>{ram_usage}%</code>\n\n"
        "<i>Use the controls below to configure features or manage the instance:</i>"
    )

    buttons = [
        [
            custom.Button.inline("🛡️ Toggle PM Security", b"panel_toggle_pm"),
            custom.Button.inline("🗄️ Database Info", b"panel_db_details"),
        ],
        [
            custom.Button.inline("🔄 Refresh Stats", b"panel_refresh"),
            custom.Button.inline("⚡ Ping Check", b"panel_ping"),
        ],
        [
            custom.Button.inline("🔄 Restart Altruix", b"panel_restart"),
            custom.Button.inline("✖ Close Panel", b"panel_close"),
        ],
    ]
    return text, buttons


# ==========================================
# Assistant Bot Command: /panel or /settings
# ==========================================

@Altruix.bot.on_message(filters.command(["panel", "settings", "control"]))
async def bot_panel_cmd(c, m):
    sender_id = getattr(m, "sender_id", None) or getattr(getattr(m, "from_user", None), "id", None)
    if not is_owner(sender_id):
        return await m.reply("⛔ Access Denied: Only the owner can access the Altruix Control Panel.")

    text, buttons = await _render_main_panel()
    await m.reply(text, buttons=buttons, parse_mode="html")


# ==========================================
# Userbot Command: .panel or .settings
# ==========================================

@Altruix.register_on_cmd(
    ["panel", "settings", "control"],
    cmd_help={
        "help": "Open the interactive owner control panel in Telegram.",
        "example": "panel",
    },
)
async def userbot_panel_cmd(c, m):
    msg = await m.handle_message("PROCESSING")
    text, buttons = await _render_main_panel()
    # Try inline widget via assistant bot if available
    try:
        from Main.utils.inline_helper import send_inline_widget
        sent = await send_inline_widget(c, m, "panel")
        if sent:
            await msg.delete_if_self()
            return
    except Exception:
        pass

    # Direct edit/reply if assistant bot inline is disabled
    try:
        await msg.edit(text, buttons=buttons, parse_mode="html")
    except Exception:
        await msg.edit(text, parse_mode="html")


# ==========================================
# Interactive Callback Handler
# ==========================================

@Altruix.bot.on_callback_query(pattern=r"^panel_")
async def on_panel_callback(c, cq):
    if not is_owner_cb(cq):
        return await cq.answer("⛔ Access denied: Owner only.", alert=True)

    data = cq.data.decode("utf-8") if isinstance(cq.data, bytes) else str(cq.data)

    if data == "panel_close":
        try:
            await cq.delete()
        except Exception:
            await cq.edit("<i>Control panel closed.</i>", buttons=None, parse_mode="html")
        return

    if data == "panel_refresh":
        await cq.answer("🔄 Updating stats...")
        text, buttons = await _render_main_panel()
        try:
            await cq.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            pass
        return

    if data == "panel_toggle_pm":
        current = await Altruix.config.get_pm_sts()
        new_val = not current
        await Altruix.config.set_pm_sts(new_val)
        status_txt = "ENABLED" if new_val else "DISABLED"
        await cq.answer(f"🛡️ PM Security is now {status_txt}!", alert=True)
        text, buttons = await _render_main_panel()
        try:
            await cq.edit(text, buttons=buttons, parse_mode="html")
        except Exception:
            pass
        return

    if data == "panel_ping":
        start = time.perf_counter()
        await cq.answer("Measuring ping...")
        duration = round((time.perf_counter() - start) * 1000, 2)
        await cq.answer(f"🏓 Pong! Response time: {duration}ms", alert=True)
        return

    if data == "panel_db_details":
        db_obj = getattr(Altruix, "db", None)
        if db_obj is None:
            details = "No database attached."
        else:
            cls = db_obj.__class__.__name__
            name = getattr(db_obj, "db_name", "Altruix")
            details = f"• Backend: {cls}\n• Database Name: {name}"
            if hasattr(db_obj, "dialect"):
                details += f"\n• Dialect: {db_obj.dialect}"
        await cq.answer(f"🗄️ Database Info:\n{details}", alert=True)
        return

    if data == "panel_restart":
        await cq.answer("🔄 Restarting Altruix instance...", alert=True)
        try:
            await cq.edit("🔄 <i>Restarting Altruix instance now...</i>", buttons=None, parse_mode="html")
        except Exception:
            pass
        Altruix.restart()
        return
