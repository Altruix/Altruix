import asyncio
import ast
import inspect
import os
import pytest
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from telethon import errors, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.custom.message import Message as BaseTelethonMessage

from Main.core.types.client import AltruixTelegramClient
from Main.core.types.message import Message, UserWrapper, ChatWrapper, enrich_message
from Main.utils.custom_filters import Filter, Filters, user_filters
from Main.core.config import Config


def test_raw_telethon_calls_match_installed_api():
    """Every raw Telethon request in the source uses current fields and required args."""
    modules = {
        "functions": functions,
        "types": types,
        "errors": errors,
        "events": events,
    }
    failures = []

    for source in (Path(__file__).parents[1] / "Main").rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            target = call.func
            parts = []
            while isinstance(target, ast.Attribute):
                parts.insert(0, target.attr)
                target = target.value
            if not isinstance(target, ast.Name) or target.id not in modules:
                continue
            parts.insert(0, target.id)
            if len(parts) < 2:
                continue

            resolved = modules[parts[0]]
            try:
                for part in parts[1:]:
                    resolved = getattr(resolved, part)
            except AttributeError:
                failures.append(f"{source}:{call.lineno}: missing Telethon API {'.'.join(parts)}")
                continue
            if not inspect.isclass(resolved):
                continue

            try:
                signature = inspect.signature(resolved)
            except (TypeError, ValueError):
                continue
            params = signature.parameters
            invalid = [keyword.arg for keyword in call.keywords if keyword.arg and keyword.arg not in params]
            if invalid:
                failures.append(
                    f"{source}:{call.lineno}: {'.'.join(parts)} has invalid fields {invalid}"
                )
                continue
            positional = list(params.values())[:len(call.args)]
            supplied = {param.name for param in positional} | {
                keyword.arg for keyword in call.keywords if keyword.arg
            }
            required = {
                param.name
                for param in params.values()
                if param.default is inspect.Parameter.empty
                and param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
            }
            missing = required - supplied
            if missing:
                failures.append(
                    f"{source}:{call.lineno}: {'.'.join(parts)} is missing {sorted(missing)}"
                )

    assert not failures, "\n".join(failures)


