# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import unittest
from Main import Altruix
from Main.utils.progress import render_progress_bar, human_bytes, format_eta
from XtraPlugins.media.ytdl_tools import _parse_ytdl_flags, _parse_time_str


class TestYtdlAndProgress(unittest.IsolatedAsyncioTestCase):
    def test_progress_bar_rendering(self):
        self.assertEqual(render_progress_bar(0.0), "[░░░░░░░░░░░░] 0.0%")
        self.assertEqual(render_progress_bar(50.0), "[██████░░░░░░] 50.0%")
        self.assertEqual(render_progress_bar(100.0), "[████████████] 100.0%")
        self.assertEqual(human_bytes(1024 * 1024 * 5), "5.0 MB")
        self.assertEqual(format_eta(90), "1m 30s")
        self.assertEqual(format_eta(3665), "1h 1m")

    async def test_progress_bar_setting_default_disabled(self):
        # Default should be False (clean mode to avoid flood waits)
        await Altruix.config.set_progress_bar_sts(False)
        self.assertFalse(await Altruix.config.get_progress_bar_sts())

        # Toggle to True
        await Altruix.config.set_progress_bar_sts(True)
        self.assertTrue(await Altruix.config.get_progress_bar_sts())

        # Toggle back to False
        await Altruix.config.set_progress_bar_sts(False)
        self.assertFalse(await Altruix.config.get_progress_bar_sts())

    def test_ytdl_flag_parsing(self):
        # 1. Quality flag
        f1 = _parse_ytdl_flags("https://youtu.be/abc -1080p -doc")
        self.assertEqual(f1["quality"], "1080")
        self.assertTrue(f1["as_document"])
        self.assertEqual(f1["clean_query"], "https://youtu.be/abc")

        # 2. Audio flags
        f2 = _parse_ytdl_flags("lofi hip hop -audio -flac -320k")
        self.assertTrue(f2["audio_only"])
        self.assertEqual(f2["audio_format"], "flac")
        self.assertEqual(f2["audio_bitrate"], "320")
        self.assertEqual(f2["clean_query"], "lofi hip hop")

        # 3. Trimming flags
        f3 = _parse_ytdl_flags("https://youtu.be/xyz -ss 00:30 -to 01:45 -subs")
        self.assertEqual(f3["start_time"], 30)
        self.assertEqual(f3["end_time"], 105)
        self.assertTrue(f3["subtitles"])
        self.assertEqual(f3["clean_query"], "https://youtu.be/xyz")

        # 4. 4K / Best
        f4 = _parse_ytdl_flags("nature documentary -4k -thumb")
        self.assertEqual(f4["quality"], "2160")
        self.assertTrue(f4["thumb_separate"])

    def test_parse_time_str(self):
        self.assertEqual(_parse_time_str("45"), 45)
        self.assertEqual(_parse_time_str("01:15"), 75)
        self.assertEqual(_parse_time_str("01:02:03"), 3723)
        self.assertIsNone(_parse_time_str("invalid"))


if __name__ == "__main__":
    unittest.main()
