# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.


class Cache:
    def __init__(self, config, db, clients) -> None:
        self.config = config
        self.db = db
        self.clients = clients

    async def update_all(self):
        """Update all in-memory caches across all connected client sessions."""
        await self.update_auto_post_cache()
        await self.update_filters_cache()
        await self.update_blacklist_cache()

    async def update_auto_post_cache(self):
        auto_post_db = self.db.make_collection("auto_post_s")
        for client in self.clients:
            if not self.config.AUTOPOST_CACHE.get(client.myself.id):
                self.config.AUTOPOST_CACHE[client.myself.id] = {}
            async for adb in auto_post_db.find({"client_id": client.myself.id}):
                if adb and adb.get("from_chat") and adb.get("to_chat"):
                    from_chat = int(adb["from_chat"])
                    to_chat = int(adb["to_chat"])
                    if from_chat not in self.config.AUTOPOST_CACHE[client.myself.id]:
                        self.config.AUTOPOST_CACHE[client.myself.id][from_chat] = [to_chat]
                    else:
                        self.config.AUTOPOST_CACHE[client.myself.id][from_chat].append(to_chat)

    async def update_filters_cache(self):
        filters_db = self.db.make_collection("FILTERS")
        for client in self.clients:
            my_id = client.myself.id
            if my_id not in self.config.FILTERS_CACHE:
                self.config.FILTERS_CACHE[my_id] = {}
            async for doc in filters_db.find({"client_id": my_id}):
                chat_id = doc.get("chat_id")
                kw = doc.get("keyword")
                reply = doc.get("reply")
                if chat_id is not None and kw:
                    self.config.FILTERS_CACHE[my_id].setdefault(chat_id, {})[kw.lower()] = reply

    async def update_blacklist_cache(self):
        bl_db = self.db.make_collection("BLACKLIST")
        for client in self.clients:
            my_id = client.myself.id
            if my_id not in self.config.BLACKLIST_CACHE:
                self.config.BLACKLIST_CACHE[my_id] = {}
            async for doc in bl_db.find({"client_id": my_id}):
                chat_id = doc.get("chat_id")
                word = doc.get("bl_word")
                warns = doc.get("warns", False)
                if chat_id is not None and word:
                    self.config.BLACKLIST_CACHE[my_id].setdefault(chat_id, {})[word.lower()] = warns
