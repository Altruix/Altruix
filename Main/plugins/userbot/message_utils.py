# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import time
import urllib.parse
from typing import Optional, Tuple
from cachetools import TTLCache

from Main import Altruix
from Main.core.types.client import AltruixTelegramClient as Client
from Main.core.types.message import Message
from Main.utils.file_helpers import run_in_exc
from Main.utils.suppress import suppress_error
from gtts import gTTS, lang

# In-memory TTL caches for instant repeat lookups
_TRANSLATION_CACHE: TTLCache = TTLCache(maxsize=1000, ttl=86400)
_TTS_CACHE: TTLCache = TTLCache(maxsize=100, ttl=3600)

LANGUAGES = {
    "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic", "hy": "Armenian",
    "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian", "bn": "Bengali", "bs": "Bosnian",
    "bg": "Bulgarian", "ca": "Catalan", "ceb": "Cebuano", "ny": "Chichewa", "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)", "co": "Corsican", "hr": "Croatian", "cs": "Czech", "da": "Danish",
    "nl": "Dutch", "en": "English", "eo": "Esperanto", "et": "Estonian", "tl": "Filipino",
    "fi": "Finnish", "fr": "French", "fy": "Frisian", "gl": "Galician", "ka": "Georgian",
    "de": "German", "el": "Greek", "gu": "Gujarati", "ht": "Haitian Creole", "ha": "Hausa",
    "haw": "Hawaiian", "iw": "Hebrew", "he": "Hebrew", "hi": "Hindi", "hmn": "Hmong",
    "hu": "Hungarian", "is": "Icelandic", "ig": "Igbo", "id": "Indonesian", "ga": "Irish",
    "it": "Italian", "ja": "Japanese", "jw": "Javanese", "kn": "Kannada", "kk": "Kazakh",
    "km": "Khmer", "ko": "Korean", "ku": "Kurdish", "ky": "Kyrgyz", "lo": "Lao",
    "la": "Latin", "lv": "Latvian", "lt": "Lithuanian", "lb": "Luxembourgish", "mk": "Macedonian",
    "mg": "Malagasy", "ms": "Malay", "ml": "Malayalam", "mt": "Maltese", "mi": "Maori",
    "mr": "Marathi", "mn": "Mongolian", "my": "Myanmar (Burmese)", "ne": "Nepali", "no": "Norwegian",
    "ps": "Pashto", "fa": "Persian", "pl": "Polish", "pt": "Portuguese", "pa": "Punjabi",
    "ro": "Romanian", "ru": "Russian", "sm": "Samoan", "gd": "Scots Gaelic", "sr": "Serbian",
    "st": "Sesotho", "sn": "Shona", "sd": "Sindhi", "si": "Sinhala", "sk": "Slovak",
    "sl": "Slovenian", "so": "Somali", "es": "Spanish", "su": "Sundanese", "sw": "Swahili",
    "sv": "Swedish", "tg": "Tajik", "ta": "Tamil", "te": "Telugu", "th": "Thai",
    "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese",
    "cy": "Welsh", "xh": "Xhosa", "yi": "Yiddish", "yo": "Yoruba", "zu": "Zulu",
}


def _resolve_lang_code(val: str) -> Optional[str]:
    v = val.lower().strip()
    if v in LANGUAGES:
        return v
    for code, name in LANGUAGES.items():
        if name.lower() == v:
            return code
    return None


async def _async_translate(c: Client, text: str, dest: str, src: str = "auto") -> Tuple[Optional[str], str]:
    cache_key = (text, src, dest)
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    encoded = urllib.parse.quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src}&tl={dest}&dt=t&q={encoded}"

    http_client = getattr(c, "http", None) or getattr(Altruix, "http", None)
    if http_client:
        res = await http_client.get(url, headers={"User-Agent": "Mozilla/5.0"})
    else:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as temp_client:
            res = await temp_client.get(url, headers={"User-Agent": "Mozilla/5.0"})

    if res.status_code != 200:
        return None, src

    data = res.json()
    chunks = []
    detected = src
    if data and isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], list):
            for part in data[0]:
                if part and len(part) > 0 and part[0]:
                    chunks.append(part[0])
        if len(data) > 2 and isinstance(data[2], str):
            detected = data[2]

    result = ("".join(chunks), detected)
    _TRANSLATION_CACHE[cache_key] = result
    return result


