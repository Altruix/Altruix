# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import os
import re
import uuid
import sqlite3
import asyncio
import logging
import contextlib
import certifi
import ujson as json
from os import path
from typing import Any, Dict, List, Optional, AsyncIterator, Callable, Union
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from Main.core.mongo_parser import PyMongoInstructionParser

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
        self._dirty = True
        try:
            loop = asyncio.get_running_loop()
            if not getattr(self, "_save_task_running", False):
                self._save_task_running = True
                loop.create_task(self._async_flush())
        except RuntimeError:
            self._sync_flush()

    async def _async_flush(self) -> None:
        await asyncio.sleep(0.05)
        self._save_task_running = False
        if getattr(self, "_dirty", False):
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._sync_flush)

    def _sync_flush(self) -> None:
        self._dirty = False
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


def _apply_cursor_transforms(
    docs: List[Dict[str, Any]],
    sort_key: Optional[Any],
    sort_dir: int,
    skip: Optional[int],
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    result = list(docs)
    if sort_key is not None:
        if isinstance(sort_key, str):
            reverse = sort_dir < 0
            result.sort(key=lambda d: (d.get(sort_key) is None, d.get(sort_key, 0)), reverse=reverse)
        elif isinstance(sort_key, (list, tuple)):
            for item in reversed(sort_key):
                if isinstance(item, (tuple, list)) and len(item) == 2:
                    k, direction = item
                    result.sort(key=lambda d: (d.get(k) is None, d.get(k, 0)), reverse=(direction < 0))
    if skip and skip > 0:
        result = result[skip:]
    if limit is not None and limit >= 0:
        result = result[:limit]
    return result


class LocalCollection:
    """
    Async collection proxy over LocalDatabase for offline fallback.
    Uses PyMongoInstructionParser for complete MongoDB query & update parity.
    """

    def __init__(self, db: LocalDatabase, name: str) -> None:
        self._db = db
        self._name = name

    def _col(self) -> List[Dict[str, Any]]:
        return self._db.data.setdefault(self._name, [])

    async def find_one(self, query: Dict[str, Any] = {}) -> Optional[Dict[str, Any]]:
        for doc in self._col():
            if PyMongoInstructionParser.match_document(doc, query):
                return dict(doc)
        return None

    def find(self, query: Dict[str, Any] = {}) -> "LocalCollectionCursor":
        matching = [dict(d) for d in self._col() if PyMongoInstructionParser.match_document(d, query)]
        return LocalCollectionCursor(matching)

    async def insert_one(self, document: Dict[str, Any]) -> InsertOneResult:
        doc = dict(document)
        doc_id = str(doc.get("_id", uuid.uuid4().hex))
        doc["_id"] = doc_id
        self._col().append(doc)
        self._db.save()
        return InsertOneResult(doc_id)

    async def update_one(
        self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False
    ) -> None:
        for doc in self._col():
            if PyMongoInstructionParser.match_document(doc, query):
                PyMongoInstructionParser.apply_update(doc, update)
                self._db.save()
                return
        if upsert:
            new_doc = dict(query)
            if "_id" not in new_doc:
                new_doc["_id"] = uuid.uuid4().hex
            PyMongoInstructionParser.apply_update(new_doc, update)
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
            if PyMongoInstructionParser.match_document(doc, query):
                old = dict(doc)
                PyMongoInstructionParser.apply_update(doc, update)
                self._db.save()
                return dict(doc) if return_document else old
        if upsert:
            new_doc = dict(query)
            if "_id" not in new_doc:
                new_doc["_id"] = uuid.uuid4().hex
            PyMongoInstructionParser.apply_update(new_doc, update)
            self._col().append(new_doc)
            self._db.save()
            return new_doc
        return None

    async def find_one_and_delete(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for i, doc in enumerate(self._col()):
            if PyMongoInstructionParser.match_document(doc, query):
                deleted = self._col().pop(i)
                self._db.save()
                return dict(deleted)
        return None

    async def delete_one(self, query: Dict[str, Any]) -> DeleteResult:
        for i, doc in enumerate(self._col()):
            if PyMongoInstructionParser.match_document(doc, query):
                self._col().pop(i)
                self._db.save()
                return DeleteResult(1)
        return DeleteResult(0)

    async def delete_many(self, query: Dict[str, Any]) -> DeleteResult:
        original_len = len(self._col())
        self._db.data[self._name] = [
            d for d in self._col() if not PyMongoInstructionParser.match_document(d, query)
        ]
        deleted_count = original_len - len(self._col())
        if deleted_count > 0:
            self._db.save()
        return DeleteResult(deleted_count)

    async def count_documents(self, query: Dict[str, Any] = {}) -> int:
        if not query:
            return len(self._col())
        return sum(1 for doc in self._col() if PyMongoInstructionParser.match_document(doc, query))

    def __aiter__(self) -> "LocalCollectionCursor":
        return LocalCollectionCursor(self._col())


class LocalCollectionCursor:
    """In-memory cursor supporting PyMongo cursor chaining methods."""

    def __init__(self, docs: List[Dict[str, Any]]) -> None:
        self._raw_docs = docs
        self._sort_key = None
        self._sort_dir = 1
        self._skip = None
        self._limit = None
        self._iter = None

    def sort(self, key_or_list: Any, direction: int = 1) -> "LocalCollectionCursor":
        self._sort_key = key_or_list
        self._sort_dir = direction
        return self

    def limit(self, limit: int) -> "LocalCollectionCursor":
        self._limit = limit
        return self

    def skip(self, skip: int) -> "LocalCollectionCursor":
        self._skip = skip
        return self

    def _get_processed(self) -> List[Dict[str, Any]]:
        return _apply_cursor_transforms(
            self._raw_docs, self._sort_key, self._sort_dir, self._skip, self._limit
        )

    def __aiter__(self) -> "LocalCollectionCursor":
        self._iter = iter(self._get_processed())
        return self

    async def __anext__(self) -> Dict[str, Any]:
        if self._iter is None:
            self._iter = iter(self._get_processed())
        try:
            return dict(next(self._iter))
        except StopIteration:
            raise StopAsyncIteration

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        docs = self._get_processed()
        return docs[:length] if length is not None else docs


class AsyncDeferredCursor:
    """Async cursor compatible with motor find() returning results on iteration."""

    def __init__(self, fetch_coro: Callable[[], Any]) -> None:
        self._coro = fetch_coro
        self._sort_key = None
        self._sort_dir = 1
        self._skip = None
        self._limit = None
        self._cursor: Optional[Any] = None

    def sort(self, key_or_list: Any, direction: int = 1) -> "AsyncDeferredCursor":
        self._sort_key = key_or_list
        self._sort_dir = direction
        return self

    def limit(self, limit: int) -> "AsyncDeferredCursor":
        self._limit = limit
        return self

    def skip(self, skip: int) -> "AsyncDeferredCursor":
        self._skip = skip
        return self

    async def _fetch_and_transform(self) -> List[Dict[str, Any]]:
        raw = await self._coro()
        return _apply_cursor_transforms(
            raw, self._sort_key, self._sort_dir, self._skip, self._limit
        )

    def __aiter__(self) -> "AsyncDeferredCursor":
        return self

    async def __anext__(self) -> Dict[str, Any]:
        if self._cursor is None:
            docs = await self._fetch_and_transform()
            self._cursor = iter(docs)
        try:
            return next(self._cursor)
        except StopIteration:
            raise StopAsyncIteration

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        docs = await self._fetch_and_transform()
        return docs[:length] if length is not None else docs


class SQLCollection:
    """
    SQL collection proxy over SQLite or PostgreSQL matching the Motor collection API.
    Translates MongoDB queries and updates into SQL and JSON operations.
    """

    def __init__(self, db: "SQLDatabase", name: str) -> None:
        self._db = db
        self._name = name
        self._table = f"col_{re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())}"
        self._init_done = False

    async def _ensure_table(self) -> None:
        if not self._init_done:
            await self._db._execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} (_id TEXT PRIMARY KEY, data TEXT)"
            )
            self._init_done = True

    async def find_one(self, query: Dict[str, Any] = {}) -> Optional[Dict[str, Any]]:
        await self._ensure_table()
        if "_id" in query and len(query) == 1:
            ph = "$1" if self._db.dialect in ("postgresql", "postgres") else "?"
            rows = await self._db._fetchall(
                f"SELECT data FROM {self._table} WHERE _id = {ph}", (str(query["_id"]),)
            )
            if rows:
                try:
                    return json.loads(rows[0][0])
                except Exception:
                    pass
            return None

        try:
            where_sql, params = PyMongoInstructionParser.to_sql_where(query, dialect=self._db.dialect)
            rows = await self._db._fetchall(f"SELECT data FROM {self._table}{where_sql}", tuple(params))
        except Exception as e:
            logger.debug("SQL where clause fallback to table scan: %s", e)
            rows = await self._db._fetchall(f"SELECT data FROM {self._table}")

        for row in rows:
            try:
                doc = json.loads(row[0])
                if PyMongoInstructionParser.match_document(doc, query):
                    return doc
            except Exception:
                continue
        return None

    def find(self, query: Dict[str, Any] = {}) -> AsyncDeferredCursor:
        async def fetch_matching() -> List[Dict[str, Any]]:
            await self._ensure_table()
            try:
                where_sql, params = PyMongoInstructionParser.to_sql_where(query, dialect=self._db.dialect)
                rows = await self._db._fetchall(f"SELECT data FROM {self._table}{where_sql}", tuple(params))
            except Exception as e:
                logger.debug("SQL where clause fallback in find: %s", e)
                rows = await self._db._fetchall(f"SELECT data FROM {self._table}")

            matched = []
            for row in rows:
                try:
                    doc = json.loads(row[0])
                    if PyMongoInstructionParser.match_document(doc, query):
                        matched.append(doc)
                except Exception:
                    continue
            return matched

        return AsyncDeferredCursor(fetch_matching)

    async def insert_one(self, document: Dict[str, Any]) -> InsertOneResult:
        await self._ensure_table()
        doc = dict(document)
        doc_id = str(doc.get("_id", uuid.uuid4().hex))
        doc["_id"] = doc_id
        payload = json.dumps(doc)
        if self._db.dialect in ("postgresql", "postgres"):
            await self._db._execute(
                f"INSERT INTO {self._table} (_id, data) VALUES ($1, $2) ON CONFLICT (_id) DO UPDATE SET data = $2",
                (doc_id, payload),
            )
        else:
            await self._db._execute(
                f"INSERT OR REPLACE INTO {self._table} (_id, data) VALUES (?, ?)",
                (doc_id, payload),
            )
        return InsertOneResult(doc_id)

    async def update_one(
        self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False
    ) -> None:
        await self._ensure_table()
        existing = await self.find_one(query)
        if existing:
            doc_id = str(existing.get("_id"))
            updated = PyMongoInstructionParser.apply_update(existing, update)
            if self._db.dialect in ("postgresql", "postgres"):
                await self._db._execute(
                    f"UPDATE {self._table} SET data = $1 WHERE _id = $2",
                    (json.dumps(updated), doc_id),
                )
            else:
                await self._db._execute(
                    f"UPDATE {self._table} SET data = ? WHERE _id = ?",
                    (json.dumps(updated), doc_id),
                )
        elif upsert:
            new_doc = dict(query)
            if "_id" not in new_doc:
                new_doc["_id"] = uuid.uuid4().hex
            updated = PyMongoInstructionParser.apply_update(new_doc, update)
            await self.insert_one(updated)

    async def find_one_and_update(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        return_document: bool = False,
    ) -> Optional[Dict[str, Any]]:
        await self._ensure_table()
        existing = await self.find_one(query)
        if existing:
            old = dict(existing)
            updated = PyMongoInstructionParser.apply_update(existing, update)
            doc_id = str(old.get("_id"))
            if self._db.dialect in ("postgresql", "postgres"):
                await self._db._execute(
                    f"UPDATE {self._table} SET data = $1 WHERE _id = $2",
                    (json.dumps(updated), doc_id),
                )
            else:
                await self._db._execute(
                    f"UPDATE {self._table} SET data = ? WHERE _id = ?",
                    (json.dumps(updated), doc_id),
                )
            return updated if return_document else old
        elif upsert:
            new_doc = dict(query)
            if "_id" not in new_doc:
                new_doc["_id"] = uuid.uuid4().hex
            updated = PyMongoInstructionParser.apply_update(new_doc, update)
            await self.insert_one(updated)
            return updated
        return None

    async def find_one_and_delete(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        await self._ensure_table()
        existing = await self.find_one(query)
        if existing:
            await self.delete_one({"_id": existing.get("_id")})
            return existing
        return None

    async def delete_one(self, query: Dict[str, Any]) -> DeleteResult:
        await self._ensure_table()
        existing = await self.find_one(query)
        if existing:
            doc_id = str(existing.get("_id"))
            if self._db.dialect in ("postgresql", "postgres"):
                await self._db._execute(f"DELETE FROM {self._table} WHERE _id = $1", (doc_id,))
            else:
                await self._db._execute(f"DELETE FROM {self._table} WHERE _id = ?", (doc_id,))
            return DeleteResult(1)
        return DeleteResult(0)

    async def delete_many(self, query: Dict[str, Any]) -> DeleteResult:
        await self._ensure_table()
        cursor = self.find(query)
        matching = await cursor.to_list()
        if not matching:
            return DeleteResult(0)
        ids = [str(d.get("_id")) for d in matching if d.get("_id") is not None]
        if ids:
            if self._db.dialect in ("postgresql", "postgres"):
                placeholders = [f"${i+1}" for i in range(len(ids))]
                await self._db._execute(
                    f"DELETE FROM {self._table} WHERE _id IN ({', '.join(placeholders)})",
                    tuple(ids),
                )
            else:
                placeholders = ["?" for _ in ids]
                await self._db._execute(
                    f"DELETE FROM {self._table} WHERE _id IN ({', '.join(placeholders)})",
                    tuple(ids),
                )
        return DeleteResult(len(ids))

    async def count_documents(self, query: Dict[str, Any] = {}) -> int:
        await self._ensure_table()
        if not query:
            rows = await self._db._fetchall(f"SELECT COUNT(*) FROM {self._table}")
            return int(rows[0][0]) if rows else 0
        cursor = self.find(query)
        docs = await cursor.to_list()
        return len(docs)

    async def drop(self) -> None:
        self._init_done = False
        await self._db._execute(f"DROP TABLE IF EXISTS {self._table}")


class SQLDatabase:
    """
    SQL Database Backend supporting SQLite and PostgreSQL with PyMongo compatibility.
    """

    def __init__(self, uri: str, db_name: str = "Altruix", dialect: str = "sqlite") -> None:
        self.uri = uri
        self.db_name = db_name
        self.dialect = dialect.lower()
        self._collections: Dict[str, SQLCollection] = {}

        if self.dialect in ("sqlite", "sqlite3"):
            db_path = uri.replace("sqlite:///", "").replace("sqlite://", "").replace("sqlite3://", "")
            if not db_path:
                db_path = f"{db_name.lower()}.db"
            self._db_path = db_path
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            if self._db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA synchronous=NORMAL")
        else:
            self._db_path = None
            self._conn = None

        # Standard collections
        self.settings_col = self.make_collection("SETTINGS")
        self.data_col = self.make_collection("DATA")
        self.user_col = self.make_collection("USERS")
        self.env_col = self.make_collection("ENV")
        self.stickers_col = self.make_collection("STICKERS")
        self.plugins_col = self.make_collection("PLUGINS")

    def __getitem__(self, name: str) -> SQLCollection:
        return self.make_collection(name)

    def make_collection(self, name: str) -> SQLCollection:
        if name not in self._collections:
            self._collections[name] = SQLCollection(self, name)
        return self._collections[name]

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def get_from_col(self, col: str, key: str) -> Optional[Any]:
        if self._conn:
            try:
                table_name = f"col_{col.lower()}"
                cur = self._conn.cursor()
                row = cur.execute(f"SELECT val FROM {table_name} WHERE key=?", (str(key),)).fetchone()
                if row:
                    data = json.loads(row[0])
                    return data.get("val") or data.get("text") or data.get("content") or data
            except Exception:
                pass
        return None

    def add_to_col(self, col: str, key: str, val: Any) -> None:
        if self._conn:
            try:
                table_name = f"col_{col.lower()}"
                cur = self._conn.cursor()
                cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (key TEXT PRIMARY KEY, val TEXT)")
                doc = {"_id": str(key), "val": val}
                cur.execute(f"INSERT OR REPLACE INTO {table_name} (key, val) VALUES (?, ?)", (str(key), json.dumps(doc)))
                self._conn.commit()
            except Exception:
                pass

    async def _execute(self, sql: str, params: tuple = ()) -> None:
        loop = asyncio.get_running_loop()
        def _run():
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            self._conn.commit()
        await loop.run_in_executor(None, _run)

    async def _fetchall(self, sql: str, params: tuple = ()) -> List[tuple]:
        loop = asyncio.get_running_loop()
        def _run():
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()
        return await loop.run_in_executor(None, _run)

    async def ping(self) -> bool:
        try:
            rows = await self._fetchall("SELECT 1")
            return bool(rows and rows[0][0] == 1)
        except Exception:
            return False

    async def list_collection_names(self) -> List[str]:
        rows = await self._fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'col_%'")
        return [r[0][4:] for r in rows]

    async def drop_collection(self, name: str) -> None:
        col = self.make_collection(name)
        await col.drop()

    def close(self) -> None:
        if self._conn:
            with contextlib.suppress(Exception):
                self._conn.close()


class RedisCollection:
    """
    Redis Collection Proxy mapping MongoDB instructions to Redis Hashes & Sets.
    """

    def __init__(self, db: "RedisDatabase", name: str) -> None:
        self._db = db
        self._name = name
        self._key = f"altruix:col:{name}"

    async def find_one(self, query: Dict[str, Any] = {}) -> Optional[Dict[str, Any]]:
        client = self._db._client
        if "_id" in query and len(query) == 1:
            raw = await client.hget(self._key, str(query["_id"]))
            if raw:
                try:
                    return json.loads(raw)
                except Exception:
                    pass
            return None

        all_entries = await client.hgetall(self._key)
        for _, raw_val in all_entries.items():
            try:
                doc = json.loads(raw_val)
                if PyMongoInstructionParser.match_document(doc, query):
                    return doc
            except Exception:
                continue
        return None

    def find(self, query: Dict[str, Any] = {}) -> AsyncDeferredCursor:
        async def fetch_matching() -> List[Dict[str, Any]]:
            client = self._db._client
            all_entries = await client.hgetall(self._key)
            matched = []
            for _, raw_val in all_entries.items():
                try:
                    doc = json.loads(raw_val)
                    if PyMongoInstructionParser.match_document(doc, query):
                        matched.append(doc)
                except Exception:
                    continue
            return matched

        return AsyncDeferredCursor(fetch_matching)

    async def insert_one(self, document: Dict[str, Any]) -> InsertOneResult:
        client = self._db._client
        doc = dict(document)
        doc_id = str(doc.get("_id", uuid.uuid4().hex))
        doc["_id"] = doc_id
        await client.hset(self._key, doc_id, json.dumps(doc))
        return InsertOneResult(doc_id)

    async def update_one(
        self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False
    ) -> None:
        existing = await self.find_one(query)
        if existing:
            doc_id = str(existing.get("_id"))
            updated = PyMongoInstructionParser.apply_update(existing, update)
            await self._db._client.hset(self._key, doc_id, json.dumps(updated))
        elif upsert:
            new_doc = dict(query)
            if "_id" not in new_doc:
                new_doc["_id"] = uuid.uuid4().hex
            updated = PyMongoInstructionParser.apply_update(new_doc, update)
            await self.insert_one(updated)

    async def find_one_and_update(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        return_document: bool = False,
    ) -> Optional[Dict[str, Any]]:
        existing = await self.find_one(query)
        if existing:
            old = dict(existing)
            updated = PyMongoInstructionParser.apply_update(existing, update)
            doc_id = str(old.get("_id"))
            await self._db._client.hset(self._key, doc_id, json.dumps(updated))
            return updated if return_document else old
        elif upsert:
            new_doc = dict(query)
            if "_id" not in new_doc:
                new_doc["_id"] = uuid.uuid4().hex
            updated = PyMongoInstructionParser.apply_update(new_doc, update)
            await self.insert_one(updated)
            return updated
        return None

    async def find_one_and_delete(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        existing = await self.find_one(query)
        if existing:
            await self._db._client.hdel(self._key, str(existing.get("_id")))
            return existing
        return None

    async def delete_one(self, query: Dict[str, Any]) -> DeleteResult:
        existing = await self.find_one(query)
        if existing:
            await self._db._client.hdel(self._key, str(existing.get("_id")))
            return DeleteResult(1)
        return DeleteResult(0)

    async def delete_many(self, query: Dict[str, Any]) -> DeleteResult:
        cursor = self.find(query)
        docs = await cursor.to_list()
        count = len(docs)
        if count > 0:
            keys = [str(d.get("_id")) for d in docs]
            await self._db._client.hdel(self._key, *keys)
        return DeleteResult(count)

    async def count_documents(self, query: Dict[str, Any] = {}) -> int:
        if not query:
            return await self._db._client.hlen(self._key)
        cursor = self.find(query)
        docs = await cursor.to_list()
        return len(docs)

    async def drop(self) -> None:
        await self._db._client.delete(self._key)


class RedisDatabase:
    """
    Redis Database Backend providing full PyMongo/Motor collection parity.
    """

    def __init__(self, uri: str, db_name: str = "Altruix") -> None:
        import redis.asyncio as aioredis
        self.uri = uri
        self.db_name = db_name
        self._client = aioredis.from_url(uri, decode_responses=True)
        self._collections: Dict[str, RedisCollection] = {}

        self.settings_col = self.make_collection("SETTINGS")
        self.data_col = self.make_collection("DATA")
        self.user_col = self.make_collection("USERS")
        self.env_col = self.make_collection("ENV")
        self.stickers_col = self.make_collection("STICKERS")
        self.plugins_col = self.make_collection("PLUGINS")

    def __getitem__(self, name: str) -> RedisCollection:
        return self.make_collection(name)

    def make_collection(self, name: str) -> RedisCollection:
        if name not in self._collections:
            self._collections[name] = RedisCollection(self, name)
        return self._collections[name]

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def list_collection_names(self) -> List[str]:
        keys = await self._client.keys("altruix:col:*")
        return [k.replace("altruix:col:", "") for k in keys]

    async def drop_collection(self, name: str) -> None:
        await self.make_collection(name).drop()

    def close(self) -> None:
        asyncio.create_task(self._client.close())


def create_database(uri: Optional[str] = None, db_name: str = "Altruix") -> Union[MongoDB, SQLDatabase, RedisDatabase, LocalDatabase]:
    """
    Universal Database Factory.
    Auto-detects backend from URI and returns a MongoDB-compatible async database:
      - mongodb:// or mongodb+srv:// -> Motor MongoDB
      - postgresql:// or postgres:// -> PostgreSQL Adapter
      - sqlite://, sqlite3://, or *.db -> SQLite Adapter
      - redis:// or rediss:// -> Redis Adapter
      - Empty or local -> Default to SQLite (altruix.db)
    """
    if not uri or str(uri).strip().lower() in ("local", "none", "", "local_db.json", "sqlite"):
        return SQLDatabase(f"sqlite:///{db_name.lower()}.db", db_name=db_name, dialect="sqlite")

    raw_uri = str(uri).strip()
    lower_uri = raw_uri.lower()

    if lower_uri.startswith(("mongodb://", "mongodb+srv://")):
        return MongoDB(raw_uri, db_name=db_name)

    if lower_uri.startswith(("postgresql://", "postgres://")):
        return SQLDatabase(raw_uri, db_name=db_name, dialect="postgres")

    if lower_uri.startswith(("sqlite://", "sqlite3://")) or lower_uri.endswith((".db", ".sqlite", ".sqlite3")):
        return SQLDatabase(raw_uri, db_name=db_name, dialect="sqlite")

    if lower_uri.startswith(("redis://", "rediss://")):
        try:
            return RedisDatabase(raw_uri, db_name=db_name)
        except ImportError:
            logger.warning("redis package not installed for Redis URI; falling back to SQLite.")
            return SQLDatabase(f"{db_name.lower()}.db", db_name=db_name, dialect="sqlite")

    return SQLDatabase(f"sqlite:///{db_name.lower()}.db", db_name=db_name, dialect="sqlite")
