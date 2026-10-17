# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import sys
from Main import Altruix


def main() -> None:
    try:
        Altruix.run()
    except (KeyboardInterrupt, SystemExit):
        Altruix.log("Altruix process terminated.")
        sys.exit(0)


if __name__ == "__main__":
    main()
