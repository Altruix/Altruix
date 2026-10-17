import pytest
import os
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock

import Main
from Main.core.client import AltruixClient
from Main.core.types.client import AltruixTelegramClient
from Main.core.types.message import Message, UserWrapper, ChatWrapper, enrich_message
from Main.utils.essentials import Essentials
from Main.utils.dev_func import eval_py, exec_terminal
from Main.utils import file_helpers
from Main.utils.custom_filters import filters, user_filters, create, Filter


@pytest.fixture(scope="module")
def altruix_app():
    """Initializes and returns Main.Altruix with all plugins loaded."""
    asyncio.run(Main.Altruix.load_all_modules())
    return Main.Altruix


def test_all_modules_and_plugins_loaded(altruix_app):
    """Verify that every single module and plugin loads without failure."""
    assert len(altruix_app._command_help_message_data) > 0
    # Check that core plugins are in help registry
    core_plugins = ["ping", "alive", "help", "afk", "blacklist", "welcome", "reactions", "whois"]
    for p in core_plugins:
        assert p in altruix_app._command_help_message_data, f"Plugin {p} not registered in help data!"

    # Check pending handlers were registered
    assert len(altruix_app._pending_handlers) > 0


def test_utils_essentials():
    """Verify Essentials utility methods."""
    # Readable time
    assert "s" in Essentials.get_readable_time(45)
    assert "m" in Essentials.get_readable_time(125)
    assert "h" in Essentials.get_readable_time(3700)
    assert "d" in Essentials.get_readable_time(90000)

    # Human bytes
    assert Essentials.humanbytes(500) == "500.0 B"
    assert "KB" in Essentials.humanbytes(2048)
    assert "MB" in Essentials.humanbytes(5 * 1024 * 1024)
    assert "GB" in Essentials.humanbytes(2 * 1024 * 1024 * 1024)

    # Markdown to text
    md = "**Hello** _World_ `code` [link](https://example.com)"
    clean = Essentials.md_to_text(md)
    assert "**" not in clean
    assert "_" not in clean
    assert "`" not in clean


@pytest.mark.asyncio
async def test_utils_dev_func():
    """Verify dev_func helpers."""
    success, output, code = await exec_terminal("python -c \"print('Altruix')\"")
    assert success is True
    assert "Altruix" in output
    assert code == 0


@pytest.mark.asyncio
async def test_file_helpers(tmp_path):
    """Verify asynchronous file helper operations."""
    test_file = str(tmp_path / "test_out.txt")
    created = await file_helpers.make_file_from_text("Hello Altruix", file_name=test_file)
    assert os.path.exists(created)
    with open(created, "r", encoding="utf-8") as f:
        assert f.read() == "Hello Altruix"

    new_path = str(tmp_path / "renamed_out.txt")
    renamed = await file_helpers.rename_file(created, new_path)
    assert renamed is True
    assert os.path.exists(new_path)


@pytest.mark.asyncio
async def test_database_all_plugin_collections():
    """Verify all database collections used by plugins work with LocalDatabase."""
    db = Main.Altruix.local_db
    collections = [
        "SETTINGS", "DATA", "USERS", "ENV", "STICKERS",
        "PLUGINS", "WELCOME", "BLACKLIST", "FILTERS", "PM_PERMIT"
    ]
    for col_name in collections:
        col = db.make_collection(col_name)
        # Test insert
        doc_id = f"test_{col_name}_id"
        ins = await col.insert_one({"_id": doc_id, "data": "initial", "tags": ["a"]})
        assert ins is not None

        # Test find_one_and_update with $addToSet
        updated = await col.find_one_and_update(
            {"_id": doc_id},
            {"$addToSet": {"tags": "b"}, "$set": {"data": "modified"}},
            upsert=True,
            return_document=True,
        )
        assert updated is not None
        assert updated["data"] == "modified"
        assert "b" in updated["tags"]

        # Test find_one_and_update with $push and $pull
        await col.find_one_and_update({"_id": doc_id}, {"$push": {"tags": "c"}})
        check_push = await col.find_one({"_id": doc_id})
        assert "c" in check_push["tags"]

        await col.find_one_and_update({"_id": doc_id}, {"$pull": {"tags": "a"}})
        check_pull = await col.find_one({"_id": doc_id})
        assert "a" not in check_pull["tags"]

        # Test find_one_and_delete
        deleted = await col.find_one_and_delete({"_id": doc_id})
        assert deleted is not None
        assert await col.find_one({"_id": doc_id}) is None


