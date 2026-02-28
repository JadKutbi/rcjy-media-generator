import logging

import streamlit as st

from config import RCJY_LOGO_URL, SUPPORTED_FILE_TYPES, get_api_key
from content_extractor import get_content_from_input
from generators import (
    _sanitize_error,
    generate_image,
    generate_podcast,
    generate_text,
    generate_video,
    generate_voice,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rcjy.app")

# ─── Translations ────────────────────────────────────────────────────────────
T = {
    "en": {
        "page_title":             "RCJY Media Generator",
        "app_name":               "Media Generator",
        "dept":                   "الإدارة العامة للاتصال والإعلام",
        "lang_label":             "Interface",
        "output_lang_label":      "Output Language",
        "url_label":              "Reference URL",
        "url_placeholder":        "https://example.com/article",
        "attach_label":           "Upload Reference Files",
        "attached":               "Attached",
        "context_loaded":         "Context loaded",
        "chars":                  "chars",
        "context_label":          "Reference Material",
        "context_hint":           "Attach URLs or files to give the AI extra context.",
        # Tab labels — newline makes emoji sit above text in the card
        "tab_text":               "✍️\nText",
        "tab_image":              "🖼️\nImage",
        "tab_video":              "🎬\nVideo",
        "tab_voice":              "🎙️\nVoice",
        "tab_podcast":            "🎧\nPodcast",
        # Prompts
        "prompt_label":           "Prompt",
        "prompt_ph_text":         "Describe the content you want to create…\ne.g. Write a press release about Jubail Industrial City's new green hydrogen plant.",
        "prompt_ph_image":        "Describe the image to generate…\ne.g. Aerial golden-hour view of Jubail Industrial City with petrochemical towers and the sea.",
        "prompt_ph_video":        "Describe the video scene…\ne.g. Cinematic drone flight over Yanbu Industrial Port at sunrise, calm sea, dramatic sky.",
        "prompt_ph_voice":        "Enter the text you want spoken aloud…",
        "prompt_ph_podcast":      "Describe the podcast topic…\ne.g. The economic transformation of Jubail and Yanbu and their role in Saudi Vision 2030.",
        # Settings
        "model_label":            "Model",
        "aspect_label":           "Aspect Ratio",
        "duration_label":         "Duration (sec)",
        "voice_label":            "Voice",
        "quality_label":          "Quality",
        "style_label":            "Delivery Style",
        "style_placeholder":      "e.g. professional, warm, authoritative",
        "length_label":           "Episode Length",
        "length_short":           "Short — 4–5 min",
        "length_standard":        "Standard — ~10 min",
        "host_label":             "Host Voice",
        "guest_label":            "Guest Voice",
        "text_type_label":        "Content Type",
        "text_tone_label":        "Tone",
        "text_model_label":       "Model",
        "text_type_article":      "Article / Blog",
        "text_type_social":       "Social Media",
        "text_type_press":        "Press Release",
        "text_type_ad":           "Ad Copy",
        "text_type_email":        "Email",
        "text_type_script":       "Script",
        "text_type_summary":      "Summary",
        "text_type_creative":     "Creative Writing",
        "text_tone_professional": "Professional",
        "text_tone_friendly":     "Friendly",
        "text_tone_formal":       "Formal",
        "text_tone_persuasive":   "Persuasive",
        "text_tone_informative":  "Informative",
        # Buttons
        "btn_text":               "Generate Text",
        "btn_image":              "Generate Image",
        "btn_video":              "Generate Video",
        "btn_voice":              "Generate Voice",
        "btn_podcast":            "Generate Podcast",
        "btn_download":           "Download",
        # Warnings / spinners
        "warn_prompt":            "Please enter a prompt before generating.",
        "warn_topic":             "Please enter a topic or attach reference content.",
        "warn_text":              "Please enter the text you want spoken.",
        "warn_api":               "API key not configured — set GEMINI_API_KEY as an environment variable.",
        "spin_text":              "Generating text…",
        "spin_image":             "Generating image…",
        "spin_video":             "Generating video… this may take 2–5 minutes",
        "spin_voice":             "Generating speech…",
        "spin_podcast":           "Creating podcast… this may take 2–3 minutes",
        # Footer
        "footer_org":             "Royal Commission for Jubail and Yanbu",
        "footer_dept":            "Communication & Media Department",
        "footer_powered":         "Powered by",
    },
    "ar": {
        "page_title":             "مولّد الوسائط - الهيئة الملكية",
        "app_name":               "مولّد الوسائط",
        "dept":                   "الإدارة العامة للاتصال والإعلام",
        "lang_label":             "الواجهة",
        "output_lang_label":      "لغة المحتوى",
        "url_label":              "رابط مرجعي",
        "url_placeholder":        "https://example.com/article",
        "attach_label":           "رفع ملفات مرجعية",
        "attached":               "مرفقات",
        "context_loaded":         "تم تحميل المحتوى",
        "chars":                  "حرف",
        "context_label":          "مواد مرجعية",
        "context_hint":           "أرفق روابط أو ملفات لإعطاء الذكاء الاصطناعي سياقاً إضافياً.",
        "tab_text":               "✍️\nنص",
        "tab_image":              "🖼️\nصورة",
        "tab_video":              "🎬\nفيديو",
        "tab_voice":              "🎙️\nصوت",
        "tab_podcast":            "🎧\nبودكاست",
        "prompt_label":           "الوصف",
        "prompt_ph_text":         "اكتب وصفاً للمحتوى الذي تريد إنشاءه…\nمثال: اكتب بياناً صحفياً عن مصنع الهيدروجين الأخضر الجديد في الجبيل.",
        "prompt_ph_image":        "اكتب وصفاً للصورة التي تريد إنشاءها…\nمثال: منظر جوي لمدينة الجبيل الصناعية عند الغسق مع أبراج البتروكيماويات والبحر.",
        "prompt_ph_video":        "اكتب وصفاً لمشهد الفيديو…\nمثال: تحليق سينمائي بطائرة مسيّرة فوق ميناء ينبع الصناعي عند الفجر، بحر هادئ، سماء درامية.",
        "prompt_ph_voice":        "أدخل النص الذي تريد تحويله إلى صوت…",
        "prompt_ph_podcast":      "اكتب موضوع البودكاست…\nمثال: التحول الاقتصادي لمدينتي الجبيل وينبع ودورهما في رؤية 2030.",
        "model_label":            "النموذج",
        "aspect_label":           "نسبة الأبعاد",
        "duration_label":         "المدة (ثانية)",
        "voice_label":            "الصوت",
        "quality_label":          "الجودة",
        "style_label":            "أسلوب الأداء",
        "style_placeholder":      "مثال: رسمي، دافئ، موثوق",
        "length_label":           "مدة الحلقة",
        "length_short":           "قصيرة — ٤-٥ دقائق",
        "length_standard":        "عادية — ~١٠ دقائق",
        "host_label":             "صوت المقدّم",
        "guest_label":            "صوت الضيف",
        "text_type_label":        "نوع المحتوى",
        "text_tone_label":        "الأسلوب",
        "text_model_label":       "النموذج",
        "text_type_article":      "مقال / مدونة",
        "text_type_social":       "منشور تواصل اجتماعي",
        "text_type_press":        "بيان صحفي",
        "text_type_ad":           "نص إعلاني",
        "text_type_email":        "بريد إلكتروني",
        "text_type_script":       "سيناريو",
        "text_type_summary":      "ملخص",
        "text_type_creative":     "كتابة إبداعية",
        "text_tone_professional": "احترافي",
        "text_tone_friendly":     "ودّي",
        "text_tone_formal":       "رسمي",
        "text_tone_persuasive":   "إقناعي",
        "text_tone_informative":  "إعلامي",
        "btn_text":               "إنشاء النص",
        "btn_image":              "إنشاء الصورة",
        "btn_video":              "إنشاء الفيديو",
        "btn_voice":              "إنشاء الصوت",
        "btn_podcast":            "إنشاء البودكاست",
        "btn_download":           "تحميل",
        "warn_prompt":            "الرجاء إدخال وصف قبل الإنشاء.",
        "warn_topic":             "الرجاء إدخال موضوع أو إرفاق محتوى مرجعي.",
        "warn_text":              "الرجاء إدخال النص للنطق.",
        "warn_api":               "مفتاح API غير مضبوط — أضف GEMINI_API_KEY كمتغير بيئة.",
        "spin_text":              "جارٍ إنشاء النص…",
        "spin_image":             "جارٍ إنشاء الصورة…",
        "spin_video":             "جارٍ إنشاء الفيديو… قد يستغرق ٢-٥ دقائق",
        "spin_voice":             "جارٍ إنشاء الصوت…",
        "spin_podcast":           "جارٍ إنشاء البودكاست… قد يستغرق ٢-٣ دقائق",
        "footer_org":             "الهيئة الملكية للجبيل وينبع",
        "footer_dept":            "الإدارة العامة للاتصال والإعلام",
        "footer_powered":         "مدعوم بـ",
    },
}

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RCJY Media Generator",
    page_icon="https://www.rcjy.gov.sa/o/rcjy-theme/images/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Session state ────────────────────────────────────────────────────────────
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "en"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "text"
for _k in ("result_text", "result_image", "result_video", "result_voice", "result_podcast"):
    if _k not in st.session_state:
        st.session_state[_k] = None

is_ar   = st.session_state.ui_lang == "ar"
L       = T[st.session_state.ui_lang]
_api_ok = bool(get_api_key())

# IBM Plex Sans covers both Latin and Arabic weights perfectly
_fonts = (
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;"
    "0,500;0,600;0,700;1,400&family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap"
)

# RTL overrides — applied only for Arabic
_rtl = """
  .stApp                         { direction: rtl; text-align: right; }
  .hdr-inner                     { flex-direction: row-reverse; }
  .lang-bar-inner                { flex-direction: row-reverse; }
  .settings-row                  { direction: rtl; }
  .section-head                  { flex-direction: row-reverse; }
  .section-head::before          { margin-right: 0; margin-left: .5rem; }
  .ctx-badge                     { flex-direction: row-reverse; }
  div[data-testid="stRadio"] [role="radiogroup"] { direction: rtl; }
  .stTabs [data-baseweb="tab-list"]              { direction: rtl; }
  .stSelectbox label, .stTextArea label, .stTextInput label { direction: rtl; }
""" if is_ar else ""

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('{_fonts}');

/* ════════════════════════════════════════════════════════
   DESIGN TOKENS
   ════════════════════════════════════════════════════════ */
:root {{
  --c-primary:       #1B8354;
  --c-primary-dk:    #14573A;
  --c-primary-xdk:   #051912;
  --c-gold:          #C8A84B;
  --c-gold-lt:       #E8C87A;
  --c-text:          #0D121C;
  --c-text-sec:      #4B5563;
  --c-text-muted:    #6C737F;
  --c-border:        #D2D6DB;
  --c-border-lt:     #E5E7EB;
  --c-bg:            #F3F4F6;
  --c-surface:       #FFFFFF;
  --c-surface-alt:   #F8FAFB;
  --font:            'IBM Plex Sans', 'IBM Plex Sans Arabic', system-ui, sans-serif;
  --radius-sm:       8px;
  --radius-md:       12px;
  --radius-lg:       16px;
  --radius-xl:       20px;
  --shadow-sm:       0 1px 4px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md:       0 4px 16px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
  --shadow-lg:       0 12px 40px rgba(0,0,0,.10), 0 4px 8px rgba(0,0,0,.04);
  --shadow-green:    0 6px 24px rgba(27,131,84,.28);
  --transition:      all .2s cubic-bezier(.4,0,.2,1);
}}

/* ════════════════════════════════════════════════════════
   BASE
   ════════════════════════════════════════════════════════ */
html, body, .stApp {{
  font-family: var(--font) !important;
  font-size: 15px;
  line-height: 1.6;
  color: var(--c-text);
  background: var(--c-bg) !important;
  -webkit-font-smoothing: antialiased;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
{_rtl}

/* ════════════════════════════════════════════════════════
   HEADER — dark geometric band
   ════════════════════════════════════════════════════════ */
.rcjy-hdr {{
  background:
    radial-gradient(ellipse 60% 120% at 92% 50%, rgba(27,131,84,.22) 0%, transparent 65%),
    radial-gradient(ellipse 35% 80% at 78% 10%, rgba(200,168,75,.13) 0%, transparent 55%),
    linear-gradient(135deg, #030F07 0%, #062715 35%, #0A3A1E 70%, #0E4825 100%);
  margin: -1rem -1rem 0 -1rem;
  position: relative;
  overflow: hidden;
}}
/* Geometric SVG decoration — RCJY logo motif: nested rings + dot grid */
.rcjy-hdr::before {{
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle, rgba(255,255,255,.07) 1.5px, transparent 1.5px),
    radial-gradient(circle, rgba(255,255,255,.04) 1px, transparent 1px);
  background-size: 28px 28px, 14px 14px;
  background-position: 0 0, 7px 7px;
  pointer-events: none;
}}
.hdr-inner {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 2rem;
  position: relative;
  z-index: 1;
  gap: 1.5rem;
}}
.hdr-logo {{
  display: flex;
  align-items: center;
  gap: 1rem;
  text-decoration: none;
  flex-shrink: 0;
}}
.hdr-logo img {{
  height: 56px;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,.4));
}}
.hdr-logo-text h1 {{
  color: #fff !important;
  font-size: 1.375rem !important;
  font-weight: 700 !important;
  letter-spacing: -.015em;
  line-height: 1.2;
  margin: 0 !important;
}}
.hdr-logo-text p {{
  color: rgba(255,255,255,.55);
  font-size: .8rem;
  margin: .15rem 0 0;
  letter-spacing: .06em;
  text-transform: uppercase;
  font-weight: 400;
}}
/* Concentric-ring SVG decoration (right side of header) */
.hdr-rings {{
  position: absolute;
  right: 0; top: 50%;
  transform: translateY(-50%);
  opacity: .55;
  pointer-events: none;
}}
/* Gold accent bar under header */
.gold-bar {{
  height: 3px;
  background: linear-gradient(90deg,
    var(--c-primary-xdk) 0%,
    var(--c-gold) 30%,
    var(--c-gold-lt) 55%,
    var(--c-gold) 75%,
    var(--c-primary-xdk) 100%);
  margin: 0 -1rem;
}}

