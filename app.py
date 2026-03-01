import logging

import streamlit as st

from rcjy_config import RCJY_LOGO_URL, SUPPORTED_FILE_TYPES, get_api_key
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

# ── Translations ──────────────────────────────────────────────────────────────
T = {
    "en": {
        "app_name":               "Media Generator",
        "dept":                   "General Administration of Communication and Media",
        "lang_label":             "Interface",
        "output_lang_label":      "Output Language",
        "url_label":              "Reference URL (optional)",
        "url_placeholder":        "https://...",
        "attach_label":           "Upload Reference Files",
        "attached":               "Attached",
        "context_loaded":         "Context loaded",
        "chars":                  "chars",
        "context_label":          "Attachments",
        "context_hint":           "Optionally attach a URL or files — the AI will use them as context.",
        "tab_text":               "Text",
        "tab_image":              "Image",
        "tab_video":              "Video",
        "tab_voice":              "Voice",
        "tab_podcast":            "Podcast",
        "prompt_label":           "Prompt",
        "prompt_ph_text":         "Describe what you want to create…\ne.g. A press release about Jubail Industrial City's new green hydrogen facility.",
        "prompt_ph_image":        "Describe the image…\ne.g. Aerial golden-hour view of Jubail Industrial City, petrochemical towers, calm sea.",
        "prompt_ph_video":        "Describe the video scene…\ne.g. Cinematic drone flight over Yanbu Industrial Port at sunrise, dramatic sky.",
        "prompt_ph_voice":        "Enter the text to be spoken…",
        "prompt_ph_podcast":      "Describe the podcast topic…\ne.g. The economic transformation of Jubail and Yanbu and their role in Vision 2030.",
        "model_label":            "Model",
        "aspect_label":           "Aspect Ratio",
        "duration_label":         "Duration (sec)",
        "resolution_label":       "Resolution",
        "video_model_label":      "Video Model",
        "voice_label":            "Voice",
        "quality_label":          "Quality",
        "style_label":            "Delivery Style",
        "style_placeholder":      "e.g. professional, warm, authoritative",
        "length_label":           "Episode Length",
        "length_short":           "Short (4–5 min)",
        "length_standard":        "Standard (~10 min)",
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
        "btn_text":               "Generate Text",
        "btn_image":              "Generate Image",
        "btn_video":              "Generate Video",
        "btn_voice":              "Generate Voice",
        "btn_podcast":            "Generate Podcast",
        "btn_download":           "Download",
        "warn_prompt":            "Please enter a prompt.",
        "warn_topic":             "Please enter a topic or attach reference content.",
        "warn_text":              "Please enter text to speak.",
        "warn_api":               "GEMINI_API_KEY is not set. Add it as an environment variable.",
        "spin_text":              "Generating text…",
        "spin_image":             "Generating image…",
        "spin_video":             "Generating video… (2–5 min)",
        "spin_voice":             "Generating speech…",
        "spin_podcast":           "Creating podcast… (2–3 min)",
        "footer_org":             "Royal Commission for Jubail and Yanbu",
        "footer_dept":            "General Administration of Communication and Media",
    },
    "ar": {
        "app_name":               "مولّد الوسائط",
        "dept":                   "الإدارة العامة للاتصال والإعلام",
        "lang_label":             "الواجهة",
        "output_lang_label":      "لغة المحتوى",
        "url_label":              "رابط مرجعي (اختياري)",
        "url_placeholder":        "https://...",
        "attach_label":           "رفع ملفات مرجعية",
        "attached":               "مرفقات",
        "context_loaded":         "تم تحميل المحتوى",
        "chars":                  "حرف",
        "context_label":          "المرفقات",
        "context_hint":           "أرفق رابطاً أو ملفات اختيارياً — سيستخدمها الذكاء الاصطناعي كسياق.",
        "tab_text":               "نص",
        "tab_image":              "صورة",
        "tab_video":              "فيديو",
        "tab_voice":              "صوت",
        "tab_podcast":            "بودكاست",
        "prompt_label":           "الوصف",
        "prompt_ph_text":         "اكتب وصفاً لما تريد إنشاءه…\nمثال: بيان صحفي عن منشأة الهيدروجين الأخضر الجديدة في الجبيل.",
        "prompt_ph_image":        "اكتب وصفاً للصورة…\nمثال: منظر جوي لمدينة الجبيل الصناعية عند الغسق.",
        "prompt_ph_video":        "اكتب وصفاً لمشهد الفيديو…\nمثال: تحليق سينمائي فوق ميناء ينبع عند الفجر.",
        "prompt_ph_voice":        "أدخل النص الذي تريد تحويله إلى صوت…",
        "prompt_ph_podcast":      "اكتب موضوع البودكاست…\nمثال: التحول الاقتصادي لمدينتي الجبيل وينبع ودورهما في رؤية 2030.",
        "model_label":            "النموذج",
        "aspect_label":           "نسبة الأبعاد",
        "duration_label":         "المدة (ثانية)",
        "resolution_label":       "الدقة",
        "video_model_label":      "نموذج الفيديو",
        "voice_label":            "الصوت",
        "quality_label":          "الجودة",
        "style_label":            "أسلوب الأداء",
        "style_placeholder":      "مثال: رسمي، دافئ، موثوق",
        "length_label":           "مدة الحلقة",
        "length_short":           "قصيرة (٤–٥ دقائق)",
        "length_standard":        "عادية (~١٠ دقائق)",
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
        "warn_prompt":            "الرجاء إدخال وصف.",
        "warn_topic":             "الرجاء إدخال موضوع أو إرفاق محتوى.",
        "warn_text":              "الرجاء إدخال النص للنطق.",
        "warn_api":               "مفتاح GEMINI_API_KEY غير مضبوط.",
        "spin_text":              "جارٍ إنشاء النص…",
        "spin_image":             "جارٍ إنشاء الصورة…",
        "spin_video":             "جارٍ إنشاء الفيديو… (٢–٥ دقائق)",
        "spin_voice":             "جارٍ إنشاء الصوت…",
        "spin_podcast":           "جارٍ إنشاء البودكاست… (٢–٣ دقائق)",
        "footer_org":             "الهيئة الملكية للجبيل وينبع",
        "footer_dept":            "الإدارة العامة للاتصال والإعلام",
    },
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RCJY Media Generator",
    page_icon="https://www.rcjy.gov.sa/o/rcjy-theme/images/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state ─────────────────────────────────────────────────────────────
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "en"
for _k in ("result_text", "result_image", "result_video", "result_voice", "result_podcast"):
    if _k not in st.session_state:
        st.session_state[_k] = None

# Sync UI language from URL params so nav language toggles work without widgets
_qp = st.query_params
_qp_lang = _qp.get("lang", st.session_state.ui_lang)
if _qp_lang not in ("en", "ar"):
    _qp_lang = "en"
st.session_state.ui_lang = _qp_lang

is_ar   = st.session_state.ui_lang == "ar"
L       = T[st.session_state.ui_lang]
_api_ok = bool(get_api_key())

# ── CSS ───────────────────────────────────────────────────────────────────────
_fonts = (
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700"
    "&family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap"
)
_dir = "rtl" if is_ar else "ltr"

st.markdown(f"""
<style>
@import url('{_fonts}');

/* ── Reset & base ── */
html, body, .stApp {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', system-ui, sans-serif !important;
  font-size: 15px;
  color: #161616;
  background: #F3F4F6 !important;
  -webkit-font-smoothing: antialiased;
  direction: {_dir};
}}
#MainMenu, footer, header {{ visibility: hidden; }}

[data-testid="stMainBlockContainer"] {{
  max-width: 1080px !important;
  margin: 0 auto !important;
  padding: 0 1.5rem 3rem !important;
  background: transparent !important;
}}

/* ════════════════════════════════════════
   NAVBAR  (pure-HTML, full-bleed, sticky)
   ════════════════════════════════════════ */
.rcjy-nav {{
  background: #fff;
  border-bottom: 3px solid #1B8354;
  margin: 0 -1.5rem 1.5rem;
  box-shadow: 0 1px 4px rgba(13,18,28,.08);
  position: sticky;
  top: 0;
  z-index: 999;
}}
.rcjy-nav-inner {{
  display: flex;
  align-items: center;
  padding: 0 2rem;
  min-height: 72px;
  gap: 1.25rem;
  max-width: 1280px;
  margin: 0 auto;
  direction: ltr;
}}
.rcjy-nav-logo-link {{
  display: flex;
  align-items: center;
  flex-shrink: 0;
  text-decoration: none;
}}
.rcjy-nav-logo {{ height: 48px; display: block; }}
.rcjy-nav-links {{
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 2px;
  flex: 1 1 auto;
  align-items: center;
}}
.rcjy-nav-item {{
  display: block;
  padding: 10px 16px;
  border-radius: 8px;
  font-family: 'IBM Plex Sans','IBM Plex Sans Arabic',sans-serif;
  font-size: .9rem;
  font-weight: 500;
  color: #0d121c;
  text-decoration: none;
  white-space: nowrap;
  transition: background .2s, color .2s;
}}
.rcjy-nav-item:hover {{ background: #F3F4F6; color: #1B8354; }}
.rcjy-nav-active {{
  background: #1B8354 !important;
  color: #fff !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 3px rgba(27,131,84,.25);
}}
/* Right-side language controls */
.rcjy-nav-right {{
  display: flex;
  align-items: center;
  gap: .75rem;
  flex-shrink: 0;
}}
/* Primary UI-language toggle */
.rcjy-lang-link {{
  font-family: 'IBM Plex Sans','IBM Plex Sans Arabic',sans-serif;
  font-size: .875rem;
  font-weight: 500;
  color: #0d121c;
  text-decoration: none;
  padding: 8px 16px;
  border: 1px solid #D2D6DB;
  border-radius: 8px;
  transition: background .2s, color .2s, border-color .2s;
  white-space: nowrap;
}}
.rcjy-lang-link:hover {{ background: #F3F4F6; color: #1B8354; border-color: #1B8354; }}
/* Output-language segmented toggle */
.rcjy-outlang {{
  display: flex;
  border: 1px solid #D2D6DB;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}}
.rcjy-out-opt {{
  font-family: 'IBM Plex Sans','IBM Plex Sans Arabic',sans-serif;
  font-size: .82rem;
  font-weight: 500;
  color: #6C737F;
  text-decoration: none;
  padding: 7px 12px;
  transition: background .2s, color .2s;
  white-space: nowrap;
}}
.rcjy-out-opt + .rcjy-out-opt {{ border-left: 1px solid #D2D6DB; }}
.rcjy-out-opt:hover {{ background: #F3F4F6; color: #1B8354; }}
.rcjy-out-active {{
  background: #1B8354 !important;
  color: #fff !important;
  font-weight: 600 !important;
}}

/* ════════════════════════════════════════
   CONTENT CARD — RCJY card style
   ════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {{
  border: 1px solid #D2D6DB !important;
  border-radius: 16px !important;
  background: #fff !important;
  box-shadow: 0px 2px 4px -2px rgba(16,24,40,.06), 0px 4px 8px -2px rgba(16,24,40,.1) !important;
  overflow: hidden !important;
  margin-top: .5rem !important;
  transition: box-shadow .3s ease !important;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
  box-shadow: 0px 4px 8px -2px rgba(16,24,40,.1), 0px 8px 16px -4px rgba(16,24,40,.12) !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] {{
  padding: 1.5rem !important;
  gap: .875rem !important;
}}

/* ════════════════════════════════════════
   LABELS
   ════════════════════════════════════════ */
.stSelectbox > label,
.stTextArea  > label,
.stTextInput > label {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .7rem !important;
  font-weight: 600 !important;
  letter-spacing: .07em !important;
  text-transform: uppercase !important;
  color: #6C737F !important;
  margin-bottom: .3rem !important;
}}
.stCaption, [data-testid="stCaptionContainer"] p {{
  font-size: .8rem !important;
  color: #9DA4AE !important;
  line-height: 1.55 !important;
}}

/* ════════════════════════════════════════
   TEXTAREA
   ════════════════════════════════════════ */
.stTextArea textarea {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .9625rem !important;
  font-weight: 400 !important;
  line-height: 1.7 !important;
  color: #161616 !important;
  background: #F9FAFB !important;
  border: 1px solid #9DA4AE !important;
  border-radius: 6px !important;
  padding: .8rem 1rem !important;
  transition: border-color .2s, box-shadow .2s !important;
  caret-color: #1B8354;
}}
.stTextArea textarea:focus {{
  background: #fff !important;
  border-color: #1B8354 !important;
  box-shadow: 0 0 0 3px rgba(27,131,84,.12) !important;
  outline: none !important;
}}
.stTextArea textarea::placeholder {{
  color: #B8BEC8 !important;
  font-size: .9rem !important;
}}

/* ════════════════════════════════════════
   TEXT INPUT
   ════════════════════════════════════════ */
.stTextInput input {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .9rem !important;
  color: #161616 !important;
  background: #F9FAFB !important;
  border: 1px solid #9DA4AE !important;
  border-radius: 6px !important;
  padding: .6rem .9rem !important;
  transition: border-color .2s, box-shadow .2s !important;
}}
.stTextInput input:focus {{
  background: #fff !important;
  border-color: #1B8354 !important;
  box-shadow: 0 0 0 3px rgba(27,131,84,.12) !important;
  outline: none !important;
}}

/* ════════════════════════════════════════
   SELECTBOX
   ════════════════════════════════════════ */
.stSelectbox [data-baseweb="select"] > div {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .9rem !important;
  font-weight: 500 !important;
  color: #161616 !important;
  background: #F9FAFB !important;
  border: 1px solid #9DA4AE !important;
  border-radius: 6px !important;
  transition: border-color .2s !important;
}}
.stSelectbox [data-baseweb="select"]:focus-within > div {{
  border-color: #1B8354 !important;
  box-shadow: 0 0 0 3px rgba(27,131,84,.12) !important;
}}

/* ════════════════════════════════════════
   MODEL TAGS
   ════════════════════════════════════════ */
.mtags {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: .5rem; }}
.mtag {{
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: .67rem;
  font-weight: 600;
  letter-spacing: .05em;
  text-transform: uppercase;
  color: #14573A;
  background: #EBF5EE;
  border: 1px solid #C3E0CC;
  border-radius: 4px;
  padding: .18rem .55rem;
  display: inline-block;
  transition: background .15s, color .15s;
}}
.mtag:hover {{ background: #D4EDDB; color: #104631; }}

/* ════════════════════════════════════════
   DIVIDER
   ════════════════════════════════════════ */
hr {{ border-color: #E5E7EB !important; margin: .25rem 0 !important; }}

/* ════════════════════════════════════════
   PRIMARY BUTTON
   ════════════════════════════════════════ */
.stButton > button {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .9375rem !important;
  font-weight: 600 !important;
  letter-spacing: .01em !important;
  color: #fff !important;
  background: #1B8354 !important;
  border: none !important;
  border-radius: 8px !important;
  padding: .875rem 2.5rem !important;
  min-height: 52px !important;
  width: 100%;
  box-shadow: 0 1px 3px rgba(16,24,40,.12), 0 1px 2px rgba(16,24,40,.08) !important;
  transition: background .15s ease, box-shadow .15s ease, transform .1s ease !important;
  cursor: pointer !important;
}}
.stButton > button:hover {{
  background: #14573A !important;
  box-shadow: 0 4px 8px rgba(16,24,40,.15), 0 2px 4px rgba(16,24,40,.10) !important;
  transform: translateY(-1px) !important;
}}
.stButton > button:active {{ background: #104631 !important; transform: translateY(0) !important; }}
.stButton > button:focus  {{
  outline: 2px solid #0d121c !important;
  outline-offset: 2px !important;
}}

/* ════════════════════════════════════════
   DOWNLOAD BUTTON
   ════════════════════════════════════════ */
.stDownloadButton > button {{
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: .875rem !important;
  font-weight: 600 !important;
  background: transparent !important;
  color: #161616 !important;
  border: 1px solid #9DA4AE !important;
  border-radius: 8px !important;
  padding: .6rem 1.75rem !important;
  box-shadow: none !important;
  transition: background .15s, border-color .15s, transform .1s !important;
}}
.stDownloadButton > button:hover {{
  background: #F3F4F6 !important;
  border-color: #384250 !important;
  transform: translateY(-1px) !important;
}}

/* ════════════════════════════════════════
   FILE UPLOADER
   ════════════════════════════════════════ */
[data-testid="stFileUploader"] section {{
  border: 2px dashed #D2D6DB !important;
  border-radius: 8px !important;
  background: #F9FAFB !important;
  transition: border-color .2s, background .2s !important;
}}
[data-testid="stFileUploader"] section:hover {{
  border-color: #1B8354 !important;
  background: #F0FAF4 !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] div small,
[data-testid="stFileUploaderDropzone"] small {{ display: none !important; }}

/* ════════════════════════════════════════
   EXPANDER
   ════════════════════════════════════════ */
[data-testid="stExpander"] {{
  border: 1px solid #D2D6DB !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: .875rem !important;
  font-weight: 500 !important;
  color: #384250 !important;
  padding: .7rem 1rem !important;
  background: #F9FAFB !important;
}}
[data-testid="stExpander"] summary:hover {{ color: #1B8354 !important; }}
[data-testid="stExpander"] > div > div {{ padding: .9rem 1rem !important; }}

/* ════════════════════════════════════════
   CONTEXT BADGE
   ════════════════════════════════════════ */
.ctx-badge {{
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  background: #EBF5EE;
  color: #14573A;
  border: 1px solid #C3E0CC;
  border-radius: 4px;
  padding: .25rem .8rem;
  font-size: .8rem;
  font-weight: 600;
  margin-top: .35rem;
}}

/* ════════════════════════════════════════
   RESULT AREA
   ════════════════════════════════════════ */
.result-wrap {{
  background: #fff;
  border: 1px solid #D2D6DB;
  border-radius: 16px;
  padding: 1.5rem 1.75rem;
  margin-top: 1rem;
  box-shadow: 0px 2px 4px -2px rgba(16,24,40,.06), 0px 4px 8px -2px rgba(16,24,40,.1);
  border-top: 3px solid #1B8354;
}}
.result-wrap p  {{ font-size: .9375rem !important; line-height: 1.8 !important; color: #161616 !important; }}
.result-wrap li {{ font-size: .9375rem !important; line-height: 1.8 !important; color: #161616 !important; }}
.result-wrap h1,
.result-wrap h2,
.result-wrap h3 {{ color: #161616 !important; font-weight: 600 !important; }}

/* ════════════════════════════════════════
   ALERTS & SPINNER
   ════════════════════════════════════════ */
.stAlert {{ border-radius: 8px !important; }}
.stAlert p {{ font-size: .9rem !important; }}
.stSpinner > div {{ border-top-color: #1B8354 !important; }}


/* ════════════════════════════════════════
   SIDEBAR
   ════════════════════════════════════════ */
[data-testid="stSidebar"] {{ background: #fff; }}

/* ════════════════════════════════════════
   FOOTER — clean green & white
   ════════════════════════════════════════ */
.rcjy-footer {{
  background: #1B8354;
  margin: 3rem -1.5rem -3rem;
  font-family: 'IBM Plex Sans','IBM Plex Sans Arabic',sans-serif;
}}
.rcjy-ftr-main {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1280px;
  margin: 0 auto;
  padding: 1.5rem 2.5rem;
  gap: 2rem;
  flex-wrap: wrap;
}}
.rcjy-ftr-left {{
  display: flex;
  flex-direction: column;
  gap: .5rem;
}}
.rcjy-ftr-copy {{
  color: rgba(255,255,255,.85);
  font-size: .82rem;
  font-weight: 500;
}}
.rcjy-ftr-links {{
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
}}
.rcjy-ftr-links a {{
  color: rgba(255,255,255,.65);
  text-decoration: none;
  font-size: .78rem;
  transition: color .2s;
}}
.rcjy-ftr-links a:hover {{ color: #fff; }}
.rcjy-ftr-logos {{
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-shrink: 0;
}}
.rcjy-ftr-rcjy {{ height: 44px; display: block; }}
.rcjy-ftr-divv {{ width: 1px; height: 40px; background: rgba(255,255,255,.3); }}
.rcjy-ftr-vision {{ height: 44px; display: block; }}

/* ════════════════════════════════════════
   RESPONSIVE
   ════════════════════════════════════════ */
@media (max-width: 760px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 0 .75rem 2rem !important; }}
  .rcjy-nav {{ margin: 0 -.75rem 1rem; }}
  .rcjy-nav-inner {{ padding: 0 .75rem; gap: .5rem; min-height: 56px; flex-wrap: wrap; }}
  .rcjy-nav-item {{ font-size: .78rem !important; padding: 7px 9px !important; }}
  .rcjy-nav-logo {{ height: 36px; }}
  .rcjy-nav-right {{ gap: .5rem; }}
  .rcjy-footer {{ margin: 3rem -.75rem -3rem; }}
  .rcjy-ftr-main {{ padding: 1.25rem 1rem; flex-direction: column; align-items: flex-start; }}
  .rcjy-ftr-rcjy, .rcjy-ftr-vision {{ height: 36px; }}
}}
@media (max-width: 480px) {{
  .rcjy-nav-links {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
}}
</style>
""", unsafe_allow_html=True)

# ── NAVBAR (pure HTML + URL params) ───────────────────────────────────────────
active_tab = _qp.get("tab", "text")
if active_tab not in ("text", "image", "video", "voice", "podcast"):
    active_tab = "text"
lang = _qp.get("outlang", "en")
if lang not in ("en", "ar"):
    lang = "en"
_nl = st.session_state.ui_lang  # current UI lang


def _ni(key, label):
    """One nav item — target=_self keeps navigation in the same tab."""
    cls = "rcjy-nav-item rcjy-nav-active" if key == active_tab else "rcjy-nav-item"
    return (f'<li><a href="?tab={key}&lang={_nl}&outlang={lang}" '
            f'class="{cls}" target="_self">{label}</a></li>')


# UI language — single link showing the OTHER language (RCJY site style)
_other_lang_text = "العربية" if _nl == "en" else "English"
_other_lang_href = f"?tab={active_tab}&lang={'ar' if _nl == 'en' else 'en'}&outlang={lang}"

# Output language — segmented toggle, active one highlighted
_out_en_cls = "rcjy-out-opt rcjy-out-active" if lang == "en" else "rcjy-out-opt"
_out_ar_cls = "rcjy-out-opt rcjy-out-active" if lang == "ar" else "rcjy-out-opt"
_out_en_href = f"?tab={active_tab}&lang={_nl}&outlang=en"
_out_ar_href = f"?tab={active_tab}&lang={_nl}&outlang=ar"

_VISION_LOGO = "https://www.rcjy.gov.sa/documents/d/rcjy-internet/vision_logo"

st.markdown(f"""
<nav class="rcjy-nav">
  <div class="rcjy-nav-inner">
    <a href="?tab={active_tab}&lang={_nl}&outlang={lang}" class="rcjy-nav-logo-link" target="_self">
      <img class="rcjy-nav-logo" src="{RCJY_LOGO_URL}" alt="RCJY"
           onerror="this.style.display='none'">
    </a>
    <ul class="rcjy-nav-links">
      {_ni("text",    L["tab_text"])}
      {_ni("image",   L["tab_image"])}
      {_ni("video",   L["tab_video"])}
      {_ni("voice",   L["tab_voice"])}
      {_ni("podcast", L["tab_podcast"])}
    </ul>
    <div class="rcjy-nav-right">
      <a href="{_other_lang_href}" class="rcjy-lang-link" target="_self">{_other_lang_text}</a>
      <div class="rcjy-outlang">
        <a href="{_out_en_href}" class="{_out_en_cls}" target="_self">EN</a>
        <a href="{_out_ar_href}" class="{_out_ar_cls}" target="_self">عر</a>
      </div>
    </div>
  </div>
</nav>
""", unsafe_allow_html=True)

if not _api_ok:
    st.warning(L["warn_api"])


# ── SHARED HELPERS ────────────────────────────────────────────────────────────
def _tags(*names):
    html = "".join(f'<span class="mtag">{n}</span>' for n in names)
    st.markdown(f'<div class="mtags">{html}</div>', unsafe_allow_html=True)


def _ctx_widget():
    """Reference material expander — same keys across tabs so state is shared."""
    with st.expander(L["context_label"], expanded=False):
        st.caption(L["context_hint"])
        _cu, _cf = st.columns(2, gap="medium")
        with _cu:
            url = st.text_input(L["url_label"], placeholder=L["url_placeholder"], key="input_url")
        with _cf:
            files = st.file_uploader(
                L["attach_label"], type=SUPPORTED_FILE_TYPES,
                accept_multiple_files=True, key="input_files",
            )
        if files:
            st.caption(f"{L['attached']}: {', '.join(f.name for f in files)}")
        return url, files


def _load_ctx(url, files):
    ctx, _ = get_content_from_input(text="", url=url, files=files)
    has_ctx = bool(ctx and ctx != "No content provided.")
    if has_ctx:
        st.markdown(
            f'<span class="ctx-badge">✦ {L["context_loaded"]} — {len(ctx):,} {L["chars"]}</span>',
            unsafe_allow_html=True,
        )
    return ctx, has_ctx


# ════════════════════════════════════════════════════════════════════════════
#  TEXT
# ════════════════════════════════════════════════════════════════════════════
if active_tab == "text":
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

    with st.container(border=True):
        _tags("Gemini 3 Pro", "Gemini 3 Flash")
        _c1, _c2, _c3 = st.columns(3)
        with _c1:
            text_type = _type_map[st.selectbox(L["text_type_label"], list(_type_map), key="text_type")]
        with _c2:
            text_tone = _tone_map[st.selectbox(L["text_tone_label"], list(_tone_map), key="text_tone")]
        with _c3:
            _ms = st.selectbox(L["text_model_label"], ["Pro", "Flash"], key="text_model")
            text_model = "pro" if _ms == "Pro" else "flash"

        st.divider()

        text_prompt = st.text_area(
            L["prompt_label"], key="prompt_text",
            placeholder=L["prompt_ph_text"], height=160,
        )
        input_url, input_files = _ctx_widget()
        ctx_text, has_ctx = _load_ctx(input_url, input_files)

    if st.button(L["btn_text"], use_container_width=True, key="btn_text"):
        if not text_prompt.strip() and not has_ctx:
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_text"]):
                try:
                    st.session_state.result_text = generate_text(
                        prompt=text_prompt.strip() or "Summarize the provided content",
                        context_text=ctx_text if has_ctx else "",
                        url=input_url or "", files=input_files,
                        text_type=text_type, tone=text_tone,
                        model=text_model, lang=lang,
                    )
                except Exception as e:
                    logger.exception("Text generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_text:
        with st.container(border=True):
            st.markdown(st.session_state.result_text)
        st.download_button(
            L["btn_download"], data=st.session_state.result_text,
            file_name="rcjy_content.txt", mime="text/plain", key="dl_text",
        )

# ════════════════════════════════════════════════════════════════════════════
#  IMAGE
# ════════════════════════════════════════════════════════════════════════════
elif active_tab == "image":
    with st.container(border=True):
        _tags("Imagen 4 Fast", "Imagen 4", "Imagen 4 Ultra", "Nano Banana")
        _i1, _i2 = st.columns(2)
        with _i1:
            img_model = st.selectbox(
                L["model_label"],
                ["imagen_fast", "imagen", "imagen_ultra", "nano_banana", "nano_banana_pro"],
                format_func=lambda x: {
                    "nano_banana_pro": "Nano Banana Pro — 4K",
                    "imagen_fast":     "Imagen 4 Fast",
                    "imagen":          "Imagen 4 Flagship",
                    "imagen_ultra":    "Imagen 4 Ultra",
                    "nano_banana":     "Nano Banana",
                }[x],
                key="img_model",
            )
        with _i2:
            img_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16", "1:1", "4:3", "3:4"], key="img_aspect")

        st.divider()

        img_prompt = st.text_area(
            L["prompt_label"], key="prompt_image",
            placeholder=L["prompt_ph_image"], height=160,
        )
        input_url, input_files = _ctx_widget()
        ctx_text, has_ctx = _load_ctx(input_url, input_files)

    if st.button(L["btn_image"], use_container_width=True, key="btn_img"):
        if not img_prompt.strip():
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_image"]):
                try:
                    data, mime = generate_image(
                        prompt=img_prompt.strip(),
                        context_text=ctx_text if has_ctx else "",
                        files=input_files, model=img_model,
                        aspect_ratio=img_aspect, lang=lang,
                    )
                    st.session_state.result_image = (data, mime)
                except Exception as e:
                    logger.exception("Image generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_image:
        st.image(st.session_state.result_image[0], use_container_width=True)
        st.download_button(
            L["btn_download"], data=st.session_state.result_image[0],
            file_name="rcjy_image.png", mime="image/png", key="dl_img",
        )

# ════════════════════════════════════════════════════════════════════════════
#  VIDEO
# ════════════════════════════════════════════════════════════════════════════
elif active_tab == "video":
    with st.container(border=True):
        _tags("Veo 3.1 Standard", "Veo 3.1 Fast", "Up to 4K", "Up to 8s")
        _v1, _v2, _v3, _v4 = st.columns(4)
        with _v1:
            _vm = st.selectbox(L["video_model_label"], ["Standard", "Fast"], key="vid_model")
            vid_model = "standard" if _vm == "Standard" else "fast"
        with _v2:
            vid_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16"], key="vid_aspect")
        with _v3:
            vid_res = st.selectbox(L["resolution_label"], ["720p", "1080p", "4K"], index=1, key="vid_res")
        with _v4:
            # 1080p and 4K require 8s per Veo API docs
            if vid_res in ("1080p", "4K"):
                vid_dur = st.selectbox(L["duration_label"], ["8"], key="vid_dur_hi")
            else:
                vid_dur = st.selectbox(L["duration_label"], ["4", "6", "8"], index=2, key="vid_dur_lo")

        st.divider()

        vid_prompt = st.text_area(
            L["prompt_label"], key="prompt_video",
            placeholder=L["prompt_ph_video"], height=160,
        )
        input_url, input_files = _ctx_widget()
        ctx_text, has_ctx = _load_ctx(input_url, input_files)

    if st.button(L["btn_video"], use_container_width=True, key="btn_vid"):
        if not vid_prompt.strip():
            st.warning(L["warn_prompt"])
        else:
            with st.spinner(L["spin_video"]):
                try:
                    data, mime = generate_video(
                        prompt=vid_prompt.strip(),
                        context_text=ctx_text if has_ctx else "",
                        aspect_ratio=vid_aspect, duration=vid_dur,
                        resolution=vid_res.lower(), model=vid_model, lang=lang,
                    )
                    st.session_state.result_video = (data, mime)
                except Exception as e:
                    logger.exception("Video generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_video:
        st.video(st.session_state.result_video[0])
        st.download_button(
            L["btn_download"], data=st.session_state.result_video[0],
            file_name="rcjy_video.mp4", mime="video/mp4", key="dl_vid",
        )

# ════════════════════════════════════════════════════════════════════════════
#  VOICE  — single prompt, no duplicate textarea
# ════════════════════════════════════════════════════════════════════════════
elif active_tab == "voice":
    _voice_opts_v = {
        "Kore ♀":    "Kore",
        "Aoede ♀":   "Aoede",
        "Leda ♀":    "Leda",
        "Zephyr ♀":  "Zephyr",
        "Schedar ♀": "Schedar",
        "Puck ♂":    "Puck",
        "Charon ♂":  "Charon",
        "Fenrir ♂":  "Fenrir",
        "Orus ♂":    "Orus",
        "Perseus ♂": "Perseus",
    }
    with st.container(border=True):
        _tags("Gemini TTS Flash", "Gemini TTS Pro")
        _o1, _o2, _o3 = st.columns(3)
        with _o1:
            _vsel = st.selectbox(
                L["voice_label"], list(_voice_opts_v), key="voice_name_sel",
            )
            voice_name = _voice_opts_v[_vsel]
        with _o2:
            tts_quality = st.selectbox(L["quality_label"], ["Flash", "Pro"], key="tts_q")
        with _o3:
            style_hint = st.text_input(
                L["style_label"], placeholder=L["style_placeholder"], key="voice_style",
            )

        st.divider()

        voice_prompt = st.text_area(
            L["prompt_label"], key="prompt_voice",
            placeholder=L["prompt_ph_voice"], height=200,
        )

    if st.button(L["btn_voice"], use_container_width=True, key="btn_voice"):
        if not voice_prompt.strip():
            st.warning(L["warn_text"])
        else:
            with st.spinner(L["spin_voice"]):
                try:
                    data, mime = generate_voice(
                        text=voice_prompt.strip(), context_text="",
                        voice_name=voice_name, style_hint=style_hint,
                        tts_model="pro" if tts_quality == "Pro" else "flash",
                        lang=lang,
                    )
                    st.session_state.result_voice = (data, mime)
                except Exception as e:
                    logger.exception("Voice generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_voice:
        st.audio(st.session_state.result_voice[0], format="audio/wav")
        st.download_button(
            L["btn_download"], data=st.session_state.result_voice[0],
            file_name="rcjy_voice.wav", mime="audio/wav", key="dl_voice",
        )

# ════════════════════════════════════════════════════════════════════════════
#  PODCAST
# ════════════════════════════════════════════════════════════════════════════
elif active_tab == "podcast":
    _pod_len_opts = [L["length_short"], L["length_standard"]]
    _voice_opts   = {
        "Kore ♀":    "Kore",
        "Aoede ♀":   "Aoede",
        "Leda ♀":    "Leda",
        "Zephyr ♀":  "Zephyr",
        "Schedar ♀": "Schedar",
        "Puck ♂":    "Puck",
        "Charon ♂":  "Charon",
        "Fenrir ♂":  "Fenrir",
        "Orus ♂":    "Orus",
        "Perseus ♂": "Perseus",
    }

    with st.container(border=True):
        _tags("Gemini 3 Flash", "Multi-Speaker TTS")
        _p1, _p2, _p3 = st.columns(3)
        with _p1:
            pod_len_idx = st.selectbox(
                L["length_label"], range(len(_pod_len_opts)),
                format_func=lambda i: _pod_len_opts[i], key="pod_len",
            )
        with _p2:
            pod_host = _voice_opts[st.selectbox(L["host_label"],  list(_voice_opts), index=0, key="pod_host")]
        with _p3:
            pod_guest= _voice_opts[st.selectbox(L["guest_label"], list(_voice_opts), index=3, key="pod_guest")]

        st.divider()

        pod_prompt = st.text_area(
            L["prompt_label"], key="prompt_podcast",
            placeholder=L["prompt_ph_podcast"], height=160,
        )
        input_url, input_files = _ctx_widget()
        ctx_text, has_ctx = _load_ctx(input_url, input_files)

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
                        url=input_url or "", files=input_files,
                        length="short" if pod_len_idx == 0 else "standard",
                        voice_host=pod_host, voice_guest=pod_guest, lang=lang,
                    )
                    st.session_state.result_podcast = (data, mime)
                except Exception as e:
                    logger.exception("Podcast generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_podcast:
        st.audio(st.session_state.result_podcast[0], format="audio/wav")
        st.download_button(
            L["btn_download"], data=st.session_state.result_podcast[0],
            file_name="rcjy_podcast.wav", mime="audio/wav", key="dl_pod",
        )

# ── FOOTER ────────────────────────────────────────────────────────────────────
_ftr_html = (
    '<div class="rcjy-footer"><div class="rcjy-ftr-main">'
    '<div class="rcjy-ftr-left">'
    '<span class="rcjy-ftr-copy">All rights reserved to the Royal Commission for Jubail and Yanbu &copy; 2026</span>'
    '<div class="rcjy-ftr-links">'
    '<a href="https://www.rcjy.gov.sa/en/privacy-policy" target="_blank" rel="noopener">Privacy Policy</a>'
    '<a href="https://www.rcjy.gov.sa/en/terms-and-conditions" target="_blank" rel="noopener">Terms &amp; Conditions</a>'
    '<a href="https://www.rcjy.gov.sa/en/home" target="_blank" rel="noopener">RCJY Official Website</a>'
    '</div></div>'
    '<div class="rcjy-ftr-logos">'
    f'<img class="rcjy-ftr-rcjy" src="{RCJY_LOGO_URL}" alt="RCJY" onerror="this.style.display=\'none\'">'
    '<div class="rcjy-ftr-divv"></div>'
    f'<img class="rcjy-ftr-vision" src="{_VISION_LOGO}" alt="Vision 2030" onerror="this.style.display=\'none\'">'
    '</div>'
    '</div></div>'
)
st.markdown(_ftr_html, unsafe_allow_html=True)
