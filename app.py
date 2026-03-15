import html as html_mod
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

try:
    import history
    _history_ok = history.is_available()
except Exception:
    history = None
    _history_ok = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rcjy.app")

# translations
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
        "prompt_ph_text":         "Describe what you want to create…\ne.g. A press release about Jubail Industrial City's new green hydrogen facility.\n\nTip: Output follows your interface language. To override, specify in your prompt (e.g. 'write in Arabic').",
        "prompt_ph_image":        "Describe the image…\ne.g. Aerial golden-hour view of Jubail Industrial City, petrochemical towers, calm sea.",
        "prompt_ph_video":        "Describe the video scene…\ne.g. Cinematic drone flight over Yanbu Industrial Port at sunrise, dramatic sky.",
        "prompt_ph_voice":        "Enter the text to be spoken…\n\nTip: Output follows your interface language. To override, specify in your prompt.",
        "prompt_ph_podcast":      "Describe the podcast topic…\ne.g. The economic transformation of Jubail and Yanbu and their role in Vision 2030.\n\nTip: Output follows your interface language. To override, specify in your prompt.",
        "model_label":            "Model",
        "aspect_label":           "Aspect Ratio",
        "duration_label":         "Duration (sec)",
        "total_duration_label":   "Total Duration",
        "total_dur_8":            "8s (single clip)",
        "total_dur_15":           "~15s (1 extension)",
        "total_dur_22":           "~22s (2 extensions)",
        "total_dur_29":           "~29s (3 extensions)",
        "total_dur_43":           "~43s (5 extensions)",
        "total_dur_57":           "~57s (7 extensions)",
        "total_dur_78":           "~78s (10 extensions)",
        "total_dur_148":          "~148s (20 extensions, max)",
        "extend_note":            "Extension forces 720p resolution. Each step adds ~7s and takes 2-5 min.",
        "resolution_label":       "Resolution",
        "video_model_label":      "Video Model",
        "voice_label":            "Voice",
        "quality_label":          "Quality",
        "style_label":            "Delivery Style",
        "style_placeholder":      "e.g. professional, warm, authoritative",
        "length_label":           "Episode Length",
        "length_short":           "Short",
        "length_standard":        "Long",
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
        "prompt_label":           "الوصف",
        "prompt_ph_text":         "اكتب وصفاً لما تريد إنشاءه…\nمثال: بيان صحفي عن منشأة الهيدروجين الأخضر الجديدة في الجبيل.\n\nتلميح: المخرجات تتبع لغة الواجهة. للتغيير، حدد في الوصف (مثلاً: 'اكتب بالإنجليزية').",
        "prompt_ph_image":        "اكتب وصفاً للصورة…\nمثال: منظر جوي لمدينة الجبيل الصناعية عند الغسق.",
        "prompt_ph_video":        "اكتب وصفاً لمشهد الفيديو…\nمثال: تحليق سينمائي فوق ميناء ينبع عند الفجر.",
        "prompt_ph_voice":        "أدخل النص الذي تريد تحويله إلى صوت…\n\nتلميح: المخرجات تتبع لغة الواجهة. للتغيير، حدد في الوصف.",
        "prompt_ph_podcast":      "اكتب موضوع البودكاست…\nمثال: التحول الاقتصادي لمدينتي الجبيل وينبع ودورهما في رؤية 2030.\n\nتلميح: المخرجات تتبع لغة الواجهة. للتغيير، حدد في الوصف.",
        "model_label":            "النموذج",
        "aspect_label":           "نسبة الأبعاد",
        "duration_label":         "المدة (ثانية)",
        "total_duration_label":   "المدة الإجمالية",
        "total_dur_8":            "٨ث (مقطع واحد)",
        "total_dur_15":           "~١٥ث (تمديد ١)",
        "total_dur_22":           "~٢٢ث (تمديدان ٢)",
        "total_dur_29":           "~٢٩ث (٣ تمديدات)",
        "total_dur_43":           "~٤٣ث (٥ تمديدات)",
        "total_dur_57":           "~٥٧ث (٧ تمديدات)",
        "total_dur_78":           "~٧٨ث (١٠ تمديدات)",
        "total_dur_148":          "~١٤٨ث (٢٠ تمديد، الحد الأقصى)",
        "extend_note":            "التمديد يفرض دقة 720p. كل خطوة تضيف ~٧ث وتستغرق ٢-٥ دقائق.",
        "resolution_label":       "الدقة",
        "video_model_label":      "نموذج الفيديو",
        "voice_label":            "الصوت",
        "quality_label":          "الجودة",
        "style_label":            "أسلوب الأداء",
        "style_placeholder":      "مثال: رسمي، دافئ، موثوق",
        "length_label":           "مدة الحلقة",
        "length_short":           "قصير",
        "length_standard":        "طويل",
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

