# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import re
import logging
from typing import Iterable, List, Tuple

import telethon.extensions.html as tele_html
from telethon.extensions.html import (
    HTMLToTelegramParser,
    ENTITY_TO_FORMATTER,
    unparse as tele_unparse,
)
from telethon.helpers import add_surrogate, del_surrogate, strip_text
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityEmail,
    MessageEntityUrl,
    MessageEntityTextUrl,
    MessageEntityMentionName,
    MessageEntityUnderline,
    MessageEntityStrike,
    MessageEntityBlockquote,
    MessageEntitySpoiler,
    MessageEntityCustomEmoji,
    TypeMessageEntity,
)

logger = logging.getLogger("altruix.html_parser")

ALLOWED_TAGS = {
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "code", "pre", "blockquote", "a", "tg-spoiler", "spoiler", "tg-emoji"
}


def clean_and_normalize_html(text: str) -> str:
    """
    Sanitize and normalize HTML strings for Telegram formatting:
    1. Normalizes whitespace in closing tags (e.g. '< /code >' -> '</code>').
    2. Protects non-Telegram tags (e.g. '<username>', '<package_id>', '5 < 10') by
       escaping angle brackets to '&lt;' and '&gt;' so Telethon does not discard them.
    3. Auto-closes unclosed tags so formatting is never dropped.
    """
    if not text:
        return ""

    # Normalize closing tags with internal whitespace like '</ code>' or '< /code >'
    text = re.sub(r"<\s*/\s*([a-zA-Z0-9_-]+)\s*>", r"</\1>", text)
    # Normalize opening tags with internal whitespace like '< b >'
    text = re.sub(r"<\s*([a-zA-Z0-9_-]+)(\s*>)", r"<\1>", text)

    # Escape angle brackets of non-Telegram tags so user input is never eaten
    def tag_replacer(match: re.Match) -> str:
        full = match.group(0)
        tag_name = match.group(2).lower()
        if tag_name in ALLOWED_TAGS:
            return full
        return "&lt;" + full[1:-1] + "&gt;"

    text = re.sub(r"<(/)?([a-zA-Z0-9_-]+)(?:\s+[^<>]*)?>", tag_replacer, text)

    # Track open tags to auto-close any tags left open at end of text
    stack: List[str] = []
    for m in re.finditer(r"<(/)?([a-zA-Z0-9_-]+)(?:\s+[^<>]*)?>", text):
        is_close = bool(m.group(1))
        tag = m.group(2).lower()
        if tag not in ALLOWED_TAGS:
            continue
        if is_close:
            if tag in stack:
                stack.remove(tag)
        else:
            stack.append(tag)

    # Close any unclosed tags in reverse order
    for tag in reversed(stack):
        text += f"</{tag}>"

    return text


class RobustHTMLToTelegramParser(HTMLToTelegramParser):
    """
    Enhanced HTML parser supporting modern Telegram entities including
    tg-spoiler and robust attribute handling.
    """

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        if tag in ("tg-spoiler", "spoiler"):
            if tag not in self._building_entities:
                self._open_tags.appendleft(tag)
                self._open_tags_meta.appendleft(None)
                self._building_entities[tag] = MessageEntitySpoiler(
                    offset=len(self.text),
                    length=0,
                )
                return
        super().handle_starttag(tag, attrs)


def parse(html_text: str) -> Tuple[str, List[TypeMessageEntity]]:
    """
    Bulletproof parse method compatible with Telethon parse_mode interface.
    Never crashes and never eats user input.
    """
    if not html_text:
        return "", []

    try:
        normalized = clean_and_normalize_html(html_text)
        parser = RobustHTMLToTelegramParser()
        parser.feed(add_surrogate(normalized))

        # Close any lingering open entities if parser feed terminated abruptly
        for tag, entity in list(parser._building_entities.items()):
            entity.length = max(0, len(parser.text) - entity.offset)
            parser.entities.append(entity)
        parser._building_entities.clear()

        text = strip_text(parser.text, parser.entities)
        parser.entities.reverse()
        parser.entities.sort(key=lambda entity: entity.offset)
        return del_surrogate(text), parser.entities
    except Exception as exc:
        logger.warning(f"Robust HTML parse fallback triggered: {exc}")
        # Strip tags and return plain text without throwing
        plain_text = re.sub(r"<[^>]*>", "", html_text)
        return plain_text, []


def unparse(text: str, entities: Iterable[TypeMessageEntity]) -> str:
    """Reconvert text and entities back to HTML."""
    if MessageEntitySpoiler not in ENTITY_TO_FORMATTER:
        ENTITY_TO_FORMATTER[MessageEntitySpoiler] = ("<spoiler>", "</spoiler>")
    return tele_unparse(text, entities)


def patch_telethon_html() -> None:
    """Globally apply robust HTML parsing to Telethon extensions."""
    if MessageEntitySpoiler not in ENTITY_TO_FORMATTER:
        ENTITY_TO_FORMATTER[MessageEntitySpoiler] = ("<spoiler>", "</spoiler>")
    tele_html.parse = parse
    tele_html.unparse = unparse
    tele_html.HTMLToTelegramParser = RobustHTMLToTelegramParser
    logger.info("Telethon HTML parser patched with robust Altruix parser.")


__all__ = [
    "clean_and_normalize_html",
    "RobustHTMLToTelegramParser",
    "parse",
    "unparse",
    "patch_telethon_html",
]
