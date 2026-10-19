"""Collecte RSS/Atom generique, sans dependance a un fournisseur."""
from __future__ import annotations

import datetime as dt
import html
import math
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from ..models import DataSourceStatus, DataState, NewsItem, SourceRef


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].lower()


def _text(element: ET.Element, names: set[str]) -> str:
    for child in element:
        if _tag(child) in names:
            value = "".join(child.itertext())
            if value:
                return " ".join(value.split())
    return ""


def _link(element: ET.Element) -> str | None:
    for child in element:
        if _tag(child) == "link":
            return child.attrib.get("href") or (child.text or "").strip() or None
    return None


def _plain(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html.unescape(value or "")).split())


def _clip(value: str, limit: int) -> str:
    """Coupe proprement un texte trop long (sur un mot), avec points de suspension."""
    if len(value) <= limit:
        return value
    cut = value[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return cut + "…"


_TZ_ABBREVIATIONS = {
    "UTC": 0, "GMT": 0, "CET": 1, "CEST": 2,
    "EST": -5, "EDT": -4, "CST": -6, "CDT": -5,
    "MST": -7, "MDT": -6, "PST": -8, "PDT": -7,
}
_DATETIME_ATTR = re.compile(r'datetime\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


def _parse_date(value: str) -> dt.datetime | None:
    value = " ".join((value or "").split())
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    # Formats non standard rencontres (ex. Sixth Tone) :
    # "2026 Oct 16 04:17:33 PDT" et "Oct 16, 2026".
    parts = value.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].upper() in _TZ_ABBREVIATIONS:
        offset = dt.timezone(dt.timedelta(hours=_TZ_ABBREVIATIONS[parts[1].upper()]))
        for fmt in ("%Y %b %d %H:%M:%S", "%b %d, %Y %H:%M:%S", "%d %b %Y %H:%M:%S"):
            try:
                return dt.datetime.strptime(parts[0], fmt).replace(tzinfo=offset)
            except ValueError:
                continue
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %B %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return None


def _date(element: ET.Element) -> dt.datetime | None:
    parsed = _parse_date(_text(element, {"pubdate", "published", "updated", "date"}))
    if parsed is None:
        # Certains flux (ex. ESMA) n'ont pas de date d'item : la date figure
        # seulement dans une balise <time datetime="..."> de la description.
        for child in element:
            if _tag(child) in {"description", "summary", "content", "encoded"}:
                match = _DATETIME_ATTR.search(html.unescape("".join(child.itertext())))
                if match:
                    parsed = _parse_date(match.group(1))
                    if parsed:
                        break
    if parsed is None:
        return None
    return parsed.astimezone() if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc).astimezone()


def _payload(url: str) -> bytes:
    # L'en-tete Accept est requis par certains serveurs (ex. NPR repond 403 sans).
    request = urllib.request.Request(url, headers={
        "User-Agent": "Signal-Matin/1.0",
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
    })
    with urllib.request.urlopen(request, timeout=12) as response:
        return response.read(2_000_000)


_ROOT_END = re.compile(rb"</(?:rss|feed|rdf:RDF)\s*>", re.IGNORECASE)


def _trim_trailing_junk(payload: bytes) -> bytes:
    """Retire ce qu'un CDN injecte apres la balise racine (ex. script Cloudflare)."""
    ends = list(_ROOT_END.finditer(payload))
    return payload[: ends[-1].end()] if ends else payload


def collect_rss(
    feeds: list, now: dt.datetime, *, limit: int = 12, max_age_hours: int = 72,
    status_name: str = "Actualites",
) -> tuple[list[NewsItem], DataSourceStatus]:
    if not feeds:
        return [], DataSourceStatus(
            name=status_name, state=DataState.DISABLED,
            detail="Aucun flux RSS configure.",
        )
    buckets: list[list[NewsItem]] = []
    seen: set[str] = set()
    cutoff = now - dt.timedelta(hours=max_age_hours)
    future_limit = now + dt.timedelta(hours=6)
    per_feed = max(2, math.ceil(limit / max(1, len(feeds))))
    errors = 0
    for entry in feeds:
        if isinstance(entry, str):
            name, category, url = "Source", "Actualites", entry
        elif isinstance(entry, dict):
            name = str(entry.get("name") or entry.get("nom") or "Source")
            category = str(entry.get("category") or entry.get("categorie") or "Actualites")
            url = str(entry.get("url") or "")
        else:
            continue
        if not url:
            continue
        try:
            payload = _trim_trailing_junk(_payload(url))
            try:
                root = ET.fromstring(payload)
            except ET.ParseError:
                repaired = payload.decode("utf-8", errors="replace")
                repaired = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", repaired)
                repaired = re.sub(
                    r"&(?!#\d+;|#x[0-9A-Fa-f]+;|[A-Za-z][A-Za-z0-9]+;)",
                    "&amp;", repaired,
                )
                root = ET.fromstring(repaired)
            bucket: list[NewsItem] = []
            for node in (node for node in root.iter() if _tag(node) in {"item", "entry"}):
                title = _plain(_text(node, {"title"}))
                link = _link(node) or url
                key = (link or title).casefold()
                published = _date(node)
                if not title or key in seen:
                    continue
                if published and (published < cutoff or published > future_limit):
                    continue
                summary = _plain(_text(node, {"description", "summary", "content"}))
                try:
                    item = NewsItem(
                        title=_clip(title, 240),
                        category=category,
                        summary=_clip(summary, 1600) or "Resume non fourni par le flux.",
                        expanded_summary=_clip(summary, 3200),
                        source=SourceRef(name=name, url=link, published_at=published),
                    )
                except ValueError:
                    # Un article mal forme ne doit pas faire tomber tout le flux.
                    continue
                seen.add(key)
                bucket.append(item)
                if len(bucket) >= per_feed:
                    break
            if bucket:
                buckets.append(bucket)
        except Exception:
            errors += 1
    items: list[NewsItem] = []
    while len(items) < limit and any(buckets):
        for bucket in buckets:
            if bucket and len(items) < limit:
                items.append(bucket.pop(0))
    state = DataState.LIVE if items else DataState.UNAVAILABLE
    detail = f"{len(feeds) - errors}/{len(feeds)} flux lus"
    return items, DataSourceStatus(
        name=status_name, state=state, detail=detail, item_count=len(items),
    )
