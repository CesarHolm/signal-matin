"""Collecte des candidats par bloc et recuperation du texte complet des articles."""
from __future__ import annotations

import datetime as dt
import re
import urllib.request
from dataclasses import dataclass, field

from ..connectors.rss import collect_rss

USER_AGENT = "Mozilla/5.0 (compatible; Signal-Matin/1.0; journal personnel)"


@dataclass
class Candidat:
    id: str
    bloc: str
    rubrique: str
    source: str
    titre: str
    resume: str
    url: str
    publie_le: dt.datetime | None
    nature: str = "actu"  # "actu" ou "methode" (sport)
    texte: str = ""
    auteur: str = ""

    def pour_tri(self) -> dict:
        return {
            "id": self.id, "rubrique": self.rubrique, "source": self.source,
            "nature": self.nature, "titre": self.titre,
            "date": self.publie_le.strftime("%Y-%m-%d %H:%M") if self.publie_le else "inconnue",
            "resume": self.resume[:600],
        }


@dataclass
class Bloc:
    id: str
    titre: str
    rubriques: list[str]
    candidats: list[Candidat] = field(default_factory=list)


def fenetre_heures(jour: dt.date, config: dict) -> int:
    """24 h du mardi au vendredi ; le lundi couvre vendredi, samedi et dimanche."""
    if jour.weekday() == 0:
        return int(config.get("fenetre_lundi_heures", 72))
    return int(config.get("fenetre_heures", 24))


def collecter(config: dict, maintenant: dt.datetime, deja_publies: set[str]) -> tuple[list[Bloc], list[str]]:
    heures = fenetre_heures(maintenant.date(), config)
    blocs: list[Bloc] = []
    erreurs: list[str] = []
    compteur = 0
    for bloc_conf in config.get("blocs", []):
        bloc = Bloc(id=bloc_conf["id"], titre=bloc_conf["titre"],
                    rubriques=[s.get("rubrique", "") for s in bloc_conf.get("sources", [])])
        for source in bloc_conf.get("sources", []):
            items, statut = collect_rss(
                [{"name": source["nom"], "url": source["url"], "category": source.get("rubrique", "")}],
                maintenant, limit=int(source.get("max", 12)), max_age_hours=heures,
                status_name=source["nom"],
            )
            if not statut.detail.startswith("1/1"):
                erreurs.append(source["nom"])
            for item in items:
                url = str(item.source.url or "")
                if url in deja_publies:
                    continue
                compteur += 1
                bloc.candidats.append(Candidat(
                    id=f"a{compteur}", bloc=bloc.id, rubrique=source.get("rubrique", ""),
                    source=source["nom"], titre=item.title, resume=item.summary, url=url,
                    publie_le=item.source.published_at, nature=source.get("nature", "actu"),
                ))
        blocs.append(bloc)
    return blocs, erreurs


def texte_integral(url: str, repli: str = "") -> tuple[str, str]:
    """Retourne (texte, auteur). Repli sur le resume du flux si l'extraction echoue."""
    try:
        import trafilatura
    except ImportError:  # dependance optionnelle
        return repli, ""
    try:
        requete = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(requete, timeout=20) as reponse:
            page = reponse.read(3_000_000).decode("utf-8", errors="replace")
        texte = trafilatura.extract(page, include_comments=False, include_tables=False,
                                    favor_precision=True) or ""
        meta = trafilatura.extract_metadata(page)
        auteur = (meta.author or "") if meta else ""
    except Exception:
        return repli, ""
    texte = re.sub(r"\n{3,}", "\n\n", texte).strip()
    if len(texte) < max(400, len(repli)):
        return repli, auteur
    return texte[:40_000], auteur
