import html as html_mod
import io
import logging
import random
import time

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from rcjy_config import RCJY_LOGO_URL, SUPPORTED_FILE_TYPES, has_credentials
from content_extractor import get_content_from_input
from generators import (
    _sanitize_error,
    generate_image,
    generate_podcast,
    generate_text,
    generate_video,
    generate_voice,
)

try:
    import history
    _history_ok = history.is_available()
    if not _history_ok:
        logging.getLogger("rcjy.app").warning("GCS history not available — falling back to session history")
        import history_local as history
        _history_ok = True
except Exception as _hist_err:
    logging.getLogger("rcjy.app").warning("GCS history import/init failed (%s) — using session history", _hist_err)
    try:
        import history_local as history
        _history_ok = True
    except Exception:
        history = None
        _history_ok = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rcjy.app")

# rate limiting per session
_RATE_COOLDOWN = {"text": 5, "image": 10, "video": 30, "voice": 10, "podcast": 20}

def _rate_check(action: str) -> bool:
    # Returns True if allowed, False if rate limited
    key = f"_last_{action}"
    now = time.time()
    last = st.session_state.get(key, 0)
    cooldown = _RATE_COOLDOWN.get(action, 10)
    if now - last < cooldown:
        remaining = int(cooldown - (now - last))
        msg = f"انتظر {remaining} ثانية" if st.session_state.get("ui_lang") == "ar" else f"Please wait {remaining}s before generating again"
        st.warning(msg)
        return False
    st.session_state[key] = now
    return True

# captcha gate (one-time per session)
def _generate_captcha() -> tuple[bytes, str]:
    # Generate image CAPTCHA with random code
    code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
    w, h = 320, 100
    img = Image.new("RGB", (w, h), color=(249, 250, 251))
    draw = ImageDraw.Draw(img)
    # Try to load a larger font
    _font = None
    for size in (40, 36, 32):
        try:
            _font = ImageFont.truetype("arial.ttf", size)
            break
        except OSError:
            try:
                _font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
                break
            except OSError:
                continue
    if _font is None:
        _font = ImageFont.load_default()
    # Noise lines
    for _ in range(8):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(180, 220), random.randint(180, 220), random.randint(180, 220)), width=2)
    # Draw each character with slight offset and rotation
    char_w = w // (len(code) + 1)
    for i, ch in enumerate(code):
        x = char_w * (i + 1) - char_w // 2 + random.randint(-5, 5)
        y = random.randint(15, 35)
        color = (random.randint(0, 60), random.randint(60, 120), random.randint(0, 80))
        draw.text((x, y), ch, fill=color, font=_font)
    # Noise dots
    for _ in range(150):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        draw.point((x, y), fill=(random.randint(140, 200), random.randint(140, 200), random.randint(140, 200)))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), code

