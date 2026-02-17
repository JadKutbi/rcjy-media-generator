import logging

import streamlit as st

from config import RCJY_LOGO_URL, SUPPORTED_FILE_TYPES, get_api_key
from content_extractor import get_content_from_input
from generators import generate_image, generate_podcast, generate_video, generate_voice
from generators import _sanitize_error

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rcjy.app")

T = {
    "en": {
        "page_title": "RCJY Media Generator",
        "app_name": "RCJY Media Generator",
        "dept": "Communication & Media Department",
        "hero_title": "Create Professional Media Content with AI",
        "hero_sub": "Generate images, videos, voice-overs, and podcasts",
        "lang_label": "Language",
        "prompt_label": "Your Prompt",
        "prompt_placeholder": "Describe what you want to create...\ne.g. A professional poster about Jubail industrial city",
        "output_lang_label": "Output Language",
        "url_label": "Reference URL (optional)",
        "attach_label": "Attach files",
        "attached": "Attached",
        "context_loaded": "Context loaded",
        "chars": "characters",
        "generate_label": "Generate",
        "tab_image": "Image",
        "tab_video": "Video",
        "tab_voice": "Voice",
        "tab_podcast": "Podcast",
        "model_label": "Model",
        "aspect_label": "Aspect Ratio",
        "duration_label": "Duration (sec)",
        "voice_label": "Voice",
        "quality_label": "Quality",
        "style_label": "Style hint",
        "style_placeholder": "e.g. professionally",
        "voice_note": "Your prompt text will be spoken. Optionally paste different text below:",
        "tts_placeholder": "(Optional) Paste specific text to speak instead...",
        "length_label": "Length",
        "length_short": "Short (4-5 min)",
        "length_standard": "Standard (~10 min)",
        "host_label": "Host voice",
        "guest_label": "Guest voice",
        "btn_image": "Generate Image",
        "btn_video": "Generate Video",
        "btn_voice": "Generate Voice",
        "btn_podcast": "Generate Podcast",
        "btn_download": "Download",
        "warn_prompt": "Please enter a prompt above.",
        "warn_topic": "Please enter a topic or attach content.",
        "warn_text": "Please enter text.",
        "warn_api": "API key not configured. Set GEMINI_API_KEY as an environment variable.",
        "spin_image": "Generating image...",
        "spin_video": "Generating video... (2-5 minutes)",
        "spin_voice": "Generating speech...",
        "spin_podcast": "Creating podcast... (2-3 minutes)",
        "footer_org": "Royal Commission for Jubail and Yanbu",
        "footer_dept": "Communication & Media Department",
    },
    "ar": {
        "page_title": "مولّد الوسائط - الهيئة الملكية",
        "app_name": "مولّد الوسائط",
        "dept": "إدارة الاتصال والإعلام",
        "hero_title": "أنشئ محتوى إعلامياً احترافياً بالذكاء الاصطناعي",
        "hero_sub": "صور، فيديو، تعليق صوتي، بودكاست",
        "lang_label": "اللغة",
        "prompt_label": "الوصف",
        "prompt_placeholder": "اكتب وصفاً لما تريد إنشاءه...\nمثال: ملصق احترافي عن مدينة الجبيل الصناعية",
        "output_lang_label": "لغة المحتوى",
        "url_label": "رابط مرجعي (اختياري)",
        "attach_label": "إرفاق ملفات",
        "attached": "مرفقات",
        "context_loaded": "تم تحميل المحتوى",
        "chars": "حرف",
        "generate_label": "إنشاء المحتوى",
        "tab_image": "صورة",
        "tab_video": "فيديو",
        "tab_voice": "صوت",
        "tab_podcast": "بودكاست",
        "model_label": "النموذج",
        "aspect_label": "نسبة العرض إلى الارتفاع",
        "duration_label": "المدة (ثانية)",
        "voice_label": "الصوت",
        "quality_label": "الجودة",
        "style_label": "أسلوب الأداء",
        "style_placeholder": "مثال: بشكل رسمي",
        "voice_note": "سيتم نطق النص الذي كتبته في الوصف أعلاه، أو يمكنك لصق نص مختلف هنا:",
        "tts_placeholder": "(اختياري) الصق نصاً مختلفاً للنطق...",
        "length_label": "مدة الحلقة",
        "length_short": "قصيرة (٤-٥ دقائق)",
        "length_standard": "عادية (~١٠ دقائق)",
        "host_label": "صوت المقدّم",
        "guest_label": "صوت الضيف",
        "btn_image": "إنشاء الصورة",
        "btn_video": "إنشاء الفيديو",
        "btn_voice": "إنشاء الصوت",
        "btn_podcast": "إنشاء البودكاست",
        "btn_download": "تحميل",
        "warn_prompt": "الرجاء إدخال وصف في الحقل أعلاه.",
        "warn_topic": "الرجاء إدخال موضوع أو إرفاق محتوى.",
        "warn_text": "الرجاء إدخال نص.",
        "warn_api": "لم يتم تعيين مفتاح API. قم بتعيين GEMINI_API_KEY كمتغير بيئة.",
        "spin_image": "جارٍ إنشاء الصورة...",
        "spin_video": "جارٍ إنشاء الفيديو... (٢-٥ دقائق)",
        "spin_voice": "جارٍ إنشاء الصوت...",
        "spin_podcast": "جارٍ إنشاء البودكاست... (٢-٣ دقائق)",
        "footer_org": "الهيئة الملكية للجبيل وينبع",
        "footer_dept": "إدارة الاتصال والإعلام",
    },
}

