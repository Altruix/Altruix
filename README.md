<h1 align="center"><b>Altruix</b></h1>
<p align="center"><img src="https://telegra.ph/file/f51efe570b5f0a9165f8e.png" width="1155px"><br></p>

<p align="center">
  <b>A high-performance, modular Telegram UserBot and Assistant Bot engine built on Telethon & modern asynchronous Python.</b>
</p>

<p align="center">
  <a href="https://github.com/Altruix/Altruix"><img src="https://img.shields.io/badge/Altruix-v2.0-007ACC.svg?style=flat-square&logo=telegram" alt="Altruix Version"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://github.com/LonamiWebs/Telethon"><img src="https://img.shields.io/badge/Telethon-Async-blue.svg?style=flat-square" alt="Telethon"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-green.svg?style=flat-square" alt="License"></a>
  <a href="https://t.me/AltruiXUB"><img src="https://img.shields.io/badge/Channel-@AltruiXUB-red.svg?style=flat-square&logo=telegram" alt="Channel"></a>
  <a href="https://t.me/AltruixChat"><img src="https://img.shields.io/badge/Community-@AltruixChat-blue.svg?style=flat-square&logo=telegram" alt="Support Chat"></a>
</p>

---

## ⚡ Highlights & Capabilities

* **Dual-Engine Operation**: Seamlessly pairs **Telethon StringSessions** (Userbot) with an interactive **Telegram Bot Token** (Assistant Bot) under a single unified process.
* **APM v3 Package Manager**: Hot-install, update, and segregate third-party plugin suites directly from GitHub repositories without touching core code.
* **Zero-Latency Boot**: Pre-flight `importlib` dependency satisfaction eliminates slow `pip` invocations during startup.
* **Universal Database**: Zero-config local SQLite persistence (`altruix.db`) out of the box, with seamless high-throughput MongoDB and PostgreSQL support.
* **Multi-Session Multi-Client**: Run and manage multiple user sessions concurrently from a single instance.

---

## 🚀 Quick Start & Workflow