/* ════════════════════════════════════════════════════════
   LANGUAGE CONTROLS
   ════════════════════════════════════════════════════════ */
.lang-bar-inner {{
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: .6rem 0;
}}
/* Make selectbox labels smaller / quieter */
.lang-bar-inner .stSelectbox label {{
  font-size: .75rem !important;
  font-weight: 600 !important;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--c-text-muted) !important;
}}

/* ════════════════════════════════════════════════════════
   CATEGORY NAV — styled st.radio as premium tab cards
   ════════════════════════════════════════════════════════ */
.cat-nav {{
  background: var(--c-surface);
  margin: .75rem -1rem 0;
  padding: 1rem 2rem .75rem;
  border-bottom: 1px solid var(--c-border-lt);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 200;
}}
/* Suppress default radio label above group */
div[data-testid="stRadio"] > label {{
  display: none !important;
}}
/* The flex row of radio items */
div[data-testid="stRadio"] [role="radiogroup"] {{
  display: flex !important;
  flex-direction: row !important;
  gap: 10px !important;
  width: 100% !important;
}}
/* Each radio item → tab card */
div[data-testid="stRadio"] label {{
  flex: 1 1 0 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 4px !important;
  min-height: 80px !important;
  padding: 12px 8px !important;
  background: var(--c-surface-alt) !important;
  border: 1.5px solid var(--c-border) !important;
  border-radius: var(--radius-lg) !important;
  cursor: pointer !important;
  text-align: center !important;
  font-family: var(--font) !important;
  font-size: .875rem !important;
  font-weight: 600 !important;
  color: var(--c-text-sec) !important;
  letter-spacing: .01em;
  white-space: pre-line !important;
  line-height: 1.35 !important;
  transition: var(--transition) !important;
  user-select: none !important;
  -webkit-user-select: none !important;
}}
/* Hide radio circle dot */
div[data-testid="stRadio"] label > div:first-child {{
  display: none !important;
}}
/* ── Active tab card ── */
div[data-testid="stRadio"] label:has(input:checked) {{
  background: linear-gradient(145deg, #1B8354 0%, #0D5234 55%, #062C1C 100%) !important;
  border-color: var(--c-primary) !important;
  color: #fff !important;
  box-shadow: 0 8px 28px rgba(27,131,84,.35), 0 2px 6px rgba(27,131,84,.2) !important;
  transform: translateY(-3px) !important;
}}
/* ── Hover (inactive) ── */
div[data-testid="stRadio"] label:hover:not(:has(input:checked)) {{
  background: #EBF5EE !important;
  border-color: var(--c-primary) !important;
  color: var(--c-primary-dk) !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--shadow-sm) !important;
}}