@pytest.mark.asyncio
async def test_userbot_ping_alive_execution():
    """Verify userbot ping and alive command functions."""
    import Main.plugins.userbot.ping as ping_mod
    import Main.plugins.userbot.alive as alive_mod

    mock_client = MagicMock()
    mock_client.get_me = AsyncMock(return_value=MagicMock(first_name="TestUser", id=12345))
    mock_client.myself = MagicMock(first_name="TestUser", id=12345)

    mock_msg = Message(id=1, peer_id=None)
    mock_msg.message = ".ping"
    mock_msg._sender_id_override = 12345
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)
    mock_msg.delete_if_self = AsyncMock(return_value=True)
    mock_msg.reply_file = AsyncMock(return_value=mock_msg)

    # Call ping handler
    await ping_mod.ping_ub_cmd(mock_client, mock_msg)
    mock_msg.handle_message.assert_called_once()
    assert "Pong" in mock_msg.handle_message.call_args[0][0]

    # Call alive handler
    mock_msg.handle_message.reset_mock()
    await alive_mod.alive(mock_client, mock_msg)
    mock_msg.handle_message.assert_called_once()
    alive_text = mock_msg.handle_message.call_args[0][0]
    assert "operational" in alive_text or "Alive" in alive_text


@pytest.mark.asyncio
async def test_userbot_reactions():
    """Verify reactions plugin command handlers."""
    import Main.plugins.userbot.reactions as react_mod

    mock_client = AsyncMock()
    mock_client.get_input_entity = AsyncMock(return_value=MagicMock())

    replied_msg = MagicMock(id=99)
    mock_msg = Message(id=2, peer_id=None)
    mock_msg.message = ".react 🔥"
    mock_msg.chat_id = -100123456789
    mock_msg.get_reply_message = AsyncMock(return_value=replied_msg)
    mock_msg.delete_if_self = AsyncMock(return_value=True)
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)

    # React
    await react_mod.react_to_message(mock_client, mock_msg)
    mock_msg.delete_if_self.assert_called_once()

    # Unreact
    mock_msg.delete_if_self.reset_mock()
    mock_msg.message = ".unreact"
    await react_mod.remove_reaction(mock_client, mock_msg)
    mock_msg.delete_if_self.assert_called_once()


@pytest.mark.asyncio
async def test_userbot_welcome_filter_and_commands():
    """Verify welcome plugin filter and commands."""
    import Main.plugins.userbot.welcome as welcome_mod

    mock_client = MagicMock()
    mock_client.myself = MagicMock(id=12345)

    mock_msg = Message(id=3, peer_id=None)
    mock_msg.chat_id = -100111222333
    mock_msg.message = ".welcome"
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)

    # Filter should return False when no welcome configured
    res = await welcome_mod.welcome_filter(mock_client, mock_msg)
    assert res is False

    # Check command
    await welcome_mod.welcome_settings_cmd(mock_client, mock_msg)
    mock_msg.handle_message.assert_called_once()


@pytest.mark.asyncio
async def test_bot_help_and_settings_buttons():
    """Verify bot help menu pagination and settings button generator."""
    from Main.plugins.bot.help import get_help_menu, get_plugin_data
    from Main.internals.settings import get_sessions_buttons, arrange_buttons

    # Help menu
    buttons = await get_help_menu()
    assert buttons is not None
    assert len(buttons) > 0

    p_text, p_buttons = await get_plugin_data("ping")
    assert "ping" in p_text.lower()
    assert len(p_buttons) > 0

    # Settings buttons
    buttons_list, has_next, total_pages = get_sessions_buttons(1)
    assert isinstance(buttons_list, list)
    grid = arrange_buttons(buttons_list, 3)
    assert isinstance(grid, list)


