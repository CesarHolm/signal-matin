import datetime as dt

from signal_matin.connectors.rss import collect_rss
from signal_matin.models import DataState


RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Une information de test</title><link>https://example.org/a</link>
<description>Un resume entierement fictif pour le test du connecteur.</description>
<pubDate>Sat, 26 Sep 2026 06:00:00 +0000</pubDate></item>
</channel></rss>"""


def test_rss_is_normalized(monkeypatch):
    monkeypatch.setattr("signal_matin.connectors.rss._payload", lambda _url: RSS)
    now = dt.datetime(2026, 9, 26, 8, tzinfo=dt.timezone.utc)
    items, status = collect_rss([
        {"name": "Source test", "category": "Monde", "url": "https://example.org/rss"}
    ], now)
    assert status.state == DataState.LIVE
    assert items[0].title == "Une information de test"
    assert items[0].source.name == "Source test"


def test_empty_rss_is_optional():
    items, status = collect_rss([], dt.datetime.now().astimezone())
    assert items == []
    assert status.state == DataState.DISABLED


def test_rss_tolerates_cdn_script_after_root(monkeypatch):
    payload = b"""<?xml version="1.0"?><rss><channel><item><title>Titre GC</title>
<link>https://exemple.org/gc</link><pubDate>Sat, 17 Oct 2026 08:00:00 +0000</pubDate></item>
</channel></rss>
<script src="https://static.cloudflareinsights.com/beacon.min.js"></script>"""
    monkeypatch.setattr("signal_matin.connectors.rss._payload", lambda url: payload)
    now = dt.datetime(2026, 10, 18, 7, tzinfo=dt.timezone.utc)
    items, status = collect_rss([{"name": "GC", "url": "https://exemple.org/feed"}], now)
    assert [item.title for item in items] == ["Titre GC"]
    assert status.state == DataState.LIVE


def test_rss_parses_non_standard_dates():
    from signal_matin.connectors.rss import _parse_date
    assert _parse_date("2026 Oct 16   04:17:33 PDT").utcoffset() == dt.timedelta(hours=-7)
    assert _parse_date("Oct 16, 2026").date() == dt.date(2026, 10, 16)


def test_rss_reads_date_from_time_tag_in_description(monkeypatch):
    payload = b"""<rss><channel><item><title>Q&amp;A ESMA</title><link>https://exemple.org/esma</link>
<description>&lt;time datetime="2026-10-16T16:14:51+02:00"&gt;16 October 2026&lt;/time&gt; Texte</description>
</item></channel></rss>"""
    monkeypatch.setattr("signal_matin.connectors.rss._payload", lambda url: payload)
    now = dt.datetime(2026, 10, 18, 7, tzinfo=dt.timezone.utc)
    items, _ = collect_rss([{"name": "ESMA", "url": "https://exemple.org/esma"}], now, max_age_hours=24)
    assert items == []  # date retrouvee (> 24 h) : l'article est bien filtre
    items, _ = collect_rss([{"name": "ESMA", "url": "https://exemple.org/esma"}], now, max_age_hours=72)
    assert items[0].source.published_at.date() == dt.date(2026, 10, 16)
