# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


from subprocess import PIPE, Popen


try:
    from pyrogram import Client
except Exception:
    print("\033[93mPyrogram was not found.\033[39m")
    import sys
    import time
    import itertools

    spinner = itertools.cycle(["-", "/", "|", "\\"])
    proc = Popen(
        [sys.executable, "-m", "pip", "install", "pyrogram"], stdout=PIPE, stderr=PIPE
    )
    print("\033[93mInstalling Pyrogram...\033[39m")
    while proc.poll() is None:
        sys.stdout.write(next(spinner))
        sys.stdout.flush()
        sys.stdout.write("\b")
        time.sleep(0.1)
    print("\033[92mPyrogram was installed successfully.\033[39m")
    from pyrogram import Client

banner_ = (
    "\033[96m"
    + r"""
     _    _ _              _
    / \  | | |_ _ __ _   _(_)_  __
   / _ \ | | __| '__| | | | \ \/ /
  / ___ \| | |_| |  | |_| | |>  <
 /_/   \_\_|\__|_|   \__,_|_/_/\_\

"""
)

print(banner_)
print("\033[39m")
while True:
    api_id = input("Enter Your \033[92mAPI ID\033[39m: \n>> ")
    if api_id.isdigit():
        break
    print("\033[31m Invalid API ID, Try again.")
    print("\033[39m")

while True:
    api_hash = input("Enter Your \033[92mAPI HASH\033[39m: \n>> ")
    if api_hash and not api_hash.isspace():
        break
    print("\033[31m Invalid API HASH, Try again.")
    print("\033[39m")

with Client("new_sessions", api_id=api_id, api_hash=api_hash, in_memory=True) as client:
    user = client.get_me()
    print(f"\033[92m Logged in as {user.first_name}")
    to_send = f"<b><u>String Session For {user.mention()}</b></u>\n\n"
    to_send += "================ START ================\n"
    to_send += f"<code>{client.export_session_string()}</code>\n"
    to_send += "================ END ================\n"
    client.send_message("me", to_send)
    print("your requested string session has been sent to your Saved Messages")
    print("\033[39m")
