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
        "tab_text":               "✍️  Text",
        "tab_image":              "🖼️  Image",
        "tab_video":              "🎬  Video",
        "tab_voice":              "🎙️  Voice",
        "tab_podcast":            "🎧  Podcast",
        "prompt_label":           "Prompt",
        "prompt_ph_text":         "Describe what you want to create…\ne.g. A press release about Jubail Industrial City's new green hydrogen facility.",
        "prompt_ph_image":        "Describe the image…\ne.g. Aerial golden-hour view of Jubail Industrial City, petrochemical towers, calm sea.",
        "prompt_ph_video":        "Describe the video scene…\ne.g. Cinematic drone flight over Yanbu Industrial Port at sunrise, dramatic sky.",
        "prompt_ph_voice":        "Enter the text to be spoken…",
        "prompt_ph_podcast":      "Describe the podcast topic…\ne.g. The economic transformation of Jubail and Yanbu and their role in Vision 2030.",
        "model_label":            "Model",
        "aspect_label":           "Aspect Ratio",
        "duration_label":         "Duration (sec)",
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
        "footer_dept":            "Communication & Media Department",
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
        "tab_text":               "✍️  نص",
        "tab_image":              "🖼️  صورة",
        "tab_video":              "🎬  فيديو",
        "tab_voice":              "🎙️  صوت",
        "tab_podcast":            "🎧  بودكاست",
        "prompt_label":           "الوصف",
        "prompt_ph_text":         "اكتب وصفاً لما تريد إنشاءه…\nمثال: بيان صحفي عن منشأة الهيدروجين الأخضر الجديدة في الجبيل.",
        "prompt_ph_image":        "اكتب وصفاً للصورة…\nمثال: منظر جوي لمدينة الجبيل الصناعية عند الغسق.",
        "prompt_ph_video":        "اكتب وصفاً لمشهد الفيديو…\nمثال: تحليق سينمائي فوق ميناء ينبع عند الفجر.",
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
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "text"
for _k in ("result_text", "result_image", "result_video", "result_voice", "result_podcast"):
    if _k not in st.session_state:
        st.session_state[_k] = None

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
  color: #1A1A1A;
  background: #F5F3F0 !important;
  -webkit-font-smoothing: antialiased;
  direction: {_dir};
}}
#MainMenu, footer, header {{ visibility: hidden; }}

/* Centre & constrain the app content */
[data-testid="stMainBlockContainer"] {{
  max-width: 1060px !important;
  margin: 0 auto !important;
  padding: 0 1.5rem 3rem !important;
  background: #F5F3F0 !important;
}}

/* ════════════════════════════════════════
   HEADER
   ════════════════════════════════════════ */
