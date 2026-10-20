"""Outils PDF : lecture, aperçu (JPEG) et fusion."""

from __future__ import annotations

import io
import threading

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter

# pdfium n'est pas thread-safe
_pdfium_lock = threading.Lock()


def inspect(data: bytes) -> dict:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = len(reader.pages)
    except Exception as exc:
        raise ValueError("PDF illisible") from exc
    if pages < 1:
        raise ValueError("PDF vide")
    return {"pages": pages}


def render_page(data: bytes, index: int, width: int = 1200) -> bytes:
    with _pdfium_lock:
        pdf = pdfium.PdfDocument(data)
        try:
            if not 0 <= index < len(pdf):
                raise IndexError(index)
            page = pdf[index]
            page_width = page.get_width() or 595
            bitmap = page.render(scale=width / page_width)
            image = bitmap.to_pil()
            buf = io.BytesIO()
            image.convert("RGB").save(buf, format="JPEG", quality=82, optimize=True, progressive=True)
            page.close()
            return buf.getvalue()
        finally:
            pdf.close()


def merge(documents: list[bytes]) -> bytes:
    writer = PdfWriter()
    for data in documents:
        writer.append(PdfReader(io.BytesIO(data)))
    buf = io.BytesIO()
    writer.write(buf)
    writer.close()
    return buf.getvalue()
