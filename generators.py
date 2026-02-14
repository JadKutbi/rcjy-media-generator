import base64
import io
import logging
import os
import tempfile
import time
import wave

from config import MODELS, require_api_key
from content_extractor import get_content_from_input

logger = logging.getLogger("rcjy.generators")

_TIMEOUT_FAST = (30, 180)
_TIMEOUT_SLOW = (30, 300)
_TIMEOUT_HEAVY = (30, 600)

MAX_PROMPT_LENGTH = 10_000
MAX_CONTEXT_LENGTH = 50_000
MAX_TTS_TEXT_LENGTH = 5_000


def _sanitize_error(e: Exception) -> str:
    msg = str(e)
    if "key=" in msg.lower():
        msg = msg.split("key=")[0] + "key=***"
    if "timed out" in msg.lower() or "timeout" in msg.lower():
        return "Request timed out. Please try again with simpler content or a shorter prompt."
    if "quota" in msg.lower() or "rate" in msg.lower() or "429" in msg:
        return "API rate limit reached. Please wait a moment and try again."
    if "403" in msg or "permission" in msg.lower():
        return "API access denied. Please check your API key permissions."
    if "404" in msg:
        return "The requested AI model is not available. Please try a different model."
    if "400" in msg or "invalid" in msg.lower():
        return "Invalid request. Please simplify your prompt and try again."
    if "safety" in msg.lower() or "blocked" in msg.lower():
        return "Content was blocked by safety filters. Please modify your prompt."
    if len(msg) > 200:
        msg = msg[:200] + "..."
    return f"Generation failed: {msg}"


def _validate_prompt(prompt: str, max_len: int = MAX_PROMPT_LENGTH) -> str:
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt cannot be empty.")
    if len(prompt) > max_len:
        logger.warning("Prompt truncated from %d to %d chars", len(prompt), max_len)
        prompt = prompt[:max_len]
    return prompt


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_data)
    return buf.getvalue()


def _concat_wavs(wav_list: list[bytes]) -> bytes:
    if len(wav_list) == 1:
        return wav_list[0]
    all_frames = b""
    params = None
    for wav_bytes in wav_list:
        with wave.open(io.BytesIO(wav_bytes), "rb") as w:
            if params is None:
                params = w.getparams()
            all_frames += w.readframes(w.getnframes())
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setparams(params)
        out.writeframes(all_frames)
    return buf.getvalue()


def _api_post(url: str, payload: dict, timeout=_TIMEOUT_SLOW, retries: int = 2):
    import requests
    last_err = None
    for attempt in range(retries + 1):
        try:
            t0 = time.monotonic()
            resp = requests.post(url, json=payload, timeout=timeout)
            elapsed = time.monotonic() - t0
            resp.raise_for_status()
            logger.info("API call OK (%.1fs)", elapsed)
            return resp.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            logger.warning("API timeout (attempt %d/%d): %s", attempt + 1, retries + 1, type(e).__name__)
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
            continue
        except requests.exceptions.HTTPError as e:
            if e.response is not None and 400 <= e.response.status_code < 500:
                logger.error("API client error %d", e.response.status_code)
                raise
            last_err = e
            logger.warning("API server error (attempt %d/%d)", attempt + 1, retries + 1)
            if attempt < retries:
                time.sleep(5)
            continue
    raise RuntimeError(f"API call failed after {retries + 1} attempts: {last_err}")


def _lang_instruction(lang: str) -> str:
    if lang == "ar":
        return "IMPORTANT: Generate ALL output in Arabic (العربية). "
    if lang == "both":
        return "IMPORTANT: Generate output in both Arabic and English (bilingual). "
    return ""


def generate_image(
    prompt: str,
    context_text: str = "",
    files: list = None,
    model: str = "imagen_fast",
    aspect_ratio: str = "16:9",
    lang: str = "en",
) -> tuple[bytes, str]:
    prompt = _validate_prompt(prompt)
    context_text = context_text[:MAX_CONTEXT_LENGTH] if context_text else ""
    model_id = MODELS["image"].get(model, MODELS["image"]["imagen_fast"])
    lang_prefix = _lang_instruction(lang)
    full_prompt = f"{lang_prefix}{context_text}\n\n{prompt}".strip() if context_text else f"{lang_prefix}{prompt}"
    key = require_api_key()

    logger.info("Generating image: model=%s, aspect=%s, lang=%s", model, aspect_ratio, lang)
    is_imagen = "imagen" in model_id

    if is_imagen:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:predict?key={key}"
        payload = {
            "instances": [{"prompt": full_prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": aspect_ratio},
        }
        data = _api_post(api_url, payload, timeout=_TIMEOUT_SLOW)
        preds = data.get("predictions", [])
        if not preds:
            raise RuntimeError("No image returned. Try a different prompt or model.")
        p = preds[0]
        b64 = (
            p.get("bytesBase64Encoded")
            or p.get("b64_json")
            or (p.get("image", {}).get("bytesBase64Encoded") if isinstance(p.get("image"), dict) else None)
        )
        if b64:
            return base64.b64decode(b64), "image/png"
        raise RuntimeError("Could not extract image data. Try a different model.")

    else:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}"
        parts = [{"text": full_prompt}]
        if files:
            _, file_attachments = get_content_from_input(files=files)
            for name, mime, raw in file_attachments:
                if "image" in mime:
                    parts.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(raw).decode()}})
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        if aspect_ratio:
            payload["generationConfig"]["imageConfig"] = {"aspectRatio": aspect_ratio}
        data = _api_post(api_url, payload, timeout=_TIMEOUT_SLOW)
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                b64 = part["inlineData"].get("data")
                if b64:
                    return base64.b64decode(b64), "image/png"

    raise RuntimeError("No image in API response. Try a different prompt.")


