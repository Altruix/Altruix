# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from typing import Optional
from telethon import utils
from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message


async def resolve_chat_id(c: Client, target: str) -> Optional[int]:
    """Resolve a chat ID, username, or t.me link to an integer peer ID."""
    target = target.strip()
    if target.lstrip("-").isdigit():
        return int(target)

    # Strip URL formatting
    for p in ("https://t.me/", "http://t.me/", "t.me/"):
        if target.startswith(p):
            target = target[len(p):]
            break
    target = target.rstrip("/")
    if not target:
        return None

    # Try resolving entity via Telethon
    candidates = [target]
    if not target.startswith("@") and not target.startswith("+"):
        candidates.append(f"@{target}")
    else:
        candidates.append(target.lstrip("@"))

    for cand in candidates:
        try:
            entity = await c.get_entity(cand)
            if entity:
                return utils.get_peer_id(entity)
        except Exception:
            continue
    return None


@Altruix.register_on_cmd(
    ["badd", "broadcastadd", "bcastadd"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Add chat(s) to the broadcast database by ID, @username, or link (supports comma-separated bulk add).",
        "example": "badd @channel1, @channel2, -1001234567890",
    },
)
async def bcast_add(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if Altruix.db is None:
        return await msg.edit("No database connected.")
    bcast_db = Altruix.db.make_collection("Broadcast")
    my_id = c.myself.id

    if m.user_input:
        raw_targets = [t.strip() for t in m.user_input.split(",") if t.strip()]
    else:
        raw_targets = [str(m.chat.id)]

    added = []
    already_in = []
    failed = []

    for target_str in raw_targets:
        chat_id = await resolve_chat_id(c, target_str)
        if chat_id is None:
            failed.append(target_str)
            continue
        check = await bcast_db.find_one({"chat_id": int(chat_id), "client_id": my_id})
        if check:
            already_in.append(str(chat_id))
            continue
        await bcast_db.insert_one({"chat_id": int(chat_id), "client_id": my_id})
        added.append(str(chat_id))

    res_parts = []
    if added:
        res_parts.append(f"✅ <b>Added {len(added)} chat(s):</b> {', '.join(f'<code>{a}</code>' for a in added)}")
    if already_in:
        res_parts.append(f"ℹ️ <b>Already in database ({len(already_in)}):</b> {', '.join(f'<code>{a}</code>' for a in already_in)}")
    if failed:
        res_parts.append(f"❌ <b>Failed to resolve ({len(failed)}):</b> {', '.join(f'<code>{f}</code>' for f in failed)}")

    await msg.edit("\n".join(res_parts) if res_parts else "No chats processed.", parse_mode="html")


@Altruix.register_on_cmd(
    ["bremove", "brm", "broadcastremove", "broadcastrm", "bcastrm", "bcastremove"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Remove chat(s) from the broadcast database by ID, @username, or link (supports comma-separated bulk remove).",
        "example": "bcastrm @channel1, @channel2, <chatid>",
    },
)
async def bcast_remove(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")
    if Altruix.db is None:
        return await msg.edit("No database connected.")
    bcast_db = Altruix.db.make_collection("Broadcast")

    if m.user_input:
        raw_targets = [t.strip() for t in m.user_input.split(",") if t.strip()]
    else:
        raw_targets = [str(m.chat.id)]

    deleted = []
    not_found = []
    failed = []

    for target_str in raw_targets:
        chat_id = await resolve_chat_id(c, target_str)
        if chat_id is None:
            failed.append(target_str)
            continue
        check = await bcast_db.find_one({"chat_id": int(chat_id), "client_id": c.myself.id})
        if not check:
            not_found.append(str(chat_id))
            continue
        await bcast_db.delete_one({"chat_id": int(chat_id), "client_id": c.myself.id})
        deleted.append(str(chat_id))

    res_parts = []
    if deleted:
        res_parts.append(f"🗑️ <b>Deleted {len(deleted)} chat(s):</b> {', '.join(f'<code>{d}</code>' for d in deleted)}")
    if not_found:
        res_parts.append(f"ℹ️ <b>Not in database ({len(not_found)}):</b> {', '.join(f'<code>{n}</code>' for n in not_found)}")
    if failed:
        res_parts.append(f"❌ <b>Failed to resolve ({len(failed)}):</b> {', '.join(f'<code>{f}</code>' for f in failed)}")

    await msg.edit("\n".join(res_parts) if res_parts else "No chats processed.", parse_mode="html")


@Altruix.register_on_cmd(
    ["bcast", "broadcast"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Broadcast the replied message to all saved chats in DB, or to comma-separated chats/usernames.",
        "example": "bcast (replying to message) or bcast @chat1, @chat2, -100123456",
    },
    requires_reply=True,
)
async def broadcast(c: Client, m: Message):
    msg = await m.handle_message("PROCESSING")

    # If specific target(s) are provided in user input, broadcast to them
    if m.user_input:
        raw_targets = [t.strip() for t in m.user_input.split(",") if t.strip()]
        success = 0
        err = 0
        failed_resolve = []
        for target_str in raw_targets:
            chat_id = await resolve_chat_id(c, target_str)
            if chat_id is None:
                failed_resolve.append(target_str)
                continue
            try:
                await c.send_message(chat_id, m.reply_to_message)
                success += 1
            except Exception:
                err += 1
        res = f"📢 Broadcasted to <code>{success}</code> specified chat(s) (errors: <code>{err}</code>)"
        if failed_resolve:
            res += f"\n❌ Unresolved: {', '.join(f'<code>{f}</code>' for f in failed_resolve)}"
        return await msg.edit(res, parse_mode="html")

    # Otherwise broadcast to all saved chats in DB
    if Altruix.db is None:
        return await msg.edit_msg("BROADCAST_NO_DB")

    bcast_db = Altruix.db.make_collection("Broadcast")
    chats = []
    async for x in bcast_db.find({"client_id": c.myself.id}):
        chats.append(x["chat_id"])

    if not chats:
        return await msg.edit_msg("<b>No chats saved in broadcast database.</b>")

    success = 0
    err = 0
    for chat in chats:
        try:
            await c.send_message(int(chat), m.reply_to_message)
            success += 1
        except Exception:
            err += 1

    await msg.edit_msg("BROADCAST_DONE", string_args=(success, err))
