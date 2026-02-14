import csv
import io
import re
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from PIL import Image

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".bmp": "image/bmp", ".tiff": "image/tiff", ".tif": "image/tiff",
    ".ico": "image/x-icon",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
    ".m4a": "audio/mp4", ".flac": "audio/flac", ".aac": "audio/aac",
    ".wma": "audio/x-ms-wma",
    ".mp4": "video/mp4", ".avi": "video/x-msvideo", ".mov": "video/quicktime",
    ".mkv": "video/x-matroska", ".webm": "video/webm", ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv", ".mpeg": "video/mpeg",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv", ".json": "application/json", ".xml": "application/xml",
    ".html": "text/html", ".htm": "text/html",
    ".txt": "text/plain", ".md": "text/markdown", ".rtf": "application/rtf",
}


def get_mime_type(filename: str) -> str:
    return MIME_MAP.get(Path(filename).suffix.lower(), "application/octet-stream")


def is_image(filename: str) -> bool:
    return get_mime_type(filename).startswith("image/")


def is_audio(filename: str) -> bool:
    return get_mime_type(filename).startswith("audio/")


def is_video(filename: str) -> bool:
    return get_mime_type(filename).startswith("video/")


def extract_from_url(url: str, max_chars: int = 50000) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; RCJY-MediaBot/1.0)"}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated...]"
        return text.strip() or "Could not extract text from URL."
    except Exception as e:
        return f"Error fetching URL: {e}"


def extract_from_pdf(file) -> str:
    if PdfReader is None:
        return "Error: pypdf not installed."
    try:
        reader = PdfReader(file)
        parts = [page.extract_text() for page in reader.pages if page.extract_text()]
        return "\n\n".join(parts)[:50000] or "No text found in PDF."
    except Exception as e:
        return f"Error reading PDF: {e}"


def extract_from_docx(file) -> str:
    if DocxDocument is None:
        return "Error: python-docx not installed."
    try:
        doc = DocxDocument(file)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())[:50000] or "No text found."
    except Exception as e:
        return f"Error reading DOCX: {e}"


def extract_from_txt(file) -> str:
    try:
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")
        return content[:50000]
    except Exception as e:
        return f"Error reading file: {e}"


def extract_from_csv(file) -> str:
    try:
        content = file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(content))
        rows = []
        for i, row in enumerate(reader):
            if i > 500:
                rows.append("[... truncated ...]")
                break
            rows.append(" | ".join(row))
        return "\n".join(rows)[:50000]
    except Exception as e:
        return f"Error reading CSV: {e}"


def extract_from_pptx(file) -> str:
    try:
        from pptx import Presentation
        prs = Presentation(file)
        parts = []
        for i, slide in enumerate(prs.slides, 1):
            slide_text = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        if para.text.strip():
                            slide_text.append(para.text.strip())
            if slide_text:
                parts.append(f"[Slide {i}]\n" + "\n".join(slide_text))
        return "\n\n".join(parts)[:50000] or "No text found in presentation."
    except ImportError:
        return "Error: python-pptx not installed."
    except Exception as e:
        return f"Error reading PPTX: {e}"


def extract_from_xlsx(file) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file, data_only=True)
        parts = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(max_row=200, values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                parts.append(f"[Sheet: {sheet_name}]\n" + "\n".join(rows))
        return "\n\n".join(parts)[:50000] or "No data found in spreadsheet."
    except ImportError:
        return "Error: openpyxl not installed."
    except Exception as e:
        return f"Error reading Excel: {e}"


def get_content_from_input(
    text: Optional[str] = None,
    url: Optional[str] = None,
    files: Optional[list] = None,
) -> tuple[str, list[tuple[str, str, bytes]]]:
    parts: list[tuple[str, str]] = []
    attachments: list[tuple[str, str, bytes]] = []

    if text and text.strip():
        parts.append(("User input", text.strip()))

    if url and url.strip():
        parts.append(("URL content", extract_from_url(url.strip())))

    if files:
        for f in files:
            if f is None:
                continue
            name = getattr(f, "name", "attachment")
            suffix = Path(name).suffix.lower()
            mime = get_mime_type(name)

            try:
                f.seek(0)
            except Exception:
                pass

            if is_image(name):
                try:
                    data = f.read()
                    attachments.append((name, mime, data))
                    parts.append((f"Image: {name}", "[Image attached]"))
                except Exception:
                    pass

            elif is_audio(name):
                try:
                    data = f.read()
                    attachments.append((name, mime, data))
                    parts.append((f"Audio: {name}", f"[Audio file attached: {name}]"))
                except Exception:
                    pass

            elif is_video(name):
                try:
                    data = f.read()
                    attachments.append((name, mime, data))
                    parts.append((f"Video: {name}", f"[Video file attached: {name}]"))
                except Exception:
                    pass

            elif suffix == ".pdf":
                content = extract_from_pdf(f)
                parts.append((f"PDF: {name}", content))
                try:
                    f.seek(0)
                    attachments.append((name, mime, f.read()))
                except Exception:
                    pass

            elif suffix in (".docx", ".doc"):
                content = extract_from_docx(f)
                parts.append((f"Document: {name}", content))
                try:
                    f.seek(0)
                    attachments.append((name, mime, f.read()))
                except Exception:
                    pass

            elif suffix in (".pptx", ".ppt"):
                content = extract_from_pptx(f)
                parts.append((f"Presentation: {name}", content))
                try:
                    f.seek(0)
                    attachments.append((name, mime, f.read()))
                except Exception:
                    pass

            elif suffix in (".xlsx", ".xls"):
                content = extract_from_xlsx(f)
                parts.append((f"Spreadsheet: {name}", content))
                try:
                    f.seek(0)
                    attachments.append((name, mime, f.read()))
                except Exception:
                    pass

            elif suffix == ".csv":
                parts.append((f"CSV: {name}", extract_from_csv(f)))

            elif suffix in (".txt", ".md", ".rtf", ".json", ".xml", ".html", ".htm"):
                parts.append((f"Text: {name}", extract_from_txt(f)))

            else:
                try:
                    raw = f.read()
                    if isinstance(raw, bytes):
                        if len(raw) < 200_000:
                            try:
                                txt = raw.decode("utf-8", errors="strict")
                                parts.append((f"File: {name}", txt[:30000]))
                            except UnicodeDecodeError:
                                attachments.append((name, mime, raw))
                                parts.append((f"Binary: {name}", f"[Binary file attached: {name}]"))
                        else:
                            attachments.append((name, mime, raw))
                            parts.append((f"File: {name}", f"[Large file attached: {name}]"))
                except Exception:
                    pass

    combined = "\n\n---\n\n".join(f"[{title}]\n{content}" for title, content in parts)
    return combined or "No content provided.", attachments