/* ════════════════════════════════════════════════════════
   CONTENT CARD
   ════════════════════════════════════════════════════════ */
.content-card {{
  background: var(--c-surface);
  border: 1px solid var(--c-border-lt);
  border-radius: var(--radius-xl);
  padding: 1.75rem 2rem;
  margin: 1.25rem 0 .75rem;
  box-shadow: var(--shadow-md);
}}

/* ════════════════════════════════════════════════════════
   SETTINGS STRIP inside content card
   ════════════════════════════════════════════════════════ */
.settings-strip {{
  background: var(--c-surface-alt);
  border: 1px solid var(--c-border-lt);
  border-radius: var(--radius-md);
  padding: .9rem 1.1rem 1rem;
  margin-bottom: 1.25rem;
}}

/* ════════════════════════════════════════════════════════
   MODEL TAGS
   ════════════════════════════════════════════════════════ */
.model-tags {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 1.1rem;
}}
.mtag {{
  display: inline-flex;
  align-items: center;
  background: #EBF5EE;
  color: var(--c-primary-dk);
  border: 1px solid #C3E0CA;
  border-radius: 6px;
  padding: .22rem .65rem;
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
}}

/* ════════════════════════════════════════════════════════
   SECTION HEADINGS
   ════════════════════════════════════════════════════════ */
