# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import os
import asyncio
import logging
import mimetypes
from typing import Any, Dict, List, Optional, Tuple, Union

from telethon import TelegramClient, functions, types, errors, utils
from Main.utils.file_utils import FileHelpers

logger = logging.getLogger("altruix.client")

def _user_mention(user):
    name = getattr(user, "first_name", None) or "User"
    if getattr(user, "username", None):
        return f"@{user.username}"
    return f"<a href='tg://user?id={user.id}'>{name}</a>"

for _target, _attr, _val in [
    (types.User, "is_bot", property(lambda self: bool(getattr(self, "bot", False)))),
    (types.User, "mention", property(_user_mention)),
    (types.User, "type", "private"),
    (types.Channel, "type", property(lambda self: "channel" if getattr(self, "broadcast", False) else "supergroup")),
    (types.Channel, "mention", property(lambda self: f"@{self.username}" if getattr(self, "username", None) else f"<b>{getattr(self, 'title', 'Channel')}</b>")),
    (types.Chat, "type", "group"),
    (types.Chat, "mention", property(lambda self: f"<b>{getattr(self, 'title', 'Group')}</b>")),
]:
    if not hasattr(_target, _attr):
        try:
            setattr(_target, _attr, _val)
        except Exception:
            pass


class AltruixTelegramClient(TelegramClient):
    """
    Subclassed Telethon TelegramClient providing high-level convenience methods
    and backwards compatibility with Altruix plugin interfaces.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__class__.__module__ = "telethon.client.telegramclient"
        from Main.core.html_parser import patch_telethon_html
        patch_telethon_html()
        self.parse_mode = "html"
        self.myself: Optional[types.User] = None
        self._permission_cache: Dict[int, Dict[str, Any]] = {}

    async def send_message(self, *args, **kwargs) -> Any:
        res = await super().send_message(*args, **kwargs)
        from Main.core.types.message import enrich_message
        return enrich_message(res, self)

    async def edit_message(self, *args, **kwargs) -> Any:
        res = await super().edit_message(*args, **kwargs)
        from Main.core.types.message import enrich_message
        return enrich_message(res, self)

    async def send_file(self, *args, **kwargs) -> Any:
        progress_msg = kwargs.pop("progress_msg", None)
        if progress_msg and "progress_callback" not in kwargs:
            file_target = args[1] if len(args) > 1 else kwargs.get("file")
            fname = "file"
            if isinstance(file_target, (str, bytes, os.PathLike)):
                fname = os.path.basename(str(file_target))
            from Main.utils.progress import create_progress_callback
            kwargs["progress_callback"] = create_progress_callback(
                progress_msg,
                action="Uploading",
                file_name=fname,
            )
        res = await super().send_file(*args, **kwargs)
        from Main.core.types.message import enrich_message
        return enrich_message(res, self)

    async def invoke(self, query: Any, *args, **kwargs) -> Any:
        """Execute a raw MTProto TL request with automatic FloodWait handling."""
        max_retries = 5
        retries = 0
        while True:
            try:
                return await self(query)
            except errors.FloodWaitError as e:
                retries += 1
                if retries > max_retries:
                    raise
                wait_sec = e.seconds + 3
                logger.warning(f"FloodWait: sleeping for {wait_sec}s")
                await asyncio.sleep(wait_sec)
            except errors.SlowModeWaitError as e:
                retries += 1
                if retries > max_retries:
                    raise
                wait_sec = e.seconds + 2
                logger.warning(f"SlowmodeWait: sleeping for {wait_sec}s")
                await asyncio.sleep(wait_sec)

    async def get_users(self, entity: Union[int, str, types.User]) -> types.User:
        """Fetch a User entity by username or ID."""
        ent = await self.get_entity(entity)
        if hasattr(ent, "first_name"):
            return ent
        return ent

    async def get_group(self, entity: Union[int, str]) -> Any:
        """Fetch a Chat / Channel entity."""
        return await self.get_entity(entity)

    async def get_chat(self, entity: Union[int, str]) -> Any:
        return await self.get_entity(entity)

    async def get_chat_member(self, chat_id: Union[int, str], user_id: Union[int, str]) -> Any:
        return await self.get_permissions(chat_id, user_id)

    async def pin_chat_message(self, chat_id: Union[int, str], message_id: int, notify: bool = False) -> Any:
        return await self.pin_message(chat_id, message_id, notify=notify)

    async def unpin_chat_message(self, chat_id: Union[int, str], message_id: int) -> Any:
        return await self.unpin_message(chat_id, message_id)

    async def set_chat_title(self, chat_id: Union[int, str], title: str) -> Any:
        entity = await self.get_entity(chat_id)
        if isinstance(entity, types.Channel):
            return await self(functions.channels.EditTitleRequest(
                channel=utils.get_input_channel(await self.get_input_entity(entity)),
                title=title,
            ))
        if isinstance(entity, types.Chat):
            return await self(functions.messages.EditChatTitleRequest(
                chat_id=entity.id,
                title=title,
            ))
        raise ValueError("A group or channel is required to change its title")

    async def set_chat_photo(self, chat_id: Union[int, str], photo: str) -> Any:
        uploaded = await self.upload_file(photo)
        entity = await self.get_entity(chat_id)
        chat_photo = types.InputChatUploadedPhoto(file=uploaded)
        if isinstance(entity, types.Channel):
            return await self(functions.channels.EditPhotoRequest(
                channel=utils.get_input_channel(await self.get_input_entity(entity)),
                photo=chat_photo,
            ))
        if isinstance(entity, types.Chat):
            return await self(functions.messages.EditChatPhotoRequest(
                chat_id=entity.id,
                photo=chat_photo,
            ))
        raise ValueError("A group or channel is required to change its photo")

    async def delete_chat_photo(self, chat_id: Union[int, str]) -> Any:
        entity = await self.get_entity(chat_id)
        chat_photo = types.InputChatPhotoEmpty()
        if isinstance(entity, types.Channel):
            return await self(functions.channels.EditPhotoRequest(
                channel=utils.get_input_channel(await self.get_input_entity(entity)),
                photo=chat_photo,
            ))
        if isinstance(entity, types.Chat):
            return await self(functions.messages.EditChatPhotoRequest(
                chat_id=entity.id,
                photo=chat_photo,
            ))
        raise ValueError("A group or channel is required to remove its photo")

    async def ban_chat_member(self, chat_id: Union[int, str], user_id: Union[int, str], until_date=None) -> Any:
        return await self.edit_permissions(chat_id, user_id, view_messages=False, until_date=until_date)

    async def unban_chat_member(self, chat_id: Union[int, str], user_id: Union[int, str]) -> Any:
        return await self.edit_permissions(
            chat_id,
            user_id,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True,
            embed_link_previews=True,
            send_polls=True,
            change_info=False,
            invite_users=True,
            pin_messages=False,
        )

    async def kick_chat_member(self, chat_id: Union[int, str], user_id: Union[int, str]) -> Any:
        try:
            return await self.kick_participant(chat_id, user_id)
        except Exception:
            return await self.ban_chat_member(chat_id, user_id)

    def guess_mime_type(self, file_path: str) -> str:
        mime, _ = mimetypes.guess_type(file_path)
        return mime or "application/octet-stream"

    async def fetch_chats(self) -> List[Any]:
        """Fetch all groups and channels where client participates."""
        chats = []
        async for dialog in self.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                chats.append(dialog.entity)
        return chats

    def get_chat_history(self, chat_id: Union[int, str], limit: Optional[int] = None):
        """Async iterator over chat messages."""
        return self.iter_messages(chat_id, limit=limit)

    async def check_my_perm(self, msg: Any, perm_type: str) -> Tuple[Optional[bool], Optional[Dict[str, Any]]]:
        """Check admin permissions for current client in given chat."""
        try:
            chat_id = msg.chat_id if hasattr(msg, "chat_id") else msg.chat.id
        except Exception:
            return None, None

        if hasattr(msg, "user_args") and "-no-cache" not in msg.user_args and chat_id in self._permission_cache:
            perms_json = self._permission_cache[chat_id]
            return perms_json.get(perm_type, False), perms_json

        try:
            perms = await self.get_permissions(chat_id, "me")
            is_creator = getattr(perms, "is_creator", False)
            perms_json = {
                "chat": chat_id,
                "can_delete_messages": is_creator or getattr(perms, "delete_messages", False),
                "can_restrict_members": is_creator or getattr(perms, "ban_users", False),
                "can_promote_members": is_creator or getattr(perms, "add_admins", False),
                "can_change_info": is_creator or getattr(perms, "change_info", False),
                "can_invite_users": is_creator or getattr(perms, "invite_users", False),
                "can_pin_messages": is_creator or getattr(perms, "pin_messages", False),
                "can_manage_voice_chats": is_creator or getattr(perms, "manage_call", False),
                "is_anonymous": getattr(perms, "anonymous", False),
                "can_be_edited": getattr(perms, "has_admin_rights", False),
            }
            self._permission_cache[chat_id] = perms_json
            return perms_json.get(perm_type, False), perms_json
        except Exception as e:
            logger.debug(f"Could not check permissions: {e}")
            return None, None

    async def get_inline_bot_results(self, bot: Union[str, int, types.User], query: str = "") -> Any:
        """Fetch inline bot results."""
        return await self.inline_query(bot, query)

    async def send_inline_bot_result(
        self,
        chat_id: Union[int, str],
        query_id: Any = None,
        result_id: Any = None,
        reply_to_message_id: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """Send an inline bot result to a chat."""
        try:
            return await self(functions.messages.SendInlineBotResultRequest(
                peer=await self.get_input_entity(chat_id),
                query_id=int(query_id) if query_id else 0,
                id=str(result_id),
                random_id=int.from_bytes(os.urandom(8), byteorder="big", signed=True),
                reply_to=(
                    types.InputReplyToMessage(reply_to_message_id)
                    if reply_to_message_id is not None
                    else None
                ),
            ))
        except Exception as e:
            logger.error(f"Error sending inline bot result: {e}")
            raise

    async def resolve_peer(self, peer: Any) -> Any:
        """Resolve a peer entity to an InputPeer."""
        return await self.get_input_entity(peer)

    async def upload_doc(self, file_path: str, peer: Any = None, force_file: bool = False) -> types.InputDocument:
        """Upload a file and return an InputDocument representation."""
        from telethon import utils
        uploaded = await self.upload_file(file_path)
        mime = self.guess_mime_type(file_path)
        if file_path.endswith(".tgs"):
            mime = "application/x-tgsticker"
        elif file_path.endswith(".webm"):
            mime = "video/webm"
        elif file_path.endswith(".png"):
            mime = "image/png"

        if peer:
            resolved = await self.get_input_entity(peer)
            target_peer = utils.get_input_peer(resolved)
        else:
            target_peer = types.InputPeerSelf()

        uploaded_media = await self(functions.messages.UploadMediaRequest(
            peer=target_peer,
            media=types.InputMediaUploadedDocument(
                file=uploaded,
                mime_type=mime,
                attributes=[types.DocumentAttributeFilename(os.path.basename(file_path))],
                force_file=force_file,
            ),
        ))
        return utils.get_input_document(uploaded_media.document)

    async def copy_message(
        self,
        chat_id: Union[int, str],
        from_chat_id: Union[int, str],
        id: int,
        reply_to_message_id: Optional[int] = None,
        caption: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Copy a message from one chat to another."""
        msg = await self.get_messages(from_chat_id, ids=id)
        if not msg:
            return None
        text = caption if caption is not None else (msg.text or msg.message or "")
        if msg.media:
            return await self.send_file(
                chat_id,
                file=msg.media,
                caption=text,
                reply_to=reply_to_message_id,
            )
        return await self.send_message(
            chat_id,
            message=text,
            reply_to=reply_to_message_id,
        )





# Expose Client alias for legacy plugin imports
Client = AltruixTelegramClient
AltruixTelegramClient.__module__ = "telethon.client.telegramclient"
