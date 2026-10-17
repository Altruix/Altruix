# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import time
import asyncio
from typing import Optional, Union, Callable, Any
from telethon import errors
from Main import Altruix


def human_bytes(size: Union[int, float]) -> str:
    """Format byte size into human readable string (KB, MB, GB)."""
    if not size or size <= 0:
        return "0 B"
    power = 1024
    units = ["B", "KB", "MB", "GB", "TB"]
    raised = 0
    size_f = float(size)
    while size_f >= power and raised < len(units) - 1:
        size_f /= power
        raised += 1
    return f"{size_f:.1f} {units[raised]}"


def format_eta(seconds: Union[int, float]) -> str:
    """Format seconds into concise ETA string."""
    sec = max(0, int(seconds))
    if sec < 60:
        return f"{sec}s"
    minutes, sec = divmod(sec, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def render_progress_bar(percentage: float, length: int = 12) -> str:
    """Generate high-contrast visual ASCII progress bar."""
    pct = max(0.0, min(100.0, percentage))
    filled = int(length * (pct / 100.0))
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {pct:.1f}%"


def create_progress_callback(
    message: Any,
    action: str = "Uploading",
    file_name: Optional[str] = None,
    throttle_seconds: float = 4.0,
) -> Callable:
    """Create a flood-wait safe, throttled progress callback for Telethon file transfers."""
    start_time = time.time()
    last_update = 0.0

    async def _progress_callback(current: int, total: int):
        nonlocal last_update
        if not message or not total or total <= 0:
            return

        # Check user preference (Clean mode vs Progress Bar)
        enabled = False
        if hasattr(Altruix, "config") and hasattr(Altruix.config, "get_progress_bar_sts"):
            try:
                enabled = await Altruix.config.get_progress_bar_sts()
            except Exception:
                enabled = False

        if not enabled:
            return

        now = time.time()
        # Strictly throttle updates to avoid Telegram flood waits
        if (now - last_update < throttle_seconds) and (current < total):
            return
        last_update = now

        diff = max(0.001, now - start_time)
        pct = (current / total) * 100.0
        speed = current / diff
        eta_sec = (total - current) / speed if speed > 0 else 0

        bar = render_progress_bar(pct, length=12)
        fname = file_name or "file"
        icon = "⬆️" if "upload" in action.lower() else "⬇️"

        text = (
            f"{icon} <b>{action}:</b> <code>{fname}</code>\n"
            f"<code>{bar}</code>\n"
            f"• <b>Transferred:</b> <code>{human_bytes(current)} / {human_bytes(total)}</code>\n"
            f"• <b>Speed:</b> <code>{human_bytes(speed)}/s</code> | <b>ETA:</b> <code>{format_eta(eta_sec)}</code>"
        )

        try:
            if hasattr(message, "edit_msg"):
                await message.edit_msg(text)
            elif hasattr(message, "edit"):
                await message.edit(text, parse_mode="html")
        except errors.FloodWaitError as fwe:
            # Back off dynamically on flood wait
            last_update = now + fwe.seconds + 1.0
        except errors.MessageNotModifiedError:
            pass
        except Exception:
            pass

    return _progress_callback
