import base64
import io
import logging
import os
import tempfile
import time
import wave

from google.genai import types as genai_types

from rcjy_config import MODELS, get_genai_client
from content_extractor import get_content_from_input

logger = logging.getLogger("rcjy.generators")

MAX_PROMPT_LENGTH = 10_000
MAX_CONTEXT_LENGTH = 50_000
MAX_TTS_TEXT_LENGTH = 5_000


def _scrub_api_key(text: str) -> str:
    # Remove API key patterns from text
    import re
    text = re.sub(r'(?i)key=[\w\-]{10,}', 'key=***REDACTED***', text)
    text = re.sub(r'AIza[A-Za-z0-9_\-]{30,}', '***REDACTED***', text)
    text = re.sub(r'(?i)bearer\s+[\w\-\.]{10,}', 'Bearer ***REDACTED***', text)
    return text


def _sanitize_error(e: Exception) -> str:
    msg = _scrub_api_key(str(e))
    low = msg.lower()
    if "timed out" in low or "timeout" in low:
        return "Request timed out. Please try again with simpler content or a shorter prompt."
    if "safety" in low or "blocked" in low or "filtered" in low or "responsible ai" in low:
        return "Content was blocked by safety filters. Please rephrase your prompt and try again."
    if "quota" in low or "rate limit" in low or "429" in msg:
        logger.error("Rate/quota error (raw): %s", msg)
        return "API rate or quota limit reached. Please wait a moment and try again."
    if "403" in msg or "permission" in low:
        logger.error("Permission error (raw): %s", msg)
        return "API access denied. Please check your API key configuration."
    if "404" in msg:
        return "The requested AI model is not available. Please try a different model."
    if "400" in msg or "invalid" in low:
        return "Invalid request. Please simplify your prompt and try again."
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


# Allowlists
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


def _retry(fn, retries=2):
    # Retry on rate-limit and timeout errors
    last_err = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            # Don't retry safety/content filter errors
            if "filtered" in msg or "responsible ai" in msg or "safety" in msg or "blocked" in msg:
                raise
            if "429" in str(e) or "rate limit" in msg or "quota" in msg or "resource_exhausted" in msg:
                wait = min(30 * (attempt + 1), 120)
                logger.warning("Rate limited, waiting %ds (attempt %d/%d)", wait, attempt + 1, retries + 1)
                if attempt < retries:
                    time.sleep(wait)
                    continue
            if "timeout" in msg or "timed out" in msg or "deadline" in msg:
                logger.warning("Timeout (attempt %d/%d)", attempt + 1, retries + 1)
                if attempt < retries:
                    time.sleep(5 * (attempt + 1))
                    continue
            raise
    raise last_err


def _lang_instruction(lang: str) -> str:
    if lang == "ar":
        return ("IMPORTANT: By default, generate output in Arabic. "
                "However, if the user's prompt is written in English or another language, "
                "respond in that language instead. If the prompt explicitly requests a specific language, use that language. ")
    if lang == "both":
        return "IMPORTANT: Generate output in both Arabic and English (bilingual). "
    return ("IMPORTANT: By default, generate output in English. "
            "However, if the user's prompt is written in Arabic or another language, "
            "respond in that language instead. If the prompt explicitly requests a specific language, use that language. ")



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

    client = get_genai_client()
    logger.info("Generating text: type=%s, tone=%s, model=%s, lang=%s", text_type, tone, model, lang)

    response = _retry(lambda: client.models.generate_content(
        model=model_id,
        contents=f"{system_prompt}\n\n{user_content}",
        config=genai_types.GenerateContentConfig(
            temperature=0.8,
            max_output_tokens=8192,
        ),
    ))

    result = response.text or ""
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

    client = get_genai_client()
    logger.info("Generating image: model=%s, aspect=%s, lang=%s", model, aspect_ratio, lang)
    is_imagen = "imagen" in model_id

    if is_imagen:
        response = _retry(lambda: client.models.generate_images(
            model=model_id,
            prompt=full_prompt,
            config=genai_types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
            ),
        ))
        if not response.generated_images:
            raise RuntimeError("No image returned. Try a different prompt or model.")
        img = response.generated_images[0]
        return img.image.image_bytes, "image/png"

    else:
        # Gemini native image generation
        parts = [genai_types.Part(text=full_prompt)]
        if files:
            _, file_attachments = get_content_from_input(files=files)
            for name, mime, raw in file_attachments:
                if "image" in mime:
                    parts.append(genai_types.Part(
                        inline_data=genai_types.Blob(mime_type=mime, data=raw)
                    ))
        response = _retry(lambda: client.models.generate_content(
            model=model_id,
            contents=genai_types.Content(role="user", parts=parts),
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        ))
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data, part.inline_data.mime_type or "image/png"
        logger.warning("Gemini image response had no image data")

    raise RuntimeError("No image in API response. Try a different prompt.")



