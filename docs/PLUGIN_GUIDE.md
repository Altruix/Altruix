# Altruix Plugin Development Guide 🚀

Welcome to the definitive guide for building plugins for **Altruix** (Telethon Edition). Whether you are developing internal plugins or public modules distributed through the **Altruix Package Manager (APM)**, this guide covers everything you need.

---

## Table of Contents
1. [Plugin Architecture Overview](#1-plugin-architecture-overview)
2. [Quickstart: Your First Plugin](#2-quickstart-your-first-plugin)
3. [The `@Altruix.register_on_cmd` Decorator](#3-the-altruixregister_on_cmd-decorator)
4. [The `Message` Object](#4-the-message-object)
5. [The `Client` (`AltruixTelegramClient`) Object](#5-the-client-altruixtelegramclient-object)
6. [Parsing Flags and Arguments (`user_args`)](#6-parsing-flags-and-arguments-user_args)
7. [Permission Checks and Decorators](#7-permission-checks-and-decorators)
8. [Database Storage (MongoDB & Local DB)](#8-database-storage-mongodb--local-db)
9. [Assistant Bot Integration (Inline Queries & Callbacks)](#9-assistant-bot-integration-inline-queries--callbacks)
10. [Packaging for APM (`plugin.json` Specification)](#10-packaging-for-apm-pluginjson-specification)
11. [Complete Real-World Examples](#11-complete-real-world-examples)
12. [Common Gotchas & Telethon Best Practices](#12-common-gotchas--telethon-best-practices)

---

## 1. Plugin Architecture Overview

Altruix automatically discovers and hot-loads plugins from several directories:
* `Main/plugins/userbot/*.py`: Standard userbot plugins executed by your Telegram user session(s).
* `Main/plugins/bot/*.py`: Assistant bot plugins executed by your bot token (handles inline queries, callbacks, `/start`).
* `Main/plugins/external/**/*.py`: Modules dynamically installed via APM (`.apm_install`).
* `Main/internals/*.py`: Core operational tools (session generation, environment manager, settings).

### Module Namespace Injection
When Altruix loads a plugin file dynamically, it automatically injects key objects into the module's global scope:
* `Altruix`: The global `AltruixClient` singleton instance.
* `bot`: The `BotWrapper` instance for assistant bot event handling.
* `Client`: The `AltruixTelegramClient` subclassed Telethon client.
* `filters`: Composable event filters (`filters.command`, `filters.regex`, `filters.private`, etc.).

---

## 2. Quickstart: Your First Plugin

Create a new file `Main/plugins/userbot/hello.py`:

```python
from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message

@Altruix.register_on_cmd(
    ["hello", "hi"],
    cmd_help={
        "help": "Send a friendly greeting.",
        "example": "hello",
    },
)
async def hello_command(c: Client, m: Message):
    # m.handle_message edits your message if sent by yourself,
    # or replies if invoked by a sudo user.
    msg = await m.handle_message("Processing...")
    name = c.myself.first_name if hasattr(c, "myself") else "there"
    await msg.edit_msg(f"👋 Hello from <b>{name}</b>!")
```

Type `.hello` or `.hi` in any Telegram chat to run it!

---

## 3. The `@Altruix.register_on_cmd` Decorator

This is the primary decorator for registering commands. Altruix handles prefix matching, permission verification, and automatic help generation for you.

```python
@Altruix.register_on_cmd(
    cmd: Union[str, List[str]],               # Command trigger(s), e.g. ["mute", "m"]
    cmd_help: dict = {},                      # Help schema dictionary
    requires_input: bool = False,             # Error if user didn't provide text
    requires_reply: bool = False,             # Error if user didn't reply to a message
    group_only: bool = False,                 # Restrict command to groups & supergroups
    channel_only: bool = False,               # Restrict command to broadcast channels
    pm_only: bool = False,                    # Restrict command to private 1-on-1 chats
    bot_mode_unsupported: bool = False,       # Disable if running solely in bot mode
    disallow_if_sender_is_channel: bool = False,
)
```

### Help Schema (`cmd_help`)
The help dictionary powers `.help <plugin>` and the interactive inline bot menu:

```python
cmd_help = {
    "help": "Short description of what the command does.",
    "example": "pin -silent (reply to message)",
    "user_args": [
        {
            "arg": "silent",
            "help": "Pin without notifying members.",
            "requires_input": False,
        },
        {
            "arg": "reason",
            "help": "Specify reason for audit logs.",
            "requires_input": True,
        },
    ],
}
```

---

## 4. The `Message` Object

Every handler receives an enriched `Message` object subclassing Telethon's `Message`:

| Property / Method | Description |
| :--- | :--- |
| `m.user_input` | Extracted text arguments *excluding* command name and flags. |
| `m.raw_user_input` | The entire string following the command prefix and name. |
| `m.user_args` | Composable `Args` object containing parsed flags (e.g. `-s val`). |
| `m.reply_to_message` | Enriched `Message` object of the message being replied to (or `None`). |
| `m.chat_id` / `m.chat.id` | Integer ID of the current chat (resolves supergroup/channel peers). |
| `m.chat.type` | String indicating `"private"`, `"group"`, `"supergroup"`, or `"channel"`. |
| `m.sender_id` | Integer ID of the sender. |
| `m.get_user` | Tuple `(user_id_or_username, reason, is_channel)` parsed from reply or input. |
| `m.extract_time` | Tuple `(datetime_object, formatted_string)` extracted from input like `1d`, `2h`. |
| `await m.handle_message(text)` | Edits message if sent by yourself; replies if sent by sudo user. |
| `await m.edit_msg(text)` | Edits message (supports localization string keys). |
| `await m.delete_if_self()` | Deletes message only if it was sent by your account. |
| `await m.download_media(path)` | Downloads photo, document, or audio to local directory. |

---

## 5. The `Client` (`AltruixTelegramClient`) Object

The client represents your active Telegram MTProto session:

* **Sending Messages:**
  ```python
  sent_msg = await c.send_message(chat_id, "<b>Hello</b>", parse_mode="html")
  ```
* **Sending Files & Media:**
  ```python
  await c.send_file(chat_id, "path/to/image.png", caption="Sample caption")
  ```
* **Resolving Users & Peers:**
  ```python
  user_entity = await c.get_users("@username_or_id")
  ```
* **Admin Actions (Permissions):**
  ```python
  # Ban / Restrict
  await c.edit_permissions(chat_id, user_id, view_messages=False, until_date=timestamp)
  # Pin / Unpin
  await c.pin_chat_message(chat_id, message_id, notify=False)
  await c.unpin_chat_message(chat_id, message_id)
  ```
* **Direct MTProto Invocations with FloodWait Guard:**
  ```python
  # Automatically handles and sleeps on FloodWaitError
  res = await c.invoke(functions.channels.GetFullChannelRequest(channel=peer))
  ```

---

## 6. Parsing Flags and Arguments (`user_args`)

Altruix includes built-in flag parsing on `m.user_args`.

### Flag Syntax:
When a user runs:
```text
.mypin -s -reason "Spamming links"
```

In your Python code:
```python
user_args = m.user_args

# Check boolean flags:
is_silent = "s" in user_args or "silent" in user_args

# Extract flag values:
reason = user_args.reason or user_args.get("reason")  # -> "Spamming links"
```

---

## 7. Permission Checks and Decorators

Protect commands in groups by adding `@check_perm`:

```python
from Main.core.decorators import check_perm

@Altruix.register_on_cmd(["ban"], group_only=True)
@check_perm("can_restrict_members")
async def ban_handler(c: Client, m: Message):
    ...
```

Supported permission tokens:
* `"can_restrict_members"`: Ban, kick, or mute members.
* `"can_delete_messages"`: Delete other members' messages.
* `"can_pin_messages"`: Pin/unpin messages in group.
* `"can_invite_users"`: Generate invite links or add members.
* `"can_promote_members"`: Add or edit administrators.

Multiple permissions:
```python
@check_perm(["can_delete_messages", "can_restrict_members"])
```

---

## 8. Database Storage (MongoDB & Local DB)

Altruix abstracts database operations so your plugin runs seamlessly whether MongoDB is configured or falling back to local JSON storage (`local_db.json`).

```python
# Access collection
notes_db = Altruix.db.make_collection("notes")

# Insert document
await notes_db.insert_one({
    "chat_id": m.chat.id,
    "name": "rules",
    "content": "Be nice to everyone!",
    "client_id": c.myself.id
})

# Find document
note = await notes_db.find_one({"chat_id": m.chat.id, "name": "rules"})
if note:
    await m.handle_message(note["content"])

# Query multiple items (async for loop)
async for doc in notes_db.find({"chat_id": m.chat.id}):
    print(doc["name"])

# Delete document
await notes_db.delete_one({"chat_id": m.chat.id, "name": "rules"})
```

---

## 9. Assistant Bot Integration (Inline Queries & Callbacks)

Altruix allows plugins to register assistant bot handlers via `Altruix.bot`:

### Inline Query Handler:
```python
from Main.utils.custom_filters import filters
from telethon import custom

@Altruix.bot.on_inline_query(filters.regex(r"^calc (.+)"))
async def calc_inline(client, iq):
    expression = iq.pattern_match.group(1)
    result_val = str(eval(expression))  # (Use safe math parser in production)
    
    article = iq.builder.article(
        title=f"Result: {result_val}",
        text=f"<code>{expression}</code> = <b>{result_val}</b>",
        parse_mode="html",
        buttons=[[custom.Button.inline("Share", f"share_{result_val}".encode())]]
    )
    await iq.answer([article])
```

### Callback Query Handler:
```python
@Altruix.bot.on_callback_query(filters.regex(r"^share_(.*)"))
async def share_callback(client, cq):
    val = cq.pattern_match.group(1)
    await cq.answer(f"Calculated value was: {val}", alert=True)
```

---

## 10. Packaging for APM (`plugin.json` Specification)

To share plugins with other Altruix users via `.apm_install https://github.com/username/my-plugin`, create a Git repository with the following structure:

### Repository Structure:
```text
my-altruix-plugin/
├── plugin.json         # Manifest metadata
├── my_feature.py       # Plugin code
└── README.md
```

### `plugin.json` Schema:
```json
{
  "name": "weather_plugin",
  "version": "1.0.0",
  "description": "Fetch real-time weather forecasts directly in Telegram.",
  "author": "YourName",
  "entry": "my_feature.py",
  "dependencies": ["httpx", "geopy"]
}
```

* **`name`**: Unique alphanumeric package identifier.
* **`version`**: Semantic version string (e.g. `1.0.0`).
* **`author`**: Developer or maintainer handle.
* **`entry`**: Name of the `.py` script to load (if omitted, all non-underscore `.py` files in the repository are loaded).
* **`dependencies`**: Python packages from PyPI that APM will automatically pip-install prior to loading your plugin.

---

## 11. Complete Real-World Examples

### Example A: Weather Plugin with HTTP API & Flags
```python
# weather.py
import httpx
from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message

@Altruix.register_on_cmd(
    ["weather", "wt"],
    cmd_help={
        "help": "Get real-time weather for a city.",
        "example": "weather Tokyo or weather London -f",
        "user_args": [
            {
                "arg": "f",
                "help": "Display temperature in Fahrenheit.",
                "requires_input": False,
            }
        ],
    },
    requires_input=True,
)
async def weather_cmd(c: Client, m: Message):
    msg = await m.handle_message("Fetching weather...")
    city = m.user_input.strip()
    use_fahrenheit = "f" in m.user_args

    url = f"https://wttr.in/{city}?format=j1"
    async with httpx.AsyncClient(timeout=10.0) as http:
        try:
            resp = await http.get(url)
            if resp.status_code != 200:
                return await msg.edit_msg(f"❌ City '<code>{city}</code>' not found.")
            data = resp.json()
        except Exception as e:
            return await msg.edit_msg(f"❌ Error fetching weather: {e}")

    current = data["current_condition"][0]
    temp = current["temp_F"] if use_fahrenheit else current["temp_C"]
    unit = "°F" if use_fahrenheit else "°C"
    desc = current["weatherDesc"][0]["value"]
    humidity = current["humidity"]
    wind = current["windspeedKmph"]

    out = (
        f"🌤️ <b>Weather in {city.title()}</b>:\n"
        f"• <b>Temperature:</b> <code>{temp}{unit}</code>\n"
        f"• <b>Condition:</b> <i>{desc}</i>\n"
        f"• <b>Humidity:</b> <code>{humidity}%</code>\n"
        f"• <b>Wind:</b> <code>{wind} km/h</code>"
    )
    await msg.edit_msg(out)
```

---

### Example B: Moderation Kick Plugin with Reply Parsing
```python
# quickkick.py
from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.core.decorators import check_perm

@Altruix.register_on_cmd(
    ["kick"],
    cmd_help={
        "help": "Kick a member from the group chat.",
        "example": "kick (reply to user) <reason>",
    },
    group_only=True,
)
@check_perm("can_restrict_members")
async def kick_user(c: Client, m: Message):
    msg = await m.handle_message("Processing...")
    user_target, reason, _ = m.get_user

    if not user_target:
        return await msg.edit_msg("❌ Please reply to a user or specify a user ID/username.")

    try:
        user_obj = await c.get_users(user_target)
        # In Telethon, kicking is removing participant from group
        await c.kick_participant(m.chat.id, user_obj.id)
        mention = getattr(user_obj, "mention", str(user_target))
        reason_txt = f"\n• <b>Reason:</b> <i>{reason}</i>" if reason else ""
        await msg.edit_msg(f"👢 Kicked {mention} from the chat!{reason_txt}")
    except Exception as e:
        await msg.edit_msg(f"❌ Failed to kick user: <code>{e}</code>")
```

---

## 12. Common Gotchas & Telethon Best Practices

1. **Inline Results are Lists in Telethon:**
   * ❌ *Wrong (Pyrogram style):* `if results.results: result_id = results.results[0].id`
   * ✅ *Correct (Telethon style):* `if results: await results[0].click(chat_id)`

2. **Non-blocking Asynchronous I/O:**
   * Always use `asyncio.sleep()` instead of `time.sleep()`.
   * Always use `httpx.AsyncClient` or `aiofiles` instead of `requests` or synchronous `open()`.

3. **Message Replies vs Direct Commands:**
   * When accessing replied messages, use `m.reply_to_message`. Altruix automatically fetches and enriches the replied message for commands that require it.

4. **Multi-Account Client Awareness:**
   * Always reference `c.myself.id` (the current client executing the handler) rather than assuming a single static account ID.
