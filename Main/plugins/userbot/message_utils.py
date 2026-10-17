# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
from Main import Altruix
from gtts import gTTS, lang
from Main.utils.file_helpers import run_in_exc
try:
    from googletrans import LANGUAGES, Translator
    translator_2_ = Translator()
    translate_now = run_in_exc(translator_2_.translate)
except (ImportError, Exception):
    LANGUAGES = {}
    translator_2_ = None
    translate_now = None


@run_in_exc
def tts_(to_tts, lang):
    temp_dir = os.path.abspath("./temp")
    os.makedirs(temp_dir, exist_ok=True)
    import time
    file_name = os.path.join(temp_dir, f"tts_{int(time.time() * 1000)}.mp3")
    tts = gTTS(to_tts, lang=lang)
    tts.save(file_name)
    return file_name


@Altruix.register_on_cmd(
    "tts",
    cmd_help={
        "help": "Convert text to speech",
        "example": "tts en",
    },
    requires_reply=True,
)
async def tts_now(c, m):
    msg_ = await m.handle_message("PROCESSING")
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm or not rm.text:
        return await msg_.edit_msg("INVALID_REPLY")
    input_ = m.user_input
    langs_ = lang.tts_langs()
    lang_ = "en"
    if input_ and langs_.get(input_.lower()):
        lang_ = input_.lower()
    elif not langs_.get(lang_):
        await msg_.edit("INVALID_LANG")
        lang_ = "en"
    file_ = await tts_(rm.text, lang_)
    await m.reply_voice(
        file_,
        caption="<b>TTS </b> \n<b>Converted and processed by Altruix</b>",
        quote=True,
    )
    await msg_.delete_if_self()
    if os.path.exists(file_):
        os.remove(file_)


@Altruix.register_on_cmd(
    "tr",
    cmd_help={"help": "Translate text to your desired language", "example": "tr en"},
    requires_reply=True,
)
async def translate_(c, m):
    _m_ = await m.handle_message("PROCESSING")
    if translate_now is None:
        return await _m_.edit_msg("Please install googletrans: <code>pip install googletrans==3.1.0a0</code>")
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm:
        return await _m_.edit_msg("REPLY_TO_MESSAGE")
    to_tr = rm.text or getattr(rm, "caption", None) or getattr(rm, "message", "")
    if not to_tr:
        return await _m_.edit_msg("REPLY_TO_MESSAGE")
    from_lang = "auto"
    lang_to = "en"
    if m.user_input:
        input_ = m.user_input.strip().split(" ", 1)
        lang_to = input_[0]
        from_lang = input_[1] if len(input_) != 1 else "auto"
    if not LANGUAGES.get(lang_to.lower()):
        return await _m_.edit_msg("LANGUAGE_NOT_SUPPORTED", string_args=(lang_to))
    if from_lang != "auto" and not LANGUAGES.get(from_lang.lower()):
        return await _m_.edit_msg("LANGUAGE_NOT_SUPPORTED", string_args=(from_lang))
    translation = await translate_now(
        to_tr, src=from_lang.lower(), dest=lang_to.lower()
    )
    await _m_.edit_msg(
        "TRANSLATED",
        string_args=(
            LANGUAGES.get(translation.src.title()) or translation.src.title(),
            LANGUAGES.get(translation.dest.title()) or translation.dest.title(),
            translation.text,
        ),
    )