.section-head {{
  display: flex;
  align-items: center;
  gap: .45rem;
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--c-text-muted);
  margin: 0 0 .55rem;
}}
.section-head::before {{
  content: '';
  display: inline-block;
  width: 3px;
  height: 13px;
  background: linear-gradient(180deg, var(--c-gold) 0%, var(--c-gold-lt) 100%);
  border-radius: 2px;
  flex-shrink: 0;
}}

/* ════════════════════════════════════════════════════════
   TYPOGRAPHY — Streamlit overrides
   ════════════════════════════════════════════════════════ */
/* Selectbox labels */
.stSelectbox label {{
  font-size: .78rem !important;
  font-weight: 600 !important;
  letter-spacing: .05em !important;
  text-transform: uppercase !important;
  color: var(--c-text-muted) !important;
  margin-bottom: .2rem !important;
}}
/* Text area & input labels */
.stTextArea label, .stTextInput label {{
  font-size: .78rem !important;
  font-weight: 600 !important;
  letter-spacing: .05em !important;
  text-transform: uppercase !important;
  color: var(--c-text-muted) !important;
}}
/* Captions */
.stCaption, [data-testid="stCaptionContainer"] {{
  font-size: .8rem !important;
  color: var(--c-text-muted) !important;
}}

/* ════════════════════════════════════════════════════════
   INPUTS
   ════════════════════════════════════════════════════════ */
.stTextArea textarea, .stTextInput input {{
  font-family: var(--font) !important;
  font-size: .9375rem !important;
  font-weight: 400 !important;
  line-height: 1.65 !important;
  color: var(--c-text) !important;
  background: var(--c-surface) !important;
  border: 1.5px solid var(--c-border) !important;
  border-radius: var(--radius-md) !important;
  padding: .75rem 1rem !important;
  transition: var(--transition) !important;
  caret-color: var(--c-primary);
}}
.stTextArea textarea:focus, .stTextInput input:focus {{
  border-color: var(--c-primary) !important;
  box-shadow: 0 0 0 3px rgba(27,131,84,.12) !important;
  outline: none !important;
  background: var(--c-surface) !important;
}}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {{
  color: #9DA4AE !important;
  font-weight: 400 !important;
}}

/* Selectbox */
.stSelectbox [data-baseweb="select"] > div {{
  font-family: var(--font) !important;
  font-size: .9rem !important;
  font-weight: 500 !important;
  border: 1.5px solid var(--c-border) !important;
  border-radius: var(--radius-md) !important;
  background: var(--c-surface) !important;
  color: var(--c-text) !important;
  transition: var(--transition) !important;
}}
.stSelectbox [data-baseweb="select"]:focus-within > div {{
  border-color: var(--c-primary) !important;
  box-shadow: 0 0 0 3px rgba(27,131,84,.12) !important;
}}

/* ════════════════════════════════════════════════════════
   FILE UPLOADER
   ════════════════════════════════════════════════════════ */
