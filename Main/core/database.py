# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import os
import logging
import certifi
import ujson as json
from os import path
from typing import Any, Dict, List, Optional, AsyncIterator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure

logger = logging.getLogger("altruix.database")


class MongoDB:
    """
    Async MongoDB wrapper using motor v3.x (pymongo>=4.7 backend).
    Provides all collection accessors and a make_collection factory.
    """

    def __init__(self, uri: str, db_name: str = "Altruix") -> None:
        self.tlsca_ = certifi.where()
        self._client = AsyncIOMotorClient(
            uri,
            tlsCAFile=self.tlsca_,
            serverSelectionTimeoutMS=10_000,
            connectTimeoutMS=10_000,
            socketTimeoutMS=30_000,
            maxPoolSize=50,
            minPoolSize=5,
        )
        self._db_name: AsyncIOMotorDatabase = self._client[db_name]

        # Standard collections
        self.settings_col: AsyncIOMotorCollection = self._db_name["SETTINGS"]
        self.data_col: AsyncIOMotorCollection = self._db_name["DATA"]
        self.user_col: AsyncIOMotorCollection = self._db_name["USERS"]
        self.env_col: AsyncIOMotorCollection = self._db_name["ENV"]
        self.stickers_col: AsyncIOMotorCollection = self._db_name["STICKERS"]
        self.plugins_col: AsyncIOMotorCollection = self._db_name["PLUGINS"]

    async def ping(self) -> bool:
        """Ping the MongoDB server to verify connectivity."""
        try:
            result = await self._db_name.command("ping")
            return result.get("ok") == 1.0
        except (ServerSelectionTimeoutError, OperationFailure) as e:
            logger.error(f"MongoDB ping failed: {e}")
            return False

    def make_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get or create a named collection."""
        return self._db_name[name]

    async def list_collection_names(self) -> List[str]:
        return await self._db_name.list_collection_names()

    async def drop_collection(self, name: str) -> None:
        await self._db_name.drop_collection(name)

    def close(self) -> None:
        """Close the motor client connection pool."""
        self._client.close()

    async def __aenter__(self) -> "MongoDB":
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.close()


class LocalDatabase:
    """
    JSON-backed fallback database for offline / credential-less mode.
    Provides a MongoDB-like async interface for simple key-value collections.
    """

    def __init__(self, file_path: str = "local_db.json") -> None:
        self.path = file_path
        self.data: Dict[str, Any] = {}
        if path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (ValueError, json.JSONDecodeError):
                self.data = {}
        self.save()
        # Build collection proxies
        self.settings_col = self.make_collection("SETTINGS")
        self.data_col = self.make_collection("DATA")
        self.user_col = self.make_collection("USERS")
        self.env_col = self.make_collection("ENV")
        self.stickers_col = self.make_collection("STICKERS")
        self.plugins_col = self.make_collection("PLUGINS")

    def __getitem__(self, name: str) -> "LocalCollection":
        return self.make_collection(name)

    def make_collection(self, name: str) -> "LocalCollection":
        if name not in self.data:
            self.data[name] = []
        return LocalCollection(self, name)

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save LocalDatabase: {e}")

    async def command(self, cmd: str, **kwargs: Any) -> Dict[str, Any]:
        """Stub for compatibility with code calling db._db_name.command()."""
        if cmd == "ping":
            return {"ok": 1.0}
        if cmd == "dbstats":
            return {"dataSize": 0, "storageSize": 0}
        return {}


class InsertOneResult:
    def __init__(self, inserted_id: Any) -> None:
        self.inserted_id = inserted_id


class DeleteResult:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count


class LocalCollection:
    """
    Minimal async collection proxy over LocalDatabase for offline fallback.
    Mimics the motor AsyncIOMotorCollection interface.
    """

    def __init__(self, db: LocalDatabase, name: str) -> None:
        self._db = db
        self._name = name

    def _col(self) -> List[Dict[str, Any]]:
        return self._db.data.setdefault(self._name, [])

    def _matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        for k, v in query.items():
            if isinstance(v, dict) and "$in" in v:
                if doc.get(k) not in v["$in"]:
                    return False
            elif doc.get(k) != v:
                return False
        return True

    async def find_one(self, query: Dict[str, Any] = {}) -> Optional[Dict[str, Any]]:
        for doc in self._col():
            if self._matches(doc, query):
                return dict(doc)
        return None

    def find(self, query: Dict[str, Any] = {}) -> "LocalCollectionCursor":
        matching = [dict(d) for d in self._col() if self._matches(d, query)]
        return LocalCollectionCursor(matching)

    async def insert_one(self, document: Dict[str, Any]) -> InsertOneResult:
        doc = dict(document)
        self._col().append(doc)
        self._db.save()
        return InsertOneResult(doc.get("_id"))

    def _apply_update(self, doc: Dict[str, Any], update: Dict[str, Any]) -> None:
        if "$set" in update:
            doc.update(update["$set"])
        if "$addToSet" in update:
            for k, v in update["$addToSet"].items():
                lst = doc.setdefault(k, [])
                if not isinstance(lst, list):
                    lst = [lst]
                    doc[k] = lst
                if isinstance(v, dict) and "$each" in v:
                    for item in v["$each"]:
                        if item not in lst:
                            lst.append(item)
                elif v not in lst:
                    lst.append(v)
        if "$push" in update:
            for k, v in update["$push"].items():
                lst = doc.setdefault(k, [])
                if not isinstance(lst, list):
                    lst = [lst]
                    doc[k] = lst
                if isinstance(v, dict) and "$each" in v:
                    lst.extend(v["$each"])
                else:
                    lst.append(v)
        if "$pull" in update:
            for k, v in update["$pull"].items():
                if k in doc and isinstance(doc[k], list):
                    doc[k] = [x for x in doc[k] if x != v]
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = doc.get(k, 0) + v

    async def update_one(
        self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False
    ) -> None:
        for doc in self._col():
            if self._matches(doc, query):
                self._apply_update(doc, update)
                self._db.save()
                return
        if upsert:
            new_doc = dict(query)
            self._apply_update(new_doc, update)
            self._col().append(new_doc)
            self._db.save()

    async def find_one_and_update(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        return_document: bool = False,
    ) -> Optional[Dict[str, Any]]:
        for doc in self._col():
            if self._matches(doc, query):
                old = dict(doc)
                self._apply_update(doc, update)
                self._db.save()
                return dict(doc) if return_document else old
        if upsert:
            new_doc = dict(query)
            self._apply_update(new_doc, update)
            self._col().append(new_doc)
            self._db.save()
            return dict(new_doc)
        return None

    async def find_one_and_delete(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        col = self._col()
        for i, doc in enumerate(col):
            if self._matches(doc, query):
                removed = col.pop(i)
                self._db.save()
                return dict(removed)
        return None

    async def delete_one(self, query: Dict[str, Any]) -> DeleteResult:
        col = self._col()
        for i, doc in enumerate(col):
            if self._matches(doc, query):
                col.pop(i)
                self._db.save()
                return DeleteResult(1)
        return DeleteResult(0)

    async def delete_many(self, query: Dict[str, Any]) -> None:
        self._db.data[self._name] = [
            d for d in self._col() if not self._matches(d, query)
        ]
        self._db.save()

    async def count_documents(self, query: Dict[str, Any] = {}) -> int:
        return sum(1 for d in self._col() if self._matches(d, query))

    def __aiter__(self) -> "LocalCollectionCursor":
        return LocalCollectionCursor(self._col())


class LocalCollectionCursor:
    def __init__(self, docs: List[Dict[str, Any]]) -> None:
        self._docs = iter(docs)

    def __aiter__(self) -> "LocalCollectionCursor":
        return self

    async def __anext__(self) -> Dict[str, Any]:
        try:
            return dict(next(self._docs))
        except StopIteration:
            raise StopAsyncIteration