@pytest.mark.asyncio
async def test_selftest_and_diagnostics():
    """Verify single-account self-test mode and diagnostic tools."""
    import Main.plugins.userbot.selftest as selftest_mod

    mock_client = AsyncMock()
    mock_client.myself = MagicMock(first_name="TestUser", id=12345)
    mock_client.get_me = AsyncMock(return_value=mock_client.myself)

    mock_msg = Message(id=10, peer_id=None)
    mock_msg.chat_id = -100123456
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)

    # Enable self-test mode
    mock_msg.user_input = "on"
    await selftest_mod.toggle_selftest_cmd(mock_client, mock_msg)
    assert Main.Altruix.self_test_mode is True
    assert "ENABLED" in mock_msg.handle_message.call_args[0][0]

    # Run system diagnostics
    mock_msg.handle_message.reset_mock()
    mock_msg.user_input = ""
    await selftest_mod.test_diagnose_cmd(mock_client, mock_msg)
    mock_msg.handle_message.assert_called_once()
    assert "Diagnostics" in mock_msg.handle_message.call_args[0][0]

    # Disable self-test mode
    mock_msg.handle_message.reset_mock()
    mock_msg.user_input = "off"
    await selftest_mod.toggle_selftest_cmd(mock_client, mock_msg)
    assert Main.Altruix.self_test_mode is False
    assert "DISABLED" in mock_msg.handle_message.call_args[0][0]


@pytest.mark.asyncio
async def test_account_settings_and_flags():
    """Verify telegram_account_manager handles flags and overview gracefully."""
    import Main.plugins.userbot.telegram_account_manager as acc_mod
    from telethon.tl import types

    mock_client = AsyncMock()
    mock_client.myself = MagicMock(id=9999, first_name="Dev", last_name="User", username="devuser")
    mock_client.get_me = AsyncMock(return_value=mock_client.myself)
    mock_client.__call__ = AsyncMock(return_value=MagicMock(days=180, authorizations=[]))

    mock_msg = Message(id=1, peer_id=None)
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)
    mock_msg.edit_msg = AsyncMock(return_value=mock_msg)
    mock_msg.user_args = []
    mock_msg.user_input = None

    # Overview without flags
    await acc_mod.account_modify(mock_client, mock_msg)
    mock_msg.edit_msg.assert_called_once()
    assert "Telegram Account Settings" in mock_msg.edit_msg.call_args[0][0]

    # Name flag
    mock_msg.edit_msg.reset_mock()
    mock_msg.user_args = ["-name"]
    mock_msg.user_input = "Alice Wonderland"
    await acc_mod.account_modify(mock_client, mock_msg)
    mock_msg.edit_msg.assert_called_once()
    assert "Alice Wonderland" in mock_msg.edit_msg.call_args[0][0]


@pytest.mark.asyncio
async def test_help_is_bot_safety():
    """Verify help command does not crash with 'User' object has no attribute 'is_bot'."""
    import Main.plugins.userbot.help as help_mod
    from telethon.tl.types import User

    # Raw telethon User without is_bot
    raw_user = User(id=123, bot=False)
    mock_client = AsyncMock()
    mock_client.myself = raw_user

    mock_msg = Message(id=1, peer_id=None)
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)
    mock_msg.user_input = None
    mock_msg.user_args = []
    mock_msg.chat_id = 12345

    await help_mod.help_normal(mock_client, mock_msg)
    mock_msg.handle_message.assert_called_once()
    assert "Plugins Available" in mock_msg.handle_message.call_args[0][0]


