# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import unittest
import asyncio
from XtraPlugins.botbased.fban import (
    _classify_fban_response,
    _classify_unfban_response,
    _get_fed_config,
    fed_db,
)


class TestFbanPlugin(unittest.IsolatedAsyncioTestCase):
    async def test_classify_fban_response(self):
        self.assertEqual(_classify_fban_response("New FedBan Reason: Spam"), "✅ Banned")
        self.assertEqual(_classify_fban_response("FedBanned user 12345 in CryptoFed"), "✅ Banned")
        self.assertEqual(_classify_fban_response("User is already banned in this federation!"), "⚠️ Already Banned")
        self.assertEqual(_classify_fban_response("You aren't a federation admin!"), "❌ Not Fed Admin")
        self.assertEqual(_classify_fban_response("This user is a federation admin and cannot be banned!"), "⛔ Target is Fed Admin")
        self.assertEqual(_classify_fban_response("Invalid federation id specified."), "❌ Invalid Fed / Target")

    async def test_classify_unfban_response(self):
        self.assertEqual(_classify_unfban_response("FedUnBanned user 12345"), "✅ Unbanned")
        self.assertEqual(_classify_unfban_response("This user isn't banned in this federation."), "⚠️ Not Banned")
        self.assertEqual(_classify_unfban_response("You aren't a federation admin!"), "❌ Not Fed Admin")

    async def test_federations_db_segregation(self):
        client_a = 111111
        client_b = 222222

        # Client A saves 2 federations
        feds_a = ["fed-uuid-1", "fed-uuid-2"]
        await fed_db.update_one(
            {"_id": f"feds_{client_a}"},
            {"$set": {"client_id": client_a, "federations": feds_a, "fed_bot": "MissRose_bot"}},
            upsert=True,
        )

        # Client B saves 1 federation
        feds_b = ["fed-uuid-99"]
        await fed_db.update_one(
            {"_id": f"feds_{client_b}"},
            {"$set": {"client_id": client_b, "federations": feds_b, "fed_bot": "MarieRoseBot"}},
            upsert=True,
        )

        # Verify Client A
        bot_a, retrieved_a = await _get_fed_config(client_a)
        self.assertEqual(bot_a, "MissRose_bot")
        self.assertEqual(retrieved_a, ["fed-uuid-1", "fed-uuid-2"])

        # Verify Client B
        bot_b, retrieved_b = await _get_fed_config(client_b)
        self.assertEqual(bot_b, "MarieRoseBot")
        self.assertEqual(retrieved_b, ["fed-uuid-99"])

        # Test adding and removing on Client A
        await fed_db.update_one(
            {"_id": f"feds_{client_a}"},
            {"$set": {"federations": ["fed-uuid-1"]}},
        )
        _, updated_a = await _get_fed_config(client_a)
        self.assertEqual(updated_a, ["fed-uuid-1"])


if __name__ == "__main__":
    unittest.main()