# i18n
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
        "tab_history":            "History",
        "prompt_label":           "Prompt",
        "prompt_ph_text":         "Describe what you want to create…\ne.g. A press release about Jubail Industrial City's role as one of the world's largest industrial hubs.\n\nTip: Output follows your interface language. To override, specify in your prompt (e.g. 'write in Arabic').",
        "prompt_ph_image":        "Describe the image…\ne.g. Aerial golden-hour view of Jubail Industrial City, petrochemical towers, calm sea.",
        "prompt_ph_video":        "Describe the video scene…\ne.g. Cinematic drone flight over Yanbu Industrial Port at sunrise, dramatic sky.",
        "prompt_ph_voice":        "Enter the text to be spoken…\n\nTip: Output follows your interface language. To override, specify in your prompt.",
        "prompt_ph_podcast":      "Describe the podcast topic…\ne.g. The economic transformation of Jubail and Yanbu and their role in Vision 2030.\n\nTip: Output follows your interface language. To override, specify in your prompt.",
        "model_label":            "Model",
        "aspect_label":           "Aspect Ratio",
        "duration_label":         "Duration (sec)",
        "total_duration_label":   "Total Duration",
        "total_dur_8":            "8 seconds",
        "total_dur_15":           "~15 seconds",
        "total_dur_22":           "~22 seconds",
        "total_dur_29":           "~29 seconds",
        "total_dur_43":           "~43 seconds",
        "total_dur_57":           "~57 seconds",
        "total_dur_78":           "~78 seconds",
        "total_dur_99":           "~99 seconds",
        "total_dur_120":          "~120 seconds",
        "total_dur_148":          "~148 seconds",
        "extend_note":            "Extended videos are rendered at 720p. Each step takes 2-5 min.",
        "resolution_label":       "Resolution",
        "video_model_label":      "Video Model",
        "voice_label":            "Voice",
        "quality_label":          "Quality",
        "style_label":            "Delivery Style",
        "style_professional":     "Professional",
        "style_warm":             "Warm",
        "style_authoritative":    "Authoritative",
        "style_conversational":   "Conversational",
        "style_energetic":        "Energetic",
        "style_calm":             "Calm",
        "style_formal":           "Formal",
        "img_generate_new":       "Generate New Image",
        "img_generate_edit":      "Generate / Edit Image",
        "length_label":           "Episode Length",
        "length_short":           "~2 minutes",
        "length_standard":        "~4 minutes",
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
        "warn_api":               "No API credentials configured. Add GCP service account or GEMINI_API_KEY.",
        "spin_text":              "Generating text…",
        "spin_image":             "Generating image…",
        "spin_video":             "Generating video…",
        "spin_video_extend":      "Generating extended video…",
        "spin_voice":             "Generating speech…",
        "spin_podcast":           "Creating podcast… (2–3 min)",
        "footer_org":             "Royal Commission for Jubail and Yanbu",
        "footer_dept":            "General Administration of Communication and Media",
        "hist_title":             "History",
        "hist_total":             "Total",
        "hist_size":              "Storage",
        "hist_filter":            "Filter by type",
        "hist_all":               "All",
        "hist_empty":             "No history yet.",
        "hist_empty_hint":        "Generated content will appear here.",
        "hist_delete":            "Delete",
        "hist_clear":             "Clear All",
        "hist_clear_confirm":     "Are you sure? This cannot be undone.",
        "hist_confirm_yes":       "Yes, delete all",
        "hist_confirm_no":        "Cancel",
        "hist_cleared":           "History cleared.",
        "hist_download":          "Download",
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
        "tab_history":            "السجل",
        "prompt_label":           "الوصف",
        "prompt_ph_text":         "اكتب وصفاً لما تريد إنشاءه…\nمثال: بيان صحفي عن مدينة الجبيل الصناعية ودورها كأحد أكبر المراكز الصناعية في العالم.\n\nتلميح: المخرجات تتبع لغة الواجهة. للتغيير، حدد في الوصف (مثلاً: 'اكتب بالإنجليزية').",
        "prompt_ph_image":        "اكتب وصفاً للصورة…\nمثال: منظر جوي لمدينة الجبيل الصناعية عند الغسق.",
        "prompt_ph_video":        "اكتب وصفاً لمشهد الفيديو…\nمثال: تحليق سينمائي فوق ميناء ينبع عند الفجر.",
        "prompt_ph_voice":        "أدخل النص الذي تريد تحويله إلى صوت…\n\nتلميح: المخرجات تتبع لغة الواجهة. للتغيير، حدد في الوصف.",
        "prompt_ph_podcast":      "اكتب موضوع البودكاست…\nمثال: التحول الاقتصادي لمدينتي الجبيل وينبع ودورهما في رؤية 2030.\n\nتلميح: المخرجات تتبع لغة الواجهة. للتغيير، حدد في الوصف.",
        "model_label":            "النموذج",
        "aspect_label":           "نسبة الأبعاد",
        "duration_label":         "المدة (ثانية)",
        "total_duration_label":   "المدة الإجمالية",
        "total_dur_8":            "٨ ثوانٍ",
        "total_dur_15":           "~١٥ ثانية",
        "total_dur_22":           "~٢٢ ثانية",
        "total_dur_29":           "~٢٩ ثانية",
        "total_dur_43":           "~٤٣ ثانية",
        "total_dur_57":           "~٥٧ ثانية",
        "total_dur_78":           "~٧٨ ثانية",
        "total_dur_99":           "~٩٩ ثانية",
        "total_dur_120":          "~١٢٠ ثانية",
        "total_dur_148":          "~١٤٨ ثانية",
        "extend_note":            "الفيديوهات الممتدة تُعرض بدقة 720p. كل خطوة تستغرق ٢-٥ دقائق.",
        "resolution_label":       "الدقة",
        "video_model_label":      "نموذج الفيديو",
        "voice_label":            "الصوت",
        "quality_label":          "الجودة",
        "style_label":            "أسلوب الأداء",
        "style_professional":     "احترافي",
        "style_warm":             "دافئ",
        "style_authoritative":    "موثوق",
        "style_conversational":   "حواري",
        "style_energetic":        "حيوي",
        "style_calm":             "هادئ",
        "style_formal":           "رسمي",
        "img_generate_new":       "إنشاء صورة جديدة",
        "img_generate_edit":      "إنشاء / تعديل صورة",
        "length_label":           "مدة الحلقة",
        "length_short":           "~٢ دقائق",
        "length_standard":        "~٤ دقائق",
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
        "warn_api":               "لم يتم إعداد بيانات الاعتماد. أضف حساب خدمة GCP أو مفتاح GEMINI_API_KEY.",
        "spin_text":              "جارٍ إنشاء النص…",
        "spin_image":             "جارٍ إنشاء الصورة…",
        "spin_video":             "جارٍ إنشاء الفيديو…",
        "spin_video_extend":      "جارٍ إنشاء فيديو ممتد…",
        "spin_voice":             "جارٍ إنشاء الصوت…",
        "spin_podcast":           "جارٍ إنشاء البودكاست… (٢–٣ دقائق)",
        "footer_org":             "الهيئة الملكية للجبيل وينبع",
        "footer_dept":            "الإدارة العامة للاتصال والإعلام",
        "hist_title":             "السجل",
        "hist_total":             "الإجمالي",
        "hist_size":              "التخزين",
        "hist_filter":            "تصفية حسب النوع",
        "hist_all":               "الكل",
        "hist_empty":             "لا توجد سجلات بعد.",
        "hist_empty_hint":        "المحتوى المُنشأ سيظهر هنا.",
        "hist_delete":            "حذف",
        "hist_clear":             "مسح الكل",
        "hist_clear_confirm":     "هل أنت متأكد؟ لا يمكن التراجع.",
        "hist_confirm_yes":       "نعم، حذف الكل",
        "hist_confirm_no":        "إلغاء",
        "hist_cleared":           "تم مسح السجل.",
        "hist_download":          "تحميل",
    },
}