[data-testid="stFileUploader"] {{
  border: 2px dashed var(--c-border) !important;
  border-radius: var(--radius-md) !important;
  background: var(--c-surface-alt) !important;
  transition: var(--transition) !important;
}}
[data-testid="stFileUploader"]:hover {{
  border-color: var(--c-primary) !important;
  background: #EBF5EE !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] div small,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploader"] section > div:first-child small {{
  display: none !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] div {{
  font-size: .85rem !important;
  font-weight: 500 !important;
  color: var(--c-text-sec) !important;
}}

/* ════════════════════════════════════════════════════════
   GENERATE BUTTON
   ════════════════════════════════════════════════════════ */
.stButton > button {{
  font-family: var(--font) !important;
  font-size: .9375rem !important;
  font-weight: 700 !important;
  letter-spacing: .02em !important;
  color: #fff !important;
  background: linear-gradient(135deg, #1B8354 0%, #0E5233 60%, #062C1C 100%) !important;
  border: none !important;
  border-radius: var(--radius-md) !important;
  padding: .85rem 2.5rem !important;
  height: auto !important;
  min-height: 52px !important;
  box-shadow: 0 4px 18px rgba(27,131,84,.30), 0 1px 4px rgba(0,0,0,.12) !important;
  transition: var(--transition) !important;
  cursor: pointer !important;
}}
.stButton > button:hover {{
  background: linear-gradient(135deg, #1E9460 0%, #115C3A 60%, #062C1C 100%) !important;
  box-shadow: 0 8px 30px rgba(27,131,84,.42), 0 2px 8px rgba(0,0,0,.15) !important;
  transform: translateY(-2px) !important;
}}
.stButton > button:active {{
  transform: translateY(0) !important;
  box-shadow: 0 3px 12px rgba(27,131,84,.28) !important;
}}
.stButton > button:focus {{
  outline: 3px solid rgba(27,131,84,.4) !important;
  outline-offset: 2px !important;
}}
.stDownloadButton > button {{
  font-family: var(--font) !important;
  font-size: .875rem !important;
  font-weight: 600 !important;
  background: var(--c-text) !important;
  color: #fff !important;
  border: none !important;
  border-radius: var(--radius-md) !important;
  padding: .65rem 1.75rem !important;
  box-shadow: var(--shadow-sm) !important;
  transition: var(--transition) !important;
}}
.stDownloadButton > button:hover {{
  background: #1C2B22 !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--shadow-md) !important;
}}

/* ════════════════════════════════════════════════════════
   CONTEXT EXPANDER
   ════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {{
  border: 1px solid var(--c-border-lt) !important;
  border-radius: var(--radius-md) !important;
  background: var(--c-surface-alt) !important;
  margin-top: 1rem !important;
}}
[data-testid="stExpander"] summary {{
  font-size: .875rem !important;
  font-weight: 600 !important;
  color: var(--c-text-sec) !important;
  padding: .65rem .9rem !important;
}}
[data-testid="stExpander"] summary:hover {{
  color: var(--c-primary) !important;
}}

/* ════════════════════════════════════════════════════════
   CONTEXT BADGE
   ════════════════════════════════════════════════════════ */
.ctx-badge {{
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  background: #E6F4EC;
  color: #0A4225;
  border: 1px solid #B8DFC5;
  border-radius: 20px;
  padding: .28rem .85rem;
  font-size: .8rem;
  font-weight: 600;
  margin-top: .5rem;
}}

/* ════════════════════════════════════════════════════════
   ALERTS & SPINNER
   ════════════════════════════════════════════════════════ */
.stAlert {{
  border-radius: var(--radius-md) !important;
  font-size: .9rem !important;
}}
.stAlert [data-testid="stMarkdownContainer"] p {{
  font-size: .9rem !important;
  line-height: 1.5 !important;
}}
.stSpinner > div {{
  border-top-color: var(--c-primary) !important;
}}
.stSpinner p {{
  font-size: .9rem !important;
  color: var(--c-text-sec) !important;
}}

/* ════════════════════════════════════════════════════════
   RESULT CONTENT
   ════════════════════════════════════════════════════════ */
.result-card {{
  background: var(--c-surface);
  border: 1px solid var(--c-border-lt);
  border-radius: var(--radius-lg);
  padding: 1.5rem 1.75rem;
  margin-top: 1.25rem;
  box-shadow: var(--shadow-sm);
}}
.result-card p, .result-card li {{
  font-size: .9375rem !important;
  line-height: 1.75 !important;
  color: var(--c-text) !important;
}}
.result-card h1, .result-card h2, .result-card h3 {{
  color: var(--c-text) !important;
  font-weight: 700 !important;
}}

/* ════════════════════════════════════════════════════════
   FOOTER
   ════════════════════════════════════════════════════════ */
.app-footer {{
  border-top: 1px solid var(--c-border-lt);
  margin-top: 3rem;
  padding: 2rem 1rem 1.5rem;
  text-align: center;
  color: var(--c-text-muted);
  font-size: .8rem;
  line-height: 1.9;
}}
.app-footer strong {{ color: var(--c-text); }}
.app-footer a {{
  color: var(--c-primary);
  text-decoration: none;
  font-weight: 500;
}}
.app-footer a:hover {{ text-decoration: underline; }}
.footer-models {{
  font-size: .72rem;
  color: #9DA4AE;
  margin-top: .3rem;
}}

/* ════════════════════════════════════════════════════════
   MISC STREAMLIT OVERRIDES
   ════════════════════════════════════════════════════════ */
hr {{ border-color: var(--c-border-lt) !important; margin: 1rem 0 !important; }}
[data-testid="stSidebar"] {{ background: var(--c-surface-alt); }}
.stMarkdown p {{ font-size: .9375rem; line-height: 1.7; }}

/* ════════════════════════════════════════════════════════
   RESPONSIVE
   ════════════════════════════════════════════════════════ */
@media (max-width: 780px) {{
  .hdr-inner    {{ padding: 1rem; flex-direction: column; gap: .75rem; }}
  .cat-nav      {{ padding: .75rem 1rem; }}
  .content-card {{ padding: 1.1rem 1rem; }}
  div[data-testid="stRadio"] label {{
    min-height: 60px !important;
    font-size: .78rem !important;
  }}
}}
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────────────────
# Geometric SVG: concentric rings + dot matrix, inspired by RCJY logo
_geo_svg = """
<svg class="hdr-rings" width="240" height="130" viewBox="0 0 240 130"
     fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Concentric rings (the RCJY logo uses many circles) -->
  <circle cx="185" cy="65" r="110" stroke="rgba(255,255,255,.04)" stroke-width="1.5"/>
  <circle cx="185" cy="65" r="86"  stroke="rgba(255,255,255,.055)" stroke-width="1.5"/>
  <circle cx="185" cy="65" r="64"  stroke="rgba(200,168,75,.13)" stroke-width="1.5"/>
  <circle cx="185" cy="65" r="44"  stroke="rgba(255,255,255,.07)" stroke-width="1.5"/>
  <circle cx="185" cy="65" r="26"  stroke="rgba(200,168,75,.18)" stroke-width="1.5"/>
  <circle cx="185" cy="65" r="12"  fill="rgba(200,168,75,.14)"/>
  <!-- Small accent circles (logo dot motif) -->
  <circle cx="55"  cy="22" r="4.5" fill="rgba(255,255,255,.07)"/>
  <circle cx="75"  cy="22" r="3"   fill="rgba(200,168,75,.12)"/>
  <circle cx="92"  cy="22" r="4.5" fill="rgba(255,255,255,.06)"/>
  <circle cx="55"  cy="40" r="3"   fill="rgba(200,168,75,.1)"/>
  <circle cx="75"  cy="40" r="4.5" fill="rgba(255,255,255,.07)"/>
  <circle cx="92"  cy="40" r="3"   fill="rgba(200,168,75,.1)"/>
  <!-- Rotated square = diamond (logo square motif) -->
  <rect x="28" y="52" width="18" height="18"
        transform="rotate(45 37 61)" stroke="rgba(255,255,255,.08)" stroke-width="1.5"/>
  <rect x="12" y="68" width="12" height="12"
        transform="rotate(45 18 74)" stroke="rgba(200,168,75,.12)" stroke-width="1"/>
</svg>
"""

st.markdown(f"""
<div class="rcjy-hdr">
  {_geo_svg}
  <div class="hdr-inner">
    <div class="hdr-logo">
      <img src="{RCJY_LOGO_URL}" alt="RCJY Logo"
           onerror="this.style.display='none'">
      <div class="hdr-logo-text">
        <h1>{L['app_name']}</h1>
        <p>{L['dept']}</p>
      </div>
    </div>
  </div>
</div>
<div class="gold-bar"></div>
""", unsafe_allow_html=True)

# ─── LANGUAGE CONTROLS ────────────────────────────────────────────────────────
lc1, lc2, lc_gap = st.columns([1, 1, 5])
with lc1:
    new_lang = st.selectbox(
        L["lang_label"],
        ["English", "العربية"],
        index=1 if is_ar else 0,
        key="lang_sel",
    )
    _target = "ar" if new_lang == "العربية" else "en"
    if _target != st.session_state.ui_lang:
        st.session_state.ui_lang = _target
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

# ─── CATEGORY NAVIGATION ──────────────────────────────────────────────────────
st.markdown('<div class="cat-nav">', unsafe_allow_html=True)

_tab_keys   = ["text", "image", "video", "voice", "podcast"]
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
    key="active_tab",             # persists — no auto-reset on rerun
    label_visibility="collapsed",
)

st.markdown('</div>', unsafe_allow_html=True)


# ─── SHARED HELPERS ───────────────────────────────────────────────────────────
def _model_tags(*tags):
    html = "".join(f'<span class="mtag">{t}</span>' for t in tags)
    st.markdown(f'<div class="model-tags">{html}</div>', unsafe_allow_html=True)


def _section(label):
    st.markdown(f'<div class="section-head">{label}</div>', unsafe_allow_html=True)


def _ctx_inputs():
    """Reference material expander — shared widget keys keep state across tabs."""
    with st.expander(f"📎  {L['context_label']}", expanded=False):
        st.caption(L["context_hint"])
        cu, cf = st.columns([1, 1], gap="medium")
        with cu:
            url = st.text_input(
                L["url_label"],
                placeholder=L["url_placeholder"],
                key="input_url",
            )
        with cf:
            files = st.file_uploader(
                L["attach_label"],
                type=SUPPORTED_FILE_TYPES,
                accept_multiple_files=True,
                key="input_files",
            )
        if files:
            st.caption(f"{L['attached']}: {', '.join(f.name for f in files)}")
        return url, files


def _resolve_ctx(url, files):
    ctx, _ = get_content_from_input(text="", url=url, files=files)
    has_ctx = bool(ctx and ctx != "No content provided.")
    if has_ctx:
        st.markdown(
            f'<div class="ctx-badge">✦ {L["context_loaded"]} — '
            f'{len(ctx):,} {L["chars"]}</div>',
            unsafe_allow_html=True,
        )
    return ctx, has_ctx


# ════════════════════════════════════════════════════════════════════════════
# TEXT TAB
# ════════════════════════════════════════════════════════════════════════════
if active_tab == "text":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    _model_tags("Gemini 3 Pro", "Gemini 3 Flash")

    _type_map = {
        L["text_type_article"]: "article", L["text_type_social"]:  "social",
        L["text_type_press"]:   "press",   L["text_type_ad"]:      "ad",
        L["text_type_email"]:   "email",   L["text_type_script"]:  "script",
        L["text_type_summary"]: "summary", L["text_type_creative"]: "creative",
    }
    _tone_map = {
        L["text_tone_professional"]: "professional",
        L["text_tone_friendly"]:     "friendly",
        L["text_tone_formal"]:       "formal",
        L["text_tone_persuasive"]:   "persuasive",
        L["text_tone_informative"]:  "informative",
    }

    # Settings strip
    st.markdown('<div class="settings-strip">', unsafe_allow_html=True)
    _section(f"{L['text_type_label']}  ·  {L['text_tone_label']}  ·  {L['text_model_label']}")
    s1, s2, s3 = st.columns(3)
    with s1:
        text_type = _type_map[st.selectbox(L["text_type_label"], list(_type_map), key="text_type")]
    with s2:
        text_tone = _tone_map[st.selectbox(L["text_tone_label"], list(_tone_map), key="text_tone")]
    with s3:
        _ms = st.selectbox(L["text_model_label"], ["Pro", "Flash"], key="text_model")
        text_model = "pro" if _ms == "Pro" else "flash"
    st.markdown('</div>', unsafe_allow_html=True)

    # Prompt
    _section(L["prompt_label"])
    text_prompt = st.text_area(
        L["prompt_label"],
        key="prompt_text",
        placeholder=L["prompt_ph_text"],
        height=148,
        label_visibility="collapsed",
    )

    input_url, input_files = _ctx_inputs()
    ctx_text, has_ctx = _resolve_ctx(input_url, input_files)
    st.markdown('</div>', unsafe_allow_html=True)  # close content-card

    if st.button(L["btn_text"], use_container_width=True, key="btn_text"):
        if not text_prompt.strip() and not has_ctx:
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_text"]):
                try:
                    res = generate_text(
                        prompt=text_prompt.strip() or "Summarize the provided content",
                        context_text=ctx_text if has_ctx else "",
                        url=input_url or "", files=input_files,
                        text_type=text_type, tone=text_tone,
                        model=text_model, lang=lang,
                    )
                    st.session_state.result_text = res
                except Exception as e:
                    logger.exception("Text generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_text:
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.result_text)
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button(
            L["btn_download"],
            data=st.session_state.result_text,
            file_name="rcjy_content.txt",
            mime="text/plain",
            key="dl_text",
        )

# ════════════════════════════════════════════════════════════════════════════
# IMAGE TAB
# ════════════════════════════════════════════════════════════════════════════
elif active_tab == "image":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    _model_tags("Imagen 4 Fast", "Imagen 4", "Imagen 4 Ultra", "Nano Banana")

    st.markdown('<div class="settings-strip">', unsafe_allow_html=True)
    _section(f"{L['model_label']}  ·  {L['aspect_label']}")
    i1, i2 = st.columns(2)
    with i1:
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
    with i2:
        img_aspect = st.selectbox(
            L["aspect_label"], ["16:9", "9:16", "1:1", "4:3", "3:4"], key="img_aspect"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    _section(L["prompt_label"])
    img_prompt = st.text_area(
        L["prompt_label"],
        key="prompt_image",
        placeholder=L["prompt_ph_image"],
        height=148,
        label_visibility="collapsed",
    )

    input_url, input_files = _ctx_inputs()
    ctx_text, has_ctx = _resolve_ctx(input_url, input_files)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(L["btn_image"], use_container_width=True, key="btn_img"):
        if not img_prompt.strip():
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_image"]):
                try:
                    data, mime = generate_image(
                        prompt=img_prompt.strip(),
                        context_text=ctx_text if has_ctx else "",
                        files=input_files,
                        model=img_model,
                        aspect_ratio=img_aspect,
                        lang=lang,
                    )
                    st.session_state.result_image = (data, mime)
                except Exception as e:
                    logger.exception("Image generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_image:
        img_data, _ = st.session_state.result_image
        st.image(img_data, use_container_width=True)
        st.download_button(
            L["btn_download"],
            data=img_data,
            file_name="rcjy_image.png",
            mime="image/png",
            key="dl_img",
        )

# ════════════════════════════════════════════════════════════════════════════
# VIDEO TAB
# ════════════════════════════════════════════════════════════════════════════
elif active_tab == "video":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    _model_tags("Veo 3.1")

    st.markdown('<div class="settings-strip">', unsafe_allow_html=True)
    _section(f"{L['aspect_label']}  ·  {L['duration_label']}")
    v1, v2 = st.columns(2)
    with v1:
        vid_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16"], key="vid_aspect")
    with v2:
        vid_dur = st.selectbox(
            L["duration_label"], ["4", "6", "8"], index=2, key="vid_dur"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    _section(L["prompt_label"])
    vid_prompt = st.text_area(
        L["prompt_label"],
        key="prompt_video",
        placeholder=L["prompt_ph_video"],
        height=148,
        label_visibility="collapsed",
    )

    input_url, input_files = _ctx_inputs()
    ctx_text, has_ctx = _resolve_ctx(input_url, input_files)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(L["btn_video"], use_container_width=True, key="btn_vid"):
        if not vid_prompt.strip():
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_video"]):
                try:
                    data, mime = generate_video(
                        prompt=vid_prompt.strip(),
                        context_text=ctx_text if has_ctx else "",
                        aspect_ratio=vid_aspect,
                        duration=vid_dur,
                        lang=lang,
                    )
                    st.session_state.result_video = (data, mime)
                except Exception as e:
                    logger.exception("Video generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_video:
        vid_data, _ = st.session_state.result_video
        st.video(vid_data)
        st.download_button(
            L["btn_download"],
            data=vid_data,
            file_name="rcjy_video.mp4",
            mime="video/mp4",
            key="dl_vid",
        )

# ════════════════════════════════════════════════════════════════════════════
# VOICE TAB  — single prompt, no duplicate textarea
# ════════════════════════════════════════════════════════════════════════════
elif active_tab == "voice":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    _model_tags("Gemini TTS Flash", "Gemini TTS Pro", "Chirp 3")

    st.markdown('<div class="settings-strip">', unsafe_allow_html=True)
    _section(f"{L['voice_label']}  ·  {L['quality_label']}  ·  {L['style_label']}")
    o1, o2, o3 = st.columns(3)
    with o1:
        voice_name = st.selectbox(
            L["voice_label"],
            ["Kore", "Puck", "Zephyr", "Charon", "Fenrir",
             "Aoede", "Leda", "Orus", "Perseus", "Schedar"],
            key="voice_name",
        )
    with o2:
        tts_quality = st.selectbox(L["quality_label"], ["Flash", "Pro"], key="tts_q")
    with o3:
        style_hint = st.text_input(
            L["style_label"],
            placeholder=L["style_placeholder"],
            key="voice_style",
        )
    st.markdown('</div>', unsafe_allow_html=True)

    _section(L["prompt_label"])
    voice_prompt = st.text_area(
        L["prompt_label"],
        key="prompt_voice",
        placeholder=L["prompt_ph_voice"],
        height=180,
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(L["btn_voice"], use_container_width=True, key="btn_voice"):
        if not voice_prompt.strip():
            st.warning(L["warn_text"])
        else:
            with st.spinner(L["spin_voice"]):
                try:
                    data, mime = generate_voice(
                        text=voice_prompt.strip(),
                        context_text="",
                        voice_name=voice_name,
                        style_hint=style_hint,
                        tts_model="pro" if tts_quality == "Pro" else "flash",
                        lang=lang,
                    )
                    st.session_state.result_voice = (data, mime)
                except Exception as e:
                    logger.exception("Voice generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_voice:
        voice_data, _ = st.session_state.result_voice
        st.audio(voice_data, format="audio/wav")
        st.download_button(
            L["btn_download"],
            data=voice_data,
            file_name="rcjy_voice.wav",
            mime="audio/wav",
            key="dl_voice",
        )

# ════════════════════════════════════════════════════════════════════════════
# PODCAST TAB
# ════════════════════════════════════════════════════════════════════════════
elif active_tab == "podcast":
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    _model_tags("Gemini 3 Flash", "Multi-Speaker TTS")

    _voice_opts = {
        "Kore ♀":   "Kore",  "Aoede ♀":  "Aoede",  "Leda ♀":   "Leda",
        "Puck ♂":   "Puck",  "Charon ♂": "Charon", "Fenrir ♂": "Fenrir",
        "Orus ♂":   "Orus",
    }
    _pod_len_opts = [L["length_short"], L["length_standard"]]

    st.markdown('<div class="settings-strip">', unsafe_allow_html=True)
    _section(f"{L['length_label']}  ·  {L['host_label']}  ·  {L['guest_label']}")
    p1, p2, p3 = st.columns(3)
    with p1:
        pod_len_idx = st.selectbox(
            L["length_label"],
            range(len(_pod_len_opts)),
            format_func=lambda i: _pod_len_opts[i],
            key="pod_len",
        )
    with p2:
        _host_lbl = st.selectbox(L["host_label"], list(_voice_opts), index=0, key="pod_host")
        pod_host = _voice_opts[_host_lbl]
    with p3:
        _guest_lbl = st.selectbox(L["guest_label"], list(_voice_opts), index=3, key="pod_guest")
        pod_guest = _voice_opts[_guest_lbl]
    st.markdown('</div>', unsafe_allow_html=True)

    _section(L["prompt_label"])
    pod_prompt = st.text_area(
        L["prompt_label"],
        key="prompt_podcast",
        placeholder=L["prompt_ph_podcast"],
        height=148,
        label_visibility="collapsed",
    )

    input_url, input_files = _ctx_inputs()
    ctx_text, has_ctx = _resolve_ctx(input_url, input_files)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(L["btn_podcast"], use_container_width=True, key="btn_pod"):
        if not pod_prompt.strip() and not has_ctx:
            st.warning(L["warn_topic"])
        else:
            with st.spinner(L["spin_podcast"]):
                try:
                    data, mime = generate_podcast(
                        prompt=pod_prompt.strip() or (
                            "ناقش المحتوى المقدّم" if lang == "ar" else "Discuss the provided content"
                        ),
                        context_text=ctx_text if has_ctx else "",
                        url=input_url or "",
                        files=input_files,
                        length="short" if pod_len_idx == 0 else "standard",
                        voice_host=pod_host,
                        voice_guest=pod_guest,
                        lang=lang,
                    )
                    st.session_state.result_podcast = (data, mime)
                except Exception as e:
                    logger.exception("Podcast generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_podcast:
        pod_data, _ = st.session_state.result_podcast
        st.audio(pod_data, format="audio/wav")
        st.download_button(
            L["btn_download"],
            data=pod_data,
            file_name="rcjy_podcast.wav",
            mime="audio/wav",
            key="dl_pod",
        )

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-footer">
  <strong>{L['footer_org']}</strong><br>
  {L['footer_dept']}<br>
  <div class="footer-models">
    Gemini 3 Pro &nbsp;·&nbsp; Imagen 4 Ultra &nbsp;·&nbsp; Nano Banana
    &nbsp;·&nbsp; Veo 3.1 &nbsp;·&nbsp; Gemini TTS &nbsp;·&nbsp; Gemini 3 Flash
  </div>
  <div style="margin-top:.5rem;">
    <a href="https://www.rcjy.gov.sa/en/" target="_blank" rel="noopener">rcjy.gov.sa</a>
    &nbsp;·&nbsp; &copy; 2026
  </div>
</div>
""", unsafe_allow_html=True)