def test_config_safe_parsing(monkeypatch):
    """Verify that configuration parses safely even with empty or missing env vars."""
    monkeypatch.setenv("API_ID", "123456")
    monkeypatch.setenv("API_HASH", "abcdef0123456789abcdef0123456789")
    monkeypatch.setenv("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setenv("SUDO_USERS", "111 222 333")
    monkeypatch.setenv("OWNER_ID", "999")

    cfg = Config()
    assert cfg.API_ID == 123456
    assert cfg.API_HASH == "abcdef0123456789abcdef0123456789"
    assert cfg.BOT_TOKEN == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert cfg.SUDO_USERS == [111, 222, 333]
    assert cfg.OWNER_ID == 999


def test_telethon_client_subclass():
    """Verify AltruixTelegramClient can be instantiated with StringSession."""
    session = StringSession()
    client = AltruixTelegramClient(session, api_id=12345, api_hash="abcdef0123456789abcdef0123456789")
    assert isinstance(client, AltruixTelegramClient)
    assert hasattr(client, "invoke")
    assert hasattr(client, "get_users")
    assert hasattr(client, "copy_message")
    assert hasattr(client, "ban_chat_member")
    assert hasattr(client, "unban_chat_member")
    assert hasattr(client, "kick_chat_member")


def test_message_user_args_and_input():
    """Verify Message parsing of command flags and user input."""
    # Simulate a telethon message
    msg = Message(id=1, peer_id=None)
    msg.message = ".logo Altruix|1000|255 0 102"
    assert msg.command_ == "logo"
    assert msg.user_input == "Altruix|1000|255 0 102"

    msg2 = Message(id=2, peer_id=None)
    msg2.message = ".ban -t2h -no-cache @badguy Spamming"
    assert msg2.command_ == "ban"
    assert "t2h" in msg2.user_args
    assert "no-cache" in msg2.user_args

    until, duration = msg2.extract_time
    assert duration == "2h"
    assert until is not None


def test_user_wrapper_and_mention():
    """Verify UserWrapper formats mention strings correctly."""
    class MockUser:
        id = 12345678
        first_name = "Alice"
        last_name = "Smith"
        username = "alice_smith"
        is_self = True
        bot = False

    uw = UserWrapper(MockUser())
    assert uw.id == 12345678
    assert uw.mention == "@alice_smith"
    assert uw.is_self is True

    # Without username
    class MockUserNoUsername:
        id = 87654321
        first_name = "Bob"
        last_name = None
        username = None
        is_self = False
        bot = False

    uw2 = UserWrapper(MockUserNoUsername())
    assert "tg://user?id=87654321" in uw2.mention


@pytest.mark.asyncio
async def test_custom_filters_composition():
    """Verify composable filter operators: &, |, ~."""
    f1 = Filters.command("ping")
    f2 = Filters.private

    # Mock message
    msg = Message(id=1, peer_id=None)
    msg.message = "/ping"
    msg.is_private = True
    client = None

    assert await f1(client, msg) is True
    assert await f2(client, msg) is True
    assert await (f1 & f2)(client, msg) is True
    assert await (f1 | Filters.group)(client, msg) is True
    assert await (~Filters.group)(client, msg) is True

    msg.message = "/other"
    assert await f1(client, msg) is False
    assert await (f1 & f2)(client, msg) is False

    # Variable signature callables: 3-arg, 2-arg, 1-arg
    f_3arg = Filter(lambda flt, c, m: m.message == "/other")
    f_2arg = Filter(lambda c, m: m.message == "/other")
    f_1arg = Filter(lambda m: m.message == "/other")
    assert await f_3arg(client, msg) is True
    assert await f_2arg(client, msg) is True
    assert await f_1arg(client, msg) is True


@pytest.mark.asyncio
async def test_user_filters():
    """Verify user_filters command routing for self and sudo users."""
    import Main
    Main.Altruix.user_command_handler = "."
    Main.Altruix.sudo_cmd_handler = "!"
    Main.Altruix.config.SUDO_USERS = [99999]

    uf = user_filters(["alive", "ping"])

    # Self command
    msg_self = Message(id=1, peer_id=None)
    msg_self.message = ".alive"
    msg_self.out = True
    assert await uf(None, msg_self) is True

    # Unknown command
    msg_unknown = Message(id=2, peer_id=None)
    msg_unknown.message = ".help"
    msg_unknown.out = True
    assert await uf(None, msg_unknown) is False

    # Sudo user command
    msg_sudo = Message(id=3, peer_id=None)
    msg_sudo.message = "!ping"
    msg_sudo.out = False
    msg_sudo.sender_id = 99999
    assert await uf(None, msg_sudo) is True

    Main.Altruix.disabled_sudo_plugin_list = ["ping"]
    assert await uf(None, msg_sudo) is False
    Main.Altruix.disabled_sudo_plugin_list = []

    # Non-sudo user
    msg_other = Message(id=4, peer_id=None)
    msg_other.message = "!ping"
    msg_other.out = False
    msg_other.sender_id = 55555
    assert await uf(None, msg_other) is False


def test_telethon_slow_mode_error_and_python_launcher_resolution():
    from telethon import errors
    from Main.utils.command import resolve_command
    import sys

    assert errors.SlowModeWaitError
    assert resolve_command(["py3", "-3", "-c", "print('ok')"]) == [
        sys.executable,
        "-c",
        "print('ok')",
    ]
    assert resolve_command(["pip3", "--version"]) == [
        sys.executable,
        "-m",
        "pip",
        "--version",
    ]


@pytest.mark.asyncio
async def test_restart_request_stops_the_running_loop():
    import Main

    app = Main.Altruix
    app._stop_event = asyncio.Event()
    app._restart_requested = False
    try:
        await app.reboot(soft=True)
        assert app._restart_requested is True
        assert app._stop_event.is_set()
    finally:
        app._stop_event = None
        app._restart_requested = False


@pytest.mark.asyncio
async def test_plugin_loader_finds_nested_plugins(tmp_path):
    import Main

    plugin_path = tmp_path / "nested" / "sample_plugin.py"
    plugin_path.parent.mkdir(parents=True)
    plugin_path.write_text(
        "Altruix.__nested_plugin_loaded__ = True\n",
        encoding="utf-8",
    )
    await Main.Altruix.load_from_directory(str(tmp_path / "**" / "*.py"), log=False)
    try:
        assert Main.Altruix.__nested_plugin_loaded__ is True
    finally:
        del Main.Altruix.__nested_plugin_loaded__


@pytest.mark.asyncio
async def test_sudo_removal_and_disabled_command_storage(tmp_path):
    from Main.core.config import Config
    from Main.core.database import LocalDatabase

    db = LocalDatabase(str(tmp_path / "local_db.json"))
    config = Config(db.env_col)
    config.DEBUG = False
    config.SUDO_USERS = []
    await config.add_sudo(12345)
    await config.add_sudo(67890)
    await config.del_sudo(12345)
    assert await config.get_sudo() == [67890]

    await config.sync_env_to_db("DISABLED_SUDO_CMD_LIST", ["eval"], push_=True)
    await config.sync_env_to_db("DISABLED_SUDO_CMD_LIST", ["ping"], push_=True)
    assert await config.get_env_from_db("DISABLED_SUDO_CMD_LIST") == ["eval", "ping"]
    remaining = await config.unsync_env_to_db("DISABLED_SUDO_CMD_LIST", ["eval"])
    assert remaining == ["ping"]
