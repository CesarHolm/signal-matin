"""Memoire du journal d'une edition a l'autre (stockee localement, hors depot).

Chaque edition enregistre ce qu'elle a imprime dans data/editions/AAAA-MM-JJ.json :
mots appris, mots a reviser (avec leurs definitions), solutions des jeux,
reponses du quiz et articles publies. L'edition suivante relit la precedente
pour imprimer les reponses de la veille.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from ..config import ROOT

DOSSIER = ROOT / "data"


def dossier_editions(racine: Path = DOSSIER) -> Path:
    chemin = racine / "editions"
    chemin.mkdir(parents=True, exist_ok=True)
    return chemin


def enregistrer_edition(jour: dt.date, contenu: dict, racine: Path = DOSSIER) -> Path:
    chemin = dossier_editions(racine) / f"{jour.isoformat()}.json"
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin


def editions_passees(jour: dt.date, racine: Path = DOSSIER) -> list[dict]:
    """Editions anterieures a `jour`, de la plus ancienne a la plus recente."""
    resultat = []
    for fichier in sorted(dossier_editions(racine).glob("*.json")):
        try:
            date = dt.date.fromisoformat(fichier.stem)
        except ValueError:
            continue
        if date < jour:
            try:
                resultat.append(json.loads(fichier.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
    return resultat


def edition_precedente(jour: dt.date, racine: Path = DOSSIER) -> dict | None:
    passees = editions_passees(jour, racine)
    return passees[-1] if passees else None


def articles_deja_publies(jour: dt.date, racine: Path = DOSSIER, jours: int = 10) -> set[str]:
    limite = jour - dt.timedelta(days=jours)
    urls: set[str] = set()
    for edition in editions_passees(jour, racine):
        if dt.date.fromisoformat(edition.get("date", "1970-01-01")) >= limite:
            urls.update(edition.get("articles", []))
    return urls
