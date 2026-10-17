import pytest
import os
import asyncio
from Main.core.database import MongoDB, LocalDatabase
from Main.core.plugin_manager import PluginManager, PluginMetadata, GitHubPluginProvider
from Main.core.types.client import AltruixTelegramClient
from Main.core.types.message import Message


@pytest.mark.asyncio
async def test_localdatabase_mock_matching_mongo():
    """Verify LocalDatabase provides async motor/pymongo compatible interface."""
    db = LocalDatabase()
    col = db["test_collection"]

    # Insert
    res = await col.insert_one({"_id": "test_key", "value": "test_val", "count": 1})
    assert res is not None

    # Find one
    doc = await col.find_one({"_id": "test_key"})
    assert doc is not None
    assert doc["value"] == "test_val"

    # Update one
    await col.update_one({"_id": "test_key"}, {"$set": {"value": "updated_val"}})
    doc2 = await col.find_one({"_id": "test_key"})
    assert doc2["value"] == "updated_val"

    # Find with cursor
    cursor = col.find({})
    items = []
    async for item in cursor:
        items.append(item)
    assert len(items) == 1

    # find_one_and_update with $addToSet
    await col.find_one_and_update(
        {"_id": "test_key"},
        {"$addToSet": {"sessions": "session_string_123"}},
        upsert=True,
    )
    doc_set = await col.find_one({"_id": "test_key"})
    assert "session_string_123" in doc_set["sessions"]

    # find_one_and_delete
    del_doc = await col.find_one_and_delete({"_id": "test_key"})
    assert del_doc is not None
    assert await col.find_one({"_id": "test_key"}) is None


def test_plugin_metadata_and_github_provider():
    """Verify PluginManager parses GitHub repos and handles plugin registry."""
    provider = GitHubPluginProvider("https://github.com/Altruix/Plugins")
    assert provider.repo_url == "https://github.com/Altruix/Plugins"
    assert provider.repo_name == "Plugins"

    pm = PluginManager()
    assert pm.providers == []
    pm.add_provider(provider)
    assert len(pm.providers) == 1
    assert pm.providers[0].name == "github:Plugins"


def test_message_reply_and_forum_topics():
    """Verify Message handles forum topic thread id and reply attributes."""
    msg = Message(id=42, peer_id=None)
    msg.message = "Hello in topic"
    msg.reply_to_msg_id = 100
    msg.reply_to_top_id = 99  # Forum topic thread ID in modern Telegram

    assert msg.id == 42
    assert msg.text == "Hello in topic"
    assert msg.reply_to_msg_id == 100
    assert getattr(msg, "reply_to_top_id", None) == 99


@pytest.mark.asyncio
async def test_callback_query_regex_filter():
    """Verify filters.regex correctly matches Telethon CallbackQuery.Event with bytes payload."""
    from telethon.events import CallbackQuery
    from telethon.tl import types
    from Main.utils.custom_filters import filters

    query = types.UpdateBotCallbackQuery(
        query_id=123,
        user_id=456,
        peer=types.PeerUser(456),
        msg_id=789,
        chat_instance=1,
        data=b"session_yes",
    )
    event = CallbackQuery.Event(query, types.PeerUser(456), 789)

    f_yes = filters.regex("^session_yes")
    f_no = filters.regex("^session_no")

    assert await f_yes(None, event) is True
    assert await f_no(None, event) is False


def test_robust_html_parser():
    """Verify robust HTML parser handles non-telegram tags, unclosed tags, and spoilers."""
    from Main.core.html_parser import parse, clean_and_normalize_html
    from telethon.tl.types import MessageEntityBold, MessageEntityItalic, MessageEntitySpoiler, MessageEntityCode

    # 1. Non-telegram tags should NOT be stripped (e.g. <user_id> or <pkg>)
    text = "Usage: .help <plugin_name> and 5 < 10"
    parsed_text, entities = parse(text)
    assert "<plugin_name>" in parsed_text
    assert "5 < 10" in parsed_text

    # 2. Malformed spacing like < /code > should be normalized
    text2 = "Here is <code>my_code< /code >"
    parsed_text2, entities2 = parse(text2)
    assert parsed_text2 == "Here is my_code"
    assert len(entities2) == 1
    assert isinstance(entities2[0], MessageEntityCode)

    # 3. Unclosed tags should be auto-closed, preserving entities
    text3 = "<b>Bold <i>Italic text"
    parsed_text3, entities3 = parse(text3)
    assert parsed_text3 == "Bold Italic text"
    assert len(entities3) == 2
    types_set = {type(e) for e in entities3}
    assert MessageEntityBold in types_set
    assert MessageEntityItalic in types_set

    # 4. Spoilers supported
    text4 = "Secret: <tg-spoiler>hidden password</tg-spoiler>"
    parsed_text4, entities4 = parse(text4)
    assert "hidden password" in parsed_text4
    assert len(entities4) == 1
    assert isinstance(entities4[0], MessageEntitySpoiler)


@pytest.mark.asyncio
async def test_suppress_error():
    """Verify safe error suppression context manager, logger output, and decorator."""
    from Main.utils.suppress import suppress_error
    import logging

    caught_logs = []
    test_logger = logging.getLogger("test_suppress")
    test_logger.setLevel(logging.DEBUG)

    class CapturingHandler(logging.Handler):
        def emit(self, record):
            caught_logs.append(record.getMessage())

    handler = CapturingHandler()
    test_logger.addHandler(handler)

    # 1. Sync suppression
    with suppress_error(ValueError, logger_instance=test_logger, msg="Test sync"):
        raise ValueError("Invalid value test")

    assert any("Test sync" in log and "ValueError" in log for log in caught_logs)

    # 2. Async suppression
    async with suppress_error(ZeroDivisionError, logger_instance=test_logger, msg="Test async"):
        _ = 1 / 0

    assert any("Test async" in log and "ZeroDivisionError" in log for log in caught_logs)

    # 3. Does not suppress unhandled exceptions
    with pytest.raises(KeyError):
        with suppress_error(ValueError):
            raise KeyError("must not be suppressed")

    # 4. Never suppresses KeyboardInterrupt or SystemExit
    with pytest.raises(KeyboardInterrupt):
        with suppress_error():
            raise KeyboardInterrupt()

    # 5. Decorator usage
    @suppress_error(Exception, logger_instance=test_logger, msg="Decorated test")
    async def failing_coroutine():
        raise RuntimeError("Decorated async error")

    result = await failing_coroutine()
    assert result is None
    assert any("Decorated test" in log for log in caught_logs)


def test_raw_telethon_message_has_altruix_helpers():
    """Verify raw Telethon Message instances have edit_msg, reply_msg, handle_message, etc."""
    from telethon.tl.custom import Message as TelethonMessage
    from Main.core.types.message import Message, enrich_message

    raw = TelethonMessage(id=10, peer_id=None, date=None, message=".ping")
    assert hasattr(raw, "edit_msg")
    assert hasattr(raw, "reply_msg")
    assert hasattr(raw, "handle_message")
    assert hasattr(raw, "user_args")

    enriched = enrich_message(raw, None)
    assert isinstance(enriched, Message)
    assert hasattr(enriched, "edit_msg")
    assert enriched.command_ == "ping"



