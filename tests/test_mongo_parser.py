# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import re
import unittest
import asyncio
from typing import Any, Dict

from Main.core.mongo_parser import PyMongoInstructionParser, _safe_eq, _get_nested, _set_nested, _unset_nested
from Main.core.database import (
    SQLDatabase,
    SQLCollection,
    LocalDatabase,
    LocalCollection,
    create_database,
    DeleteResult,
    InsertOneResult,
)


class TestPyMongoInstructionParser(unittest.TestCase):
    """Unit tests for PyMongoInstructionParser query evaluation and document updates."""

    def test_safe_eq_coercion(self):
        self.assertTrue(_safe_eq(12345, 12345))
        self.assertTrue(_safe_eq(12345, "12345"))
        self.assertTrue(_safe_eq("999", 999))
        self.assertTrue(_safe_eq("hello", "hello"))
        self.assertFalse(_safe_eq("hello", "world"))
        self.assertFalse(_safe_eq(123, 456))

    def test_nested_get_set_unset(self):
        doc: Dict[str, Any] = {"a": {"b": {"c": 42}}, "list": [{"id": 1}, {"id": 2}]}
        self.assertEqual(_get_nested(doc, "a.b.c"), 42)
        self.assertIsNone(_get_nested(doc, "a.b.nonexistent"))

        _set_nested(doc, "a.b.d", 100)
        self.assertEqual(doc["a"]["b"]["d"], 100)

        _set_nested(doc, "new.nested.field", "hello")
        self.assertEqual(doc["new"]["nested"]["field"], "hello")

        _unset_nested(doc, "a.b.d")
        self.assertNotIn("d", doc["a"]["b"])

        _unset_nested(doc, "new.nested.field")
        self.assertNotIn("field", doc["new"]["nested"])

    def test_match_document_basic(self):
        doc = {"name": "Altruix", "version": 2, "active": True, "chat_id": -10012345678}
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"name": "Altruix"}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"chat_id": "-10012345678"}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"version": 2, "active": True}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"name": "Other"}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"active": False}))

    def test_match_document_operators(self):
        doc = {
            "num": 50,
            "role": "admin",
            "tags": ["core", "plugin", "telethon"],
            "meta": {"verified": True},
        }
        # $eq & $ne
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"role": {"$eq": "admin"}}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"role": {"$ne": "guest"}}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"role": {"$ne": "admin"}}))

        # Comparisons
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"num": {"$gt": 40}}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"num": {"$gte": 50}}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"num": {"$lt": 60}}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"num": {"$lte": 50}}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"num": {"$gt": 50}}))

        # $in & $nin
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"role": {"$in": ["user", "admin"]}}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"role": {"$nin": ["guest", "banned"]}}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"role": {"$in": ["guest"]}}))

        # $exists
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"meta": {"$exists": True}}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"missing": {"$exists": False}}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"meta": {"$exists": False}}))

        # $size & $all
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"tags": {"$size": 3}}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"tags": {"$all": ["core", "telethon"]}}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"tags": {"$all": ["core", "missing"]}}))

        # Dot-notation
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"meta.verified": True}))

    def test_match_document_regex(self):
        doc = {"title": "Altruix Userbot Framework"}
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"title": {"$regex": "^altruix", "$options": "i"}}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"title": re.compile(r"framework", re.I)}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"title": {"$regex": "^userbot"}}))

    def test_match_document_logical(self):
        doc = {"a": 1, "b": 2}
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"$or": [{"a": 1}, {"b": 99}]}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"$and": [{"a": 1}, {"b": 2}]}))
        self.assertTrue(PyMongoInstructionParser.match_document(doc, {"$nor": [{"a": 99}, {"b": 99}]}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"$or": [{"a": 99}, {"b": 99}]}))
        self.assertFalse(PyMongoInstructionParser.match_document(doc, {"$nor": [{"a": 1}, {"b": 99}]}))

    def test_apply_update_all_operators(self):
        doc: Dict[str, Any] = {
            "name": "Bot",
            "counter": 10,
            "tags": ["alpha"],
            "settings": {"mode": "fast"},
            "min_val": 100,
            "max_val": 50,
        }

        # $set & nested $set
        PyMongoInstructionParser.apply_update(doc, {"$set": {"name": "AltruixBot", "settings.mode": "ultra"}})
        self.assertEqual(doc["name"], "AltruixBot")
        self.assertEqual(doc["settings"]["mode"], "ultra")

        # $inc
        PyMongoInstructionParser.apply_update(doc, {"$inc": {"counter": 5, "new_counter": 1}})
        self.assertEqual(doc["counter"], 15)
        self.assertEqual(doc["new_counter"], 1)

        # $min & $max
        PyMongoInstructionParser.apply_update(doc, {"$min": {"min_val": 80}, "$max": {"max_val": 90}})
        self.assertEqual(doc["min_val"], 80)
        self.assertEqual(doc["max_val"], 90)

        # $addToSet
        PyMongoInstructionParser.apply_update(doc, {"$addToSet": {"tags": "beta"}})
        self.assertIn("beta", doc["tags"])
        PyMongoInstructionParser.apply_update(doc, {"$addToSet": {"tags": {"$each": ["beta", "gamma"]}}})
        self.assertEqual(doc["tags"].count("beta"), 1)
        self.assertIn("gamma", doc["tags"])

        # $push
        PyMongoInstructionParser.apply_update(doc, {"$push": {"tags": "delta"}})
        self.assertEqual(doc["tags"][-1], "delta")

        # $pull
        PyMongoInstructionParser.apply_update(doc, {"$pull": {"tags": "beta"}})
        self.assertNotIn("beta", doc["tags"])

        # $rename
        PyMongoInstructionParser.apply_update(doc, {"$rename": {"new_counter": "renamed_counter"}})
        self.assertNotIn("new_counter", doc)
        self.assertEqual(doc["renamed_counter"], 1)

        # $unset
        PyMongoInstructionParser.apply_update(doc, {"$unset": {"settings.mode": "", "renamed_counter": ""}})
        self.assertNotIn("mode", doc["settings"])
        self.assertNotIn("renamed_counter", doc)

    def test_to_sql_where(self):
        # SQLite dialect
        where, params = PyMongoInstructionParser.to_sql_where(
            {"_id": "test_id", "status": "active", "views": {"$gt": 100}},
            dialect="sqlite",
        )
        self.assertIn("_id = ?", where)
        self.assertIn("json_extract(data, '$.status') = ?", where)
        self.assertIn("CAST(json_extract(data, '$.views') AS NUMERIC) > ?", where)
        self.assertEqual(params[0], "test_id")
        self.assertEqual(params[1], "active")
        self.assertEqual(params[2], 100)

        # Postgres dialect
        where_pg, params_pg = PyMongoInstructionParser.to_sql_where(
            {"_id": "pg_id", "role": "admin"},
            dialect="postgres",
        )
        self.assertIn("_id = $1", where_pg)
        self.assertIn("data->>'role' = $2", where_pg)
        self.assertEqual(params_pg, ["pg_id", "admin"])


