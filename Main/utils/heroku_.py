# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import logging
from ..core.config import Config as config


heroku3_installed = True

try:
    import heroku3
except ImportError:
    heroku3_installed = False


async def prepare_heroku_url():
    if not heroku3_installed:
        return None
    if not config.HEROKU_APP_NAME or not config.HEROKU_API_KEY:
        return None
    heroku = heroku3.from_key(config.HEROKU_API_KEY)
    try:
        heroku_applications = heroku.apps()
    except Exception:
        return None
    heroku_app = next(
        (app for app in heroku_applications if app.name == config.HEROKU_APP_NAME),
        None,
    )
    if not heroku_app:
        logging.info(
            "Looks like the api key is correct but, heroku app name isn't in the list of apps."
        )
        return None
    return heroku_app.git_url.replace(
        "https://", f"https://api:{config.HEROKU_API_KEY}@"
    )
