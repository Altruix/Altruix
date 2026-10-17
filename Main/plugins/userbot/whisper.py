# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import asyncio
import logging
from telethon import errors

from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message

logger = logging.getLogger("altruix.whisper")


@Altruix.register_on_cmd(
    ["whisper", "w"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Send an encrypted whisper message that only the recipient (and you) can view.",
        "example": "whisper (replying to user) <secret message> or whisper @username <secret message>",
    },
)
async def whisper_cmd(c: Client, m: Message):
    if not getattr(Altruix, "bot_info", None):
        return await m.handle_message("WHISPER_NO_BOT")

    chat_id = m.chat_id or (getattr(m.chat, "id", None))
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)

    target = None
    secret_text = None

    if rm:
        # Replying to user: .whisper <message>
        target_user = getattr(rm, "sender", None) or getattr(rm, "from_user", None)
        target = getattr(target_user, "username", None)
        if target:
            target = f"@{target}"
        elif getattr(rm, "sender_id", None):
            target = str(rm.sender_id)

        secret_text = m.user_input.strip() if m.user_input else ""
    elif m.user_input:
        # Specified inline: .whisper @username <message> or .whisper @username, <message>
        parts = m.user_input.split(None, 1)
        if len(parts) >= 2:
            raw_target = parts[0].rstrip(",")
            target = raw_target
            secret_text = parts[1].strip().lstrip(",").strip()

    if not target or not secret_text:
        return await m.handle_message("INPUT_REQUIRED")

    query_str = f"whisper {target}, {secret_text}"

    try:
        results = await c.get_inline_bot_results(Altruix.bot_info.username, query_str)
        if results:
            await results[0].click(chat_id, reply_to=rm.id if rm else None)
            # Delete original message so the secret text is completely hidden
            return await m.delete_if_self()
        else:
            return await m.handle_message("WHISPER_INLINE_FAILED")
    except errors.BotInlineDisabledError:
        try:
            from Main.internals.set_inline import set_inline_in_botfather
            await set_inline_in_botfather(c)
            await asyncio.sleep(1)
            results = await c.get_inline_bot_results(Altruix.bot_info.username, query_str)
            if results:
                await results[0].click(chat_id, reply_to=rm.id if rm else None)
                return await m.delete_if_self()
        except Exception:
            return await m.handle_message("INLINE_DISABLED")
    except errors.ChatSendInlineForbiddenError:
        return await m.handle_message("WHISPER_NO_INLINE_PERM")
    except Exception as exc:
        logger.error(f"Whisper command failed: {exc}")
        return await m.handle_message(f"❌ Whisper failed: <code>{exc}</code>")
