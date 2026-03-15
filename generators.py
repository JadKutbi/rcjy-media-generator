import base64
import io
import logging
import os
import tempfile
import time
import wave

from rcjy_config import MODELS, require_api_key
from content_extractor import get_content_from_input

logger = logging.getLogger("rcjy.generators")

_TIMEOUT_FAST = (30, 180)
_TIMEOUT_SLOW = (30, 300)
_TIMEOUT_HEAVY = (30, 600)

MAX_PROMPT_LENGTH = 10_000
MAX_CONTEXT_LENGTH = 50_000
MAX_TTS_TEXT_LENGTH = 5_000


def _scrub_api_key(text: str) -> str:
    """Remove any API key patterns from text to prevent accidental leakage."""
    import re
    # Scrub Google API keys (AIza pattern) and generic key= params
    text = re.sub(r'(?i)key=[\w\-]{10,}', 'key=***REDACTED***', text)
    text = re.sub(r'AIza[A-Za-z0-9_\-]{30,}', '***REDACTED***', text)
    # Scrub any Bearer tokens
    text = re.sub(r'(?i)bearer\s+[\w\-\.]{10,}', 'Bearer ***REDACTED***', text)
    return text


def _sanitize_error(e: Exception) -> str:
    msg = _scrub_api_key(str(e))
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


# Allowlists for parameter validation (prevents injection of arbitrary model IDs)
_ALLOWED_TEXT_TYPES = {"article", "social", "press", "ad", "email", "script", "summary", "creative"}
_ALLOWED_TONES = {"professional", "friendly", "formal", "persuasive", "informative"}
_ALLOWED_LANGS = {"en", "ar", "both"}
_ALLOWED_ASPECT_RATIOS = {"16:9", "9:16", "1:1", "4:3", "3:4"}
_ALLOWED_RESOLUTIONS = {"720p", "1080p", "4k"}
_ALLOWED_DURATIONS = {"5", "6", "7", "8"}
_ALLOWED_PODCAST_LENGTHS = {"short", "standard"}


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


def _api_post(url: str, payload: dict, timeout=_TIMEOUT_SLOW, retries: int = 3):
    import requests
    last_err = None
    # Extract a safe URL for logging (strip API key query param)
    _safe_url = url.split("?")[0] if "?" in url else url
    for attempt in range(retries + 1):
        try:
            t0 = time.monotonic()
            resp = requests.post(url, json=payload, timeout=timeout)
            elapsed = time.monotonic() - t0
            resp.raise_for_status()
            logger.info("API call OK (%.1fs) %s", elapsed, _safe_url)
            return resp.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            logger.warning("API timeout (attempt %d/%d): %s", attempt + 1, retries + 1, type(e).__name__)
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
            continue
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                wait = min(30 * (attempt + 1), 120)
                logger.warning("Rate limited (429), waiting %ds (attempt %d/%d)", wait, attempt + 1, retries + 1)
                last_err = e
                if attempt < retries:
                    time.sleep(wait)
                continue
            if 400 <= status < 500:
                logger.error("API client error %d on %s", status, _safe_url)
                raise
            last_err = e
            logger.warning("API server error %d (attempt %d/%d)", status, attempt + 1, retries + 1)
            if attempt < retries:
                time.sleep(5)
            continue
    raise RuntimeError(f"API call failed after {retries + 1} attempts: {_scrub_api_key(str(last_err))}")


def _lang_instruction(lang: str) -> str:
    if lang == "ar":
        return "IMPORTANT: Generate ALL output in Arabic (العربية). "
    if lang == "both":
        return "IMPORTANT: Generate output in both Arabic and English (bilingual). "
    return ""


