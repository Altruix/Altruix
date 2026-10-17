# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

"""
Interactive First-Run Configuration Wizard for Altruix.
Guides users through credentials setup, StringSession generation,
database selection, and writes a production-ready .env file.
"""

import os
import sys

BANNER = r"""
     _    _ _              _
    / \  | | |_ _ __ _   _(_)_  __
   / _ \ | | __| '__| | | | \ \/ /
  / ___ \| | |_| |  | |_| | |>  <
 /_/   \_\_|\__|_|   \__,_|_/_/\_\

    ⚡ Altruix Interactive Setup Wizard ⚡
"""


def prompt(text: str, default: str = "") -> str:
    prompt_str = f"{text} [{default}]: " if default else f"{text}: "
    val = input(prompt_str).strip()
    return val if val else default


def main():
    print(BANNER)
    print("Welcome! This wizard will configure your Altruix userbot in under 2 minutes.\n")

    env_path = os.path.abspath(".env")
    if os.path.exists(env_path):
        ans = prompt("⚠️ An existing .env file was found. Overwrite it? (y/N)", default="n").lower()
        if ans != "y":
            print("Setup aborted. Existing .env was preserved.")
            return

    # 1. Telegram API Credentials
    print("\n--- 1. Telegram App Credentials ---")
    print("Obtain these from https://my.telegram.org/apps")
    while True:
        api_id_str = prompt("Enter your API_ID").strip()
        if api_id_str.isdigit():
            api_id = int(api_id_str)
            break
        print("❌ Invalid API_ID: must be a numeric integer. Try again.")

    while True:
        api_hash = prompt("Enter your API_HASH").strip()
        if len(api_hash) >= 16:
            break
        print("❌ Invalid API_HASH: string is too short. Try again.")

    # 2. Assistant Bot Token
    print("\n--- 2. Assistant Bot (Recommended) ---")
    print("Create a bot with @BotFather on Telegram to enable inline widgets & control panel.")
    bot_token = prompt("Enter your BOT_TOKEN (press Enter to skip)", default="").strip()

    # 3. Generate Userbot String Session
    print("\n--- 3. Telegram Account Authentication ---")
    gen_session = prompt("Generate StringSession for your user account now? (Y/n)", default="y").lower()
    session_str = ""
    owner_id = ""

    if gen_session == "y":
        try:
            from telethon.sync import TelegramClient
            from telethon.sessions import StringSession

            print("\nConnecting to Telegram servers...")
            with TelegramClient(StringSession(), api_id, api_hash) as client:
                me = client.get_me()
                session_str = client.session.save()
                owner_id = str(me.id)
                name = getattr(me, "first_name", "User")
                print(f"\n✅ Authenticated as {name} (ID: {owner_id})")

                # Send backup to Saved Messages
                backup_msg = (
                    f"**🔐 Altruix StringSession for {name}**\n\n"
                    f"`{session_str}`\n\n"
                    "Keep this session secret! Do not share it with anyone."
                )
                try:
                    client.send_message("me", backup_msg)
                    print("📁 Session string backed up to your Saved Messages.")
                except Exception:
                    pass
        except Exception as e:
            print(f"❌ Failed to generate session: {e}", file=sys.stderr)
            session_str = prompt("Paste your StringSession manually (or press Enter to skip)", default="")
    else:
        session_str = prompt("Enter your existing Telethon StringSession (or press Enter to skip)", default="")

    if not owner_id:
        owner_id = prompt("Enter your Telegram User ID (OWNER_ID)", default="0")

    # 4. Database Selection
    print("\n--- 4. Database Storage Engine ---")
    print("1) SQLite (Default & Recommended - Fast, zero-setup file database)")
    print("2) MongoDB Atlas / Local (mongodb+srv://...)")
    print("3) PostgreSQL (postgresql://...)")
    print("4) Local JSON (Fallback zero-config file)")
    db_choice = prompt("Choose database backend (1-4)", default="1").strip()

    if db_choice == "2":
        db_uri = prompt("Enter MongoDB URI", default="mongodb://localhost:27017")
    elif db_choice == "3":
        db_uri = prompt("Enter PostgreSQL URI", default="postgresql://user:pass@localhost:5432/altruix")
    elif db_choice == "4":
        db_uri = ""
    else:
        db_uri = "sqlite:///altruix.db"

    # 5. Command Handlers
    print("\n--- 5. Command Prefixes ---")
    cmd_handler = prompt("Userbot command prefix", default=".")
    sudo_handler = prompt("Sudo command prefix", default="!")

    # 6. Write .env
    print("\nWriting configuration to .env...")
    env_content = f"""# ===================================================
# Altruix Configuration File (Generated by Setup Wizard)
# ===================================================

# Telegram App Credentials
API_ID={api_id}
API_HASH={api_hash}

# Assistant Bot Token
BOT_TOKEN={bot_token}
BOT_MODE=false
OWNER_ID={owner_id}

# User Account StringSessions
SESSIONS="{session_str}"

# Database Configuration
DB_URI="{db_uri}"
DB_NAME="Altruix"

# Command Handlers
CMD_HANDLER="{cmd_handler}"
SUDO_CMD_HANDLER="{sudo_handler}"
SUDO_USERS=""

# Logging & Extras
LOG_CHAT_ID=
DEBUG=false
LOAD_XTRA_PLUGINS=true
XTRA_PLUGINS_REPOS=https://github.com/Altruix/XtraPlugins
"""
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    print("✅ Successfully generated .env file!")
    print("\n🎉 Setup is complete! You can now launch Altruix using:")
    print("   • Windows: Double-click start.bat  (or run: py -3 -m Main)")
    print("   • Linux/macOS: ./start.sh         (or run: python3 -m Main)\n")


if __name__ == "__main__":
    main()
