import logging

import streamlit as st

from config import RCJY_LOGO_URL, SUPPORTED_FILE_TYPES, get_api_key
from content_extractor import get_content_from_input
from generators import _sanitize_error, generate_image, generate_podcast, generate_text, generate_video, generate_voice

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
        "dept": "الإدارة العامة للاتصال والإعلام",
        "lang_label": "Interface",
        "output_lang_label": "Output Language",
        "url_label": "Reference URL (optional)",
        "attach_label": "Attach Reference Files",
        "attached": "Attached",
        "context_loaded": "Context loaded",
        "chars": "chars",
        "context_label": "Reference Material (optional)",
        "tab_text": "✍️  Text",
        "tab_image": "🖼️  Image",
        "tab_video": "🎬  Video",
        "tab_voice": "🎙️  Voice",
        "tab_podcast": "🎧  Podcast",
        "prompt_label": "Prompt",
        "prompt_placeholder_text": (
            "Describe the text content you want to create...\n"
            "e.g. Write a press release about Jubail Industrial City's new sustainability initiative"
        ),
        "prompt_placeholder_image": (
            "Describe the image you want to generate...\n"
            "e.g. A professional aerial view of Jubail Industrial City at golden hour"
        ),
        "prompt_placeholder_video": (
            "Describe the video scene to generate...\n"
            "e.g. A cinematic fly-through of Yanbu industrial port at sunrise"
        ),
        "prompt_placeholder_voice": "Enter the text you want converted to speech...",
        "prompt_placeholder_podcast": (
            "Describe the podcast topic...\n"
            "e.g. Economic impact of Jubail and Yanbu on Saudi Vision 2030"
        ),
        "model_label": "Model",
        "aspect_label": "Aspect Ratio",
        "duration_label": "Duration (sec)",
        "voice_label": "Voice",
        "quality_label": "Quality",
        "style_label": "Delivery Style",
        "style_placeholder": "e.g. professional, warm, confident",
        "length_label": "Episode Length",
        "length_short": "Short (4–5 min)",
        "length_standard": "Standard (~10 min)",
        "host_label": "Host Voice",
        "guest_label": "Guest Voice",
        "text_type_label": "Content Type",
        "text_tone_label": "Tone",
        "text_model_label": "Model",
        "text_type_article": "Article / Blog",
        "text_type_social": "Social Media Post",
        "text_type_press": "Press Release",
        "text_type_ad": "Ad Copy",
        "text_type_email": "Email",
        "text_type_script": "Script",
        "text_type_summary": "Summary",
        "text_type_creative": "Creative Writing",
        "text_tone_professional": "Professional",
        "text_tone_friendly": "Friendly",
        "text_tone_formal": "Formal",
        "text_tone_persuasive": "Persuasive",
        "text_tone_informative": "Informative",
        "btn_text": "Generate Text",
        "btn_image": "Generate Image",
        "btn_video": "Generate Video",
        "btn_voice": "Generate Voice",
        "btn_podcast": "Generate Podcast",
        "btn_download": "Download",
        "warn_prompt": "Please enter a prompt.",
        "warn_topic": "Please enter a topic or attach content.",
        "warn_text": "Please enter the text to speak.",
        "warn_api": "API key not configured. Set GEMINI_API_KEY as an environment variable.",
        "spin_text": "Generating text...",
        "spin_image": "Generating image...",
        "spin_video": "Generating video… (2–5 minutes)",
        "spin_voice": "Generating speech...",
        "spin_podcast": "Creating podcast… (2–3 minutes)",
        "footer_org": "Royal Commission for Jubail and Yanbu",
        "footer_dept": "Communication & Media Department",
    },
    "ar": {
        "page_title": "مولّد الوسائط - الهيئة الملكية",
        "app_name": "مولّد الوسائط",
        "dept": "الإدارة العامة للاتصال والإعلام",
        "lang_label": "الواجهة",
        "output_lang_label": "لغة المحتوى",
        "url_label": "رابط مرجعي (اختياري)",
        "attach_label": "إرفاق ملفات مرجعية",
        "attached": "مرفقات",
        "context_loaded": "تم تحميل المحتوى",
        "chars": "حرف",
        "context_label": "مواد مرجعية (اختياري)",
        "tab_text": "✍️  نص",
        "tab_image": "🖼️  صورة",
        "tab_video": "🎬  فيديو",
        "tab_voice": "🎙️  صوت",
        "tab_podcast": "🎧  بودكاست",
        "prompt_label": "الوصف",
        "prompt_placeholder_text": (
            "اكتب وصفاً للمحتوى النصي الذي تريد إنشاءه...\n"
            "مثال: اكتب بياناً صحفياً عن مبادرة الاستدامة الجديدة لمدينة الجبيل الصناعية"
        ),
        "prompt_placeholder_image": (
            "اكتب وصفاً للصورة التي تريد إنشاءها...\n"
            "مثال: منظر جوي احترافي لمدينة الجبيل الصناعية عند الغسق"
        ),
        "prompt_placeholder_video": (
            "اكتب وصفاً لمشهد الفيديو الذي تريد إنشاءه...\n"
            "مثال: مشهد سينمائي لميناء ينبع الصناعي عند الفجر"
        ),
        "prompt_placeholder_voice": "أدخل النص الذي تريد تحويله إلى صوت...",
        "prompt_placeholder_podcast": (
            "اكتب موضوع البودكاست...\n"
            "مثال: الأثر الاقتصادي لمدينتي الجبيل وينبع على رؤية 2030"
        ),
        "model_label": "النموذج",
        "aspect_label": "نسبة العرض إلى الارتفاع",
        "duration_label": "المدة (ثانية)",
        "voice_label": "الصوت",
        "quality_label": "الجودة",
        "style_label": "أسلوب الأداء",
        "style_placeholder": "مثال: رسمي، دافئ، واثق",
        "length_label": "مدة الحلقة",
        "length_short": "قصيرة (٤-٥ دقائق)",
        "length_standard": "عادية (~١٠ دقائق)",
        "host_label": "صوت المقدّم",
        "guest_label": "صوت الضيف",
        "text_type_label": "نوع المحتوى",
        "text_tone_label": "الأسلوب",
        "text_model_label": "النموذج",
        "text_type_article": "مقال / مدونة",
        "text_type_social": "منشور تواصل اجتماعي",
        "text_type_press": "بيان صحفي",
        "text_type_ad": "نص إعلاني",
        "text_type_email": "بريد إلكتروني",
        "text_type_script": "سيناريو",
        "text_type_summary": "ملخص",
        "text_type_creative": "كتابة إبداعية",
        "text_tone_professional": "احترافي",
        "text_tone_friendly": "ودّي",
        "text_tone_formal": "رسمي",
        "text_tone_persuasive": "إقناعي",
        "text_tone_informative": "إعلامي",
        "btn_text": "إنشاء النص",
        "btn_image": "إنشاء الصورة",
        "btn_video": "إنشاء الفيديو",
        "btn_voice": "إنشاء الصوت",
        "btn_podcast": "إنشاء البودكاست",
        "btn_download": "تحميل",
        "warn_prompt": "الرجاء إدخال وصف.",
        "warn_topic": "الرجاء إدخال موضوع أو إرفاق محتوى.",
        "warn_text": "الرجاء إدخال النص للنطق.",
        "warn_api": "لم يتم تعيين مفتاح API. قم بتعيين GEMINI_API_KEY كمتغير بيئة.",
        "spin_text": "جارٍ إنشاء النص...",
        "spin_image": "جارٍ إنشاء الصورة...",
        "spin_video": "جارٍ إنشاء الفيديو... (٢-٥ دقائق)",
        "spin_voice": "جارٍ إنشاء الصوت...",
        "spin_podcast": "جارٍ إنشاء البودكاست... (٢-٣ دقائق)",
        "footer_org": "الهيئة الملكية للجبيل وينبع",
        "footer_dept": "الإدارة العامة للاتصال والإعلام",
    },
}

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RCJY Media Generator",
    page_icon="https://www.rcjy.gov.sa/o/rcjy-theme/images/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Session state init ──────────────────────────────────────────────────────
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "en"
# active_tab persists across reruns (language switch, generate, etc.)
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "text"
for _k in ("result_text", "result_image", "result_video", "result_voice", "result_podcast"):
    if _k not in st.session_state:
        st.session_state[_k] = None