@pytest.mark.asyncio
async def test_account_settings_all_flags():
    """Verify telegram_account_manager handles all new flags (-sensitive, -archive, -signup, -bday, -privacy, -ts, -b, -u)."""
    import Main.plugins.userbot.telegram_account_manager as acc_mod

    mock_client = AsyncMock()
    mock_client.myself = MagicMock(id=9999, first_name="Dev", last_name="User", username="devuser")
    mock_client.get_me = AsyncMock(return_value=mock_client.myself)
    mock_client.__call__ = AsyncMock(return_value=MagicMock(days=180, authorizations=[], rules=[]))

    mock_msg = Message(id=1, peer_id=None)
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)
    mock_msg.edit_msg = AsyncMock(return_value=mock_msg)

    # Sensitive flag
    mock_msg.user_args = ["-sensitive"]
    mock_msg.user_input = "on"
    await acc_mod.account_modify(mock_client, mock_msg)
    assert "Sensitive content filter disabled" in mock_msg.edit_msg.call_args[0][0]

    # Archive flag
    mock_msg.user_args = ["-archive"]
    mock_msg.user_input = "on"
    await acc_mod.account_modify(mock_client, mock_msg)
    assert "Auto-archive enabled" in mock_msg.edit_msg.call_args[0][0]

    # Signup flag
    mock_msg.user_args = ["-signup"]
    mock_msg.user_input = "off"
    await acc_mod.account_modify(mock_client, mock_msg)
    assert "Contact joined alerts:" in mock_msg.edit_msg.call_args[0][0]

    # Birthday flag
    mock_msg.user_args = ["-bday"]
    mock_msg.user_input = "15 08 2000"
    await acc_mod.account_modify(mock_client, mock_msg)
    assert "Birthday set to:" in mock_msg.edit_msg.call_args[0][0]

    # Privacy flag
    mock_msg.user_args = ["-privacy"]
    mock_msg.user_input = None
    await acc_mod.account_modify(mock_client, mock_msg)
    assert "Telegram Privacy Settings" in mock_msg.edit_msg.call_args[0][0]

    # Bio flag
    mock_msg.user_args = ["-b"]
    mock_msg.user_input = "New Bio Here"
    await acc_mod.account_modify(mock_client, mock_msg)
    assert "Bio updated:" in mock_msg.edit_msg.call_args[0][0]

    # Terminate sessions flag
    mock_msg.user_args = ["-ts"]
    mock_msg.user_input = None
    await acc_mod.account_modify(mock_client, mock_msg)
    assert "terminated successfully" in mock_msg.edit_msg.call_args[0][0]


@pytest.mark.asyncio
async def test_telethon_types_patched_properties():
    """Verify types.User, types.Channel, and types.Chat have type and mention properties."""
    from telethon import types as tl_types
    from Main.core.types.message import Message

    u = tl_types.User(id=12345, first_name="Alice", username="alice_tg", bot=False)
    assert u.type == "private"
    assert u.mention == "@alice_tg"
    assert u.is_bot is False

    u_no_uname = tl_types.User(id=67890, first_name="Bob")
    assert u_no_uname.type == "private"
    assert "<a href='tg://user?id=67890'>Bob</a>" in u_no_uname.mention

    chan = tl_types.Channel(id=1001, title="News", broadcast=True, photo=None, date=None)
    assert chan.type == "channel"

    supergroup = tl_types.Channel(id=1002, title="GroupChat", broadcast=False, photo=None, date=None)
    assert supergroup.type == "supergroup"

    # Message fallback from_user
    msg = Message(id=1, peer_id=tl_types.PeerUser(12345))
    msg.sender_id = 55555
    assert msg.from_user is not None
    assert msg.from_user.id == 55555
    assert msg.from_user.type == "private"


