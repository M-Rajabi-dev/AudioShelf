# ebook_content.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import html
import os
import posixpath
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from typing import List
from xml.etree import ElementTree


class EbookLoadError(Exception):
    """Raised when an ebook cannot be loaded into readable text."""


@dataclass
class EbookChapter:
    title: str
    start_offset: int


@dataclass
class EbookContent:
    text: str
    chapters: List[EbookChapter]


def _decode_bytes(data: bytes) -> str:
    encodings = ["utf-8-sig", "utf-16", "cp1252", "latin-1"]
    for enc in encodings:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _html_to_text(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|section|article|h1|h2|h3|h4|h5|h6|li|tr|td)>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return _normalize_text(text)


def _first_heading(markup: str) -> str:
    m = re.search(r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>", markup)
    if not m:
        return ""
    heading = _html_to_text(m.group(1))
    return heading.strip()


def _load_plain(path: str) -> EbookContent:
    with open(path, "rb") as f:
        text = _normalize_text(_decode_bytes(f.read()))
    if not text:
        raise EbookLoadError("The ebook has no readable text content.")
    return EbookContent(text=text, chapters=[EbookChapter(title="Start", start_offset=0)])


def _load_html(path: str) -> EbookContent:
    with open(path, "rb") as f:
        markup = _decode_bytes(f.read())
    text = _html_to_text(markup)
    if not text:
        raise EbookLoadError("The ebook has no readable text content.")
    title = _first_heading(markup) or "Start"
    return EbookContent(text=text, chapters=[EbookChapter(title=title, start_offset=0)])


def _load_pdf(path: str) -> EbookContent:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as e:
        raise EbookLoadError("PDF support requires the 'pypdf' dependency.") from e

    try:
        reader = PdfReader(path)
    except Exception as e:
        raise EbookLoadError(f"Could not open PDF: {e}") from e

    pages = []
    chapters = []
    cursor = 0
    for idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        page_text = _normalize_text(page_text)
        if not page_text:
            continue

        title = f"Page {idx + 1}"
        chapters.append(EbookChapter(title=title, start_offset=cursor))
        pages.append(page_text)
        cursor += len(page_text) + 2

    if not pages:
        raise EbookLoadError("No readable text was found in the PDF.")

    return EbookContent(text="\n\n".join(pages), chapters=chapters or [EbookChapter("Start", 0)])


def _find_epub_opf(zf: zipfile.ZipFile) -> str:
    container_paths = ["META-INF/container.xml", "meta-inf/container.xml"]
    for container_path in container_paths:
        try:
            raw = zf.read(container_path)
        except KeyError:
            continue

        try:
            root = ElementTree.fromstring(raw)
        except ElementTree.ParseError:
            continue

        for rootfile in root.findall(".//{*}rootfile"):
            full_path = rootfile.attrib.get("full-path")
            if full_path:
                return full_path
    return ""


def _load_epub(path: str) -> EbookContent:
    try:
        zf = zipfile.ZipFile(path, "r")
    except Exception as e:
        raise EbookLoadError(f"Could not open EPUB: {e}") from e

    with zf:
        opf_path = _find_epub_opf(zf)
        if not opf_path:
            raise EbookLoadError("Invalid EPUB: package document not found.")

        try:
            opf_root = ElementTree.fromstring(zf.read(opf_path))
        except Exception as e:
            raise EbookLoadError(f"Invalid EPUB package: {e}") from e

        manifest = {}
        for item in opf_root.findall(".//{*}manifest/{*}item"):
            item_id = item.attrib.get("id")
            href = item.attrib.get("href")
            if item_id and href:
                manifest[item_id] = href

        spine_ids = []
        for itemref in opf_root.findall(".//{*}spine/{*}itemref"):
            idref = itemref.attrib.get("idref")
            if idref:
                spine_ids.append(idref)

        opf_dir = posixpath.dirname(opf_path)
        segments = []
        chapters = []
        cursor = 0

        for index, idref in enumerate(spine_ids):
            href = manifest.get(idref)
            if not href:
                continue

            spine_doc_path = posixpath.normpath(posixpath.join(opf_dir, href))
            try:
                raw_doc = zf.read(spine_doc_path)
            except KeyError:
                continue

            markup = _decode_bytes(raw_doc)
            text = _html_to_text(markup)
            if not text:
                continue

            chapter_title = _first_heading(markup)
            if not chapter_title:
                chapter_title = os.path.splitext(os.path.basename(href))[0].replace("_", " ").strip()
            if not chapter_title:
                chapter_title = f"Chapter {index + 1}"

            chapters.append(EbookChapter(title=chapter_title, start_offset=cursor))
            segments.append(text)
            cursor += len(text) + 2

        if not segments:
            raise EbookLoadError("No readable text was found inside the EPUB.")

        return EbookContent(
            text="\n\n".join(segments),
            chapters=chapters or [EbookChapter(title="Start", start_offset=0)]
        )


def _load_cbz(path: str) -> EbookContent:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            image_files = [
                name for name in zf.namelist()
                if os.path.splitext(name)[1].lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
            ]
    except Exception as e:
        raise EbookLoadError(f"Could not open CBZ archive: {e}") from e

    if not image_files:
        raise EbookLoadError("This CBZ file has no readable pages.")

    lines = [
        "Comic archive detected.",
        f"Total pages: {len(image_files)}.",
        "",
        "Image rendering is not yet available in AudioShelf. Use Download from Server to open this file in an external comic reader."
    ]
    return EbookContent(text="\n".join(lines), chapters=[EbookChapter("Start", 0)])


def _load_cbr(path: str) -> EbookContent:
    lines = [
        "CBR comic archive detected.",
        "Image rendering is not yet available in AudioShelf.",
        "Use Download from Server to open this file in an external comic reader."
    ]
    return EbookContent(text="\n".join(lines), chapters=[EbookChapter("Start", 0)])


def _load_mobi_like(path: str) -> EbookContent:
    try:
        import mobi  # type: ignore
    except Exception as e:
        raise EbookLoadError("MOBI/AZW3 support requires the optional 'mobi' dependency.") from e

    workdir = tempfile.mkdtemp(prefix="audioshelf_mobi_")
    try:
        extracted = mobi.extract(path, workdir)
        unpacked_path = ""
        if isinstance(extracted, tuple) and len(extracted) >= 2:
            unpacked_path = str(extracted[1] or "")
        elif isinstance(extracted, str):
            unpacked_path = extracted

        if not unpacked_path or not os.path.exists(unpacked_path):
            raise EbookLoadError("MOBI/AZW3 extraction failed.")

        ext = os.path.splitext(unpacked_path)[1].lower()
        if ext in {".html", ".htm", ".xhtml", ".xml", ".opf"}:
            return _load_html(unpacked_path)
        return _load_plain(unpacked_path)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def load_ebook_content(path: str) -> EbookContent:
    if not path:
        raise EbookLoadError("No ebook path provided.")
    if not os.path.exists(path):
        raise EbookLoadError("Ebook file not found.")

    ext = os.path.splitext(path)[1].lower()
    if ext in {".txt", ".nfo", ".abs"}:
        return _load_plain(path)
    if ext in {".html", ".htm", ".xhtml", ".xht", ".opf", ".xml"}:
        return _load_html(path)
    if ext == ".epub":
        return _load_epub(path)
    if ext == ".pdf":
        return _load_pdf(path)
    if ext == ".cbz":
        return _load_cbz(path)
    if ext == ".cbr":
        return _load_cbr(path)
    if ext in {".mobi", ".azw3"}:
        return _load_mobi_like(path)

    raise EbookLoadError(f"Unsupported ebook format: {ext or 'unknown'}.")