def generate_text(
    prompt: str,
    context_text: str = "",
    url: str = "",
    files: list = None,
    text_type: str = "article",
    tone: str = "professional",
    model: str = "pro",
    lang: str = "en",
) -> str:
    prompt = _validate_prompt(prompt)
    text_type = text_type if text_type in _ALLOWED_TEXT_TYPES else "article"
    tone = tone if tone in _ALLOWED_TONES else "professional"
    lang = lang if lang in _ALLOWED_LANGS else "en"
    if model not in MODELS.get("text", {}):
        model = "pro"
    combined_text, _ = get_content_from_input(text=prompt, url=url, files=files)
    if context_text and context_text != "No content provided.":
        combined_text = f"{context_text}\n\n---\n\n{combined_text}"

    model_id = (
        MODELS["text"].get(model, MODELS["text"]["pro"])
        if isinstance(MODELS["text"], dict) else MODELS["text"]
    )

    lang_hint = _lang_instruction(lang)
    if lang == "ar":
        lang_hint = "IMPORTANT: اكتب المحتوى بالكامل باللهجة السعودية الخليجية أو العربية الفصحى. "

    type_labels = {
        "article": "article or blog post",
        "social": "social media post (concise, engaging, with hashtags)",
        "press": "press release (formal, newsworthy)",
        "ad": "advertisement copy (persuasive, catchy)",
        "email": "professional email",
        "script": "video/presentation script",
        "summary": "summary of the provided content",
        "creative": "creative writing piece",
    }
    type_desc = type_labels.get(text_type, text_type)

    system_prompt = f"""{lang_hint}You are an expert content writer for the Royal Commission for Jubail and Yanbu (RCJY) Communication & Media Department. Write a {type_desc} with a {tone} tone.

Requirements:
- High quality, publication-ready content
- Well structured with clear sections if applicable
- Engaging and informative
- Appropriate for a government media department"""

    user_content = combined_text[:30000] if combined_text else prompt

    key = require_api_key()
    url_api = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}"
    logger.info("Generating text: type=%s, tone=%s, model=%s, lang=%s", text_type, tone, model, lang)

    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 8192},
    }

    data = _api_post(url_api, payload, timeout=_TIMEOUT_SLOW, retries=2)
    result = "".join(
        p.get("text", "")
        for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    )
    if not result.strip():
        raise RuntimeError("Text generation returned empty result.")
    logger.info("Text generated (%d chars)", len(result))
    return result


def generate_image(
    prompt: str,
    context_text: str = "",
    files: list = None,
    model: str = "imagen_fast",
    aspect_ratio: str = "16:9",
    lang: str = "en",
) -> tuple[bytes, str]:
    prompt = _validate_prompt(prompt)
    lang = lang if lang in _ALLOWED_LANGS else "en"
    aspect_ratio = aspect_ratio if aspect_ratio in _ALLOWED_ASPECT_RATIOS else "16:9"
    if model not in MODELS.get("image", {}):
        model = "imagen_fast"
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


def _build_video_prompt(prompt: str, context_text: str, lang: str) -> str:
    """Build the full prompt for video generation with standard rules."""
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
    return full_prompt


def _poll_video_operation(client, operation, timeout: int = 900):
    """Poll a video generation operation until done or timeout."""
    elapsed = 0
    while not operation.done:
        time.sleep(15)
        elapsed += 15
        operation = client.operations.get(operation)
        if elapsed % 60 == 0:
            logger.info("Video in progress... (%ds)", elapsed)
        if elapsed >= timeout:
            raise TimeoutError(f"Video generation timed out after {timeout // 60} minutes.")
    return operation


