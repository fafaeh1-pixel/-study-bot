import re
import asyncio
from io import BytesIO


VOICE_FEMALE = "fa-IR-DilaraNeural"
VOICE_MALE   = "fa-IR-FaridNeural"


async def _edge_tts_generate(text: str, voice: str) -> BytesIO:
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice)
    buf = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf


def text_to_voice(text: str, gender: str = "female") -> BytesIO:
    clean = _clean_text(text)
    voice = VOICE_FEMALE if gender == "female" else VOICE_MALE

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _edge_tts_generate(clean, voice))
                return future.result()
        else:
            return loop.run_until_complete(_edge_tts_generate(clean, voice))
    except Exception:
        return _gtts_fallback(clean)


def _gtts_fallback(text: str) -> BytesIO:
    from gtts import gTTS
    tts = gTTS(text=text, lang="fa", slow=False)
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf


def _clean_text(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub("", text)
    text = re.sub(r"[|—–_#*\[\]()]", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()