# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import random


def gen_random_useragent():
    """Generate random useragent"""
    platform = random.choice(["Macintosh", "Windows", "X11"])
    if platform == "Macintosh":
        gen_os = random.choice(["68K", "PPC"])
    elif platform == "Windows":
        gen_os = random.choice(
            [
                "Win3.11",
                "WinNT3.51",
                "WinNT4.0",
                "Windows NT 5.0",
                "Windows NT 5.1",
                "Windows NT 5.2",
                "Windows NT 6.0",
                "Windows NT 6.1",
                "Windows NT 6.2",
                "Win95",
                "Win98",
                "Win 9x 4.90",
                "WindowsCE",
            ]
        )
    elif platform == "X11":
        gen_os = random.choice(["Linux i686", "Linux x86_64"])
    browser = random.choice(["chrome", "firefox", "ie"])
    if browser == "chrome":
        webkit = str(random.randint(500, 599))
        version = (
            str(random.randint(0, 24))
            + ".0"
            + str(random.randint(0, 1500))
            + "."
            + str(random.randint(0, 999))
        )
        return (
            "Mozilla/5.0 ("
            + gen_os
            + ") AppleWebKit/"
            + webkit
            + ".0 (KHTML, live Gecko) Chrome/"
            + version
            + " Safari/"
            + webkit
        )
    elif browser == "firefox":
        year = str(random.randint(2000, 2012))
        month = random.randint(1, 12)
        month = f"0{str(month)}" if month < 10 else str(month)
        day = random.randint(1, 30)
        day = f"0{str(day)}" if day < 10 else str(day)
        gecko = year + month + day
        version = random.choice(
            [
                "1.0",
                "2.0",
                "3.0",
                "4.0",
                "5.0",
                "6.0",
                "7.0",
                "8.0",
                "9.0",
                "10.0",
                "11.0",
                "12.0",
                "13.0",
                "14.0",
                "15.0",
            ]
        )
        return (
            "Mozilla/5.0 ("
            + gen_os
            + "; rv:"
            + version
            + ") Gecko/"
            + gecko
            + " Firefox/"
            + version
        )
    elif browser == "ie":
        version = f"{str(random.randint(1, 10))}.0"
        engine = f"{str(random.randint(1, 5))}.0"
        if option := random.choice([True, False]):
            token = (
                random.choice(
                    [
                        ".NET CLR",
                        "SV1",
                        "Tablet PC",
                        "Win64; IA64",
                        "Win64; x64",
                        "WOW64",
                    ]
                )
                + "; "
            )
        elif option == False:
            token = ""
        return (
            "Mozilla/5.0 (compatible; MSIE "
            + version
            + "; "
            + gen_os
            + "; "
            + token
            + "Trident/"
            + engine
            + ")"
        )
