"""Diagnostic de l'installation : flux, extraction des articles, API Anthropic."""
from __future__ import annotations

import datetime as dt
import os

from . import articles as art
from . import ia


def diagnostiquer(config: dict, journal=print) -> int:
    conf = config.get("journal", {})
    maintenant = dt.datetime.now().astimezone()
    journal("· Flux et extraction du texte intégral (2 articles par source)")
    for bloc in conf.get("blocs", []):
        for source in bloc.get("sources", []):
            items, statut = art.collect_rss([{"name": source["nom"], "url": source["url"]}],
                                            maintenant, limit=2, max_age_hours=96)
            if not items:
                journal(f"  {source['nom']:24} flux : {statut.detail} — aucun article récent")
                continue
            for item in items[:2]:
                url = str(item.source.url or "")
                texte, _ = art.texte_integral(url, item.summary)
                cause = "" if len(texte) >= 1000 else " ← " + art.DERNIERE_ERREUR.get(url, "texte trop court")
                journal(f"  {source['nom']:24} {len(texte):6} car. {url[:70]}{cause}")
    journal("· API Anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        journal("  ! clé absente du fichier .env")
        return 1
    try:
        client = ia.ClientIA(conf.get("ia", {}), journal=journal)
        for modele in (client.modele_tri, client.modele_synthese):
            r = client.client.messages.create(model=modele, max_tokens=5,
                                              messages=[{"role": "user", "content": "Réponds OK."}])
            journal(f"  {modele} : OK ({r.usage.input_tokens} tokens)")
    except Exception as erreur:
        journal(f"  ! {type(erreur).__name__}: {str(erreur)[:300]}")
        return 1
    return 0