# config
st.set_page_config(
    page_title="RCJY Media Generator",
    page_icon="https://www.rcjy.gov.sa/o/rcjy-theme/images/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# state
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "en"
for _k in ("result_text", "result_image", "result_video", "result_voice", "result_podcast"):
    if _k not in st.session_state:
        st.session_state[_k] = None

# Sync UI lang from URL params
_qp = st.query_params
_qp_lang = _qp.get("lang", st.session_state.ui_lang)
if _qp_lang not in ("en", "ar"):
    _qp_lang = "en"
st.session_state.ui_lang = _qp_lang

is_ar   = st.session_state.ui_lang == "ar"
L       = T[st.session_state.ui_lang]
_api_ok = has_credentials()

# captcha gate — one-time per session
if _qp.get("_v") == "1":
    st.session_state["_captcha_passed"] = True
if not st.session_state.get("_captcha_passed"):
    if "_captcha_code" not in st.session_state:
        img_bytes, code = _generate_captcha()
        st.session_state["_captcha_code"] = code
        st.session_state["_captcha_img"] = img_bytes

    _cap_title = "التحقق الأمني" if is_ar else "Security Verification"
    _cap_sub = "أدخل الرمز الظاهر في الصورة للمتابعة" if is_ar else "Enter the code shown below to continue"
    _cap_hint = "أدخل الرمز" if is_ar else "Enter code"
    _cap_btn = "تحقق" if is_ar else "Verify"
    _cap_err = "الرمز غير صحيح، حاول مرة أخرى" if is_ar else "Incorrect code, try again"
    _cap_new = "رمز جديد" if is_ar else "New Code"
    _cap_dir = "rtl" if is_ar else "ltr"

    st.markdown(f"""
    <div style="max-width:440px;margin:4rem auto 0;text-align:center;direction:{_cap_dir}">
      <div style="width:56px;height:56px;margin:0 auto 1rem;background:#1B8354;border-radius:14px;display:flex;align-items:center;justify-content:center">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
      </div>
      <h2 style="font-family:'IBM Plex Sans','Noto Kufi Arabic',sans-serif;font-size:1.5rem;font-weight:600;color:#161616;margin:0 0 .375rem">{_cap_title}</h2>
      <p style="font-family:'IBM Plex Sans','Noto Kufi Arabic',sans-serif;font-size:.9rem;color:#6C737F;margin:0 0 1.5rem">{_cap_sub}</p>
    </div>
    """, unsafe_allow_html=True)

    _cap_col1, _cap_col2, _cap_col3 = st.columns([1, 2, 1])
    with _cap_col2:
        st.image(st.session_state["_captcha_img"], width="stretch")
        _cap_input = st.text_input(_cap_hint, key="_captcha_input", max_chars=5, label_visibility="collapsed", placeholder=_cap_hint)
        _bc1, _bc2 = st.columns(2)
        with _bc1:
            if st.button(_cap_new, key="_captcha_refresh", use_container_width=True):
                img_bytes, code = _generate_captcha()
                st.session_state["_captcha_code"] = code
                st.session_state["_captcha_img"] = img_bytes
                st.rerun()
        with _bc2:
            _do_verify = st.button(_cap_btn, key="_captcha_submit", type="primary", use_container_width=True)
    if _do_verify:
        if _cap_input.strip().upper() == st.session_state["_captcha_code"]:
            st.session_state["_captcha_passed"] = True
            del st.session_state["_captcha_code"]
            del st.session_state["_captcha_img"]
            st.query_params["_v"] = "1"
            st.rerun()
        else:
            st.error(_cap_err)
            img_bytes, code = _generate_captcha()
            st.session_state["_captcha_code"] = code
            st.session_state["_captcha_img"] = img_bytes
            st.rerun()
    st.stop()

# styles
_fonts = (
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700"
    "&family=Noto+Kufi+Arabic:wght@300;400;500;600;700&display=swap"
)
_dir = "rtl" if is_ar else "ltr"

st.markdown(f"""
<style>
@import url('{_fonts}');

/* base */
html, body, .stApp {{
  font-family: 'IBM Plex Sans', 'Noto Kufi Arabic', system-ui, sans-serif !important;
  font-size: 16px;
  color: #161616;
  background: #F3F4F6 !important;
  -webkit-font-smoothing: antialiased;
}}
/* RTL */
[data-testid="stMainBlockContainer"],
[data-testid="stSidebarContent"] {{
  direction: {_dir};
}}
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{
  background: transparent !important;
}}
[data-testid="stAppViewBlockContainer"] [data-testid="stBottomBlockContainer"] {{ display: none !important; }}
.viewerBadge_container__r5tak, .stDeployButton, [data-testid="stDecoration"],
[data-testid="stToolbar"], .styles_viewerBadge__CvC9N {{ display: none !important; }}

[data-testid="stMainBlockContainer"] {{
  max-width: 100% !important;
  margin: 0 auto !important;
  padding: 0 3rem 3rem !important;
  background: transparent !important;
}}

/* navbar */
.rcjy-nav {{
  background: #fff;
  border-bottom: 3px solid #1B8354;
  margin: 0 -3rem 1.5rem;
  box-shadow: 0 1px 4px rgba(13,18,28,.08);
  position: sticky;
  top: 0;
  z-index: 99;
}}
.rcjy-nav-inner {{
  display: flex;
  align-items: center;
  padding: 0 3rem;
  min-height: 72px;
  gap: 1.25rem;
  direction: {_dir};
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
  padding: 10px 18px;
  border-radius: 8px;
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .9375rem;
  font-weight: 500;
  color: #0d121c;
  text-decoration: none;
  white-space: nowrap;
  transition: background .2s, color .2s;
}}
.rcjy-nav-item:hover {{ background: #F3F4F6; color: #1B8354; text-decoration: none; }}
.rcjy-nav-item:focus, .rcjy-nav-item:visited {{ text-decoration: none; }}
.rcjy-nav-links a {{ text-decoration: none !important; }}
.rcjy-nav-active {{
  background: #1B8354 !important;
  color: #fff !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 3px rgba(27,131,84,.25);
}}
/* lang */
.rcjy-nav-right {{
  display: flex;
  align-items: center;
  gap: .75rem;
  flex-shrink: 0;
}}
/* toggle */
.rcjy-lang-link {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
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

/* card */
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlockBorderWrapper"] {{
  border: none !important;
  border-radius: 16px !important;
  background: #fff !important;
  box-shadow: none !important;
  overflow: hidden !important;
  margin-top: .5rem !important;
}}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] {{
  padding: 1.5rem !important;
  gap: .875rem !important;
}}

/* labels */
.stSelectbox > label,
.stTextArea  > label,
.stTextInput > label {{
  font-family: 'IBM Plex Sans', 'Noto Kufi Arabic', sans-serif !important;
  font-size: .75rem !important;
  font-weight: 600 !important;
  letter-spacing: .06em !important;
  text-transform: uppercase !important;
  color: #6C737F !important;
  margin-bottom: .3rem !important;
}}
.stCaption, [data-testid="stCaptionContainer"] p {{
  font-size: .75rem !important;
  color: #9DA4AE !important;
  line-height: 1.55 !important;
}}

/* textarea */
.stTextArea textarea {{
  font-family: 'IBM Plex Sans', 'Noto Kufi Arabic', sans-serif !important;
  font-size: 1rem !important;
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
  font-size: .9375rem !important;
}}

/* text input */
.stTextInput input {{
  font-family: 'IBM Plex Sans', 'Noto Kufi Arabic', sans-serif !important;
  font-size: 1rem !important;
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

/* selectbox */
.stSelectbox [data-baseweb="select"] > div {{
  font-family: 'IBM Plex Sans', 'Noto Kufi Arabic', sans-serif !important;
  font-size: 1rem !important;
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

/* tags */
.mtags {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: .5rem; }}
.mtag {{
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: .6875rem;
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

/* divider */
hr {{ border-color: #E5E7EB !important; margin: .25rem 0 !important; }}

/* button */
.stButton > button {{
  font-family: 'IBM Plex Sans', 'Noto Kufi Arabic', sans-serif !important;
  font-size: 1rem !important;
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

/* download */
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

/* uploader */
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

/* expander */
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

/* badge */
.ctx-badge {{
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  background: #EBF5EE;
  color: #14573A;
  border: 1px solid #C3E0CC;
  border-radius: 4px;
  padding: .25rem .8rem;
  font-size: .75rem;
  font-weight: 600;
  margin-top: .35rem;
}}

/* result */
.result-wrap {{
  background: #fff;
  border: 1px solid #D2D6DB;
  border-radius: 16px;
  padding: 1.5rem 1.75rem;
  margin-top: 1rem;
  box-shadow: 0px 2px 4px -2px rgba(16,24,40,.06), 0px 4px 8px -2px rgba(16,24,40,.1);
  border-top: 3px solid #1B8354;
}}
.result-wrap p  {{ font-size: 1rem !important; line-height: 1.8 !important; color: #161616 !important; }}
.result-wrap li {{ font-size: 1rem !important; line-height: 1.8 !important; color: #161616 !important; }}
.result-wrap h1,
.result-wrap h2,
.result-wrap h3 {{ color: #161616 !important; font-weight: 600 !important; }}

/* alerts */
.stAlert {{ border-radius: 8px !important; }}
.stAlert p {{ font-size: .9375rem !important; }}
.stSpinner > div {{ border-top-color: #1B8354 !important; }}


/* hide sidebar */
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{
  display: none !important;
}}

/* history */
.hist-stat-card {{
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: .625rem .75rem;
  text-align: center;
}}
.hist-stat-value {{
  font-family: 'IBM Plex Sans',sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: #161616;
  line-height: 1.2;
}}
.hist-stat-label {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .625rem;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: #9DA4AE;
  margin-top: .15rem;
}}

/* history row */
.hist-row {{
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: .5rem;
  padding: .5rem 0 .25rem;
}}
.hist-row-main {{
  display: flex;
  align-items: center;
  gap: .5rem;
  flex: 1 1 auto;
  min-width: 0;
}}
.hist-type-badge {{
  font-family: 'IBM Plex Sans',sans-serif;
  font-size: .625rem;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
  padding: .2rem .55rem;
  border-radius: 4px;
  display: inline-block;
  flex-shrink: 0;
  line-height: 1.4;
  background: #EBF5EE;
  color: #14573A;
  border: 1px solid #C3E0CC;
}}
.hist-row-prompt {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .9375rem;
  font-weight: 400;
  color: #161616;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}}
.hist-row-meta {{
  display: flex;
  gap: .75rem;
  flex-shrink: 0;
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .75rem;
  font-weight: 500;
  color: #9DA4AE;
}}
hr.hist-sep {{
  border: none !important;
  border-top: 1px solid #F3F4F6 !important;
  margin: .25rem 0 .125rem !important;
}}

/* history empty */
.hist-empty {{
  text-align: center;
  padding: 3rem 1.5rem;
}}
.hist-empty-icon {{
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  width: 52px;
  height: 52px;
  background: #EBF5EE;
  border-radius: 50%;
}}
.hist-empty-icon svg {{
  opacity: .6;
  stroke: #1B8354;
}}
.hist-empty-text {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .9375rem;
  font-weight: 500;
  color: #384250;
  margin-bottom: .25rem;
}}
.hist-empty-hint {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .8125rem;
  color: #9DA4AE;
  line-height: 1.5;
}}

/* footer */
.rcjy-footer {{
  background: #1B8354;
  margin: 4rem -3rem -3rem;
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  direction: {_dir};
}}
.rcjy-ftr-main {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem 2.5rem;
  gap: 2rem;
  flex-wrap: wrap;
}}
.rcjy-ftr-left {{
  display: flex;
  flex-direction: column;
  gap: .625rem;
}}
.rcjy-ftr-copy {{
  color: rgba(255,255,255,.9);
  font-size: .9375rem;
  font-weight: 500;
}}
.rcjy-ftr-links {{
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}}
.rcjy-ftr-links a {{
  color: rgba(255,255,255,.7);
  text-decoration: none;
  font-size: .8125rem;
  font-weight: 400;
  transition: color .2s;
}}
.rcjy-ftr-links a:hover {{ color: #fff; }}
.rcjy-ftr-logos {{
  display: flex;
  align-items: center;
  gap: 1.75rem;
  flex-shrink: 0;
}}
.rcjy-ftr-rcjy {{ height: 52px; display: block; }}
.rcjy-ftr-divv {{ width: 1px; height: 48px; background: rgba(255,255,255,.3); }}
.rcjy-ftr-vision {{ height: 52px; display: block; }}

/* disclaimer */
.rcjy-disclaimer {{
  display: flex;
  align-items: center;
  gap: .5rem;
  padding: .5rem 1rem;
  background: #F8F9FA;
  border-left: 3px solid #1B8354;
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .8rem;
  font-weight: 400;
  color: #5F6B7A;
  margin-bottom: .75rem;
  line-height: 1.4;
}}
.rcjy-disclaimer[style*="rtl"] {{
  border-left: none;
  border-right: 3px solid #1B8354;
}}

/* responsive */
@media (max-width: 760px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 0 1rem 2rem !important; }}
  .rcjy-nav {{ margin: 0 -1rem 1rem; }}
  .rcjy-nav-inner {{ padding: 0 1rem; gap: .5rem; min-height: 56px; flex-wrap: wrap; }}
  .rcjy-nav-item {{ font-size: .8125rem !important; padding: 7px 9px !important; }}
  .rcjy-nav-logo {{ height: 36px; }}
  .rcjy-nav-right {{ gap: .5rem; }}
  .rcjy-footer {{ margin: 4rem -1rem -3rem; }}
  .rcjy-ftr-main {{ padding: 1.5rem 1rem; flex-direction: column; align-items: flex-start; }}
  .rcjy-ftr-rcjy, .rcjy-ftr-vision {{ height: 42px; }}
}}
@media (max-width: 480px) {{
  .rcjy-nav-links {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
}}
</style>
<!-- security headers -->
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="DENY">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="default-src 'self' https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' https: data:; script-src 'self' 'unsafe-inline' 'unsafe-eval';">
""", unsafe_allow_html=True)

# nav
active_tab = _qp.get("tab", "text")
if active_tab not in ("text", "image", "video", "voice", "podcast", "history"):
    active_tab = "text"
# Output lang = UI lang
lang = st.session_state.ui_lang
_nl = lang


def _ni(key, label):
    # Build nav item link
    cls = "rcjy-nav-item rcjy-nav-active" if key == active_tab else "rcjy-nav-item"
    _vp = "&_v=1" if st.session_state.get("_captcha_passed") else ""
    return (f'<li><a href="?tab={key}&lang={_nl}{_vp}" '
            f'class="{cls}" target="_self">{label}</a></li>')


# lang toggle
_other_lang_text = "العربية" if _nl == "en" else "English"
_vp = "&_v=1" if st.session_state.get("_captcha_passed") else ""
_other_lang_href = f"?tab={active_tab}&lang={'ar' if _nl == 'en' else 'en'}{_vp}"

_VISION_LOGO = "https://www.rcjy.gov.sa/documents/d/rcjy-internet/vision_logo"

st.markdown(f"""
<nav class="rcjy-nav">
  <div class="rcjy-nav-inner">
    <a href="?tab={active_tab}&lang={_nl}" class="rcjy-nav-logo-link" target="_self">
      <img class="rcjy-nav-logo" src="{RCJY_LOGO_URL}" alt="RCJY"
           onerror="this.style.display='none'">
    </a>
    <ul class="rcjy-nav-links">
      {_ni("text",    L["tab_text"])}
      {_ni("image",   L["tab_image"])}
      {_ni("video",   L["tab_video"])}
      {_ni("voice",   L["tab_voice"])}
      {_ni("podcast", L["tab_podcast"])}
      {_ni("history", L["tab_history"])}
    </ul>
    <div class="rcjy-nav-right">
      <a href="{_other_lang_href}" class="rcjy-lang-link" target="_self">{_other_lang_text}</a>
    </div>
  </div>
</nav>
""", unsafe_allow_html=True)

if not _api_ok:
    st.warning(L["warn_api"])

# public data disclaimer
_disc_dir = "rtl" if is_ar else "ltr"
_disc_text = ("هذه الأداة مخصصة للبيانات العامة فقط. لا تقم بإدخال أو إرفاق أي بيانات سرية أو خاصة."
              if is_ar else "This tool is for public data use only. Do not enter or attach any confidential or private information.")
st.markdown(f'<div class="rcjy-disclaimer" style="direction:{_disc_dir}">{_disc_text}</div>', unsafe_allow_html=True)


# helpers
def _ctx_widget():
    # Reference material expander
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
            # Escape filenames for display
            safe_names = ", ".join(html_mod.escape(f.name) for f in files)
            st.caption(f"{L['attached']}: {safe_names}")
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


# tabs
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
        _c1, _c2 = st.columns(2)
        with _c1:
            text_type = _type_map[st.selectbox(L["text_type_label"], list(_type_map), key="text_type")]
        with _c2:
            text_tone = _tone_map[st.selectbox(L["text_tone_label"], list(_tone_map), key="text_tone")]
        text_model = "pro"

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
        elif not _rate_check("text"):
            pass
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
                    if _history_ok:
                        history.save_entry("text", text_prompt.strip(), st.session_state.result_text,
                                           "text/plain", {"type": text_type, "tone": text_tone, "model": text_model}, lang)
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

# image
elif active_tab == "image":
    with st.container(border=True):
        _i1, _i2 = st.columns(2)
        with _i1:
            _img_model_map = {
                L["img_generate_new"]:  "imagen",
                L["img_generate_edit"]: "gemini_pro",
            }
            img_model = _img_model_map[st.selectbox(
                L["model_label"],
                list(_img_model_map),
                key="img_model",
            )]
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
        elif not _rate_check("image"):
            pass
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
                    if _history_ok:
                        history.save_entry("image", img_prompt.strip(), data, mime,
                                           {"model": img_model, "aspect_ratio": img_aspect}, lang)
                except Exception as e:
                    logger.exception("Image generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_image:
        st.image(st.session_state.result_image[0], width="stretch")
        st.download_button(
            L["btn_download"], data=st.session_state.result_image[0],
            file_name="rcjy_image.png", mime="image/png", key="dl_img",
        )

# video
elif active_tab == "video":
    # Total duration options
    _dur_options = {
        L["total_dur_8"]:   0,
        L["total_dur_15"]:  7,
        L["total_dur_22"]:  14,
        L["total_dur_29"]:  21,
        L["total_dur_43"]:  35,
        L["total_dur_57"]:  49,
        L["total_dur_78"]:  70,
        L["total_dur_99"]:  91,
        L["total_dur_120"]: 112,
        L["total_dur_148"]: 140,
    }

    with st.container(border=True):
        vid_model = "standard"
        _v1, _v2, _v3 = st.columns(3)
        with _v1:
            vid_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16"], key="vid_aspect")
        with _v2:
            _dur_label = st.selectbox(
                L["total_duration_label"],
                list(_dur_options.keys()),
                index=0,
                key="vid_total_dur",
            )
            vid_extend = _dur_options[_dur_label]
        with _v3:
            # Extension forces 720p
            if vid_extend > 0:
                vid_res = st.selectbox(
                    L["resolution_label"], ["720p"], key="vid_res_ext",
                )
            else:
                vid_res = st.selectbox(
                    L["resolution_label"], ["720p", "1080p", "4K"],
                    index=1, key="vid_res",
                )

        if vid_extend > 0:
            st.caption(L["extend_note"])

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
        elif not _rate_check("video"):
            pass
        else:
            _spin_msg = L["spin_video_extend"] if vid_extend > 0 else L["spin_video"]
            # Progress placeholder
            _progress_placeholder = st.empty()

            def _vid_progress(msg: str):
                _progress_placeholder.info(msg)

            with st.spinner(_spin_msg):
                try:
                    data, mime = generate_video(
                        prompt=vid_prompt.strip(),
                        context_text=ctx_text if has_ctx else "",
                        aspect_ratio=vid_aspect, duration="8",
                        resolution=vid_res.lower(), model=vid_model, lang=lang,
                        extend_seconds=vid_extend,
                        progress_callback=_vid_progress if vid_extend > 0 else None,
                    )
                    st.session_state.result_video = (data, mime)
                    if _history_ok:
                        history.save_entry("video", vid_prompt.strip(), data, mime,
                                           {"model": vid_model, "aspect_ratio": vid_aspect, "resolution": vid_res, "extend_seconds": vid_extend}, lang)
                    _progress_placeholder.empty()
                except Exception as e:
                    logger.exception("Video generation failed")
                    _progress_placeholder.empty()
                    st.error(_sanitize_error(e))

    if st.session_state.result_video:
        st.video(st.session_state.result_video[0])
        st.download_button(
            L["btn_download"], data=st.session_state.result_video[0],
            file_name="rcjy_video.mp4", mime="video/mp4", key="dl_vid",
        )

# voice
elif active_tab == "voice":
    _voice_opts_v = {
        "نورة ♀":   "Kore",
        "أميرة ♀":  "Aoede",
        "ليلى ♀":   "Leda",
        "زينب ♀":   "Zephyr",
        "شهد ♀":    "Schedar",
        "فهد ♂":    "Puck",
        "خالد ♂":   "Charon",
        "ناصر ♂":   "Fenrir",
        "عمر ♂":    "Orus",
        "سلطان ♂":  "Perseus",
    } if is_ar else {
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
        _style_map = {
            L["style_professional"]:   "professional",
            L["style_warm"]:           "warm",
            L["style_authoritative"]:  "authoritative",
            L["style_conversational"]: "conversational",
            L["style_energetic"]:      "energetic",
            L["style_calm"]:           "calm",
            L["style_formal"]:         "formal",
        }
        _o1, _o2 = st.columns(2)
        with _o1:
            _vsel = st.selectbox(
                L["voice_label"], list(_voice_opts_v), key="voice_name_sel",
            )
            voice_name = _voice_opts_v[_vsel]
            _voice_display = _vsel.split(" ♀")[0].split(" ♂")[0].strip()
        with _o2:
            style_hint = _style_map[st.selectbox(
                L["style_label"], list(_style_map), key="voice_style",
            )]

        st.divider()

        voice_prompt = st.text_area(
            L["prompt_label"], key="prompt_voice",
            placeholder=L["prompt_ph_voice"], height=200,
        )
        input_url, input_files = _ctx_widget()
        ctx_text, has_ctx = _load_ctx(input_url, input_files)

    if st.button(L["btn_voice"], use_container_width=True, key="btn_voice"):
        if not voice_prompt.strip() and not has_ctx:
            st.warning(L["warn_text"])
        elif not _rate_check("voice"):
            pass
        else:
            with st.spinner(L["spin_voice"]):
                try:
                    data, mime = generate_voice(
                        text=voice_prompt.strip(), context_text=ctx_text if has_ctx else "",
                        voice_name=voice_name, display_name=_voice_display if is_ar else "",
                        style_hint=style_hint,
                        tts_model="pro",
                        lang=lang,
                    )
                    st.session_state.result_voice = (data, mime)
                    if _history_ok:
                        history.save_entry("voice", voice_prompt.strip(), data, mime,
                                           {"voice": voice_name, "quality": "pro", "style": style_hint}, lang)
                except Exception as e:
                    logger.exception("Voice generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_voice:
        st.audio(st.session_state.result_voice[0], format="audio/wav")
        st.download_button(
            L["btn_download"], data=st.session_state.result_voice[0],
            file_name="rcjy_voice.wav", mime="audio/wav", key="dl_voice",
        )

# podcast
elif active_tab == "podcast":
    _pod_len_opts = [L["length_short"], L["length_standard"]]
    _voice_opts   = {
        "نورة ♀":   "Kore",
        "أميرة ♀":  "Aoede",
        "ليلى ♀":   "Leda",
        "زينب ♀":   "Zephyr",
        "شهد ♀":    "Schedar",
        "فهد ♂":    "Puck",
        "خالد ♂":   "Charon",
        "ناصر ♂":   "Fenrir",
        "عمر ♂":    "Orus",
        "سلطان ♂":  "Perseus",
    } if is_ar else {
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
        _p1, _p2, _p3 = st.columns(3)
        with _p1:
            pod_len_idx = st.selectbox(
                L["length_label"], range(len(_pod_len_opts)),
                format_func=lambda i: _pod_len_opts[i], key="pod_len",
            )
        with _p2:
            _hsel = st.selectbox(L["host_label"],  list(_voice_opts), index=0, key="pod_host")  # default: first female
            pod_host = _voice_opts[_hsel]
            _host_disp = _hsel.split(" ♀")[0].split(" ♂")[0].strip()
        with _p3:
            _gsel = st.selectbox(L["guest_label"], list(_voice_opts), index=5, key="pod_guest")  # default: first male
            pod_guest = _voice_opts[_gsel]
            _guest_disp = _gsel.split(" ♀")[0].split(" ♂")[0].strip()

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
        elif not _rate_check("podcast"):
            pass
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
                        voice_host=pod_host, voice_guest=pod_guest,
                        host_display_name=_host_disp if is_ar else "",
                        guest_display_name=_guest_disp if is_ar else "",
                        lang=lang,
                    )
                    st.session_state.result_podcast = (data, mime)
                    if _history_ok:
                        history.save_entry("podcast", pod_prompt.strip(), data, mime,
                                           {"length": "short" if pod_len_idx == 0 else "standard", "host": pod_host, "guest": pod_guest}, lang)
                except Exception as e:
                    logger.exception("Podcast generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_podcast:
        st.audio(st.session_state.result_podcast[0], format="audio/wav")
        st.download_button(
            L["btn_download"], data=st.session_state.result_podcast[0],
            file_name="rcjy_podcast.wav", mime="audio/wav", key="dl_pod",
        )

# history
elif active_tab == "history":
    with st.container(border=True):
        if not _history_ok:
            _hist_unavail = ("خدمة السجل غير متوفرة حالياً — تحقق من صلاحيات التخزين للحساب الخدمي"
                             if is_ar else "History service unavailable — check storage permissions for the service account")
            st.warning(_hist_unavail)
        else:
            # Pending delete
            if st.session_state.get("_hist_delete_id"):
                _del_id = st.session_state.pop("_hist_delete_id")
                history.delete_entry(_del_id)
                st.rerun()

            # Pending download
            if st.session_state.get("_hist_download_id"):
                _dl_id = st.session_state.pop("_hist_download_id")
                _dl_data, _dl_mime, _dl_name = history.load_file(_dl_id)
                if _dl_data:
                    st.download_button(
                        f"⬇ {_dl_name}", data=_dl_data,
                        file_name=_dl_name, mime=_dl_mime,
                        key=f"dl_actual_{_dl_id}",
                    )

            _stats = history.get_stats()

            # Filter + stats
            _fc, _sc1, _sc2 = st.columns([3, 1, 1])
            with _fc:
                _type_labels = [L["hist_all"], L["tab_text"], L["tab_image"], L["tab_video"], L["tab_voice"], L["tab_podcast"]]
                _type_keys = [None, "text", "image", "video", "voice", "podcast"]
                _sel = st.selectbox(L["hist_filter"], range(len(_type_labels)),
                                    format_func=lambda i: _type_labels[i], key="hist_filter_sel")
                _filter_type = _type_keys[_sel]
            with _sc1:
                _tot = _stats["total"]
                st.markdown(
                    f'<div class="hist-stat-card"><div class="hist-stat-value">{_tot}</div>'
                    f'<div class="hist-stat-label">{html_mod.escape(L["hist_total"])}</div></div>',
                    unsafe_allow_html=True,
                )
            with _sc2:
                _size_fmt = history.format_file_size(_stats["total_size"])
                st.markdown(
                    f'<div class="hist-stat-card"><div class="hist-stat-value">{html_mod.escape(_size_fmt)}</div>'
                    f'<div class="hist-stat-label">{html_mod.escape(L["hist_size"])}</div></div>',
                    unsafe_allow_html=True,
                )

            st.divider()

            _entries = history.get_entries(content_type=_filter_type, limit=50)
            if not _entries:
                st.markdown(
                    f'<div class="hist-empty">'
                    f'<div class="hist-empty-icon">'
                    f'<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#9DA4AE" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
                    f'<path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="9"/>'
                    f'</svg>'
                    f'</div>'
                    f'<div class="hist-empty-text">{html_mod.escape(L["hist_empty"])}</div>'
                    f'<div class="hist-empty-hint">{html_mod.escape(L["hist_empty_hint"])}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                _badge_labels = {
                    "text": L["tab_text"], "image": L["tab_image"],
                    "video": L["tab_video"], "voice": L["tab_voice"],
                    "podcast": L["tab_podcast"],
                }
                for _e in _entries:
                    _eid = _e["id"]
                    _etype = _e.get("type", "text")
                    _badge_text = html_mod.escape(_badge_labels.get(_etype, _etype.title()))
                    _prompt_safe = html_mod.escape(_e.get("prompt", "")[:120])
                    _time = history.format_timestamp(_e.get("created_at", ""), st.session_state.ui_lang)
                    _size = history.format_file_size(_e.get("file_size", 0))

                    st.markdown(
                        f'<div class="hist-row">'
                        f'<div class="hist-row-main">'
                        f'<span class="hist-type-badge">{_badge_text}</span>'
                        f'<span class="hist-row-prompt">{_prompt_safe or "—"}</span>'
                        f'</div>'
                        f'<div class="hist-row-meta">'
                        f'<span>{html_mod.escape(_size)}</span>'
                        f'<span>{html_mod.escape(_time)}</span>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    _hc1, _hc2, _hc3 = st.columns([6, 1, 1])
                    with _hc2:
                        st.button(L["hist_download"], key=f"dl_{_eid}",
                                  on_click=lambda eid=_eid: st.session_state.update({"_hist_download_id": eid}))
                    with _hc3:
                        st.button(L["hist_delete"], key=f"del_{_eid}",
                                  on_click=lambda eid=_eid: st.session_state.update({"_hist_delete_id": eid}))
                    st.markdown('<hr class="hist-sep">', unsafe_allow_html=True)

                # Clear
                if st.button(L["hist_clear"], key="hist_clear_btn"):
                    st.session_state["_hist_confirm_clear"] = True
                if st.session_state.get("_hist_confirm_clear"):
                    st.warning(L["hist_clear_confirm"])
                    _y, _n = st.columns(2)
                    with _y:
                        if st.button(L["hist_confirm_yes"], key="hist_yes"):
                            history.clear_all()
                            st.session_state["_hist_confirm_clear"] = False
                            _cached_stats.clear()
                            _cached_entries.clear()
                            st.rerun()
                    with _n:
                        if st.button(L["hist_confirm_no"], key="hist_no"):
                            st.session_state["_hist_confirm_clear"] = False
                            st.rerun()

# footer

_ftr_lang = "ar" if is_ar else "en"
_ftr_copy = (
    "جميع الحقوق محفوظة للهيئة الملكية للجبيل وينبع" if is_ar
    else "All rights reserved to the Royal Commission for Jubail and Yanbu"
)
_ftr_privacy = "سياسة الخصوصية" if is_ar else "Privacy Policy"
_ftr_terms = "الشروط والأحكام" if is_ar else "Terms &amp; Conditions"
_ftr_site = "الموقع الرسمي" if is_ar else "RCJY Official Website"
_ftr_html = (
    '<div class="rcjy-footer"><div class="rcjy-ftr-main">'
    '<div class="rcjy-ftr-left">'
    f'<span class="rcjy-ftr-copy">{_ftr_copy} &copy; 2026</span>'
    '<div class="rcjy-ftr-links">'
    f'<a href="https://www.rcjy.gov.sa/{_ftr_lang}/privacy-policy" target="_blank" rel="noopener">{_ftr_privacy}</a>'
    f'<a href="https://www.rcjy.gov.sa/{_ftr_lang}/terms-and-conditions" target="_blank" rel="noopener">{_ftr_terms}</a>'
    f'<a href="https://www.rcjy.gov.sa/{_ftr_lang}/home" target="_blank" rel="noopener">{_ftr_site}</a>'
    '</div></div>'
    '<div class="rcjy-ftr-logos">'
    f'<img class="rcjy-ftr-rcjy" src="{RCJY_LOGO_URL}" alt="RCJY" onerror="this.style.display=\'none\'">'
    '<div class="rcjy-ftr-divv"></div>'
    f'<img class="rcjy-ftr-vision" src="{_VISION_LOGO}" alt="Vision 2030" onerror="this.style.display=\'none\'">'
    '</div>'
    '</div></div>'
)
st.markdown(_ftr_html, unsafe_allow_html=True)