class TestDatabaseAsyncOperations(unittest.IsolatedAsyncioTestCase):
    """End-to-end async tests for SQLDatabase (SQLite in-memory) and LocalDatabase."""

    async def asyncSetUp(self):
        self.sql_db = SQLDatabase("sqlite:///:memory:", db_name="TestAltruix", dialect="sqlite")
        self.local_db = LocalDatabase()

    async def asyncTearDown(self):
        self.sql_db.close()

    async def test_sql_collection_crud_lifecycle(self):
        col = self.sql_db.make_collection("TEST_COL")

        # 1. insert_one
        res = await col.insert_one({"_id": "item1", "name": "Alice", "score": 90, "tags": ["admin", "dev"]})
        self.assertIsInstance(res, InsertOneResult)
        self.assertEqual(res.inserted_id, "item1")

        await col.insert_one({"_id": "item2", "name": "Bob", "score": 75, "tags": ["user"]})
        await col.insert_one({"_id": "item3", "name": "Charlie", "score": 95, "tags": ["dev"]})

        # 2. find_one by _id
        doc = await col.find_one({"_id": "item1"})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["name"], "Alice")

        # 3. find_one by query
        doc = await col.find_one({"name": "Bob"})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["score"], 75)

        # 4. find cursor to_list, sort, skip, limit
        cursor = col.find({"tags": {"$in": ["dev"]}})
        devs = await cursor.sort("score", -1).to_list()
        self.assertEqual(len(devs), 2)
        self.assertEqual(devs[0]["name"], "Charlie")
        self.assertEqual(devs[1]["name"], "Alice")

        # 5. count_documents
        count_all = await col.count_documents({})
        self.assertEqual(count_all, 3)
        count_filtered = await col.count_documents({"score": {"$gt": 80}})
        self.assertEqual(count_filtered, 2)

        # 6. update_one with $set & $inc
        await col.update_one({"_id": "item1"}, {"$set": {"status": "promoted"}, "$inc": {"score": 5}})
        updated = await col.find_one({"_id": "item1"})
        self.assertEqual(updated["status"], "promoted")
        self.assertEqual(updated["score"], 95)

        # 7. update_one with upsert
        await col.update_one({"_id": "item4", "name": "Dave"}, {"$set": {"score": 60}}, upsert=True)
        dave = await col.find_one({"_id": "item4"})
        self.assertIsNotNone(dave)
        self.assertEqual(dave["score"], 60)

        # 8. find_one_and_update
        old_val = await col.find_one_and_update(
            {"_id": "item4"},
            {"$set": {"score": 65}},
            return_document=False,
        )
        self.assertEqual(old_val["score"], 60)
        new_val = await col.find_one_and_update(
            {"_id": "item4"},
            {"$set": {"score": 70}},
            return_document=True,
        )
        self.assertEqual(new_val["score"], 70)

        # 9. delete_one
        del_res = await col.delete_one({"_id": "item2"})
        self.assertIsInstance(del_res, DeleteResult)
        self.assertEqual(del_res.deleted_count, 1)
        self.assertIsNone(await col.find_one({"_id": "item2"}))

        # 10. delete_many
        del_many_res = await col.delete_many({"score": {"$gte": 90}})
        self.assertGreaterEqual(del_many_res.deleted_count, 2)
        remaining = await col.count_documents({})
        self.assertEqual(remaining, 1)  # Only Dave remains

        # 11. drop
        await col.drop()
        self.assertEqual(await col.count_documents({}), 0)

    async def test_local_collection_parity(self):
        col = self.local_db.make_collection("LOCAL_TEST")

        # insert_one
        await col.insert_one({"_id": "l1", "name": "LocalAlice", "val": 10})
        await col.insert_one({"_id": "l2", "name": "LocalBob", "val": 20})

        # find_one
        self.assertIsNotNone(await col.find_one({"name": "LocalAlice"}))

        # update_one
        await col.update_one({"name": "LocalBob"}, {"$inc": {"val": 10}})
        bob = await col.find_one({"_id": "l2"})
        self.assertEqual(bob["val"], 30)

        # cursor sort & limit
        cursor = col.find({})
        sorted_docs = await cursor.sort("val", -1).limit(1).to_list()
        self.assertEqual(len(sorted_docs), 1)
        self.assertEqual(sorted_docs[0]["name"], "LocalBob")

        # delete_many
        del_res = await col.delete_many({"val": {"$gt": 5}})
        self.assertEqual(del_res.deleted_count, 2)
        self.assertEqual(await col.count_documents({}), 0)

    async def test_create_database_factory(self):
        # SQLite URI
        db_sql = create_database("sqlite:///:memory:")
        self.assertIsInstance(db_sql, SQLDatabase)
        self.assertEqual(db_sql.dialect, "sqlite")
        db_sql.close()

        # Postgres URI
        db_pg = create_database("postgresql://user:pass@localhost:5432/altruix")
        self.assertIsInstance(db_pg, SQLDatabase)
        self.assertEqual(db_pg.dialect, "postgres")

        # Local fallback
        db_local = create_database(None)
        self.assertIsInstance(db_local, LocalDatabase)


    async def test_all_plugin_database_patterns(self):
        """Simulate the exact database operation patterns across all Altruix plugins."""
        # 1. welcome.py pattern
        welcome_db = self.sql_db.make_collection("WELCOME")
        await welcome_db.insert_one({"chat_id": -100111, "client_id": 555, "welcome_enabled": False})
        self.assertTrue(bool(await welcome_db.find_one({"chat_id": -100111, "client_id": 555})))
        await welcome_db.update_one({"chat_id": -100111, "client_id": 555}, {"$set": {"welcome_enabled": True}})
        w_doc = await welcome_db.find_one({"chat_id": -100111, "client_id": 555})
        self.assertTrue(w_doc["welcome_enabled"])
        await welcome_db.delete_one({"chat_id": -100111, "client_id": 555})
        self.assertIsNone(await welcome_db.find_one({"chat_id": -100111, "client_id": 555}))

        # 2. PM_Security.py pattern
        pm_col = self.sql_db.make_collection("pm_permit")
        await pm_col.update_one({"user_id": 12345}, {"$set": {"approved": False}}, upsert=True)
        pm_user = await pm_col.find_one({"user_id": 12345})
        self.assertFalse(pm_user["approved"])
        await pm_col.update_one({"user_id": 12345}, {"$set": {"approved": True}})
        pm_user = await pm_col.find_one({"user_id": 12345})
        self.assertTrue(pm_user["approved"])

        # 3. chat_filter.py pattern
        filters_col = self.sql_db.make_collection("FILTERS")
        await filters_col.insert_one({"keyword": "hello", "reply": "world", "chat_id": -100222, "client_id": 555})
        await filters_col.insert_one({"keyword": "rules", "reply": "be nice", "chat_id": -100222, "client_id": 555})
        f_doc = await filters_col.find_one({"keyword": "hello", "chat_id": -100222, "client_id": 555})
        self.assertEqual(f_doc["reply"], "world")
        del_f = await filters_col.find_one_and_delete({"keyword": "hello", "chat_id": -100222, "client_id": 555})
        self.assertEqual(del_f["keyword"], "hello")
        all_filters = await filters_col.find({"chat_id": -100222, "client_id": 555}).to_list()
        self.assertEqual(len(all_filters), 1)
        await filters_col.delete_many({"chat_id": -100222, "client_id": 555})
        self.assertEqual(await filters_col.count_documents({"chat_id": -100222}), 0)

        # 4. AltruiX_Package_Manager.py pattern
        packages_col = self.sql_db.make_collection("packages")
        await packages_col.insert_one({"_id": "APM", "plugins": ["carbon", "collage"]})
        await packages_col.update_one({"_id": "APM"}, {"$addToSet": {"plugins": "search_tools"}})
        pkg_doc = await packages_col.find_one({"_id": "APM"})
        self.assertIn("search_tools", pkg_doc["plugins"])
        await packages_col.update_one({"_id": "APM"}, {"$pull": {"plugins": "carbon"}})
        pkg_doc = await packages_col.find_one({"_id": "APM"})
        self.assertNotIn("carbon", pkg_doc["plugins"])
        self.assertIn("collage", pkg_doc["plugins"])

        # 5. config.py SUDO_USERS pattern ($addToSet $each, $pull, upsert)
        env_col = self.sql_db.make_collection("ENV")
        await env_col.find_one_and_update(
            {"_id": "SUDO_USERS"},
            {"$addToSet": {"value": {"$each": [111, 222, 333]}}},
            upsert=True,
        )
        sudo_doc = await env_col.find_one({"_id": "SUDO_USERS"})
        self.assertEqual(sudo_doc["value"], [111, 222, 333])
        await env_col.find_one_and_update(
            {"_id": "SUDO_USERS"},
            {"$pull": {"value": 222}},
        )
        sudo_doc = await env_col.find_one({"_id": "SUDO_USERS"})
        self.assertEqual(sudo_doc["value"], [111, 333])

        # 6. afk.py pattern
        settings_col = self.sql_db.make_collection("SETTINGS")
        await settings_col.update_one(
            {"_id": "AFK", "client_id": 555},
            {"$set": {"afk": True, "reason": "sleeping", "time": 1234567890.0}},
            upsert=True,
        )
        afk_rec = await settings_col.find_one({"_id": "AFK", "client_id": 555})
        self.assertTrue(afk_rec["afk"])
        self.assertEqual(afk_rec["reason"], "sleeping")
        await settings_col.delete_one({"_id": "AFK", "client_id": 555})
        self.assertIsNone(await settings_col.find_one({"_id": "AFK", "client_id": 555}))


if __name__ == "__main__":
    unittest.main()

