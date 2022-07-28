# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


import os
import asyncio
from Main import Altruix
from typing import Union
from pyrogram import Client, raw
from pyrogram.types import ChatMember
from ...utils.file_utils import FileHelpers
from ...utils.startup_helpers import monkeypatch
from pyrogram.errors.exceptions import FloodWait, SlowmodeWait


@monkeypatch(Client)
class CustomClientMethods:
    def __init__(self) -> None:
        super().__init__()

    async def get_group(self, *args, **kwargs):
        chat_obj = await self.get_chat(*args, **kwargs)
        if str(chat_obj.type).lower().startswith("chattype."):
            chat_type = str((str(chat_obj.type).lower()).split("chattype.")[1])
            chat_obj.type = chat_type
        return chat_obj

    async def invoke(self, *args, **kwargs):
        mmax_ = 5
        max_count = 0
        while True:
            try:
                return await self.__send_custom__(*args, **kwargs)
            except (FloodWait, SlowmodeWait) as e:
                if max_count > mmax_:
                    raise e
                Altruix.log(f"[{e.__class__.__name__}]: sleeping for - {e + 3}s.")
                await asyncio.sleep(e + 3)
                max_count += 1

    async def send_file(
        self: Client,
        entity: Union[str, int],
        file_path: str,
        thumb: str = None,
        *args,
        **kwargs,
    ):
        file_ = FileHelpers(file_path, self)
        if file_.is_photo:
            file_path = await file_._resize_if_req()
            return await self.send_photo(entity, file_path, *args, **kwargs)
        if file_.is_sticker or file_.is_animated_sticker:
            return await self.send_sticker(entity, file_path, *args, **kwargs)
        if file_.is_video:
            dur, width, height = await file_._get_metadata(is_audio=False)
            return await self.send_video(
                entity,
                file_path,
                thumb=thumb,
                duration=dur,
                width=width,
                height=height,
                *args,
                **kwargs,
            )
        if file_.is_audio:
            dur, title = await file_._get_metadata()
            return await self.send_audio(
                entity,
                file_path,
                thumb=thumb,
                duration=dur,
                title=title,
                *args,
                **kwargs,
            )
        if file_.is_audio_note:
            dur, title = await file_._get_metadata()
            return await self.send_voice(
                entity, file_path, duration=dur, *args, **kwargs
            )
        return await self.send_document(entity, file_path, thumb=thumb, *args, **kwargs)

    async def upload_doc(self, file_: str, peer_, force_file=False):
        uploaded_doc = await self.save_file(file_)
        chat_pperr = peer_
        mime_ = self.guess_mime_type(file_)
        media = raw.types.InputMediaUploadedDocument(
            mime_type=mime_,
            file=uploaded_doc,
            force_file=force_file,
            attributes=[
                raw.types.DocumentAttributeFilename(file_name=os.path.basename(file_))
            ],
        )
        uploaded_media_ = await self.invoke(
            raw.functions.messages.UploadMedia(peer=chat_pperr, media=media)
        )
        if os.path.exists(file_):
            os.remove(file_)
        return raw.types.InputDocument(
            id=uploaded_media_.document.id,
            access_hash=uploaded_media_.document.access_hash,
            file_reference=uploaded_media_.document.file_reference,
        )

    async def fetch_chats(self: Client):
        return [
            x
            async for x in self.get_dialogs()
            if (not x.chat.type.PRIVATE or not x.chat.type.BOT)
        ]

    async def check_my_perm(self, msg, perm_type):
        my_id = self.myself.id
        chat = msg.chat
        u_args = msg.user_args
        if (
            ("-no-cache" not in u_args)
            and Altruix.SELF_PERMISSION_CACHE.get(chat.id)
            and Altruix.SELF_PERMISSION_CACHE.get(chat.id).get(my_id)
        ):
            perms_json = Altruix.SELF_PERMISSION_CACHE[chat.id][my_id]
        else:
            try:
                c: Client = msg._client
                ps: ChatMember = await c.get_chat_member(chat.id, my_id)
            except Exception:
                return None, None
            perms_json = {
                "chat": chat.id,
                "can_delete_messages": True
                if ps.status.OWNER
                else ps.privileges.can_delete_messages,
                "can_restrict_members": True
                if ps.status.OWNER
                else ps.privileges.can_restrict_members,
                "can_promote_members": True
                if ps.status.OWNER
                else ps.privileges.can_promote_members,
                "can_change_info": True
                if ps.status.OWNER
                else ps.privileges.can_change_info,
                "can_invite_users": True
                if ps.status.OWNER
                else ps.privileges.can_invite_users,
                "can_pin_messages": True
                if ps.status.OWNER
                else ps.privileges.can_pin_messages,
                "can_manage_voice_chats": True
                if ps.status.OWNER
                else ps.privileges.can_manage_video_chats,
                "is_anonymous": True if ps.status.OWNER else ps.privileges.is_anonymous,
                "can_be_edited": ps.can_be_edited,
            }
            if not Altruix.SELF_PERMISSION_CACHE.get(chat.id):
                Altruix.SELF_PERMISSION_CACHE[chat.id] = {}
            Altruix.SELF_PERMISSION_CACHE[chat.id][my_id] = perms_json
        return perms_json[perm_type], perms_json
