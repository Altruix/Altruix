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
* **Multi-Domain Ecosystem**: First-class support for media synthesis, deep OSINT, everyday utilities, and group automation.
* **Universal Database**: Zero-config local SQLite persistence (`altruix.db`) out of the box, with seamless high-throughput MongoDB, PostgreSQL, and Redis support.
* **Multi-Session Multi-Client**: Run and manage multiple user sessions concurrently from a single instance.

---

## 🚀 Quick Start & Deployment

### 1. Local / VPS Deployment

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

### 2. Pre-Boot Dependency Verification
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

### Option A: Interactive CLI Terminal Generator
```bash
python -m Main.scripts.session_gen
```
Follow the terminal prompt to enter your phone number, two-factor password (if enabled), and OTP. The generated StringSession will be output directly to your terminal.

### Option B: Interactive Assistant Bot
Set your `BOT_TOKEN` in `.env` and start the bot. Send `/add` or `/session` to your bot in Telegram to generate and register sessions securely.

---

## ⚙️ Configuration Variables

Configure your credentials in `.env` or through environment variables:

| Variable | Required? | Default | Description |
|---|:---:|---|---|
| `API_ID` | **Yes** | — | Telegram App API ID obtained from [my.telegram.org](https://my.telegram.org/apps). |
| `API_HASH` | **Yes** | — | Telegram App API Hash obtained from [my.telegram.org](https://my.telegram.org/apps). |
| `SESSIONS` | **Yes** | `[]` | One or more Telethon StringSessions for userbot functionality. |
| `BOT_TOKEN` | Optional | `None` | Telegram Bot Token from [@BotFather](https://t.me/BotFather) for the assistant bot. |
| `OWNER_ID` | Optional | `None` | Telegram User ID of the primary owner (obtain via [@MissRose_Bot](https://t.me/MissRose_Bot) `/id`). |
| `DB_URI` | Optional | `sqlite:///altruix.db` | Database connection URI. Supports SQLite (`sqlite:///altruix.db`), MongoDB (`mongodb+srv://`), PostgreSQL (`postgresql://`), or Redis (`redis://`). |
| `DB_NAME` | Optional | `Altruix` | Database collection namespace name. |
| `CMD_HANDLER` | Optional | `.` | Command prefix for userbot commands (e.g. `.help`, `.ping`). |
| `SUDO_CMD_HANDLER` | Optional | `!` | Command prefix for authorized sudo operators. |
| `SUDO_USERS` | Optional | `[]` | List of trusted user IDs permitted to invoke bot commands. |
| `LOG_CHAT_ID` | Optional | `None` | Private Telegram chat or channel ID where bot logs and tracebacks are relayed. |
| `OCR_SPACE_API_KEY` | Optional | `helloworld` | Optional custom key for OCR Space (defaults to zero-key public tier). |
| `OCR_CUSTOM_API_URL`| Optional | `None` | Optional self-hosted AI OCR endpoint (Surya, PaddleOCR, vLLM). |

### Example `.env` File:
```env
API_ID=1234567
API_HASH=abcdef0123456789abcdef0123456789
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
SESSIONS="1BJWap1wBu..."
OWNER_ID=987654321
CMD_HANDLER="."
SUDO_CMD_HANDLER="!"

# Choose your database backend (see Multi-Database section below):
DB_URI="sqlite:///altruix.db"
DB_NAME="Altruix"
```

---

## 🗄️ Multi-Database Support (SQLite, Mongo, Postgres, & Redis)

Altruix features a **Universal Database Layer** powered by `PyMongoInstructionParser`. You can write standard async MongoDB syntax (`find()`, `find_one()`, `insert_one()`, `update_one()`, `delete_many()`, `$set`, `$inc`, `$push`) and Altruix automatically routes and translates queries to your chosen backend:

| Backend | `DB_URI` Format | Best For | Prerequisites |
|---|---|---|---|
| **SQLite (SQL)** *(Default)* | `sqlite:///altruix.db` *(or leave empty)* | Single-server / VPS deployments & local testing | Built-in (zero-config, works out of the box) |
| **MongoDB (NoSQL)** | `mongodb+srv://user:pass@cluster.mongodb.net/` | Scalable cloud database (MongoDB Atlas) | Running MongoDB cluster |
| **PostgreSQL (SQL)** | `postgresql://user:pass@host:5432/dbname` | High-concurrency production deployments (Supabase, Neon) | Running PostgreSQL instance |
| **Redis** | `redis://[:pass@]host:6379/0` | High-speed memory-backed cache/store | Running Redis instance |

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
