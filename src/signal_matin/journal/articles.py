"""Collecte des candidats par bloc et recuperation du texte complet des articles."""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import urllib.parse
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
    sources_complementaires: list[dict] = field(default_factory=list)  # [{"source", "url"}]

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
    consigne: str = ""
    recherche: bool = False


def fenetre_heures(jour: dt.date, config: dict) -> int:
    """24 h par defaut. Le lundi : 72 h pour le journal imprime (vendredi, samedi, dimanche) ;
    48 h pour la version numerique, qui parait aussi le samedi (samedi et dimanche)."""
    if jour.weekday() == 0:
        if config.get("numerique"):
            return int(config.get("fenetre_lundi_heures_numerique", 48))
        return int(config.get("fenetre_lundi_heures", 72))
    return int(config.get("fenetre_heures", 24))


def collecter(config: dict, maintenant: dt.datetime, deja_publies: set[str]) -> tuple[list[Bloc], list[str]]:
    heures = fenetre_heures(maintenant.date(), config)
    blocs: list[Bloc] = []
    erreurs: list[str] = []
    compteur = 0
    liste = config.get("blocs", [])
    if config.get("numerique") and config.get("blocs_numerique"):
        liste = config["blocs_numerique"]
    for bloc_conf in liste:
        bloc = Bloc(id=bloc_conf["id"], titre=bloc_conf["titre"],
                    rubriques=[s.get("rubrique", "") for s in bloc_conf.get("sources", [])],
                    consigne=" ".join(str(bloc_conf.get("consigne", "")).split()),
                    recherche=bool(bloc_conf.get("recherche")))
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
                titre, nom_source = item.title, source["nom"]
                if source.get("google"):
                    # Flux Google Actualites : titre « Titre - Media », lien a resoudre.
                    titre, media = _separer_media(item.title)
                    if _NON_LATIN.search(titre + media):
                        continue  # medias en coreen, cyrillique… : hors perimetre
                    url = resoudre_google(url) or ""
                    if not url:
                        continue
                    nom_source = media or nom_source
                if url in deja_publies:
                    continue
                compteur += 1
                bloc.candidats.append(Candidat(
                    id=f"a{compteur}", bloc=bloc.id, rubrique=source.get("rubrique", ""),
                    source=nom_source, titre=titre, resume=item.summary, url=url,
                    publie_le=item.source.published_at, nature=source.get("nature", "actu"),
                ))
        blocs.append(bloc)
    return blocs, erreurs


DERNIERE_ERREUR: dict[str, str] = {}


def texte_integral(url: str, repli: str = "") -> tuple[str, str]:
    """Retourne (texte, auteur). Repli sur le resume du flux si l'extraction echoue."""
    try:
        import trafilatura
    except ImportError:  # dependance optionnelle
        DERNIERE_ERREUR[url] = "trafilatura non installé"
        return repli, ""
    try:
        requete = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(requete, timeout=20) as reponse:
            page = reponse.read(3_000_000).decode("utf-8", errors="replace")
        texte = trafilatura.extract(page, include_comments=False, include_tables=False,
                                    favor_precision=True) or ""
        meta = trafilatura.extract_metadata(page)
        auteur = (meta.author or "") if meta else ""
    except Exception as erreur:
        DERNIERE_ERREUR[url] = f"{type(erreur).__name__}: {str(erreur)[:160]}"
        return repli, ""
    if not texte:
        DERNIERE_ERREUR[url] = f"page reçue ({len(page)} car.) mais aucun texte extrait"
    texte = re.sub(r"\n{3,}", "\n\n", texte).strip()
    if len(texte) < max(400, len(repli)):
        return repli, auteur
    return texte[:40_000], auteur


# ------------------------------------------------------------------ Google Actualites

_NON_LATIN = re.compile(r"[\u0370-\u03ff\u0400-\u052f\u0590-\u06ff\u0900-\u0dff\u3000-\u9fff\uac00-\ud7af]")