# page config
st.set_page_config(
    page_title="RCJY Media Generator",
    page_icon="https://www.rcjy.gov.sa/o/rcjy-theme/images/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

# session state
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

# sidebar history panel
with st.sidebar:
    # Title with icon
    st.markdown(
        f'<div class="hist-title">'
        f'<span class="hist-title-icon">H</span>'
        f'{html_mod.escape(L["hist_title"])}'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not _history_ok:
        # Empty state — styled placeholder
        st.markdown(
            f'<div class="hist-empty">'
            f'<div class="hist-empty-icon">&#9783;</div>'
            f'<div class="hist-empty-text">{html_mod.escape(L["hist_empty"])}</div>'
            f'<div class="hist-empty-hint">{html_mod.escape(L["hist_empty_hint"])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        # Stats
        @st.cache_data(ttl=30)
        def _cached_stats():
            return history.get_stats()

        _stats = _cached_stats()
        if _stats["total"] > 0:
            _size_fmt = history.format_file_size(_stats["total_size"])
            st.markdown(
                f'<div class="hist-stats">'
                f'<div class="hist-stat">'
                f'  <div class="hist-stat-value">{_stats["total"]}</div>'
                f'  <div class="hist-stat-label">{html_mod.escape(L["hist_total"])}</div>'
                f'</div>'
                f'<div class="hist-stat">'
                f'  <div class="hist-stat-value">{html_mod.escape(_size_fmt)}</div>'
                f'  <div class="hist-stat-label">{html_mod.escape(L["hist_size"])}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Type filter
        _type_labels = [L["hist_all"], L["tab_text"], L["tab_image"], L["tab_video"], L["tab_voice"], L["tab_podcast"]]
        _type_keys = [None, "text", "image", "video", "voice", "podcast"]
        _sel = st.selectbox(L["hist_filter"], range(len(_type_labels)),
                            format_func=lambda i: _type_labels[i], key="hist_filter_sel")
        _filter_type = _type_keys[_sel]

        st.divider()

        # Handle pending delete
        if st.session_state.get("_hist_delete_id"):
            _del_id = st.session_state.pop("_hist_delete_id")
            history.delete_entry(_del_id)
            _cached_stats.clear()
            st.rerun()

        # Handle pending download
        if st.session_state.get("_hist_download_id"):
            _dl_id = st.session_state.pop("_hist_download_id")
            _dl_data, _dl_mime, _dl_name = history.load_file(_dl_id)
            if _dl_data:
                st.download_button(
                    f"⬇ {_dl_name}", data=_dl_data,
                    file_name=_dl_name, mime=_dl_mime,
                    key=f"dl_actual_{_dl_id}",
                )

        # Entry list
        @st.cache_data(ttl=30)
        def _cached_entries(_type, _limit):
            return history.get_entries(content_type=_type, limit=_limit)

        _entries = _cached_entries(_filter_type, 50)
        if not _entries:
            st.markdown(
                f'<div class="hist-empty">'
                f'<div class="hist-empty-icon">&#9783;</div>'
                f'<div class="hist-empty-text">{html_mod.escape(L["hist_empty"])}</div>'
                f'<div class="hist-empty-hint">{html_mod.escape(L["hist_empty_hint"])}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            _badge_labels = {
                "text": L["tab_text"],
                "image": L["tab_image"],
                "video": L["tab_video"],
                "voice": L["tab_voice"],
                "podcast": L["tab_podcast"],
            }
            for _e in _entries:
                _eid = _e["id"]
                _etype = _e.get("type", "text")
                _badge_cls = f"hist-badge-{_etype}"
                _badge_text = html_mod.escape(_badge_labels.get(_etype, _etype.title()))
                _prompt_safe = html_mod.escape(_e.get("prompt", "")[:80])
                _time = history.format_timestamp(_e.get("created_at", ""), st.session_state.ui_lang)
                _size = history.format_file_size(_e.get("file_size", 0))

                with st.container(border=True):
                    # Header row: type badge + size
                    st.markdown(
                        f'<div class="hist-entry-header">'
                        f'<span class="hist-type-badge {_badge_cls}">{_badge_text}</span>'
                        f'<span class="hist-entry-size">{html_mod.escape(_size)}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    # Prompt preview
                    if _prompt_safe:
                        st.markdown(
                            f'<div class="hist-entry-prompt">{_prompt_safe}</div>',
                            unsafe_allow_html=True,
                        )
                    # Timestamp
                    st.markdown(
                        f'<div class="hist-entry-time">{html_mod.escape(_time)}</div>',
                        unsafe_allow_html=True,
                    )
                    # Action buttons
                    _c1, _c2 = st.columns(2)
                    with _c1:
                        st.button(f"↓ {L['hist_download']}", key=f"dl_{_eid}",
                                  on_click=lambda eid=_eid: st.session_state.update({"_hist_download_id": eid}))
                    with _c2:
                        st.button(f"× {L['hist_delete']}", key=f"del_{_eid}",
                                  on_click=lambda eid=_eid: st.session_state.update({"_hist_delete_id": eid}))

        # Clear all
        if _entries:
            st.divider()
            if st.button(L["hist_clear"], key="hist_clear_btn", type="secondary"):
                st.session_state["_hist_confirm_clear"] = True
            if st.session_state.get("_hist_confirm_clear"):
                st.warning(L["hist_clear_confirm"])
                _y, _n = st.columns(2)
                with _y:
                    if st.button(L["hist_confirm_yes"], key="hist_yes", type="primary"):
                        history.clear_all()
                        st.session_state["_hist_confirm_clear"] = False
                        _cached_stats.clear()
                        _cached_entries.clear()
                        st.rerun()
                with _n:
                    if st.button(L["hist_confirm_no"], key="hist_no", type="secondary"):
                        st.session_state["_hist_confirm_clear"] = False
                        st.rerun()

# css
_fonts = (
    "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700"
    "&family=Noto+Kufi+Arabic:wght@300;400;500;600;700&display=swap"
)
_dir = "rtl" if is_ar else "ltr"

st.markdown(f"""
<style>
@import url('{_fonts}');

/* reset & base */
html, body, .stApp {{
  font-family: 'IBM Plex Sans', 'Noto Kufi Arabic', system-ui, sans-serif !important;
  font-size: 16px;
  color: #161616;
  background: #F3F4F6 !important;
  -webkit-font-smoothing: antialiased;
  direction: {_dir};
}}
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent !important; }}

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
  z-index: 999;
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
/* lang controls */
.rcjy-nav-right {{
  display: flex;
  align-items: center;
  gap: .75rem;
  flex-shrink: 0;
}}
/* lang toggle */
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

/* content card — rcjy card style */
[data-testid="stVerticalBlockBorderWrapper"] {{
  border: none !important;
  border-radius: 16px !important;
  background: #fff !important;
  box-shadow: none !important;
  overflow: hidden !important;
  margin-top: .5rem !important;
}}
[data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] {{
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

/* model tags */
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

/* primary button */
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

/* download button */
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

/* file uploader */
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

/* context badge */
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

/* result area */
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

/* alerts & spinner */
.stAlert {{ border-radius: 8px !important; }}
.stAlert p {{ font-size: .9375rem !important; }}
.stSpinner > div {{ border-top-color: #1B8354 !important; }}


/* ──────────────── sidebar ──────────────── */
[data-testid="stSidebar"] {{
  background: #FAFBFC;
  border-right: 1px solid #E5E7EB;
  direction: {_dir};
}}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
  padding: 1.25rem 1rem 1.5rem !important;
}}
[data-testid="collapsedControl"] {{
  z-index: 1001 !important;
  position: fixed !important;
  top: 0.5rem !important;
}}

/* sidebar title */
.hist-title {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .8125rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #6C737F;
  margin: 0 0 .75rem 0;
  padding: 0 .25rem;
  display: flex;
  align-items: center;
  gap: .5rem;
}}
.hist-title-icon {{
  width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  background: #EBF5EE; border-radius: 4px;
  font-size: .625rem; color: #1B8354; font-weight: 700;
  flex-shrink: 0;
}}

/* sidebar stats bar */
.hist-stats {{
  display: flex;
  gap: .5rem;
  margin-bottom: .75rem;
}}
.hist-stat {{
  flex: 1;
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: .5rem .625rem;
  text-align: center;
}}
.hist-stat-value {{
  font-family: 'IBM Plex Sans',sans-serif;
  font-size: 1.125rem;
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
  margin-top: .125rem;
}}

/* sidebar filter — compact override */
[data-testid="stSidebar"] .stSelectbox > label {{
  font-size: .6875rem !important;
  margin-bottom: .2rem !important;
}}
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {{
  font-size: .8125rem !important;
  font-weight: 500 !important;
  min-height: 34px !important;
  padding: .25rem .5rem !important;
  border-radius: 6px !important;
  background: #fff !important;
  border-color: #E5E7EB !important;
}}

/* sidebar divider */
[data-testid="stSidebar"] hr {{
  border-color: #E5E7EB !important;
  margin: .5rem 0 !important;
}}

/* sidebar cards — override global card bloat */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {{
  border: 1px solid #E5E7EB !important;
  border-radius: 10px !important;
  background: #fff !important;
  box-shadow: none !important;
  margin-top: 0 !important;
  margin-bottom: .375rem !important;
  transition: border-color .15s ease, box-shadow .15s ease;
}}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"]:hover {{
  border-color: #C3E0CC !important;
  box-shadow: 0 1px 4px rgba(27,131,84,.08) !important;
}}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > [data-testid="stVerticalBlock"] {{
  padding: .625rem .75rem !important;
  gap: .25rem !important;
}}

/* sidebar entry card inner elements */
.hist-entry-header {{
  display: flex;
  align-items: center;
  gap: .5rem;
  margin-bottom: .125rem;
}}
.hist-type-badge {{
  font-family: 'IBM Plex Sans',sans-serif;
  font-size: .5625rem;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: .15rem .4rem;
  border-radius: 4px;
  display: inline-block;
  flex-shrink: 0;
  line-height: 1.4;
}}
.hist-badge-text    {{ background: #EBF5EE; color: #14573A; }}
.hist-badge-image   {{ background: #EDE9FE; color: #5B21B6; }}
.hist-badge-video   {{ background: #FEF3C7; color: #92400E; }}
.hist-badge-voice   {{ background: #DBEAFE; color: #1E40AF; }}
.hist-badge-podcast {{ background: #FCE7F3; color: #9D174D; }}
.hist-entry-size {{
  font-family: 'IBM Plex Sans',sans-serif;
  font-size: .6875rem;
  font-weight: 500;
  color: #9DA4AE;
  margin-inline-start: auto;
}}
.hist-entry-prompt {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .75rem;
  font-weight: 400;
  color: #384250;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: .125rem 0;
}}
.hist-entry-time {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .625rem;
  font-weight: 500;
  color: #B0B8C4;
}}

/* sidebar buttons — compact secondary style, override global green */
[data-testid="stSidebar"] .stButton > button {{
  font-size: .6875rem !important;
  font-weight: 600 !important;
  letter-spacing: .02em !important;
  min-height: 30px !important;
  padding: .3rem .5rem !important;
  border-radius: 6px !important;
  box-shadow: none !important;
  width: 100% !important;
  background: #fff !important;
  color: #384250 !important;
  border: 1px solid #E5E7EB !important;
  transition: background .15s, color .15s, border-color .15s !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  background: #F3F4F6 !important;
  border-color: #D2D6DB !important;
  transform: none !important;
}}
/* card action buttons — second column (delete) turns red on hover */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"]:last-child .stButton > button:hover {{
  background: #FEF2F2 !important;
  color: #DC2626 !important;
  border-color: #FECACA !important;
}}
/* card action buttons — first column (download) turns green on hover */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"]:first-child .stButton > button {{
  color: #1B8354 !important;
  border-color: #C3E0CC !important;
}}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"]:first-child .stButton > button:hover {{
  background: #EBF5EE !important;
  border-color: #1B8354 !important;
}}
/* download buttons — green accent (keys start with "dl_") is handled by column selectors above */
/* confirm: yes = red, no = neutral */
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {{
  background: #DC2626 !important;
  color: #fff !important;
  border: none !important;
  font-size: .6875rem !important;
  min-height: 30px !important;
  padding: .3rem .5rem !important;
}}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {{
  background: #B91C1C !important;
  transform: none !important;
}}

/* sidebar empty state */
.hist-empty {{
  text-align: center;
  padding: 2rem 1rem;
}}
.hist-empty-icon {{
  font-size: 2rem;
  line-height: 1;
  margin-bottom: .625rem;
  opacity: .35;
}}
.hist-empty-text {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .8125rem;
  font-weight: 500;
  color: #9DA4AE;
  margin-bottom: .25rem;
}}
.hist-empty-hint {{
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  font-size: .6875rem;
  color: #B0B8C4;
  line-height: 1.5;
}}

/* sidebar metrics — hide default (we use custom stats) */
[data-testid="stSidebar"] [data-testid="stMetric"] {{ display: none !important; }}

/* sidebar caption override */
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
  font-size: .6875rem !important;
  color: #B0B8C4 !important;
}}

/* sidebar download button (actual file download) */
[data-testid="stSidebar"] .stDownloadButton > button {{
  font-size: .75rem !important;
  padding: .4rem .75rem !important;
  min-height: 32px !important;
  background: #EBF5EE !important;
  color: #14573A !important;
  border: 1px solid #C3E0CC !important;
  border-radius: 6px !important;
}}

/* footer — clean green & white */
.rcjy-footer {{
  background: #1B8354;
  margin: 3rem -3rem -3rem;
  font-family: 'IBM Plex Sans','Noto Kufi Arabic',sans-serif;
  direction: {_dir};
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
  font-size: .8125rem;
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
  font-size: .75rem;
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

/* responsive */
@media (max-width: 760px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 0 1rem 2rem !important; }}
  .rcjy-nav {{ margin: 0 -1rem 1rem; }}
  .rcjy-nav-inner {{ padding: 0 1rem; gap: .5rem; min-height: 56px; flex-wrap: wrap; }}
  .rcjy-nav-item {{ font-size: .8125rem !important; padding: 7px 9px !important; }}
  .rcjy-nav-logo {{ height: 36px; }}
  .rcjy-nav-right {{ gap: .5rem; }}
  .rcjy-footer {{ margin: 3rem -1rem -3rem; }}
  .rcjy-ftr-main {{ padding: 1.25rem 1rem; flex-direction: column; align-items: flex-start; }}
  .rcjy-ftr-rcjy, .rcjy-ftr-vision {{ height: 36px; }}
}}
@media (max-width: 480px) {{
  .rcjy-nav-links {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
}}
</style>
<!-- Security headers via meta tags (defense-in-depth for client-side) -->
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="DENY">
<meta name="referrer" content="strict-origin-when-cross-origin">
""", unsafe_allow_html=True)

# navbar
active_tab = _qp.get("tab", "text")
if active_tab not in ("text", "image", "video", "voice", "podcast"):
    active_tab = "text"
# Output language = UI language (user can override via prompt instructions)
lang = st.session_state.ui_lang
_nl = lang


def _ni(key, label):
    """One nav item — target=_self keeps navigation in the same tab."""
    cls = "rcjy-nav-item rcjy-nav-active" if key == active_tab else "rcjy-nav-item"
    return (f'<li><a href="?tab={key}&lang={_nl}" '
            f'class="{cls}" target="_self">{label}</a></li>')


# UI language — single link showing the OTHER language (RCJY site style)
_other_lang_text = "العربية" if _nl == "en" else "English"
_other_lang_href = f"?tab={active_tab}&lang={'ar' if _nl == 'en' else 'en'}"

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
    </ul>
    <div class="rcjy-nav-right">
      <a href="{_other_lang_href}" class="rcjy-lang-link" target="_self">{_other_lang_text}</a>
    </div>
  </div>
</nav>
""", unsafe_allow_html=True)

if not _api_ok:
    st.warning(L["warn_api"])


# shared helpers
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
            # Sanitize filenames before display (escape HTML entities)
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


# text tab
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
        _tags("Gemini 3.1 Pro", "Gemini 3 Flash")
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

    if st.button(L["btn_text"], width="stretch", key="btn_text"):
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

# image tab
elif active_tab == "image":
    with st.container(border=True):
        _tags("Imagen 4", "Nano Banana 2", "Nano Banana Pro", "Up to 4K")
        _i1, _i2 = st.columns(2)
        with _i1:
            img_model = st.selectbox(
                L["model_label"],
                ["imagen_fast", "imagen", "imagen_ultra", "nano_banana", "nano_banana_2", "nano_banana_pro"],
                format_func=lambda x: {
                    "imagen_fast":      "Imagen 4 Fast",
                    "imagen":           "Imagen 4 Flagship",
                    "imagen_ultra":     "Imagen 4 Ultra",
                    "nano_banana":      "Nano Banana",
                    "nano_banana_2":    "Nano Banana 2",
                    "nano_banana_pro":  "Nano Banana Pro",
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

    if st.button(L["btn_image"], width="stretch", key="btn_img"):
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

# video tab
elif active_tab == "video":
    # Total-duration options: value = extend_seconds beyond the initial 8s clip
    _dur_options = {
        L["total_dur_8"]:   0,
        L["total_dur_15"]:  7,
        L["total_dur_22"]:  14,
        L["total_dur_29"]:  21,
        L["total_dur_43"]:  35,
        L["total_dur_57"]:  49,
        L["total_dur_78"]:  70,
        L["total_dur_148"]: 140,
    }

    with st.container(border=True):
        _tags("Veo 3.1 Standard", "Veo 3.1 Fast", "Up to 4K", "Up to ~148s")
        _v1, _v2, _v3, _v4 = st.columns(4)
        with _v1:
            _vm = st.selectbox(L["video_model_label"], ["Standard", "Fast"], key="vid_model")
            vid_model = "standard" if _vm == "Standard" else "fast"
        with _v2:
            vid_aspect = st.selectbox(L["aspect_label"], ["16:9", "9:16"], key="vid_aspect")
        with _v3:
            _dur_label = st.selectbox(
                L["total_duration_label"],
                list(_dur_options.keys()),
                index=0,
                key="vid_total_dur",
            )
            vid_extend = _dur_options[_dur_label]
        with _v4:
            # Extension forces 720p; only allow higher res for single clips
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

    if st.button(L["btn_video"], width="stretch", key="btn_vid"):
        if not vid_prompt.strip():
            st.warning(L["warn_prompt"])
        else:
            _spin_msg = L["spin_video_extend"] if vid_extend > 0 else L["spin_video"]
            # For extended videos use a placeholder so we can show progress
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

# voice tab
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
        _tags("Gemini TTS Flash", "Gemini TTS Pro")
        _o1, _o2, _o3 = st.columns(3)
        with _o1:
            _vsel = st.selectbox(
                L["voice_label"], list(_voice_opts_v), key="voice_name_sel",
            )
            voice_name = _voice_opts_v[_vsel]
            _voice_display = _vsel.split(" ♀")[0].split(" ♂")[0].strip()
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
        input_url, input_files = _ctx_widget()
        ctx_text, has_ctx = _load_ctx(input_url, input_files)

    if st.button(L["btn_voice"], width="stretch", key="btn_voice"):
        if not voice_prompt.strip() and not has_ctx:
            st.warning(L["warn_text"])
        else:
            with st.spinner(L["spin_voice"]):
                try:
                    data, mime = generate_voice(
                        text=voice_prompt.strip(), context_text=ctx_text if has_ctx else "",
                        voice_name=voice_name, display_name=_voice_display if is_ar else "",
                        style_hint=style_hint,
                        tts_model="pro" if tts_quality == "Pro" else "flash",
                        lang=lang,
                    )
                    st.session_state.result_voice = (data, mime)
                    if _history_ok:
                        history.save_entry("voice", voice_prompt.strip(), data, mime,
                                           {"voice": voice_name, "quality": tts_quality, "style": style_hint}, lang)
                except Exception as e:
                    logger.exception("Voice generation failed")
                    st.error(_sanitize_error(e))

    if st.session_state.result_voice:
        st.audio(st.session_state.result_voice[0], format="audio/wav")
        st.download_button(
            L["btn_download"], data=st.session_state.result_voice[0],
            file_name="rcjy_voice.wav", mime="audio/wav", key="dl_voice",
        )

# podcast tab
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
        _tags("Gemini 3 Flash", "Multi-Speaker TTS")
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

    if st.button(L["btn_podcast"], width="stretch", key="btn_pod"):
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
