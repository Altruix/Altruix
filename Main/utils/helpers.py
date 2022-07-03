# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import random
from typing import List


def arrange_buttons(array: list, no=3) -> List[list]:
    n = int(no)
    return [array[i * n : (i + 1) * n] for i in range((len(array) + n - 1) // n)]


def random_hash(length=8) -> str:
    return "".join(random.choice("0123456789abcdef") for _ in range(length))
