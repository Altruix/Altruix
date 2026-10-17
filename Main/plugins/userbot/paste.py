# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import re
from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.utils.paste import Paste
from Main.core.types.message import Message


@Altruix.register_on_cmd(
    ["paste"],
    bot_mode_unsupported=True,
    cmd_help={
        "help": "Upload text or file content to online pastebin services. Use flags to select your preferred service.",
        "example": "paste -dpaste (replying to message) or paste -spacebin <text>",
        "user_args": [
            {
                "arg": "dpaste",
                "help": "Paste to dpaste.org (supports custom title and syntax highlighting).",
                "requires_input": False,
            },
            {
                "arg": "spacebin",
                "help": "Paste to spaceb.in (clean and modern JSON paste service).",
                "requires_input": False,
            },
            {
                "arg": "pasters",
                "help": "Paste to paste.rs (fast, minimalist rust-based pastebin).",
                "requires_input": False,
            },
            {
                "arg": "cnet",
                "help": "Paste to paste.c-net.org (reliable plaintext pastebin).",
                "requires_input": False,
            },
            {
                "arg": "s",
                "help": f"Service name: {', '.join(Paste().all_bins)}.",
                "requires_input": True,
            },
            {
                "arg": "t",
                "help": "Custom title for the paste.",
                "requires_input": True,
            },
        ],
    },
)
async def paste_cmd(c: Client, m: Message):
    _m = await m.handle_message("PROCESSING")
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)

    # Check flags for services and options
    user_args = m.user_args
    chosen_service = None
    title = None

    if user_args:
        # Direct service flags
        if "dpaste" in user_args or getattr(user_args, "dpaste", None):
            chosen_service = "dpaste"
        elif "spacebin" in user_args or getattr(user_args, "spacebin", None):
            chosen_service = "spacebin"
        elif "pasters" in user_args or getattr(user_args, "pasters", None):
            chosen_service = "pasters"
        elif "cnet" in user_args or getattr(user_args, "cnet", None):
            chosen_service = "cnet"
        elif user_args.s or user_args.service or user_args.get("s") or user_args.get("service"):
            chosen_service = user_args.s or user_args.service or user_args.get("s") or user_args.get("service")

        title = user_args.t or user_args.title or user_args.get("t") or user_args.get("title")

    # Validate service if explicitly chosen
    valid_bins = Paste().all_bins
    if chosen_service:
        chosen_service = chosen_service.lower().strip()
        if chosen_service not in valid_bins:
            bins_str = ", ".join(f"<code>{b}</code>" for b in valid_bins)
            return await _m.edit_msg(f"❌ Invalid service '<code>{chosen_service}</code>'. Available services: {bins_str}")

    text = None
    if rm:
        if rm.text:
            text = rm.text
        elif rm.file:
            file_path = await rm.download_media("temp/")
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
        elif getattr(rm, "raw_text", None):
            text = rm.raw_text
        else:
            return await _m.edit_msg("Reply to a valid text message or file to paste!")
    elif m.user_input:
        raw = m.raw_user_input or m.user_input
        cleaned = raw
        # Strip flag names and their potential values from text
        for flag in ("dpaste", "spacebin", "pasters", "cnet"):
            cleaned = re.sub(rf"-{flag}\b", "", cleaned, flags=re.IGNORECASE)
        if chosen_service:
            cleaned = re.sub(rf"-(?:s|service)\s+{re.escape(chosen_service)}", "", cleaned, flags=re.IGNORECASE)
        if title:
            cleaned = re.sub(rf"-(?:t|title)\s+{re.escape(title)}", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"-(?:s|service|t|title)\b", "", cleaned, flags=re.IGNORECASE).strip()
        text = cleaned or m.user_input
    else:
        return await _m.edit_msg("Reply to a message/file or provide text to paste!")

    author_name = getattr(c.myself, "first_name", "Altruix")
    name, link = await Paste(text, author=author_name, title=title, service=chosen_service).paste()
    if not link:
        return await _m.edit_msg("❌ <b>Failed to upload to pastebin services.</b> Please try again later.")

    template = Altruix.get_string("PASTE_TEXT") or "<b>Pasted to {1}:</b> <a href='{0}'>View Link</a>"
    await _m.edit(template.format(link, name), link_preview=False, parse_mode="html")