.rcjy-hdr {{
  /* Full-bleed by matching the container's own horizontal padding */
  margin: 0 -1.5rem;
  background:
    radial-gradient(ellipse 55% 130% at 95% 50%,  rgba(245,130,31,.20) 0%, transparent 60%),
    radial-gradient(ellipse 30% 80%  at 80% 5%,   rgba(245,160,60,.12) 0%, transparent 55%),
    linear-gradient(140deg, #0F0D0B 0%, #1A1512 40%, #2A1F18 75%, #352820 100%);
  /* Dot-grid pattern from RCJY logo motif */
  background-image:
    radial-gradient(circle, rgba(255,255,255,.06) 1.2px, transparent 1.2px),
    radial-gradient(ellipse 55% 130% at 95% 50%,  rgba(245,130,31,.20) 0%, transparent 60%),
    radial-gradient(ellipse 30% 80%  at 80% 5%,   rgba(245,160,60,.12) 0%, transparent 55%),
    linear-gradient(140deg, #0F0D0B 0%, #1A1512 40%, #2A1F18 75%, #352820 100%);
  background-size: 22px 22px, auto, auto, auto;
  border-radius: 0 0 20px 20px;
  overflow: hidden;
  position: relative;
}}
.hdr-inner {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.2rem 2rem 1.3rem;
  position: relative;
  z-index: 1;
  gap: 1rem;
  flex-direction: {"row-reverse" if is_ar else "row"};
}}
.hdr-brand {{
  display: flex;
  align-items: center;
  gap: .9rem;
  flex-direction: {"row-reverse" if is_ar else "row"};
}}
.hdr-brand img {{
  height: 54px;
  filter: drop-shadow(0 2px 10px rgba(0,0,0,.5));
}}
.hdr-brand-text h1 {{
  color: #fff !important;
  font-size: 1.3rem !important;
  font-weight: 700 !important;
  letter-spacing: -.02em;
  margin: 0 !important;
  line-height: 1.2;
}}
.hdr-brand-text p {{
  color: rgba(255,255,255,.5);
  font-size: .75rem;
  margin: .12rem 0 0;
  letter-spacing: .05em;
  text-transform: uppercase;
}}
/* Concentric-ring decoration — RCJY logo circles motif */
.hdr-deco {{
  position: absolute;
  {"left" if is_ar else "right"}: -10px;
  top: 50%;
  transform: translateY(-50%);
  opacity: .45;
  pointer-events: none;
}}
/* Brand stripe — RCJY orange accent */
.gold-stripe {{
  margin: 0 -1.5rem;
  height: 3px;
  background: linear-gradient(90deg,
    #0F0D0B 0%, #D97B1F 20%, #F5821F 50%, #E88C20 75%, #0F0D0B 100%);
}}

/* ════════════════════════════════════════
   LANGUAGE / CONTROLS ROW
   ════════════════════════════════════════ */
.controls-row {{
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  padding: .9rem 0 .5rem;
  flex-direction: {"row-reverse" if is_ar else "row"};
}}

/* ════════════════════════════════════════
   SEGMENTED CONTROL (category nav)
   ════════════════════════════════════════ */
[data-testid="stSegmentedControl"] {{
  width: 100%;
  margin-bottom: .25rem;
}}
[data-testid="stSegmentedControl"] > div {{
  width: 100%;
}}
/* The pill container */
[data-testid="stSegmentedControl"] [role="radiogroup"],
[data-testid="stSegmentedControl"] > div > div {{
  background: #EBE8E5 !important;
  border-radius: 14px !important;
  padding: 4px !important;
  gap: 3px !important;
  width: 100% !important;
  display: flex !important;
}}
/* Each option */
[data-testid="stSegmentedControl"] label {{
  flex: 1 1 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .88rem !important;
  font-weight: 600 !important;
  color: #5C5652 !important;
  border-radius: 11px !important;
  padding: 10px 6px !important;
  cursor: pointer !important;
  transition: color .15s !important;
  white-space: nowrap !important;
  letter-spacing: .01em !important;
}}
[data-testid="stSegmentedControl"] label > div:first-child {{
  display: none !important;
}}
/* Active option */
[data-testid="stSegmentedControl"] label:has(input:checked) {{
  background: #fff !important;
  color: #E06B0A !important;
  font-weight: 700 !important;
  box-shadow: 0 1px 6px rgba(0,0,0,.13), 0 0 0 1px rgba(0,0,0,.04),
              inset 0 -2px 0 #F5821F !important;
}}
[data-testid="stSegmentedControl"] label:hover:not(:has(input:checked)) {{
  color: #F5821F !important;
}}

/* ════════════════════════════════════════
   BORDERED CONTAINER (content card)
   ════════════════════════════════════════ */
[data-testid="stVerticalBlockBorderWrapper"] {{
  border: 1.5px solid #E8E4E0 !important;
  border-radius: 18px !important;
  background: #fff !important;
  box-shadow: 0 2px 20px rgba(0,0,0,.055) !important;
  overflow: hidden !important;
  margin-top: .75rem !important;
  transition: box-shadow .25s ease, border-color .25s ease !important;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
  box-shadow: 0 4px 28px rgba(245,130,31,.08), 0 2px 12px rgba(0,0,0,.06) !important;
  border-color: #DDD8D3 !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] {{
  padding: 1.75rem 1.75rem 1.5rem !important;
  gap: 1rem !important;
}}

/* ════════════════════════════════════════
   TYPOGRAPHY — all labels
   ════════════════════════════════════════ */
.stSelectbox > label,
.stTextArea  > label,
.stTextInput > label {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .73rem !important;
  font-weight: 700 !important;
  letter-spacing: .07em !important;
  text-transform: uppercase !important;
  color: #72615E !important;
  margin-bottom: .3rem !important;
}}
.stCaption, [data-testid="stCaptionContainer"] p {{
  font-size: .8rem !important;
  color: #A59B99 !important;
  line-height: 1.5 !important;
}}

/* ════════════════════════════════════════
   INPUTS
   ════════════════════════════════════════ */
.stTextArea textarea {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: 1rem !important;
  font-weight: 400 !important;
  line-height: 1.7 !important;
  color: #1A1A1A !important;
  background: #FAFAFA !important;
  border: 1.5px solid #E8E4E0 !important;
  border-radius: 12px !important;
  padding: .9rem 1rem !important;
  transition: border-color .2s, box-shadow .2s !important;
  caret-color: #F5821F;
}}
.stTextArea textarea:focus {{
  background: #fff !important;
  border-color: #F5821F !important;
  box-shadow: 0 0 0 4px rgba(245,130,31,.10) !important;
  outline: none !important;
}}
.stTextArea textarea::placeholder {{
  color: #C0C8D0 !important;
  font-size: .95rem !important;
}}
.stTextInput input {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .9rem !important;
  color: #1A1A1A !important;
  background: #FAFAFA !important;
  border: 1.5px solid #E8E4E0 !important;
  border-radius: 10px !important;
  padding: .6rem .9rem !important;
  transition: border-color .2s, box-shadow .2s !important;
}}
.stTextInput input:focus {{
  background: #fff !important;
  border-color: #F5821F !important;
  box-shadow: 0 0 0 3px rgba(245,130,31,.10) !important;
  outline: none !important;
}}