### 1. Workflow
1. **Get Credentials**: Obtain `API_ID` & `API_HASH` from [my.telegram.org](https://my.telegram.org/apps) and `BOT_TOKEN` from [@BotFather](https://t.me/BotFather).
2. **Setup Environment**: Copy `example.env` to `.env` and fill in `API_ID`, `API_HASH`, and `BOT_TOKEN`. (Optionally configure `DB_URI` for MongoDB or PostgreSQL; defaults to SQLite).
3. **Add User Session (Choose One)**:
   - **Assistant Bot (Recommended)**: Start the bot (`python -m Main`), message your assistant bot on Telegram, and send `/add` to log in and register your session interactively.
   - **CLI Generator**: Run `python -m Main.scripts.session_gen` in your terminal and paste the generated session string into `SESSIONS` in `.env`.
4. **Run**: Run `python -m Main`. The engine boots user sessions, assistant bot, database, and APM plugins.

### 2. Local / VPS Deployment

```bash
# Clone repository
git clone https://github.com/Altruix/Altruix.git
cd Altruix

# Copy environment template
cp example.env .env

# Install core dependencies
python -m pip install -e .

# Launch Altruix
python -m Main
```

### 3. Pre-Boot Dependency Verification
To prepare external plugin dependencies before launching the bot (ideal for Docker, Termux, and VPS deployments):

```bash
# Batch-install any missing plugin dependencies
python -m Main.core.apm_env_setup

# Export unified external requirements for container builds
python -m Main.core.apm_env_setup --export
```

---

## 🔑 Telethon StringSession Generation

Altruix authenticates your Telegram user account using **Telethon StringSessions**. You can generate one in two ways:

### Option A: Interactive Assistant Bot (Recommended)
Set `BOT_TOKEN` in `.env` and start the bot. Send `/add` or `/session` to your bot in Telegram to log in and register sessions directly.

### Option B: Interactive CLI Terminal Generator
```bash
python -m Main.scripts.session_gen
```
Follow the terminal prompt to enter your phone number, two-factor password (if enabled), and OTP. The generated StringSession will be output directly to your terminal. Paste it into `SESSIONS` in `.env`.

---

## 🤖 Assistant Bot (Workflow, Controls & Settings)

When `BOT_TOKEN` is configured, Altruix runs an interactive assistant bot alongside your userbot accounts. It provides an owner control center, session manager, and inline utilities.

### 1. Workflow & Interactive Onboarding
* **First-Run Guide (TWP)**: If started without user sessions, the assistant bot guides the owner through initial setup. Setup is strictly locked to `OWNER_ID` (or the first user to interact if unset) to prevent unauthorized hijacking.
* **Adding Accounts (`/add` or `/session`)**:
  * **Existing session**: Paste your Telethon StringSession directly.
  * **Interactive in-chat login**: Enter your phone number, Telegram OTP, and 2FA password directly in bot PM. Altruix logs in, hot-attaches the client live without downtime, and saves the session to database and `.env`.
* **Managing Accounts (`/settings`)**: View active clients, inspect account details, add additional accounts, or disconnect sessions with 1-click inline buttons.

### 2. Interactive Control Panel (`/panel` or `/settings`)
Owner-only dashboard accessible via `/panel` (or `.panel` in userbot) to toggle settings in real time:

* **🛡️ PM Security**:
  * **Toggle Permit**: Enable/disable automated private message protection.
  * **Warning Limit**: Set spam threshold (1 to 20 warnings) before automatically blocking senders.
  * **Contacts Bypass**: Allow mutual contacts to message without triggering warnings.
  * **Message Template**: Review or set custom warning text.
  * **Queue Management**: Inspect pending users, mass-approve all incoming requests, or reset warning counters.
* **📊 Upload Progress Bar**: Toggle live progress bars for file transfers on or off.
* **🗄️ Database Details**: Inspect active backend status (SQLite, MongoDB, PostgreSQL), connection state, and collections.
* **⚡ Metrics & Power**: Real-time CPU and RAM utilization, uptime tracker, latency ping (`/ping`), and 1-click instance reboot (`/restart`).

### 3. Interactive Help Menu (`/help`)
* Categorized command browser (**Main**, **Loaded** APM plugins, or **All**).
* Paginated navigation with command descriptions, flags, usage requirements, and examples.

### 4. Inline Query Utilities
Type `@YourBot` in any Telegram chat to trigger inline tools:
* `@YourBot help`: Send interactive inline help menus.
* `@YourBot apm`: Package manager control widget (inspect plugins, run `.apm_doctor`, batch repair).
* `@YourBot pmsec`: Quick access to PM security settings.
* `@YourBot whisper @username <secret text>`: Send end-to-end masked whisper messages readable solely by the tagged user.

---

## ⚙️ Configuration Variables

### Minimum Environment Variables (Essential)

| Variable | Status | Default | Description |
|---|:---:|---|---|
| `API_ID` | **Required** | — | Telegram App API ID obtained from [my.telegram.org](https://my.telegram.org/apps). |
| `API_HASH` | **Required** | — | Telegram App API Hash obtained from [my.telegram.org](https://my.telegram.org/apps). |
| `BOT_TOKEN` | **Recommended** | `None` | Telegram Bot Token from [@BotFather](https://t.me/BotFather). Required for assistant bot, inline controls, and interactive session adding (`/add`). |
| `DB_URI` | **Recommended** | `sqlite:///altruix.db` | Database connection URI. Defaults to SQLite (`sqlite:///altruix.db`). Also supports MongoDB (`mongodb+srv://`) or PostgreSQL (`postgresql://`). |
| `SESSIONS` | Optional | `[]` | Space-separated Telethon StringSessions. Can be left empty if you generate and register sessions using `/add` in the assistant bot. |

### Extended Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `OWNER_ID` | `0` | Primary owner user ID (obtain via [@MissRose_Bot](https://t.me/MissRose_Bot) `/id`). |
| `CMD_HANDLER` | `.` | Command prefix for userbot commands (e.g. `.help`, `.ping`). |
| `SUDO_CMD_HANDLER` | `!` | Command prefix for authorized sudo operators. |
| `SUDO_USERS` | `[]` | Space-separated list of trusted user IDs permitted to invoke bot commands. |
| `LOG_CHAT_ID` | `None` | Private Telegram chat or channel ID where bot logs and tracebacks are relayed. |
| `DB_NAME` | `Altruix` | Database collection namespace name. |
| `BOT_MODE` | `false` | Run solely as assistant bot without userbot accounts. |
| `LOAD_XTRA_PLUGINS` | `true` | Automatically clone, sync, and load external plugin suites. |
| `XTRA_PLUGINS_REPOS` | `https://github.com/Altruix/XtraPlugins` | Comma- or space-separated git repository URLs for external plugin suites. |
| `UPDATE_ON_STARTUP` | `false` | Pull the latest git commits on startup. |
| `DEBUG` | `false` | Enable debug logs and skip database env syncing. |
| `UB_LANG` | `english` | Bot localization language. |
| `ALIVE_MEDIA` | `None` | Custom media link/telegraph URL for `.alive` command. |
| `CUSTOM_BOT_MEDIA` | `None` | Custom image/video URL for `/start` in the assistant bot. |
| `CUSTOM_BT_START_MSG` | `""` | Custom greeting text for the assistant bot `/start` message. |
| `HELP_MENU_ROWS` | `6` | Number of rows in the assistant bot inline help menu. |
| `HELP_MENU_COLUMNS` | `3` | Number of columns in the assistant bot inline help menu. |
| `LOAD_ENV_TO_DB` | `false` | Sync environment variables from `.env` directly into the database on startup. |

### Minimal `.env` Example:
```env
# Essential
API_ID=1234567
API_HASH=abcdef0123456789abcdef0123456789
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Recommended (leave empty for SQLite, or provide Mongo / Postgres)
DB_URI="sqlite:///altruix.db"

# Optional (or add sessions interactively via /add in your bot)
SESSIONS="1BJWap1wBu..."
OWNER_ID=987654321
CMD_HANDLER="."
SUDO_CMD_HANDLER="!"
```

---

## 🗄️ Multi-Database Support (SQLite, MongoDB, & PostgreSQL)

Altruix features a **Universal Database Layer** powered by `PyMongoInstructionParser`. You can write standard async MongoDB syntax (`find()`, `find_one()`, `insert_one()`, `update_one()`, `delete_many()`, `$set`, `$inc`, `$push`) and Altruix automatically routes and translates queries to your chosen backend:

| Backend | `DB_URI` Format | Best For | Prerequisites |
|---|---|---|---|
| **SQLite (SQL)** *(Default)* | `sqlite:///altruix.db` *(or leave empty)* | Single-server / VPS deployments & local testing | Built-in (zero-config, works out of the box) |
| **MongoDB (NoSQL)** | `mongodb+srv://user:pass@cluster.mongodb.net/` | Scalable cloud database (MongoDB Atlas) | Running MongoDB cluster |
| **PostgreSQL (SQL)** | `postgresql://user:pass@host:5432/dbname` | High-concurrency production deployments (Supabase, Neon) | Running PostgreSQL instance |

### How It Works Under The Hood:
1. **Auto-Detection:** When Altruix boots, `create_database(DB_URI)` detects the connection scheme.
2. **Transparent Query Translation:** For SQL databases (PostgreSQL & SQLite), `PyMongoInstructionParser` compiles MongoDB query dicts and update operators directly into optimized parameterized SQL statements (`SELECT data FROM table WHERE ...`), storing documents as indexed JSON objects.
3. **Async Cursor Parity:** Cursors across all backends implement standard async iteration (`async for item in col.find({...}):`), ensuring 100% plugin compatibility without writing backend-specific SQL.

---

## 📦 Altruix Package Manager (APM v3)

Altruix features a built-in package manager that installs, segregates, and updates modular plugins dynamically from GitHub without modifying core code.

### Installing Plugins
```text
# Install a full plugin suite
.apm_install https://github.com/username/my-plugin

# Install only specific segregated subcategories
.apm_install https://github.com/username/XtraPlugins -sub media,utilities

# Persist package across bot restarts
.apm_install -ios https://github.com/username/my-plugin
```

### Managing Subcategories & Packages
```text
# List all installed plugins and active subcategories
.apm_list

# Inspect segregated subcategories of an installed plugin
.apm_sub XtraPlugins

# Enable a specific subcategory on the fly
.apm_enable XtraPlugins media

# Disable a subcategory without deleting files
.apm_disable XtraPlugins shopping

# Update an installed plugin to its latest GitHub release
.apm_update my-plugin

# Uninstall and purge a plugin
.apm_uninstall my-plugin
```

### Diagnostics & Self-Healing
```text
# Run a full health audit of all plugins and Python dependencies
.apm_doctor

# 1-click batch repair of any missing packages
.apm_repair
```

> 📖 **Developer Guide**: For creating custom plugins, decorator specifications, subcategory manifests, and database models, read the [Full Plugin Developer Guide](docs/PLUGIN_GUIDE.md).

---

## 🗂 Project Structure

```text
Altruix/
├── Main/
│   ├── core/                  # Core client, APM v3, database engine, decorators, types
│   │   ├── client.py          # AltruixClient engine & Telethon session orchestrator
│   │   ├── plugin_manager.py  # APM v3 plugin lifecycle, subcategories & quarantine
│   │   ├── apm_env_setup.py   # Pre-boot dependency verification & batch resolver
│   │   ├── database.py        # MongoDB & Local JSON storage abstractions
│   │   └── types/             # Telethon Message and Client enriched subclasses
│   ├── plugins/
│   │   ├── userbot/           # Built-in userbot commands (.ping, .eval, .apm, etc.)
│   │   ├── bot/               # Built-in assistant bot commands (/start, /help, callbacks)
│   │   └── external/          # Dynamically installed APM plugins & manifests
│   ├── internals/             # System utilities, settings, session manager
│   ├── localization/          # Multi-language string catalogs (en, hi, te, bn)
│   └── scripts/               # Session generator, cleanup, maintenance utilities
├── docs/                      # Architectural specifications & Plugin Developer Guide
├── requirements.txt           # Minimal core framework dependencies
├── external_requirements.txt  # Optional unified requirements for external plugin suites
└── example.env                # Template configuration file
```

---

## 👥 Credits & Acknowledgments

* **Telethon**: Pure Python MTProto library created by [LonamiWebs](https://github.com/LonamiWebs/Telethon).
* **Altruix Contributors**: Built and maintained with contributions from:
  * [EverythingSuckz](https://github.com/EverythingSuckz)
  * [StarkGang](https://github.com/StarkGang)
  * [BilakshanP](https://github.com/BilakshanP)
  * [Reeshuxd](https://github.com/Reeshuxd)
  * [Rohith-Sreedharan](https://github.com/Rohith-Sreedharan)
  * [StarkBotIndustries](https://github.com/StarkBotIndustries)
  * [sohag02](https://github.com/sohag02)
  * [SHRE-YANSH](https://github.com/SHRE-YANSH)
  * [lostb053](https://github.com/lostb053)
  * [Nksama](https://github.com/Nksama)
  * [Crackexy](https://github.com/Crackexy)
  * [anonyindian](https://github.com/anonyindian)
  * [N0BLEWOLF](https://github.com/N0BLEWOLF)
  * [ramanveerji](https://github.com/ramanveerji)
  * [swatv3nub](https://github.com/swatv3nub)

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for details.