def generate_video(
    prompt: str,
    context_text: str = "",
    aspect_ratio: str = "16:9",
    duration: str = "8",
    lang: str = "en",
) -> tuple[bytes, str]:
    from google import genai

    prompt = _validate_prompt(prompt)
    context_text = context_text[:MAX_CONTEXT_LENGTH] if context_text else ""
    model_id = MODELS["video"]

    # Video models can't render text correctly (especially Arabic), so we
    # explicitly tell it to avoid any on-screen text, titles, or captions.
    no_text_rule = (
        "CRITICAL: Do NOT include any text, titles, subtitles, captions, watermarks, "
        "labels, or writing of any kind in the video. The video must be purely visual "
        "with no on-screen text whatsoever. "
    )

    lang_prefix = ""
    if lang == "ar":
        lang_prefix = "Create a video suitable for an Arabic-speaking audience. "
    elif lang == "both":
        lang_prefix = "Create a video suitable for a bilingual Arabic/English audience. "

    full_prompt = f"{no_text_rule}{lang_prefix}"
    if context_text:
        full_prompt += f"{context_text}\n\n"
    full_prompt += prompt

    key = require_api_key()
    logger.info("Generating video: model=%s, aspect=%s, duration=%s, lang=%s", model_id, aspect_ratio, duration, lang)

    _saved = os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)
    try:
        client = genai.Client(api_key=key, vertexai=False)
        operation = client.models.generate_videos(
            model=model_id,
            prompt=full_prompt,
            config={"aspect_ratio": aspect_ratio, "duration_seconds": duration},
        )
        timeout = 900
        elapsed = 0
        while not operation.done:
            time.sleep(15)
            elapsed += 15
            operation = client.operations.get(operation)
            if elapsed % 60 == 0:
                logger.info("Video in progress... (%ds)", elapsed)
            if elapsed >= timeout:
                raise TimeoutError("Video generation timed out after 15 minutes.")

        video = operation.response.generated_videos[0]
        client.files.download(file=video.video)
        fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
        try:
            os.close(fd)
            video.video.save(tmp_path)
            with open(tmp_path, "rb") as f:
                result = f.read()
            logger.info("Video generated (%d bytes)", len(result))
            return result, "video/mp4"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    finally:
        if _saved is not None:
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = _saved


def _tts_single(text: str, voice_name: str, model_id: str, key: str) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name}}},
        },
    }
    data = _api_post(url, payload, timeout=_TIMEOUT_SLOW, retries=2)
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            b64 = part["inlineData"].get("data")
            if b64:
                return _pcm_to_wav(base64.b64decode(b64))
    raise RuntimeError("No audio in TTS response.")


def generate_voice(
    text: str,
    context_text: str = "",
    voice_name: str = "Kore",
    style_hint: str = "",
    tts_model: str = "flash",
    lang: str = "en",
) -> tuple[bytes, str]:
    text = _validate_prompt(text, max_len=MAX_TTS_TEXT_LENGTH)
    model_id = (
        MODELS["voice"].get(tts_model, MODELS["voice"]["flash"])
        if isinstance(MODELS["voice"], dict) else MODELS["voice"]
    )
    if lang == "ar":
        full_text = f"تحدث باللغة العربية بوضوح: {text}" if not style_hint else f"تحدث باللغة العربية {style_hint}: {text}"
    elif lang == "both":
        full_text = f"Speak bilingually (Arabic and English): {text}" if not style_hint else f"Say {style_hint}, bilingually: {text}"
    else:
        full_text = f"Say {style_hint}: {text}" if style_hint else text
    if context_text:
        full_text = f"[Context: {context_text[:500]}]\n\n{full_text}"

    key = require_api_key()
    logger.info("Generating voice: voice=%s, model=%s, lang=%s", voice_name, tts_model, lang)
    wav = _tts_single(full_text, voice_name, model_id, key)
    logger.info("Voice generated (%d bytes)", len(wav))
    return wav, "audio/wav"