/* ════════════════════════════════════════
   SELECTBOX
   ════════════════════════════════════════ */
.stSelectbox [data-baseweb="select"] > div {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: .9rem !important;
  font-weight: 500 !important;
  color: #1A1A1A !important;
  background: #FAFAFA !important;
  border: 1.5px solid #E8E4E0 !important;
  border-radius: 10px !important;
  transition: border-color .2s !important;
}}
.stSelectbox [data-baseweb="select"]:focus-within > div {{
  border-color: #F5821F !important;
  box-shadow: 0 0 0 3px rgba(245,130,31,.10) !important;
}}

/* ════════════════════════════════════════
   MODEL TAGS
   ════════════════════════════════════════ */
.mtags {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: .5rem; }}
.mtag {{
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: .67rem;
  font-weight: 700;
  letter-spacing: .05em;
  text-transform: uppercase;
  color: #8B4F15;
  background: #FFF4E6;
  border: 1px solid #FFD4A8;
  border-radius: 5px;
  padding: .18rem .55rem;
  display: inline-block;
  transition: background .15s, color .15s;
}}
.mtag:hover {{
  background: #FFECD2;
  color: #D96A0F;
}}

/* ════════════════════════════════════════
   DIVIDER inside container
   ════════════════════════════════════════ */
hr {{ border-color: #F3F4F6 !important; margin: .25rem 0 !important; }}

/* ════════════════════════════════════════
   GENERATE BUTTON
   ════════════════════════════════════════ */
.stButton > button {{
  font-family: 'IBM Plex Sans', 'IBM Plex Sans Arabic', sans-serif !important;
  font-size: 1rem !important;
  font-weight: 700 !important;
  letter-spacing: .025em !important;
  color: #fff !important;
  background: linear-gradient(135deg, #F5821F 0%, #D96A0F 100%) !important;
  border: none !important;
  border-radius: 12px !important;
  padding: .9rem 2.5rem !important;
  min-height: 54px !important;
  width: 100%;
  box-shadow: 0 4px 18px rgba(245,130,31,.30), 0 1px 3px rgba(0,0,0,.15) !important;
  transition: transform .15s ease, box-shadow .15s ease, background .2s ease !important;
  cursor: pointer !important;
  position: relative !important;
  overflow: hidden !important;
}}
.stButton > button:hover {{
  background: linear-gradient(135deg, #F99340 0%, #E06B0A 100%) !important;
  box-shadow: 0 8px 28px rgba(245,130,31,.40), 0 2px 6px rgba(0,0,0,.18) !important;
  transform: translateY(-2px) !important;
}}
.stButton > button:active  {{ transform: translateY(0) !important; }}
.stButton > button:focus   {{
  outline: 3px solid rgba(245,130,31,.40) !important;
  outline-offset: 3px !important;
}}

/* ════════════════════════════════════════
   DOWNLOAD BUTTON
   ════════════════════════════════════════ */
.stDownloadButton > button {{
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: .875rem !important;
  font-weight: 600 !important;
  background: #1A1A1A !important;
  color: #fff !important;
  border: none !important;
  border-radius: 10px !important;
  padding: .6rem 1.75rem !important;
  box-shadow: 0 2px 8px rgba(0,0,0,.15) !important;
  transition: transform .15s, box-shadow .15s !important;
}}
.stDownloadButton > button:hover {{
  background: #2D2D2D !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 14px rgba(0,0,0,.2) !important;
}}

/* ════════════════════════════════════════
   FILE UPLOADER
   ════════════════════════════════════════ */
[data-testid="stFileUploader"] section {{
  border: 2px dashed #D5CFC9 !important;
  border-radius: 12px !important;
  background: #FAFAFA !important;
  transition: border-color .2s, background .2s !important;
}}
[data-testid="stFileUploader"] section:hover {{
  border-color: #F5821F !important;
  background: #FFF8F0 !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] div small,
[data-testid="stFileUploaderDropzone"] small {{
  display: none !important;
}}

/* ════════════════════════════════════════
   EXPANDER (reference material)
   ════════════════════════════════════════ */
[data-testid="stExpander"] {{
  border: 1px solid #E8E4E0 !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: .88rem !important;
  font-weight: 600 !important;
  color: #4B4845 !important;
  padding: .7rem 1rem !important;
  background: #FAFAFA !important;
}}
[data-testid="stExpander"] summary:hover {{ color: #F5821F !important; }}
[data-testid="stExpander"] > div > div {{
  padding: .9rem 1rem !important;
}}

/* ════════════════════════════════════════
   CONTEXT BADGE
   ════════════════════════════════════════ */
.ctx-badge {{
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  background: #FFF8F0;
  color: #D96A0F;
  border: 1px solid #FFE0B2;
  border-radius: 20px;
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
  border: 1.5px solid #E8E4E0;
  border-radius: 16px;
  padding: 1.5rem 1.75rem;
  margin-top: 1rem;
  box-shadow: 0 2px 16px rgba(0,0,0,.05);
  border-top: 3px solid #F5821F;
}}
.result-wrap p   {{ font-size: .9375rem !important; line-height: 1.8 !important; color: #1A1A1A !important; }}
.result-wrap li  {{ font-size: .9375rem !important; line-height: 1.8 !important; color: #1A1A1A !important; }}
.result-wrap h1,
.result-wrap h2,
.result-wrap h3  {{ color: #1A1A1A !important; font-weight: 700 !important; }}

/* ════════════════════════════════════════
   ALERTS & SPINNER
   ════════════════════════════════════════ */
.stAlert {{ border-radius: 12px !important; }}
.stAlert p {{ font-size: .9rem !important; }}
.stSpinner > div {{ border-top-color: #F5821F !important; }}

/* ════════════════════════════════════════
   FOOTER
   ════════════════════════════════════════ */
.app-footer {{
  text-align: center;
  padding: 2rem 1rem 1rem;
  margin-top: 2rem;
  border-top: 2px solid transparent;
  border-image: linear-gradient(90deg, transparent 10%, #E8E4E0 30%, #F5821F 50%, #E8E4E0 70%, transparent 90%) 1;
  color: #A59B99;
  font-size: .78rem;
  line-height: 2;
}}
.app-footer strong {{ color: #4B4845; }}
.app-footer a {{ color: #F5821F; text-decoration: none; font-weight: 500; }}
.app-footer a:hover {{ text-decoration: underline; }}

/* ════════════════════════════════════════
   SIDEBAR
   ════════════════════════════════════════ */
[data-testid="stSidebar"] {{ background: #fff; }}

/* ════════════════════════════════════════
   RESPONSIVE
   ════════════════════════════════════════ */
@media (max-width: 760px) {{
  .hdr-inner {{ padding: 1rem; flex-direction: column !important; }}
  [data-testid="stMainBlockContainer"] {{ padding: 0 .75rem 2rem !important; }}
  .gold-stripe, .rcjy-hdr {{ margin: 0 -.75rem; }}
  [data-testid="stSegmentedControl"] label {{
    font-size: .78rem !important;
    padding: 8px 4px !important;
  }}
}}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
_deco_svg = """
<svg class="hdr-deco" width="220" height="120"
     viewBox="0 0 220 120" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="170" cy="60" r="100" stroke="rgba(255,255,255,.04)" stroke-width="1.5"/>
  <circle cx="170" cy="60" r="78" stroke="rgba(255,255,255,.05)" stroke-width="1.5"/>
  <circle cx="170" cy="60" r="57" stroke="rgba(245,130,31,.12)" stroke-width="1.5"/>
  <circle cx="170" cy="60" r="38" stroke="rgba(255,255,255,.06)" stroke-width="1.5"/>
  <circle cx="170" cy="60" r="22" stroke="rgba(245,130,31,.16)" stroke-width="1.5"/>
  <circle cx="170" cy="60" r="8"  fill="rgba(245,130,31,.18)"/>
  <rect x="22" y="52" width="4" height="32" rx="1" fill="rgba(245,130,31,.07)"/>
  <rect x="30" y="40" width="4" height="44" rx="1" fill="rgba(255,255,255,.06)"/>
  <rect x="38" y="56" width="4" height="28" rx="1" fill="rgba(245,130,31,.05)"/>
  <rect x="46" y="36" width="5" height="48" rx="1" fill="rgba(255,255,255,.07)"/>
  <rect x="55" y="48" width="4" height="36" rx="1" fill="rgba(245,130,31,.06)"/>
  <rect x="63" y="44" width="4" height="40" rx="1" fill="rgba(255,255,255,.05)"/>
  <circle cx="80" cy="22" r="2.5" fill="rgba(245,130,31,.09)"/>
  <circle cx="93" cy="22" r="2.5" fill="rgba(255,255,255,.07)"/>
  <circle cx="80" cy="35" r="2.5" fill="rgba(255,255,255,.06)"/>
  <circle cx="93" cy="35" r="2.5" fill="rgba(245,130,31,.07)"/>
  <rect x="30" y="18" width="10" height="10"
        transform="rotate(45 35 23)" stroke="rgba(245,130,31,.08)" stroke-width="1" fill="none"/>
</svg>
"""

st.markdown(f"""
<div class="rcjy-hdr">
  {_deco_svg}
  <div class="hdr-inner">
    <div class="hdr-brand">
      <img src="{RCJY_LOGO_URL}" alt="RCJY"
           onerror="this.style.display='none'">
      <div class="hdr-brand-text">
        <h1>{L['app_name']}</h1>
        <p>{L['dept']}</p>
      </div>
    </div>
  </div>
</div>
<div class="gold-stripe"></div>
""", unsafe_allow_html=True)

# ── LANGUAGE CONTROLS ─────────────────────────────────────────────────────────
_lc1, _lc2, _lc_gap = st.columns([1, 1, 5])
with _lc1:
    _new_lang = st.selectbox(
        L["lang_label"], ["English", "العربية"],
        index=1 if is_ar else 0, key="lang_sel",
    )
    _tgt = "ar" if _new_lang == "العربية" else "en"
    if _tgt != st.session_state.ui_lang:
        st.session_state.ui_lang = _tgt
        st.rerun()
with _lc2:
    _out = st.selectbox(
        L["output_lang_label"], ["English", "العربية"],
        index=0, key="output_lang_sel",
    )
lang = "ar" if _out == "العربية" else "en"

if not _api_ok:
    st.warning(L["warn_api"])

# ── CATEGORY NAVIGATION ───────────────────────────────────────────────────────
_tab_keys   = ["text", "image", "video", "voice", "podcast"]
_tab_labels = {
    "text":    L["tab_text"],
    "image":   L["tab_image"],
    "video":   L["tab_video"],
    "voice":   L["tab_voice"],
    "podcast": L["tab_podcast"],
}

active_tab = st.segmented_control(
    "Category",
    options=_tab_keys,
    format_func=lambda x: _tab_labels[x],
    key="active_tab",
    default="text",
    label_visibility="collapsed",
)
# Guard: segmented_control returns None when nothing is selected yet
if active_tab is None:
    active_tab = "text"


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
        _tags("Veo 3.1")
        _v1, _v2 = st.columns(2)
        with _v1:
            vid_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16"], key="vid_aspect")
        with _v2:
            vid_dur = st.selectbox(L["duration_label"], ["4", "6", "8"], index=2, key="vid_dur")

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
                        aspect_ratio=vid_aspect, duration=vid_dur, lang=lang,
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
    with st.container(border=True):
        _tags("Gemini TTS Flash", "Gemini TTS Pro", "Chirp 3")
        _o1, _o2, _o3 = st.columns(3)
        with _o1:
            voice_name = st.selectbox(
                L["voice_label"],
                ["Kore", "Puck", "Zephyr", "Charon", "Fenrir",
                 "Aoede", "Leda", "Orus", "Perseus", "Schedar"],
                key="voice_name",
            )
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
        "Kore ♀":   "Kore",  "Aoede ♀":  "Aoede",  "Leda ♀":  "Leda",
        "Puck ♂":   "Puck",  "Charon ♂": "Charon", "Fenrir ♂":"Fenrir",
        "Orus ♂":   "Orus",
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
st.markdown(f"""
<div class="app-footer">
  <strong>{L['footer_org']}</strong><br>
  {L['footer_dept']}<br>
  <span style="font-size:.7rem;color:#D5CFC9;">
    Gemini 3 Pro &nbsp;·&nbsp; Imagen 4 Ultra &nbsp;·&nbsp; Nano Banana
    &nbsp;·&nbsp; Veo 3.1 &nbsp;·&nbsp; Gemini TTS &nbsp;·&nbsp; Gemini 3 Flash
  </span><br>
  <a href="https://www.rcjy.gov.sa/en/" target="_blank" rel="noopener">rcjy.gov.sa</a>
  &nbsp;·&nbsp; © 2026
</div>
""", unsafe_allow_html=True)
