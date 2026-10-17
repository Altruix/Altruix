# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.decorators import check_perm
from Main.core.types.message import Message
from Main.utils.custom_filters import create, Filter

warn_count = {}


@Altruix.register_on_cmd(
    ["addblacklist", "abl"],
    cmd_help={
        "help": "Add word(s) to blacklist. Supports comma-separated bulk words.",
        "example": "abl spam, scam, phishing",
        "user_args": [
            {
                "arg": "limit",
                "help": "Set a warn limit for the blacklisted words.",
                "requires_input": True,
            }
        ],
    },
    requires_input=True,
)
@check_perm("can_delete_messages")
async def add_blacklist_cmd_handler(c: Client, m: Message):
    if Altruix.db is None:
        return await m.handle_message("No database connected.")
    bl_db = Altruix.db.make_collection("BLACKLIST")
    user_args = m.user_args
    warns = user_args.limit
    if warns:
        if not str(warns).isdigit():
            return await m.handle_message("INVALID_BLACKLIST_SYNTAX")
        warns = int(warns)
    else:
        warns = False

    raw_text = m.user_input.lower().strip()
    words = [w.strip() for w in raw_text.split(",") if w.strip()]
    if not words:
        return await m.handle_message("No blacklist words specified.")

    my_id = c.myself.id
    added = []
    already = []
    for w in words:
        if await bl_db.find_one({"chat_id": m.chat.id, "bl_word": w, "client_id": my_id}):
            already.append(w)
            continue
        await bl_db.insert_one(
            {"chat_id": m.chat.id, "bl_word": w, "warns": warns, "client_id": my_id}
        )
        added.append(w)

    if len(words) == 1:
        if added:
            return await m.handle_message("WORD_BLACKLISTED", string_args=(added[0],))
        return await m.handle_message("ALREADY_BLACKLISTED", string_args=(already[0], getattr(m.chat, "title", str(m.chat.id))))

    res_parts = []
    if added:
        res_parts.append(f"⛔ <b>Blacklisted {len(added)} word(s):</b> {', '.join(f'<code>{x}</code>' for x in added)}")
    if already:
        res_parts.append(f"ℹ️ <b>Already blacklisted ({len(already)}):</b> {', '.join(f'<code>{x}</code>' for x in already)}")
    await m.handle_message("\n".join(res_parts))


@Altruix.register_on_cmd(
    ["blacklists", "listbl"],
    cmd_help={
        "help": "Shows all the blacklisted words in the chat.",
        "example": "blacklists",
    },
)
async def list_blacklist_cmd_handler(c: Client, m: Message):
    processing_msg = await m.handle_message("PROCESSING")
    if Altruix.db is None:
        return await processing_msg.edit_msg("No database connected.")
    bl_db = Altruix.db.make_collection("BLACKLIST")
    my_id = c.myself.id
    bldata = [i async for i in bl_db.find({"chat_id": m.chat.id, "client_id": my_id})]
    if not bldata:
        await processing_msg.edit_msg("NO_BLACKLIST")
        return ""
    result = Altruix.get_string("BLACKLIST_WORD", args=(getattr(m.chat, "title", str(m.chat.id)),)) or "<b>Blacklisted words:</b>\n"
    for bl_word in bldata:
        result += f"◍ <code>{bl_word['bl_word']}</code> \n"
    await processing_msg.edit(result, parse_mode="html")


@Altruix.register_on_cmd(
    ["delblacklist", "delbl", "rmbl"],
    cmd_help={
        "help": "Removes a, multiple (comma-separated), or all blacklisted words in the chat.",
        "example": "delbl word1, word2 or delbl -all",
        "user_args": [
            {
                "arg": "all",
                "help": "Removes all blacklisted words in the chat.",
                "requires_input": False,
            }
        ],
    },
)
async def delete_blacklist_cmd_handler(c: Client, m: Message):
    processing_msg = await m.handle_message("PROCESSING")
    if Altruix.db is None:
        return await processing_msg.edit_msg("No database connected.")
    bl_db = Altruix.db.make_collection("BLACKLIST")
    user_args = m.user_args
    my_id = c.myself.id

    if "all" in user_args:
        await bl_db.delete_many({"chat_id": m.chat.id, "client_id": my_id})
        await processing_msg.edit_msg("BL_REMOVE_ALL")
        return ""

    raw_text = m.user_input.lower().strip() if m.user_input else ""
    words = [w.strip() for w in raw_text.split(",") if w.strip()]
    if not words:
        return await processing_msg.edit("No words specified to remove from blacklist.")

    removed = []
    not_found = []
    for w in words:
        if await bl_db.find_one({"chat_id": m.chat.id, "bl_word": w, "client_id": my_id}):
            await bl_db.delete_one({"chat_id": m.chat.id, "bl_word": w, "client_id": my_id})
            removed.append(w)
        else:
            not_found.append(w)

    if len(words) == 1:
        if removed:
            return await processing_msg.edit_msg("BL_REMOVE", string_args=(removed[0],))
        return await processing_msg.edit_msg("NOT_BLACKLISTED", string_args=(not_found[0],))

    res_parts = []
    if removed:
        res_parts.append(f"🗑️ <b>Removed {len(removed)} blacklisted word(s):</b> {', '.join(f'<code>{x}</code>' for x in removed)}")
    if not_found:
        res_parts.append(f"ℹ️ <b>Not in blacklist ({len(not_found)}):</b> {', '.join(f'<code>{x}</code>' for x in not_found)}")
    await processing_msg.edit("\n".join(res_parts), parse_mode="html")


async def blchat_filter(c: Client, m: Message) -> bool:
    if Altruix.db is None or not m.text:
        return False
    if m.out and not getattr(Altruix, "self_test_mode", False):
        return False
    if m.text.startswith(getattr(Altruix, "user_command_handler", ".")):
        return False
    bl_db = Altruix.db.make_collection("BLACKLIST")
    my_id = getattr(c.myself, "id", None)
    if not my_id:
        return False
    chat_id = m.chat_id or (getattr(m.chat, "id", None))
    return bool(await bl_db.find_one({"chat_id": chat_id, "client_id": my_id}))


@Altruix.on_message(create(blchat_filter))
async def del_blacklisted(c: Client, m: Message):
    if Altruix.db is None or not m.text:
        return
    bl_db = Altruix.db.make_collection("BLACKLIST")
    msg = m.text.lower()
    my_id = c.myself.id
    words = msg.split()
    target_chat_id = m.chat_id or getattr(m.chat, "id", None)
    for w in words:
        data = await bl_db.find_one({"chat_id": int(target_chat_id), "bl_word": w, "client_id": my_id})
        if data:
            sender_id = getattr(m.from_user, "id", None) or m.sender_id
            if data.get("warns") and sender_id:
                warn_count[sender_id] = warn_count.get(sender_id, 0) + 1
                if warn_count[sender_id] >= data["warns"]:
                    await c.kick_participant(target_chat_id, sender_id)
                    warn_count.pop(sender_id, None)
            await m.delete()
            break