def _separer_media(titre: str) -> tuple[str, str]:
    if " - " in titre:
        debut, media = titre.rsplit(" - ", 1)
        if 0 < len(media) <= 60:
            return debut.strip(), media.strip()
    return titre, ""


def _requete(url: str, donnees: bytes | None = None, entetes: dict | None = None, taille: int = 3_000_000) -> bytes:
    requete = urllib.request.Request(url, data=donnees, headers={"User-Agent": USER_AGENT, **(entetes or {})})
    with urllib.request.urlopen(requete, timeout=20) as reponse:
        return reponse.read(taille)


def resoudre_google(url: str) -> str | None:
    """Lien Google Actualites (news.google.com/rss/articles/…) → adresse de l'article d'origine.

    Google ne redirige plus en HTTP : la page porte une signature et un horodatage qu'il
    faut renvoyer a son point d'acces « batchexecute », qui repond avec l'adresse reelle.
    """
    if "news.google.com" not in url:
        return url
    identifiant = urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1]
    if not identifiant:
        return None
    try:
        page = _requete(f"https://news.google.com/articles/{identifiant}").decode("utf-8", "replace")
        signature = re.search(r'data-n-a-sg="([^"]+)"', page)
        horodatage = re.search(r'data-n-a-ts="([^"]+)"', page)
        if not (signature and horodatage):
            DERNIERE_ERREUR[url] = "Google Actualités : signature absente"
            return None
        demande = [[["Fbv4je", json.dumps([
            "garturlreq",
            [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
             "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
            identifiant, int(horodatage.group(1)), signature.group(1)]), None, "generic"]]]
        corps = urllib.parse.urlencode({"f.req": json.dumps(demande)}).encode()
        reponse = _requete("https://news.google.com/_/DotsSplashUi/data/batchexecute", corps,
                           {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}).decode("utf-8", "replace")
        bloc = json.loads(reponse.split("\n\n", 1)[1])[:-2]
        adresse = json.loads(bloc[0][2])[1]
        return adresse if adresse.startswith("http") else None
    except Exception as erreur:  # le decodage peut casser si Google change son format
        DERNIERE_ERREUR[url] = f"Google Actualités : {type(erreur).__name__}"
        return None


# ------------------------------------------------------------------ Papiers de recherche (PDF)

def texte_pdf(url: str, plafond: int = 40_000) -> str:
    """Texte d'un papier en PDF (lien direct ou premier PDF de la page).

    Si le papier depasse le plafond : debut (resume, introduction) puis fin (conclusion).
    """
    try:
        cible = url
        nber = re.search(r"nber\.org/papers/(w\d+)", url)
        if nber:  # le lien du PDF n'apparait pas dans la page (chargee en JavaScript)
            cible = f"https://www.nber.org/system/files/working_papers/{nber.group(1)}/{nber.group(1)}.pdf"
        elif not url.lower().split("?")[0].endswith(".pdf"):
            page = _requete(url).decode("utf-8", "replace")
            lien = re.search(r'href=["\']([^"\']+?\.pdf[^"\']*)["\']', page, re.I)
            if not lien:
                return ""
            cible = urllib.parse.urljoin(url, lien.group(1))
        from pypdf import PdfReader
        lecteur = PdfReader(io.BytesIO(_requete(cible, taille=25_000_000)))
        pages = [(p.extract_text() or "") for p in lecteur.pages[:80]]
    except Exception as erreur:
        DERNIERE_ERREUR[url] = f"PDF : {type(erreur).__name__}"
        return ""
    texte = re.sub(r"[ \t]+", " ", "\n".join(pages))
    texte = re.sub(r"\n{3,}", "\n\n", texte).strip()
    # Les references bibliographiques en fin de papier n'apportent rien a la synthese.
    coupe = re.search(r"\n\s*(References|Bibliography|Références|Bibliographie)\s*\n", texte)
    if coupe and coupe.start() > len(texte) * 0.5:
        texte = texte[:coupe.start()]
    if len(texte) <= plafond:
        return texte
    debut = int(plafond * 0.6)
    return texte[:debut] + "\n\n[…]\n\n" + texte[-(plafond - debut):]


# ------------------------------------------------------------------ Meme sujet, autres sources

_VIDES = set("""le la les un une des du de d l et ou en au aux pour par sur dans avec sans plus que qui
quoi est sont a the of and to in on for with from by at as is are be its it this that new how why what""".split())


def mots_cles(titre: str) -> set[str]:
    return {m for m in re.findall(r"[\w’'-]+", titre.lower()) if len(m) >= 4 and m not in _VIDES}


def meme_sujet(a: str, b: str, seuil: float = 0.3) -> bool:
    ma, mb = mots_cles(a), mots_cles(b)
    if len(ma) < 2 or len(mb) < 2:
        return False
    return len(ma & mb) / len(ma | mb) >= seuil


def recherche_google(requete: str, langue: str = "fr", nombre: int = 3) -> list[tuple[str, str, str]]:
    """(titre, media, adresse) des premiers resultats Google Actualites des 3 derniers jours."""
    pays = {"fr": ("fr", "FR", "FR:fr"), "en": ("en-US", "US", "US:en")}[langue]
    url = ("https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{requete} when:3d", "hl": pays[0], "gl": pays[1], "ceid": pays[2]}))
    try:
        racine = __import__("xml.etree.ElementTree", fromlist=["x"]).fromstring(_requete(url))
    except Exception:
        return []
    resultats = []
    for item in racine.iter("item"):
        titre, media = _separer_media(item.findtext("title") or "")
        adresse = resoudre_google(item.findtext("link") or "")
        if adresse:
            resultats.append((titre, media, adresse))
        if len(resultats) >= nombre:
            break
    return resultats