@pytest.mark.asyncio
async def test_kang_animated_and_video_sticker_direct():
    """Verify kang steals animated and video stickers directly via InputDocument without ffmpeg or WinError 2."""
    import Main.plugins.userbot.stcr as stcr_mod
    from Main import Altruix
    from telethon import types as tl_types

    mock_client = AsyncMock()
    mock_client.myself = MagicMock(id=12345, first_name="Owner", username="owner_user")

    mock_bot = AsyncMock()
    mock_bot.resolve_peer = AsyncMock(return_value=tl_types.InputPeerUser(12345, 67890))
    mock_bot.invoke = AsyncMock(return_value=MagicMock())
    Altruix.bot = mock_bot
    Altruix.bot_info = MagicMock(id=9876, username="TestBot")

    # Mock replied message as an animated sticker (.tgs)
    attr = tl_types.DocumentAttributeSticker(alt="🔥", stickerset=tl_types.InputStickerSetEmpty())
    doc = tl_types.Document(
        id=77777,
        access_hash=88888,
        file_reference=b"ref123",
        date=None,
        mime_type="application/x-tgsticker",
        size=1024,
        dc_id=1,
        attributes=[attr],
    )
    mock_reply = Message(id=2, peer_id=tl_types.PeerUser(12345))
    mock_reply.media = tl_types.MessageMediaDocument(document=doc)

    mock_msg = Message(id=3, peer_id=tl_types.PeerUser(12345))
    mock_msg.text = ".kang"
    mock_msg.reply_to_message = mock_reply
    mock_msg.sender_id = 12345
    mock_msg.user_args = []
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)
    mock_msg.edit_msg = AsyncMock(return_value=mock_msg)

    await stcr_mod.kang_fun(mock_client, mock_msg)

    # Verify bot was invoked to create or add sticker to set
    assert mock_bot.invoke.called
    call_arg = mock_bot.invoke.call_args[0][0]
    # Check that sticker item document is InputDocument with the exact id/access_hash
    if hasattr(call_arg, "stickers"):
        item = call_arg.stickers[0]
    else:
        item = call_arg.sticker
    assert isinstance(item.document, tl_types.InputDocument)
    assert item.document.id == 77777
    assert item.document.access_hash == 88888
    assert item.emoji == "🔥"
    assert "STICKER_KANGED" in mock_msg.edit_msg.call_args[0][0]


@pytest.mark.asyncio
async def test_devtools_security_owner_enforcement():
    """Verify non-owner users cannot execute eval or terminal commands."""
    import Main.plugins.userbot.devtools as devtools_mod
    from telethon import types as tl_types

    mock_client = AsyncMock()
    mock_client.myself = MagicMock(id=12345)

    # Message sent by a non-owner stranger
    stranger_msg = Message(id=10, peer_id=tl_types.PeerUser(99999))
    stranger_msg.text = ".eval print('hacked')"
    stranger_msg.sender_id = 99999
    stranger_msg.out = False
    stranger_msg.user_args = []
    stranger_msg.handle_message = AsyncMock(return_value=stranger_msg)
    stranger_msg.edit_msg = AsyncMock(return_value=stranger_msg)

    await devtools_mod.evaluate_command_handler(mock_client, stranger_msg)
    assert "Security Violation" in stranger_msg.edit_msg.call_args[0][0]

    stranger_msg.text = ".terminal whoami"
    await devtools_mod.terminal(mock_client, stranger_msg)
    assert "Security Violation" in stranger_msg.handle_message.call_args[0][0]


@pytest.mark.asyncio
async def test_cloud_tools_rm_security_root_protection():
    """Verify rm command protects root filesystem paths from deletion."""
    import Main.plugins.userbot.cloud_tools as cloud_mod
    from telethon import types as tl_types

    mock_client = AsyncMock()
    mock_msg = Message(id=20, peer_id=tl_types.PeerUser(12345))
    mock_msg.text = ".rm /"
    mock_msg.user_args = []
    mock_msg.handle_message = AsyncMock(return_value=mock_msg)
    mock_msg.edit = AsyncMock(return_value=mock_msg)

    await cloud_mod.remove_cmd_handler(mock_client, mock_msg)
    assert "Security Violation" in mock_msg.edit.call_args[0][0]



