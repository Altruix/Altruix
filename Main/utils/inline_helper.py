# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import logging
from typing import Optional, Any
from Main import Altruix

logger = logging.getLogger("altruix.inline")


def is_inline_available() -> bool:
    """Check if the assistant bot is online, configured, and capable of inline queries."""
    if not getattr(Altruix, "bot_info", None):
        return False
    username = getattr(Altruix.bot_info, "username", None)
    return bool(username)


async def send_inline_widget(c: Any, m: Any, query: str) -> bool:
    """
    Attempt to send an interactive inline bot widget to the current chat.
    Returns True if successfully sent, False if inline is unavailable or failed.
    """
    if not is_inline_available():
        return False

    bot_username = getattr(Altruix.bot_info, "username", None)
    if not bot_username:
        return False

    chat_id = m.chat_id or getattr(m.chat, "id", None)
    if not chat_id:
        return False

    try:
        results = await c.get_inline_bot_results(bot_username, query)
        if results and len(results) > 0:
            rm = getattr(m, "reply_to_message", None)
            reply_to = rm.id if rm else m.id
            await results[0].click(chat_id, reply_to=reply_to)
            with contextlib_suppress():
                await m.delete_if_self()
            return True
    except Exception as e:
        logger.debug(f"Inline widget invocation for '{query}' failed: {e}")
        return False

    return False


def is_owner(sender_id: Optional[int]) -> bool:
    """Verify if the sender_id belongs to the primary owner or host userbot account."""
    if not sender_id:
        return False
    owner_id = getattr(Altruix.config, "OWNER_ID", None)
    if owner_id and sender_id == int(owner_id):
        return True
    for myself in getattr(Altruix, "ourselves", []):
        if getattr(myself, "id", None) == sender_id:
            return True
    for cl in getattr(Altruix, "clients", []):
        if hasattr(cl, "myself") and cl.myself and getattr(cl.myself, "id", None) == sender_id:
            return True
    return False


def is_owner_cb(cq: Any) -> bool:
    """Verify that the clicking user is strictly the owner (not sudo or stranger)."""
    sender_id = getattr(cq, "sender_id", 0)
    return is_owner(sender_id)


def is_authorized_cb(cq: Any, allowed_user_id: Optional[int] = None) -> bool:
    """Verify that the clicking user has permission to interact with this control widget."""
    sender_id = getattr(cq, "sender_id", 0)
    if allowed_user_id and sender_id == allowed_user_id:
        return True

    if is_owner(sender_id):
        return True

    sudo_users = getattr(Altruix.config, "SUDO_USERS", []) or []
    if sender_id in sudo_users:
        return True

    return False


class contextlib_suppress:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        return True
