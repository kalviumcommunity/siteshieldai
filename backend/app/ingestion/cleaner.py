"""Deterministic text normalization and running header/footer filtering."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from app.ingestion.models import ExtractedPage

_INVISIBLE_CHARS_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")
_BULLET_PREFIX_RE = re.compile(r"^[\u25cf\u2022\u25aa\u25e6]+\s*")
_MULTI_SPACE_RE = re.compile(r"[ \t\u00a0]+")
_PAGE_NUMBER_RE = re.compile(
    r"^(?:page\s*)?(\d{1,4})(?:\s*(?:/|of)\s*\d{1,4})?$",
    re.IGNORECASE,
)


def clean_line_text(raw: str) -> str:
    """Normalize Unicode and remove invisible artifacts while preserving symbols."""
    normalized = unicodedata.normalize("NFKC", raw)
    stripped = _INVISIBLE_CHARS_RE.sub("", normalized)
    collapsed = _MULTI_SPACE_RE.sub(" ", stripped).strip()
    return _BULLET_PREFIX_RE.sub("- ", collapsed)


def clean_cell_text(raw: str | None) -> str:
    """Clean a table cell while collapsing wrapped lines into spaces."""
    if not raw:
        return ""
    lines = [clean_line_text(part) for part in raw.splitlines()]
    return _MULTI_SPACE_RE.sub(" ", " ".join(part for part in lines if part)).strip()


def _normalize_margin_signature(text: str) -> str:
    """Normalize digits in margin lines to detect recurring headers/footers."""
    return re.sub(r"\d+", "#", text.strip().lower())


def strip_running_headers_footers(pages: list[ExtractedPage]) -> list[ExtractedPage]:
    """Strip recurring top/bottom margin lines on multi-page documents (>= 3 pages)."""
    if len(pages) < 3:
        return pages

    top_counts: Counter[str] = Counter()
    bottom_counts: Counter[str] = Counter()

    for page in pages:
        top_limit = page.page_height * 0.10
        bottom_limit = page.page_height * 0.90
        seen_top: set[str] = set()
        seen_bottom: set[str] = set()
        for elem in page.elements:
            if elem.kind != "line" or elem.line is None:
                continue
            sig = _normalize_margin_signature(elem.line.text)
            if not sig:
                continue
            if elem.line.y_bottom <= top_limit:
                seen_top.add(sig)
            elif elem.line.y_top >= bottom_limit:
                seen_bottom.add(sig)
        top_counts.update(seen_top)
        bottom_counts.update(seen_bottom)

    threshold = max(2, int(len(pages) * 0.6))
    recurring_top = {sig for sig, cnt in top_counts.items() if cnt >= threshold}
    recurring_bottom = {sig for sig, cnt in bottom_counts.items() if cnt >= threshold}

    for page in pages:
        top_limit = page.page_height * 0.10
        bottom_limit = page.page_height * 0.90
        kept = []
        for elem in page.elements:
            if elem.kind == "line" and elem.line is not None:
                sig = _normalize_margin_signature(elem.line.text)
                if elem.line.y_bottom <= top_limit and sig in recurring_top:
                    continue
                if elem.line.y_top >= bottom_limit and sig in recurring_bottom:
                    page_match = _PAGE_NUMBER_RE.match(elem.line.text)
                    if page_match and page.printed_page_label is None:
                        page.printed_page_label = page_match.group(1)
                    continue
            kept.append(elem)
        page.elements = kept

    return pages