def completer_par_autres_sources(candidat: Candidat, autres: list[Candidat], minimum: int,
                                 journal=print) -> bool:
    """Texte trop court mais sujet important : cherche le meme sujet ailleurs.

    1. parmi les candidats du jour d'autres sources ; 2. sur Google Actualites.
    Les textes trouves sont ajoutes, chacun identifie par sa source, sans rien inventer.
    """
    morceaux, sources = [], []
    for autre in autres:
        if autre.source == candidat.source or not meme_sujet(candidat.titre, autre.titre):
            continue
        texte, _ = texte_integral(autre.url, "")
        if len(texte) >= 1000:
            morceaux.append((autre.source, autre.url, texte))
            sources.append({"source": autre.source, "url": autre.url})
        if sum(len(m[2]) for m in morceaux) >= minimum:
            break
    if sum(len(m[2]) for m in morceaux) + len(candidat.texte) < minimum:
        requete = " ".join(sorted(mots_cles(candidat.titre), key=len, reverse=True)[:6])
        langue = "fr" if re.search(r"[éèàùç]", candidat.titre) else "en"
        for titre, media, adresse in recherche_google(requete, langue):
            if adresse == candidat.url or not meme_sujet(candidat.titre, titre, 0.2):
                continue
            texte, _ = texte_integral(adresse, "")
            if len(texte) >= 1000:
                morceaux.append((media or "autre source", adresse, texte))
                sources.append({"source": media or "autre source", "url": adresse})
            if sum(len(m[2]) for m in morceaux) + len(candidat.texte) >= minimum:
                break
    total = len(candidat.texte) + sum(len(m[2]) for m in morceaux)
    if not morceaux or total < minimum:
        return False
    parties = [f"SOURCE 1 ({candidat.source}) :\n{candidat.texte}"] + [
        f"SOURCE {i} ({nom}) :\n{texte[:15000]}" for i, (nom, _, texte) in enumerate(morceaux, start=2)]
    candidat.texte = "\n\n".join(parties)
    candidat.sources_complementaires = sources
    journal(f"  {candidat.id} complété par : " + ", ".join(s["source"] for s in sources))
    return True
