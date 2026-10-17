# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import sys
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

banner_ = r"""
     _    _ _              _
    / \  | | |_ _ __ _   _(_)_  __
   / _ \ | | __| '__| | | | \ \/ /
  / ___ \| | |_| |  | |_| | |>  <
 /_/   \_\_|\__|_|   \__,_|_/_/\_\

 Altruix - Telethon String Session Generator
"""

print(banner_)

while True:
    api_id_raw = input("Enter Your API ID:\n>> ").strip()
    if api_id_raw.isdigit():
        api_id = int(api_id_raw)
        break
    print("Invalid API ID, must be an integer. Try again.\n")

while True:
    api_hash = input("Enter Your API HASH:\n>> ").strip()
    if api_hash:
        break
    print("Invalid API HASH. Try again.\n")

print("\nConnecting to Telegram...")
try:
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        user = client.get_me()
        session_str = client.session.save()
        print(f"\nSuccessfully logged in as {getattr(user, 'first_name', 'User')}")

        to_send = (
            f"**Telethon String Session for {getattr(user, 'first_name', 'User')}**\n\n"
            "================ START ================\n"
            f"`{session_str}`\n"
            "================ END ================\n"
            "\nKeep this session secret! Do not share it with anyone."
        )
        client.send_message("me", to_send)
        print("Your Telethon string session has been sent to your Saved Messages!")
        print("\nSession string:\n")
        print(session_str)
        print("\nAdd this to your SESSIONS variable in .env or via your assistant bot.")
except Exception as e:
    print(f"\nAn error occurred while generating session: {e}", file=sys.stderr)