@run_in_exc
def tts_(to_tts: str, lang_code: str) -> str:
    temp_dir = os.path.abspath("./temp")
    os.makedirs(temp_dir, exist_ok=True)
    file_name = os.path.join(temp_dir, f"tts_{int(time.time() * 1000)}.mp3")
    tts = gTTS(to_tts, lang=lang_code)
    tts.save(file_name)
    return file_name


@Altruix.register_on_cmd(
    "tts",
    cmd_help={
        "help": "Convert replied text to speech audio note.",
        "example": "tts en",
    },
    requires_reply=True,
)
async def tts_now(c: Client, m: Message):
    msg_ = await m.handle_message("PROCESSING")
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm or not rm.text:
        return await msg_.edit_msg("INVALID_REPLY")

    input_ = (m.user_input or "").strip().lower()
    available_langs = lang.tts_langs()
    lang_ = "en"
    if input_ and available_langs.get(input_):
        lang_ = input_
    elif input_ and not available_langs.get(input_):
        await msg_.edit_msg("INVALID_LANG")
        lang_ = "en"

    cache_key = (rm.text.strip(), lang_)
    file_ = _TTS_CACHE.get(cache_key)
    if not file_ or not os.path.exists(file_):
        file_ = await tts_(rm.text, lang_)
        _TTS_CACHE[cache_key] = file_

    await m.reply_voice(
        file_,
        caption="<b>TTS</b>\n<b>Converted and processed by Altruix</b>",
        quote=True,
    )
    await msg_.delete_if_self()


@Altruix.register_on_cmd(
    "tr",
    cmd_help={
        "help": "Translate text or replied message to your desired language.",
        "example": "tr en",
    },
    requires_reply=True,
)
async def translate_(c: Client, m: Message):
    _m_ = await m.handle_message("PROCESSING")
    rm = m.reply_to_message or (await m.get_reply_message() if hasattr(m, "get_reply_message") else None)
    if not rm:
        return await _m_.edit_msg("REPLY_TO_MESSAGE")

    to_tr = rm.text or getattr(rm, "caption", None) or getattr(rm, "message", "")
    if not to_tr:
        return await _m_.edit_msg("REPLY_TO_MESSAGE")

    from_lang = "auto"
    lang_to = "en"
    if m.user_input:
        parts = m.user_input.strip().split(" ", 1)
        lang_to = parts[0]
        from_lang = parts[1] if len(parts) > 1 else "auto"

    dest_code = _resolve_lang_code(lang_to)
    if not dest_code:
        return await _m_.edit_msg("LANGUAGE_NOT_SUPPORTED", string_args=(lang_to,))

    src_code = "auto"
    if from_lang != "auto":
        src_code = _resolve_lang_code(from_lang)
        if not src_code:
            return await _m_.edit_msg("LANGUAGE_NOT_SUPPORTED", string_args=(from_lang,))

    try:
        translated_text, detected_src = await _async_translate(c, to_tr, dest=dest_code, src=src_code)
        if not translated_text:
            return await _m_.edit_msg("❌ Failed to translate message.")

        src_name = LANGUAGES.get(detected_src, detected_src.title())
        dest_name = LANGUAGES.get(dest_code, dest_code.title())

        await _m_.edit_msg(
            "TRANSLATED",
            string_args=(src_name, dest_name, translated_text),
        )
    except Exception as e:
        await _m_.edit_msg(f"❌ Translation error: <code>{e}</code>")