def _multi_speaker_tts(script: str, voice_host: str, voice_guest: str, key: str) -> bytes:
    voice_id = (
        MODELS["voice"].get("flash", MODELS["voice"])
        if isinstance(MODELS["voice"], dict) else MODELS["voice"]
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{voice_id}:generateContent?key={key}"

    lines = script.strip().split("\n")
    chunks, current_chunk, current_words = [], [], 0
    for line in lines:
        wc = len(line.split())
        if current_words + wc > 150 and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk, current_words = [line], wc
        else:
            current_chunk.append(line)
            current_words += wc
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    if len(chunks) <= 1:
        chunks = [script.strip()]

    logger.info("Podcast TTS: %d chunks from %d-word script", len(chunks), len(script.split()))

    wav_parts = []
    for i, chunk in enumerate(chunks):
        logger.info("  TTS chunk %d/%d (%d words)", i + 1, len(chunks), len(chunk.split()))
        payload = {
            "contents": [{"role": "user", "parts": [{"text": f"Read this podcast dialogue naturally:\n\n{chunk}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "multiSpeakerVoiceConfig": {
                        "speakerVoiceConfigs": [
                            {"speaker": "Host", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_host}}},
                            {"speaker": "Guest", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_guest}}},
                        ]
                    }
                },
            },
        }
        data = _api_post(url, payload, timeout=_TIMEOUT_SLOW, retries=2)
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                b64 = part["inlineData"].get("data")
                if b64:
                    wav_parts.append(_pcm_to_wav(base64.b64decode(b64)))
                    break

    if not wav_parts:
        raise RuntimeError("No audio generated from any chunk.")
    return _concat_wavs(wav_parts)


def generate_podcast(
    prompt: str,
    context_text: str = "",
    url: str = "",
    files: list = None,
    length: str = "short",
    voice_host: str = "Kore",
    voice_guest: str = "Puck",
    lang: str = "en",
) -> tuple[bytes, str]:
    prompt = _validate_prompt(prompt)
    combined_text, _ = get_content_from_input(text=prompt, url=url, files=files)
    if context_text and context_text != "No content provided.":
        combined_text = f"{context_text}\n\n---\n\n{combined_text}"

    target_words = "200-300" if length == "short" else "400-500"
    logger.info("Generating podcast: length=%s, voices=%s/%s, lang=%s", length, voice_host, voice_guest, lang)

    if lang == "ar":
        script_prompt = f"""أنت كاتب سيناريو بودكاست محترف. أنشئ سيناريو بودكاست جذاب وطبيعي باللغة العربية الفصحى.

المتطلبات:
- الطول المستهدف: {target_words} كلمة فقط (مهم جداً: لا تتجاوز هذا الحد)
- متحدثان: Host و Guest
- صيغة كل سطر: Host: [الحوار بالعربية] أو Guest: [الحوار بالعربية]
- اكتب الحوار بالعربية لكن استخدم Host و Guest كأسماء المتحدثين
- اجعله حوارياً وممتعاً وغنياً بالمعلومات
- ابدأ بمقدمة واختم بملخص

المحتوى:
{combined_text[:15000]}
"""
    elif lang == "both":
        script_prompt = f"""Create a SHORT bilingual podcast script (Arabic + English mixed).

Rules:
- STRICT limit: {target_words} words total. Do NOT exceed this.
- Two speakers: Host and Guest
- Format: Host: [dialogue] or Guest: [dialogue]
- Mix Arabic and English naturally
- Open with intro, close with summary

Content:
{combined_text[:15000]}
"""
    else:
        script_prompt = f"""Create a SHORT podcast script based on this content.

Rules:
- STRICT limit: {target_words} words total. Do NOT exceed this.
- Two speakers: Host and Guest
- Format: Host: [dialogue] or Guest: [dialogue]
- Conversational, engaging
- Open with intro, close with summary

Content:
{combined_text[:15000]}
"""

    key = require_api_key()
    url_text = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELS['podcast']}:generateContent?key={key}"
    script_data = _api_post(
        url_text,
        {"contents": [{"role": "user", "parts": [{"text": script_prompt}]}]},
        timeout=_TIMEOUT_SLOW, retries=2,
    )

    script = "".join(
        p.get("text", "")
        for p in script_data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    )
    if not script.strip():
        raise RuntimeError("Script generation returned empty result.")

    script = script.replace("المقدم:", "Host:").replace("الضيف:", "Guest:")

    words = script.split()
    if len(words) > 600:
        logger.warning("Script exceeded limit (%d words), truncating to 600", len(words))
        script = " ".join(words[:600])

    logger.info("Podcast script ready (%d words), starting TTS", len(script.split()))
    wav = _multi_speaker_tts(script, voice_host, voice_guest, key)
    logger.info("Podcast generated (%d bytes)", len(wav))
    return wav, "audio/wav"