is_ar = st.session_state.ui_lang == "ar"
L = T[st.session_state.ui_lang]
ar_font = "'IBM Plex Sans Arabic', " if is_ar else ""

rtl_extra = """
    .stApp { direction: rtl; text-align: right; }
    .rcjy-logo-area { flex-direction: row-reverse !important; }
    .rcjy-lang-bar { flex-direction: row-reverse; }
    .lbl-row { flex-direction: row-reverse; }
    .lbl-row::before { margin-right: 0; margin-left: 0.5rem; }
    .ctx-pill { flex-direction: row-reverse; }
    div[data-testid="stRadio"] [role="radiogroup"] { direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; }
""" if is_ar else ""

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap');

/* ── BASE ── */
.stApp {{
    background: #F2F7F4;
    font-family: {ar_font}'Inter', -apple-system, sans-serif;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
{rtl_extra}

/* ── DARK HEADER BAR ── */
.rcjy-topbar {{
    background: linear-gradient(135deg, #051D10 0%, #0A3D22 45%, #156843 100%);
    margin: -1rem -1rem 0 -1rem;
    padding: 0;
    position: relative;
    overflow: hidden;
}}
/* Geometric decorative circles — inspired by RCJY logo geometry */
.rcjy-topbar::before {{
    content: '';
    position: absolute;
    top: -60px; right: -40px;
    width: 220px; height: 220px;
    border: 42px solid rgba(201,168,75,0.12);
    border-radius: 50%;
    pointer-events: none;
}}
.rcjy-topbar::after {{
    content: '';
    position: absolute;
    bottom: -50px; right: 120px;
    width: 140px; height: 140px;
    border: 28px solid rgba(255,255,255,0.05);
    border-radius: 50%;
    pointer-events: none;
}}
.rcjy-header-inner {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.1rem 1.5rem;
    position: relative;
    z-index: 1;
}}
.rcjy-logo-area {{
    display: flex;
    align-items: center;
    gap: 1rem;
}}
.rcjy-logo-area img {{
    height: 52px;
    filter: drop-shadow(0 2px 6px rgba(0,0,0,0.3));
}}
.rcjy-logo-area h1 {{
    color: #fff !important;
    font-size: 1.25rem;
    font-weight: 800;
    margin: 0;
    line-height: 1.25;
    letter-spacing: -0.01em;
}}
.rcjy-logo-area p {{
    color: rgba(255,255,255,0.6);
    font-size: 0.75rem;
    margin: 0.1rem 0 0 0;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
/* Gold accent stripe */
.gold-stripe {{
    height: 3px;
    background: linear-gradient(90deg, #B8922A 0%, #E8C96A 40%, #C9A84B 70%, #9A7820 100%);
    margin: 0 -1rem;
}}

/* ── LANG BAR ── */
.rcjy-lang-bar {{
    background: #fff;
    margin: 0 -1rem;
    padding: 0.55rem 1.5rem;
    border-bottom: 1px solid #DCE9E1;
    display: flex;
    align-items: center;
    gap: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}}

/* ── CATEGORY NAV (radio → tabs) ── */
.cat-nav-wrap {{
    background: #fff;
    margin: 0 -1rem;
    padding: 1rem 1.5rem 0.8rem;
    border-bottom: 2px solid #DCE9E1;
    box-shadow: 0 3px 14px rgba(0,0,0,0.05);
    position: sticky;
    top: 0;
    z-index: 100;
}}
/* Hide the radio label (we pass label_visibility="collapsed") */
div[data-testid="stRadio"] > label {{ display: none !important; }}
/* Radio group row */
div[data-testid="stRadio"] [role="radiogroup"] {{
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 10px !important;
    width: 100% !important;
}}
/* Each radio option → card */
div[data-testid="stRadio"] label {{
    flex: 1 1 0 !important;
    background: #F5FAF7 !important;
    border: 2px solid #D8E8DE !important;
    border-radius: 14px !important;
    padding: 14px 8px !important;
    cursor: pointer !important;
    text-align: center !important;
    font-weight: 600 !important;
    font-size: 0.87rem !important;
    color: #3D6B52 !important;
    transition: all 0.18s ease !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: 68px !important;
    line-height: 1.4 !important;
    user-select: none !important;
}}
/* Hide the radio circle dot */
div[data-testid="stRadio"] label > div:first-child {{
    display: none !important;
}}
/* Active tab */
div[data-testid="stRadio"] label:has(input:checked) {{
    background: linear-gradient(145deg, #1B8354 0%, #0A3D22 100%) !important;
    border-color: #1B8354 !important;
    color: #fff !important;
    box-shadow: 0 6px 20px rgba(27,131,84,0.3) !important;
    transform: translateY(-2px) !important;
}}
/* Hover (non-active) */
div[data-testid="stRadio"] label:hover:not(:has(input:checked)) {{
    border-color: #1B8354 !important;
    color: #1B8354 !important;
    background: #EBF7F0 !important;
    transform: translateY(-1px) !important;
}}

/* ── CONTENT CARD ── */
.content-card {{
    background: #fff;
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    margin: 1.2rem 0;
    border: 1px solid #DCE9E1;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
}}

/* ── SECTION LABELS ── */
.lbl-row {{
    display: flex;
    align-items: center;
    gap: 0.45rem;
    color: #0A3D22;
    font-weight: 700;
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 0 0 0.55rem 0;
}}
.lbl-row::before {{
    content: '';
    width: 3px;
    height: 14px;
    background: linear-gradient(180deg, #C9A84B, #E8C96A);
    border-radius: 2px;
    flex-shrink: 0;
}}

/* ── MODEL TAGS ── */
.mtag {{
    display: inline-block;
    background: #EBF5EE;
    color: #156843;
    padding: 0.18rem 0.55rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 700;
    border: 1px solid #C3E0CA;
    margin: 0 3px 6px 0;
    letter-spacing: 0.03em;
}}

/* ── BUTTONS ── */
.stButton > button {{
    background: linear-gradient(135deg, #1B8354 0%, #0A3D22 100%) !important;
    color: #FFF !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.72rem 2rem !important;
    font-size: 0.9rem !important;
    box-shadow: 0 4px 16px rgba(27,131,84,0.28) !important;
    transition: all 0.18s ease !important;
    letter-spacing: 0.02em !important;
}}
.stButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 26px rgba(27,131,84,0.42) !important;
}}
.stDownloadButton > button {{
    background: #0A3D22 !important;
    color: #FFF !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 9px !important;
    letter-spacing: 0.02em !important;
}}

/* ── INPUTS ── */
.stTextArea textarea, .stTextInput input {{
    border-radius: 10px !important;
    border: 1.5px solid #D0D9D4 !important;
    color: #1A2E21 !important;
    background: #FAFCFB !important;
    font-size: 0.92rem !important;
    font-family: {ar_font}'Inter', sans-serif !important;
}}
.stTextArea textarea:focus, .stTextInput input:focus {{
    border-color: #1B8354 !important;
    box-shadow: 0 0 0 3px rgba(27,131,84,0.12) !important;
    background: #fff !important;
}}
.stSelectbox [data-baseweb="select"] {{
    border-radius: 10px !important;
}}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {{
    border: 2px dashed #C5D8CC !important;
    border-radius: 12px !important;
    background: #FAFCFB !important;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: #1B8354 !important;
    background: #EEF8F2 !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] div small,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploader"] section > div:first-child small {{
    display: none !important;
}}

/* ── CONTEXT PILL ── */
.ctx-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: #E6F4EC;
    color: #0A4225;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid #BDE0CA;
}}

/* ── ALERTS / SPINNER ── */
.stAlert {{ border-radius: 10px !important; }}
.stSpinner > div {{ border-top-color: #1B8354 !important; }}
hr {{ border-color: #DCE9E1 !important; }}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {{ background: #F2F7F4; }}
[data-testid="stSidebar"] * {{ color: #1A2E21 !important; }}

/* ── FOOTER ── */
.app-footer {{
    text-align: center;
    padding: 1.5rem 1rem;
    margin-top: 2rem;
    border-top: 1px solid #DCE9E1;
    color: #7A9088;
    font-size: 0.73rem;
    line-height: 1.8;
}}
.app-footer strong {{ color: #1A2E21; }}
.app-footer a {{ color: #1B8354; text-decoration: none; }}

/* ── RESPONSIVE ── */
@media (max-width: 768px) {{
    .rcjy-header-inner {{ flex-direction: column; gap: 0.6rem; }}
    div[data-testid="stRadio"] label {{
        min-height: 54px !important;
        font-size: 0.75rem !important;
        padding: 10px 4px !important;
    }}
    .content-card {{ padding: 1.1rem; }}
}}
</style>
""", unsafe_allow_html=True)

_api_ok = bool(get_api_key())

# ─── HEADER ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="rcjy-topbar">
  <div class="rcjy-header-inner">
    <div class="rcjy-logo-area">
      <img src="{RCJY_LOGO_URL}" alt="RCJY"
           onerror="this.style.display='none'">
      <div>
        <h1>{L['app_name']}</h1>
        <p>{L['dept']}</p>
      </div>
    </div>
  </div>
</div>
<div class="gold-stripe"></div>
""", unsafe_allow_html=True)

# ─── LANGUAGE CONTROLS (compact bar below header) ────────────────────────────
lc1, lc2, lc3 = st.columns([1, 1, 5])
with lc1:
    new_lang = st.selectbox(
        L["lang_label"],
        ["English", "العربية"],
        index=0 if not is_ar else 1,
        key="lang_sel",
        label_visibility="visible",
    )
    target_lang = "ar" if new_lang == "العربية" else "en"
    if target_lang != st.session_state.ui_lang:
        st.session_state.ui_lang = target_lang
        st.rerun()
with lc2:
    out_lang = st.selectbox(
        L["output_lang_label"],
        ["English", "العربية"],
        index=0,
        key="output_lang_sel",
    )

lang = "ar" if out_lang == "العربية" else "en"

if not _api_ok:
    st.warning(L["warn_api"])

# ─── CATEGORY NAVIGATION (sticky, top) ──────────────────────────────────────
st.markdown('<div class="cat-nav-wrap">', unsafe_allow_html=True)

_tab_keys = ["text", "image", "video", "voice", "podcast"]
_tab_labels = {
    "text":    L["tab_text"],
    "image":   L["tab_image"],
    "video":   L["tab_video"],
    "voice":   L["tab_voice"],
    "podcast": L["tab_podcast"],
}

active_tab = st.radio(
    "Category",
    options=_tab_keys,
    format_func=lambda x: _tab_labels[x],
    horizontal=True,
    key="active_tab",          # persists in session_state — no more auto-reset
    label_visibility="collapsed",
)

st.markdown('</div>', unsafe_allow_html=True)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def _ctx_section():
    """Shared context inputs (URL + files). Same keys across tabs → state persists."""
    with st.expander(L["context_label"], expanded=False):
        c_url, c_files = st.columns([1, 1], gap="medium")
        with c_url:
            url = st.text_input(L["url_label"], placeholder="https://...", key="input_url")
        with c_files:
            files = st.file_uploader(
                L["attach_label"],
                type=SUPPORTED_FILE_TYPES,
                accept_multiple_files=True,
                key="input_files",
            )
        if files:
            st.caption(f"{L['attached']}: {', '.join(f.name for f in files)}")
        return url, files


def _resolve_context(url, files, prompt):
    ctx, _ = get_content_from_input(text="", url=url, files=files)
    has_ctx = bool(ctx and ctx != "No content provided.")
    if has_ctx:
        st.markdown(
            f'<div class="ctx-pill">⬡ {L["context_loaded"]} — {len(ctx):,} {L["chars"]}</div>',
            unsafe_allow_html=True,
        )
    return ctx, has_ctx


# ─── TEXT TAB ────────────────────────────────────────────────────────────────
if active_tab == "text":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown('<span class="mtag">Gemini 3 Pro</span><span class="mtag">Gemini 3 Flash</span>', unsafe_allow_html=True)

    _type_map = {
        L["text_type_article"]: "article",
        L["text_type_social"]:  "social",
        L["text_type_press"]:   "press",
        L["text_type_ad"]:      "ad",
        L["text_type_email"]:   "email",
        L["text_type_script"]:  "script",
        L["text_type_summary"]: "summary",
        L["text_type_creative"]:"creative",
    }
    _tone_map = {
        L["text_tone_professional"]: "professional",
        L["text_tone_friendly"]:     "friendly",
        L["text_tone_formal"]:       "formal",
        L["text_tone_persuasive"]:   "persuasive",
        L["text_tone_informative"]:  "informative",
    }

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        text_type_label = st.selectbox(L["text_type_label"], list(_type_map.keys()), key="text_type")
        text_type = _type_map[text_type_label]
    with sc2:
        text_tone_label = st.selectbox(L["text_tone_label"], list(_tone_map.keys()), key="text_tone")
        text_tone = _tone_map[text_tone_label]
    with sc3:
        text_model_sel = st.selectbox(L["text_model_label"], ["Pro", "Flash"], key="text_model")
        text_model = "pro" if text_model_sel == "Pro" else "flash"
    with sc4:
        st.selectbox(L["output_lang_label"], ["English", "العربية"],
                     index=0 if lang == "en" else 1, key="text_outlang_disp",
                     disabled=True, help="Set via Output Language above")

    st.markdown(f'<div class="lbl-row">{L["prompt_label"]}</div>', unsafe_allow_html=True)
    text_prompt = st.text_area(
        "text_prompt_lbl", key="prompt_text",
        placeholder=L["prompt_placeholder_text"],
        height=130, label_visibility="collapsed",
    )

    input_url, input_files = _ctx_section()
    ctx_text, has_ctx = _resolve_context(input_url, input_files, text_prompt)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button(L["btn_text"], use_container_width=True, key="btn_text"):
        prompt = text_prompt.strip()
        if not prompt and not has_ctx:
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_text"]):
                try:
                    result = generate_text(
                        prompt=prompt or "Summarize the provided content",
                        context_text=ctx_text if has_ctx else "",
                        url=input_url or "", files=input_files,
                        text_type=text_type, tone=text_tone,
                        model=text_model, lang=lang,
                    )
                    st.session_state.result_text = result
                except Exception as e:
                    logger.exception("Text generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_text:
        st.markdown(st.session_state.result_text)
        st.download_button(
            L["btn_download"], data=st.session_state.result_text,
            file_name="rcjy_content.txt", mime="text/plain", key="dl_text",
        )

# ─── IMAGE TAB ───────────────────────────────────────────────────────────────
elif active_tab == "image":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown(
        '<span class="mtag">Imagen 4</span>'
        '<span class="mtag">Imagen 4 Ultra</span>'
        '<span class="mtag">Nano Banana</span>',
        unsafe_allow_html=True,
    )

    ic1, ic2 = st.columns(2)
    with ic1:
        img_model = st.selectbox(
            L["model_label"],
            ["imagen_fast", "imagen", "imagen_ultra", "nano_banana", "nano_banana_pro"],
            format_func=lambda x: {
                "imagen_fast":     "Imagen 4 Fast",
                "imagen":          "Imagen 4 Flagship",
                "imagen_ultra":    "Imagen 4 Ultra",
                "nano_banana":     "Nano Banana",
                "nano_banana_pro": "Nano Banana Pro — 4K",
            }[x],
            key="img_model",
        )
    with ic2:
        img_aspect = st.selectbox(
            L["aspect_label"], ["16:9", "9:16", "1:1", "4:3", "3:4"], key="img_aspect"
        )

    st.markdown(f'<div class="lbl-row">{L["prompt_label"]}</div>', unsafe_allow_html=True)
    img_prompt = st.text_area(
        "img_prompt_lbl", key="prompt_image",
        placeholder=L["prompt_placeholder_image"],
        height=130, label_visibility="collapsed",
    )

    input_url, input_files = _ctx_section()
    ctx_text, has_ctx = _resolve_context(input_url, input_files, img_prompt)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button(L["btn_image"], use_container_width=True, key="btn_img"):
        prompt = img_prompt.strip()
        if not prompt:
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_image"]):
                try:
                    data, mime = generate_image(
                        prompt=prompt,
                        context_text=ctx_text if has_ctx else "",
                        files=input_files, model=img_model,
                        aspect_ratio=img_aspect, lang=lang,
                    )
                    st.session_state.result_image = (data, mime)
                except Exception as e:
                    logger.exception("Image generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_image:
        img_data, img_mime = st.session_state.result_image
        st.image(img_data, use_container_width=True)
        st.download_button(
            L["btn_download"], data=img_data,
            file_name="rcjy_image.png", mime="image/png", key="dl_img",
        )

# ─── VIDEO TAB ───────────────────────────────────────────────────────────────
elif active_tab == "video":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown('<span class="mtag">Veo 3.1</span>', unsafe_allow_html=True)

    vc1, vc2 = st.columns(2)
    with vc1:
        vid_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16"], key="vid_aspect")
    with vc2:
        vid_dur = st.selectbox(L["duration_label"], ["4", "6", "8"], index=2, key="vid_dur")

    st.markdown(f'<div class="lbl-row">{L["prompt_label"]}</div>', unsafe_allow_html=True)
    vid_prompt = st.text_area(
        "vid_prompt_lbl", key="prompt_video",
        placeholder=L["prompt_placeholder_video"],
        height=130, label_visibility="collapsed",
    )

    input_url, input_files = _ctx_section()
    ctx_text, has_ctx = _resolve_context(input_url, input_files, vid_prompt)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button(L["btn_video"], use_container_width=True, key="btn_vid"):
        prompt = vid_prompt.strip()
        if not prompt:
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_video"]):
                try:
                    data, mime = generate_video(
                        prompt=prompt,
                        context_text=ctx_text if has_ctx else "",
                        aspect_ratio=vid_aspect, duration=vid_dur, lang=lang,
                    )
                    st.session_state.result_video = (data, mime)
                except Exception as e:
                    logger.exception("Video generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_video:
        vid_data, vid_mime = st.session_state.result_video
        st.video(vid_data)
        st.download_button(
            L["btn_download"], data=vid_data,
            file_name="rcjy_video.mp4", mime="video/mp4", key="dl_vid",
        )

# ─── VOICE TAB ───────────────────────────────────────────────────────────────
elif active_tab == "voice":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown(
        '<span class="mtag">Gemini TTS Pro</span>'
        '<span class="mtag">Gemini TTS Flash</span>'
        '<span class="mtag">Chirp 3</span>',
        unsafe_allow_html=True,
    )

    voc1, voc2, voc3 = st.columns(3)
    with voc1:
        voice_name = st.selectbox(
            L["voice_label"],
            ["Kore", "Puck", "Zephyr", "Charon", "Fenrir", "Aoede", "Leda", "Orus", "Perseus", "Schedar"],
            key="voice_name",
        )
    with voc2:
        tts_quality = st.selectbox(L["quality_label"], ["Flash", "Pro"], key="tts_q")
    with voc3:
        style_hint = st.text_input(
            L["style_label"], placeholder=L["style_placeholder"], key="voice_style"
        )

    # Single prompt — no duplicate textarea
    st.markdown(f'<div class="lbl-row">{L["prompt_label"]}</div>', unsafe_allow_html=True)
    voice_prompt = st.text_area(
        "voice_prompt_lbl", key="prompt_voice",
        placeholder=L["prompt_placeholder_voice"],
        height=160, label_visibility="collapsed",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button(L["btn_voice"], use_container_width=True, key="btn_voice"):
        speak_text = voice_prompt.strip()
        if not speak_text:
            st.warning(L["warn_text"])
        else:
            with st.spinner(L["spin_voice"]):
                try:
                    data, mime = generate_voice(
                        text=speak_text, context_text="",
                        voice_name=voice_name, style_hint=style_hint,
                        tts_model="pro" if tts_quality == "Pro" else "flash",
                        lang=lang,
                    )
                    st.session_state.result_voice = (data, mime)
                except Exception as e:
                    logger.exception("Voice generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_voice:
        voice_data, voice_mime = st.session_state.result_voice
        st.audio(voice_data, format="audio/wav")
        st.download_button(
            L["btn_download"], data=voice_data,
            file_name="rcjy_voice.wav", mime="audio/wav", key="dl_voice",
        )

# ─── PODCAST TAB ─────────────────────────────────────────────────────────────
elif active_tab == "podcast":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown(
        '<span class="mtag">Gemini 3 Flash</span>'
        '<span class="mtag">Multi-Speaker TTS</span>',
        unsafe_allow_html=True,
    )

    _pod_options = [L["length_short"], L["length_standard"]]
    _voice_options = {
        "Kore (♀)":  "Kore",
        "Aoede (♀)": "Aoede",
        "Leda (♀)":  "Leda",
        "Puck (♂)":  "Puck",
        "Charon (♂)":"Charon",
        "Fenrir (♂)":"Fenrir",
        "Orus (♂)":  "Orus",
    }
    _voice_labels = list(_voice_options.keys())

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        pod_len_idx = st.selectbox(
            L["length_label"],
            range(len(_pod_options)),
            format_func=lambda i: _pod_options[i],
            key="pod_len",
        )
    with pc2:
        host_label = st.selectbox(L["host_label"], _voice_labels, index=0, key="pod_host")
        pod_host = _voice_options[host_label]
    with pc3:
        guest_label = st.selectbox(L["guest_label"], _voice_labels, index=3, key="pod_guest")
        pod_guest = _voice_options[guest_label]

    st.markdown(f'<div class="lbl-row">{L["prompt_label"]}</div>', unsafe_allow_html=True)
    pod_prompt = st.text_area(
        "pod_prompt_lbl", key="prompt_podcast",
        placeholder=L["prompt_placeholder_podcast"],
        height=130, label_visibility="collapsed",
    )

    input_url, input_files = _ctx_section()
    ctx_text, has_ctx = _resolve_context(input_url, input_files, pod_prompt)

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button(L["btn_podcast"], use_container_width=True, key="btn_pod"):
        prompt = pod_prompt.strip()
        if not prompt and not has_ctx:
            st.warning(L["warn_topic"])
        else:
            with st.spinner(L["spin_podcast"]):
                try:
                    data, mime = generate_podcast(
                        prompt=prompt or ("ناقش المحتوى المقدّم" if lang == "ar" else "Discuss the provided content"),
                        context_text=ctx_text if has_ctx else "",
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
        st.download_button(
            L["btn_download"], data=pod_data,
            file_name="rcjy_podcast.wav", mime="audio/wav", key="dl_pod",
        )

# ─── FOOTER ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-footer">
    <strong>{L['footer_org']}</strong><br>
    {L['footer_dept']}<br>
    <span style="font-size:0.68rem; color:#9AADA4;">
        Gemini 3 Pro &bull; Imagen 4 &bull; Nano Banana &bull; Veo 3.1
        &bull; Gemini TTS &bull; Gemini 3 Flash
    </span><br>
    <a href="https://www.rcjy.gov.sa/en/" target="_blank">rcjy.gov.sa</a>
    &nbsp;&bull;&nbsp; &copy; 2026
</div>
""", unsafe_allow_html=True)