def _save_video_to_bytes(client, video) -> bytes:
    """Download a generated video and return its bytes."""
    client.files.download(file=video.video)
    fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
    try:
        os.close(fd)
        video.video.save(tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def generate_video(
    prompt: str,
    context_text: str = "",
    aspect_ratio: str = "16:9",
    duration: str = "8",
    resolution: str = "1080p",
    model: str = "standard",
    lang: str = "en",
    extend_seconds: int = 0,
    progress_callback=None,
) -> tuple[bytes, str]:
    """Generate a video, optionally extended beyond the initial clip.

    Args:
        extend_seconds: Total desired duration beyond the initial clip using
            Veo 3.1 video extension.  Each extension adds ~7 s.  Set to 0
            (default) for a single clip.  Extension forces 720p resolution.
            Maximum total duration is ~148 s.
        progress_callback: Optional callable(message: str) invoked with
            progress updates during multi-step extension.
    """
    from google import genai

    prompt = _validate_prompt(prompt)
    lang = lang if lang in _ALLOWED_LANGS else "en"
    aspect_ratio = aspect_ratio if aspect_ratio in {"16:9", "9:16"} else "16:9"
    duration = duration if duration in _ALLOWED_DURATIONS else "8"
    resolution = resolution.lower() if resolution.lower() in _ALLOWED_RESOLUTIONS else "1080p"
    extend_seconds = max(0, min(int(extend_seconds), 140))  # cap at 140s
    if model not in MODELS.get("video", {}):
        model = "standard"
    context_text = context_text[:MAX_CONTEXT_LENGTH] if context_text else ""
    model_id = (
        MODELS["video"].get(model, MODELS["video"]["standard"])
        if isinstance(MODELS["video"], dict) else MODELS["video"]
    )

    full_prompt = _build_video_prompt(prompt, context_text, lang)

    key = require_api_key()

    # force 720p when extending
    if extend_seconds > 0:
        resolution = "720p"

    logger.info(
        "Generating video: model=%s, aspect=%s, duration=%s, resolution=%s, "
        "extend_seconds=%d, lang=%s",
        model_id, aspect_ratio, duration, resolution, extend_seconds, lang,
    )

    _saved = os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)
    try:
        client = genai.Client(api_key=key, vertexai=False)

        # generate initial clip
        if progress_callback:
            progress_callback("Generating initial clip...")
        operation = client.models.generate_videos(
            model=model_id,
            prompt=full_prompt,
            config={
                "aspect_ratio": aspect_ratio,
                "duration_seconds": duration,
                "resolution": resolution.lower(),
            },
        )
        operation = _poll_video_operation(client, operation)
        video_obj = operation.response.generated_videos[0]

        if extend_seconds <= 0:
            # single clip, return directly
            result = _save_video_to_bytes(client, video_obj)
            logger.info("Video generated (%d bytes)", len(result))
            return result, "video/mp4"

        # extension loop
        initial_dur = int(duration)
        current_dur = initial_dur
        # Each extension adds 7 seconds; max 20 extensions (148 s total).
        target_dur = min(initial_dur + extend_seconds, 148)
        max_extensions = 20
        ext_count = 0

        logger.info(
            "Starting extension loop: current=%ds, target=%ds", current_dur, target_dur,
        )

        while current_dur < target_dur and ext_count < max_extensions:
            ext_count += 1

            # Pause between extensions to avoid rate limits
            if ext_count > 1:
                logger.info("Waiting 10s before next extension to avoid rate limits...")
                time.sleep(10)

            msg = f"Extending video ({current_dur}s -> {current_dur + 7}s) [step {ext_count}]..."
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

            # Use a continuation prompt that maintains scene coherence
            ext_prompt = (
                f"Continue the scene seamlessly. {full_prompt}"
            )

            # Retry extension on rate limit errors
            for attempt in range(3):
                try:
                    operation = client.models.generate_videos(
                        model=model_id,
                        prompt=ext_prompt,
                        video=video_obj.video,
                        config={
                            "number_of_videos": 1,
                            "resolution": "720p",
                        },
                    )
                    break
                except Exception as e:
                    if ("429" in str(e) or "rate" in str(e).lower() or "quota" in str(e).lower()) and attempt < 2:
                        wait = 30 * (attempt + 1)
                        logger.warning("Rate limited on extension, waiting %ds (attempt %d/3)", wait, attempt + 1)
                        if progress_callback:
                            progress_callback(f"Rate limited, retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        raise

            operation = _poll_video_operation(client, operation)
            video_obj = operation.response.generated_videos[0]
            current_dur += 7

        # download final extended video
        if progress_callback:
            progress_callback("Downloading final video...")
        result = _save_video_to_bytes(client, video_obj)
        logger.info(
            "Extended video generated (%d bytes, ~%ds, %d extensions)",
            len(result), current_dur, ext_count,
        )
        return result, "video/mp4"
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


_ALLOWED_VOICES = {
    "Kore", "Aoede", "Leda", "Zephyr", "Schedar",
    "Puck", "Charon", "Fenrir", "Orus", "Perseus",
}


def generate_voice(
    text: str,
    context_text: str = "",
    voice_name: str = "Kore",
    display_name: str = "",
    style_hint: str = "",
    tts_model: str = "flash",
    lang: str = "en",
) -> tuple[bytes, str]:
    text = _validate_prompt(text, max_len=MAX_TTS_TEXT_LENGTH)
    lang = lang if lang in _ALLOWED_LANGS else "en"
    voice_name = voice_name if voice_name in _ALLOWED_VOICES else "Kore"
    style_hint = style_hint[:100].strip()  # limit style hint length
    display_name = display_name[:50].strip()  # limit display name length
    if tts_model not in MODELS.get("voice", {}):
        tts_model = "flash"
    model_id = (
        MODELS["voice"].get(tts_model, MODELS["voice"]["flash"])
        if isinstance(MODELS["voice"], dict) else MODELS["voice"]
    )
    if lang == "ar":
        _name_hint = f"اسمك {display_name}. " if display_name else ""
        full_text = f"{_name_hint}تحدث باللهجة السعودية الخليجية بوضوح: {text}" if not style_hint else f"{_name_hint}تحدث باللهجة السعودية الخليجية {style_hint}: {text}"
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


def _multi_speaker_tts(script: str, voice_host: str, voice_guest: str, key: str, lang: str = "en") -> bytes:
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
        if lang == "ar":
            tts_instruction = f"اقرأ حوار البودكاست التالي باللهجة السعودية الخليجية بشكل طبيعي وتعبيري:\n\n{chunk}"
        elif lang == "both":
            tts_instruction = f"Read this bilingual Arabic-English podcast dialogue naturally:\n\n{chunk}"
        else:
            tts_instruction = f"Read this podcast dialogue naturally:\n\n{chunk}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": tts_instruction}]}],
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
    host_display_name: str = "",
    guest_display_name: str = "",
    lang: str = "en",
) -> tuple[bytes, str]:
    prompt = _validate_prompt(prompt)
    lang = lang if lang in _ALLOWED_LANGS else "en"
    length = length if length in _ALLOWED_PODCAST_LENGTHS else "short"
    voice_host = voice_host if voice_host in _ALLOWED_VOICES else "Kore"
    voice_guest = voice_guest if voice_guest in _ALLOWED_VOICES else "Puck"
    host_display_name = host_display_name[:50].strip()
    guest_display_name = guest_display_name[:50].strip()
    combined_text, _ = get_content_from_input(text=prompt, url=url, files=files)
    if context_text and context_text != "No content provided.":
        combined_text = f"{context_text}\n\n---\n\n{combined_text}"

    target_words = "200-300" if length == "short" else "400-500"
    logger.info("Generating podcast: length=%s, voices=%s/%s, lang=%s", length, voice_host, voice_guest, lang)

    if lang == "ar":
        _host_n = host_display_name or "المقدّم"
        _guest_n = guest_display_name or "الضيف"
        script_prompt = f"""أنت كاتب سيناريو بودكاست محترف. أنشئ سيناريو بودكاست جذاب وطبيعي باللهجة السعودية الخليجية.

المتطلبات:
- الطول المستهدف: {target_words} كلمة فقط (مهم جداً: لا تتجاوز هذا الحد)
- متحدثان: Host (اسمه {_host_n}) و Guest (اسمه {_guest_n})
- صيغة كل سطر: Host: [الحوار بالعربية] أو Guest: [الحوار بالعربية]
- اكتب الحوار بالعربية لكن استخدم Host و Guest كأسماء المتحدثين في بداية كل سطر
- المقدّم {_host_n} يعرّف نفسه باسمه والضيف {_guest_n} كذلك
- اكتب الحوار باللهجة السعودية الخليجية وليس بالإنجليزية
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
    wav = _multi_speaker_tts(script, voice_host, voice_guest, key, lang=lang)
    logger.info("Podcast generated (%d bytes)", len(wav))
    return wav, "audio/wav"