st.set_page_config(
    page_title="RCJY Media Generator",
    page_icon="https://www.rcjy.gov.sa/o/rcjy-theme/images/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "en"
for _key in ("result_image", "result_video", "result_voice", "result_podcast"):
    if _key not in st.session_state:
        st.session_state[_key] = None

is_ar = st.session_state.ui_lang == "ar"
rtl_css = """
    .stApp { direction: rtl; text-align: right; }
    .rcjy-header { flex-direction: row-reverse; }
    .section-label { direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; }
""" if is_ar else ""
ar_font = "'IBM Plex Sans Arabic', " if is_ar else ""

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap');
.stApp {{
    background: #FFFFFF;
    font-family: {ar_font}'Inter', -apple-system, sans-serif;
}}
#MainMenu, footer, header {{visibility: hidden;}}
{rtl_css}
.top-bar {{
    background: linear-gradient(135deg, #0A4225 0%, #0D6B3B 50%, #1B7A43 100%);
    height: 6px; margin: -1rem -1rem 0 -1rem;
}}
.rcjy-header {{
    background: #FFF; padding: 1.2rem 0 1rem 0;
    display: flex; align-items: center; gap: 1.2rem;
    border-bottom: 1px solid #E8ECE9; margin: 0 0 1.2rem 0;
}}
.rcjy-header img {{ height: 65px; }}
.rcjy-header .title-block h1 {{
    color: #1A2E21 !important; font-size: 1.5rem; font-weight: 800;
    margin: 0; line-height: 1.2;
}}
.rcjy-header .title-block p {{
    color: #5A6E60; font-size: 0.82rem; margin: 0.15rem 0 0 0;
}}
.hero-banner {{
    background: linear-gradient(135deg, #062715 0%, #0A4225 25%, #0D6B3B 60%, #1B7A43 100%);
    border-radius: 14px; padding: 1.8rem 2.5rem; margin-bottom: 1.5rem;
    position: relative; overflow: hidden;
}}
.hero-banner::before {{
    content: ''; position: absolute; top: -30%; right: 0;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(27,122,67,0.3) 0%, transparent 70%);
    border-radius: 50%;
}}
.hero-banner h2 {{
    color: #FFF !important; font-size: 1.3rem; font-weight: 700;
    margin: 0 0 0.25rem 0; position: relative; z-index: 1;
}}
.hero-banner p {{
    color: rgba(255,255,255,0.7); font-size: 0.85rem;
    margin: 0; position: relative; z-index: 1;
}}
.section-label {{
    color: #1A2E21; font-weight: 700; font-size: 0.95rem;
    margin: 1rem 0 0.5rem 0;
    padding-bottom: 0.35rem; border-bottom: 2px solid #0D6B3B;
}}
.stTabs [data-baseweb="tab-list"] {{
    gap: 0; background: #F5F7F6; border-radius: 10px; padding: 3px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 8px; background: transparent; color: #5A6E60;
    font-weight: 600; font-size: 0.85rem; padding: 0.5rem 1rem;
}}
.stTabs [data-baseweb="tab"]:hover {{ color: #0D6B3B; }}
.stTabs [aria-selected="true"] {{
    background: #0D6B3B !important; color: #FFF !important;
    box-shadow: 0 2px 6px rgba(13,107,59,0.25);
}}
.stButton > button {{
    background: linear-gradient(135deg, #0D6B3B 0%, #1B7A43 100%) !important;
    color: #FFF !important; font-weight: 700 !important;
    border: none !important; border-radius: 8px !important;
    padding: 0.65rem 2rem !important; font-size: 0.9rem !important;
    box-shadow: 0 3px 12px rgba(13,107,59,0.25); transition: all 0.2s;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 5px 20px rgba(13,107,59,0.35) !important;
}}
.stDownloadButton > button {{
    background: #1A2E21 !important; color: #FFF !important;
    font-weight: 600 !important; border: none !important; border-radius: 8px !important;
}}
[data-testid="stFileUploader"] {{
    border: 2px dashed #C8D5CC !important; border-radius: 10px !important;
    background: #FAFCFB !important; padding: 0.4rem !important;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: #0D6B3B !important; background: #F0F7F2 !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] div small,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploader"] section > div:first-child small {{
    display: none !important;
}}
.stTextArea textarea, .stTextInput input {{
    border-radius: 8px !important; border: 1.5px solid #D0D8D3 !important;
    color: #1A2E21 !important;
}}
.stTextArea textarea:focus, .stTextInput input:focus {{
    border-color: #0D6B3B !important;
    box-shadow: 0 0 0 2px rgba(13,107,59,0.12) !important;
}}
.stSelectbox [data-baseweb="select"] {{ border-radius: 8px !important; }}
.ctx-pill {{
    display: inline-flex; align-items: center; gap: 0.3rem;
    background: #E8F5EC; color: #0A4225;
    padding: 0.2rem 0.6rem; border-radius: 6px;
    font-size: 0.75rem; font-weight: 600; border: 1px solid #C8E6CF;
}}
.mtag {{
    display: inline-block; background: #F0F7F2; color: #0A4225;
    padding: 0.12rem 0.5rem; border-radius: 5px;
    font-size: 0.68rem; font-weight: 600; border: 1px solid #C8E6CF;
    margin-right: 3px;
}}
.app-footer {{
    text-align: center; padding: 1.5rem 1rem; margin-top: 2rem;
    border-top: 1px solid #E8ECE9; color: #8C9A90;
    font-size: 0.75rem; line-height: 1.6;
}}
.app-footer strong {{ color: #1A2E21; }}
.app-footer a {{ color: #0D6B3B; text-decoration: none; }}
[data-testid="stSidebar"] {{ background: #F5F7F6; }}
[data-testid="stSidebar"] * {{ color: #1A2E21 !important; }}
.stAlert {{ border-radius: 8px !important; }}
.stSpinner > div {{ border-top-color: #0D6B3B !important; }}
hr {{ border-color: #E8ECE9 !important; }}
@media (max-width: 768px) {{
    .rcjy-header {{ flex-direction: column; text-align: center; }}
    .hero-banner {{ padding: 1.5rem; }}
}}
</style>
""", unsafe_allow_html=True)

_api_ok = bool(get_api_key())
L = T[st.session_state.ui_lang]

st.markdown('<div class="top-bar"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="rcjy-header">
    <img src="{RCJY_LOGO_URL}" alt="RCJY" onerror="this.style.display='none'">
    <div class="title-block">
        <h1>{L['app_name']}</h1>
        <p>{L['dept']}</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="hero-banner">
    <h2>{L['hero_title']}</h2>
    <p>{L['hero_sub']}</p>
</div>
""", unsafe_allow_html=True)

lang_col, out_col, _ = st.columns([1, 1, 3])
with lang_col:
    new_lang = st.selectbox(
        L["lang_label"],
        ["English", "العربية"],
        index=0 if st.session_state.ui_lang == "en" else 1,
        key="lang_sel",
    )
    target = "ar" if new_lang == "العربية" else "en"
    if target != st.session_state.ui_lang:
        st.session_state.ui_lang = target
        st.rerun()

with out_col:
    out_lang = st.selectbox(
        L["output_lang_label"],
        ["English", "العربية"],
        index=0,
        key="output_lang_sel",
    )

lang = "ar" if out_lang == "العربية" else "en"

if not _api_ok:
    st.warning(L["warn_api"])

st.markdown(f'<div class="section-label">{L["prompt_label"]}</div>', unsafe_allow_html=True)

input_text = st.text_area(
    "prompt_main", placeholder=L["prompt_placeholder"],
    height=120, label_visibility="collapsed",
)

col_url, col_files = st.columns([1, 1], gap="medium")
with col_url:
    input_url = st.text_input(L["url_label"], placeholder="https://...")
with col_files:
    input_files = st.file_uploader(L["attach_label"], type=SUPPORTED_FILE_TYPES, accept_multiple_files=True)

if input_files:
    st.caption(f"{L['attached']}: {', '.join(f.name for f in input_files)}")

context_text, attachments = get_content_from_input(text=input_text, url=input_url, files=input_files)
has_context = context_text and context_text != "No content provided."

if has_context:
    st.markdown(
        f'<div class="ctx-pill">{L["context_loaded"]} — {len(context_text):,} {L["chars"]}</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown(f'<div class="section-label">{L["generate_label"]}</div>', unsafe_allow_html=True)

tab_img, tab_vid, tab_voice, tab_pod = st.tabs([
    L["tab_image"], L["tab_video"], L["tab_voice"], L["tab_podcast"],
])

with tab_img:
    st.markdown('<span class="mtag">Imagen 4</span><span class="mtag">Nano Banana</span>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        img_model = st.selectbox(
            L["model_label"],
            ["imagen_fast", "imagen", "imagen_ultra", "nano_banana", "nano_banana_pro"],
            format_func=lambda x: {
                "imagen_fast": "Imagen 4 Fast", "imagen": "Imagen 4 - Flagship",
                "imagen_ultra": "Imagen 4 Ultra", "nano_banana": "Nano Banana",
                "nano_banana_pro": "Nano Banana Pro - 4K",
            }[x],
            key="img_model",
        )
    with c2:
        img_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16", "1:1", "4:3", "3:4"], key="img_aspect")

    if st.button(L["btn_image"], use_container_width=True, key="btn_img"):
        prompt = input_text.strip()
        if not prompt:
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_image"]):
                try:
                    data, mime = generate_image(
                        prompt=prompt, context_text=context_text if has_context else "",
                        files=input_files, model=img_model, aspect_ratio=img_aspect, lang=lang,
                    )
                    st.session_state.result_image = (data, mime)
                except Exception as e:
                    logger.exception("Image generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_image:
        img_data, img_mime = st.session_state.result_image
        st.image(img_data, use_container_width=True)
        st.download_button(L["btn_download"], data=img_data, file_name="rcjy_image.png", mime="image/png", key="dl_img")

with tab_vid:
    st.markdown('<span class="mtag">Veo 3.1</span>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        vid_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16"], key="vid_aspect")
    with c2:
        vid_dur = st.selectbox(L["duration_label"], ["4", "6", "8"], index=2, key="vid_dur")

    if st.button(L["btn_video"], use_container_width=True, key="btn_vid"):
        prompt = input_text.strip()
        if not prompt:
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_video"]):
                try:
                    data, mime = generate_video(
                        prompt=prompt, context_text=context_text if has_context else "",
                        aspect_ratio=vid_aspect, duration=vid_dur, lang=lang,
                    )
                    st.session_state.result_video = (data, mime)
                except Exception as e:
                    logger.exception("Video generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_video:
        vid_data, vid_mime = st.session_state.result_video
        st.video(vid_data)
        st.download_button(L["btn_download"], data=vid_data, file_name="rcjy_video.mp4", mime="video/mp4", key="dl_vid")

with tab_voice:
    st.markdown('<span class="mtag">Gemini TTS</span><span class="mtag">Chirp 3</span>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        voice_name = st.selectbox(
            L["voice_label"],
            ["Kore", "Puck", "Zephyr", "Charon", "Fenrir", "Aoede", "Leda", "Orus", "Perseus", "Schedar"],
            key="voice_name",
        )
    with c2:
        tts_quality = st.selectbox(L["quality_label"], ["Flash", "Pro"], key="tts_q")
    with c3:
        style_hint = st.text_input(L["style_label"], placeholder=L["style_placeholder"], key="voice_style")

    st.caption(L["voice_note"])
    tts_override = st.text_area(
        "tts_override", value="", placeholder=L["tts_placeholder"],
        height=80, label_visibility="collapsed", key="tts_text",
    )

    if st.button(L["btn_voice"], use_container_width=True, key="btn_voice"):
        speak_text = tts_override.strip() or input_text.strip()
        if not speak_text:
            st.warning(L["warn_text"])
        else:
            with st.spinner(L["spin_voice"]):
                try:
                    data, mime = generate_voice(
                        text=speak_text, context_text="", voice_name=voice_name,
                        style_hint=style_hint, tts_model="pro" if tts_quality == "Pro" else "flash",
                        lang=lang,
                    )
                    st.session_state.result_voice = (data, mime)
                except Exception as e:
                    logger.exception("Voice generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_voice:
        voice_data, voice_mime = st.session_state.result_voice
        st.audio(voice_data, format="audio/wav")
        st.download_button(L["btn_download"], data=voice_data, file_name="rcjy_voice.wav", mime="audio/wav", key="dl_voice")

with tab_pod:
    st.markdown('<span class="mtag">Gemini 3 Flash</span><span class="mtag">Multi-Speaker TTS</span>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        _pod_options = [L["length_short"], L["length_standard"]]
        pod_len_idx = st.selectbox(
            L["length_label"], range(len(_pod_options)),
            format_func=lambda i: _pod_options[i], key="pod_len",
        )
    _voice_options = {
        "Kore (♀)": "Kore",
        "Aoede (♀)": "Aoede",
        "Leda (♀)": "Leda",
        "Puck (♂)": "Puck",
        "Charon (♂)": "Charon",
        "Fenrir (♂)": "Fenrir",
        "Orus (♂)": "Orus",
    }
    _voice_labels = list(_voice_options.keys())
    with c2:
        host_label = st.selectbox(L["host_label"], _voice_labels, index=0, key="pod_host")
        pod_host = _voice_options[host_label]
    with c3:
        guest_label = st.selectbox(L["guest_label"], _voice_labels, index=3, key="pod_guest")
        pod_guest = _voice_options[guest_label]

    if st.button(L["btn_podcast"], use_container_width=True, key="btn_pod"):
        prompt = input_text.strip()
        if not prompt and not has_context:
            st.warning(L["warn_topic"])
        else:
            with st.spinner(L["spin_podcast"]):
                try:
                    data, mime = generate_podcast(
                        prompt=prompt or ("ناقش المحتوى المقدّم" if lang == "ar" else "Discuss the provided content"),
                        context_text=context_text if has_context else "",
                        url=input_url or "", files=input_files,
                        length="short" if pod_len_idx == 0 else "standard",
                        voice_host=pod_host, voice_guest=pod_guest,
                        lang=lang,
                    )
                    st.session_state.result_podcast = (data, mime)
                except Exception as e:
                    logger.exception("Podcast generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_podcast:
        pod_data, pod_mime = st.session_state.result_podcast
        st.audio(pod_data, format="audio/wav")
        st.download_button(L["btn_download"], data=pod_data, file_name="rcjy_podcast.wav", mime="audio/wav", key="dl_pod")

st.markdown(f"""
<div class="app-footer">
    <strong>{L['footer_org']}</strong><br>
    {L['footer_dept']}<br>
    <span style="font-size:0.68rem; color:#8C9A90;">
        Imagen 4 &bull; Nano Banana &bull; Veo 3.1 &bull; Gemini TTS &bull; Gemini 3 Flash
    </span><br>
    <a href="https://www.rcjy.gov.sa/en/" target="_blank">rcjy.gov.sa</a>
    &bull; &copy; 2026
</div>
""", unsafe_allow_html=True)