def _build_video_prompt(prompt: str, context_text: str, lang: str) -> str:
    # Build prompt for video generation with standard rules
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
    # Poll video generation operation until done or timeout
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
    # Download generated video and return bytes
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
    # Generate video, optionally extended via Veo 3.1 extension loop
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

    # force 720p when extending
    if extend_seconds > 0:
        resolution = "720p"

    logger.info(
        "Generating video: model=%s, aspect=%s, duration=%s, resolution=%s, "
        "extend_seconds=%d, lang=%s",
        model_id, aspect_ratio, duration, resolution, extend_seconds, lang,
    )

    client = get_genai_client()

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
    target_dur = min(initial_dur + extend_seconds, 148)
    max_extensions = 20
    ext_count = 0

    logger.info(
        "Starting extension loop: current=%ds, target=%ds", current_dur, target_dur,
    )

    while current_dur < target_dur and ext_count < max_extensions:
        ext_count += 1

        if ext_count > 1:
            logger.info("Waiting 10s before next extension to avoid rate limits...")
            time.sleep(10)

        msg = f"Extending video ({current_dur}s -> {current_dur + 7}s) [step {ext_count}]..."
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

        ext_prompt = f"Continue the scene seamlessly. {full_prompt}"

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
                if ("429" in str(e) or "rate limit" in str(e).lower() or "quota" in str(e).lower()) and attempt < 2:
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



def _tts_single(text: str, voice_name: str, model_id: str, client) -> bytes:
    # Single-speaker TTS audio via SDK
    response = _retry(lambda: client.models.generate_content(
        model=model_id,
        contents=text,
        config=genai_types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        ),
    ))
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            return _pcm_to_wav(part.inline_data.data)
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
    style_hint = style_hint[:100].strip()
    display_name = display_name[:50].strip()
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

    client = get_genai_client()
    logger.info("Generating voice: voice=%s, model=%s, lang=%s", voice_name, tts_model, lang)
    wav = _tts_single(full_text, voice_name, model_id, client)
    logger.info("Voice generated (%d bytes)", len(wav))
    return wav, "audio/wav"



def _multi_speaker_tts(script: str, voice_host: str, voice_guest: str, client, lang: str = "en") -> bytes:
    model_id = (
        MODELS["voice"].get("flash", MODELS["voice"])
        if isinstance(MODELS["voice"], dict) else MODELS["voice"]
    )

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

        # capture loop var
        _inst = tts_instruction
        response = _retry(lambda _t=_inst: client.models.generate_content(
            model=model_id,
            contents=_t,
            config=genai_types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai_types.SpeechConfig(
                    multi_speaker_voice_config=genai_types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            genai_types.SpeakerVoiceConfig(
                                speaker="Host",
                                voice_config=genai_types.VoiceConfig(
                                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=voice_host)
                                ),
                            ),
                            genai_types.SpeakerVoiceConfig(
                                speaker="Guest",
                                voice_config=genai_types.VoiceConfig(
                                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=voice_guest)
                                ),
                            ),
                        ]
                    )
                ),
            ),
        ))
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                wav_parts.append(_pcm_to_wav(part.inline_data.data))
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

    client = get_genai_client()
    script_response = _retry(lambda: client.models.generate_content(
        model=MODELS["podcast"],
        contents=script_prompt,
    ))

    script = script_response.text or ""
    if not script.strip():
        raise RuntimeError("Script generation returned empty result.")

    script = script.replace("المقدم:", "Host:").replace("الضيف:", "Guest:")

    words = script.split()
    if len(words) > 600:
        logger.warning("Script exceeded limit (%d words), truncating to 600", len(words))
        script = " ".join(words[:600])

    logger.info("Podcast script ready (%d words), starting TTS", len(script.split()))
    wav = _multi_speaker_tts(script, voice_host, voice_guest, client, lang=lang)
    logger.info("Podcast generated (%d bytes)", len(wav))
    return wav, "audio/wav"
