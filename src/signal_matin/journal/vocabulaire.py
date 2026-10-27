"""Mots du jour : 5 nouveaux (2 faciles, 1 intermediaire, 2 difficiles) et 5 revisions.

Base hybride :
- vocabulaire_base.json (livre avec le projet) ;
- data/vocabulaire_ajouts.json, alimente par l'agent quand le stock baisse.
Repartition visee : environ 80 % de francais soutenu, 20 % de vocabulaire
professionnel (economie, droit, tech), soit un mot « pro » par jour.
"""
from __future__ import annotations

import datetime as dt
import json
import random
import re
import urllib.parse
import urllib.request
from pathlib import Path

from .etat import DOSSIER, editions_passees

BASE = Path(__file__).with_name("vocabulaire_base.json")
QUOTA = {"facile": 2, "intermediaire": 1, "difficile": 2}
ORDRE = ("facile", "facile", "intermediaire", "difficile", "difficile")
SEUIL_REALIMENTATION = 10  # jours de stock restant par niveau


def _ajouts(racine: Path = DOSSIER) -> Path:
    racine.mkdir(parents=True, exist_ok=True)
    return racine / "vocabulaire_ajouts.json"


def charger_base(racine: Path = DOSSIER) -> list[dict]:
    mots = json.loads(BASE.read_text(encoding="utf-8"))
    fichier = _ajouts(racine)
    if fichier.exists():
        try:
            mots += json.loads(fichier.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    vus, uniques = set(), []
    for mot in mots:
        cle = mot["mot"].casefold()
        if cle not in vus:
            vus.add(cle)
            uniques.append(mot)
    return uniques


def mots_appris(jour: dt.date, racine: Path = DOSSIER) -> list[dict]:
    appris = []
    for edition in editions_passees(jour, racine):
        appris.extend(edition.get("nouveaux_mots", []))
    return appris


def stock_restant(jour: dt.date, racine: Path = DOSSIER) -> dict[str, int]:
    deja = {m["mot"].casefold() for m in mots_appris(jour, racine)}
    restant = {niveau: 0 for niveau in QUOTA}
    for mot in charger_base(racine):
        if mot["mot"].casefold() not in deja:
            restant[mot["niveau"]] = restant.get(mot["niveau"], 0) + 1
    return restant


def niveaux_a_realimenter(jour: dt.date, racine: Path = DOSSIER) -> dict[str, int]:
    """Nombre de mots a demander a l'agent, par niveau, pour tenir ~30 editions."""
    besoin = {}
    for niveau, restant in stock_restant(jour, racine).items():
        if restant < QUOTA[niveau] * SEUIL_REALIMENTATION:
            besoin[niveau] = QUOTA[niveau] * 30 - restant
    return besoin


def mots_planifies(jour: dt.date, racine: Path = DOSSIER) -> list[dict]:
    """Mots choisis a l'avance pour une date (data/mots_planifies.json), s'il y en a."""
    fichier = racine / "mots_planifies.json"
    if not fichier.exists():
        return []
    try:
        return list(json.loads(fichier.read_text(encoding="utf-8")).get(jour.isoformat(), []))
    except (OSError, json.JSONDecodeError, AttributeError):
        return []


def selection_du_jour(jour: dt.date, racine: Path = DOSSIER) -> tuple[list[dict], list[dict]]:
    """Retourne (5 nouveaux mots, 5 mots a reviser)."""
    rng = random.Random(int(jour.strftime("%Y%m%d")))
    appris = mots_appris(jour, racine)
    planifies = mots_planifies(jour, racine)
    deja = {m["mot"].casefold() for m in appris}
    disponibles = [m for m in charger_base(racine) if m["mot"].casefold() not in deja]
    rng.shuffle(disponibles)

    nouveaux: list[dict] = list(planifies)
    slot_pro = rng.randrange(len(ORDRE))
    for index, niveau in enumerate(ORDRE if not planifies else ()):
        domaine_voulu = "pro" if index == slot_pro else "soutenu"
        candidats = [m for m in disponibles if m["niveau"] == niveau and m not in nouveaux]
        prefere = [m for m in candidats if m.get("domaine") == domaine_voulu]
        choix = (prefere or candidats)[:1]
        nouveaux.extend(choix)

    # Revisions : tirees au hasard parmi les mots appris, hors 5 dernieres editions
    # pour laisser un vrai temps d'oubli quand la reserve le permet.
    anciens = appris[:-25] if len(appris) > 30 else appris
    revisions = rng.sample(anciens, min(5, len(anciens))) if anciens else []
    return nouveaux, revisions


# ------------------------------------------------------------------- Realimentation


def mot_existe_cnrtl(mot: str) -> bool | None:
    """Vrai si le CNRTL (TLFi) a une entree pour ce mot ; None si le site est injoignable."""
    tete = mot.split()[0] if " " in mot and "'" not in mot else mot
    url = "https://www.cnrtl.fr/definition/" + urllib.parse.quote(tete.casefold())
    try:
        requete = urllib.request.Request(url, headers={"User-Agent": "Signal-Matin/1.0"})
        with urllib.request.urlopen(requete, timeout=12) as reponse:
            page = reponse.read(600_000).decode("utf-8", errors="replace")
    except Exception:
        return None
    # Le CNRTL affiche ce message quand le mot n'a pas d'entree dans le TLFi.
    return not re.search(r"Cette forme est introuvable", page, re.I)


def ajouter_mots(nouveaux: list[dict], racine: Path = DOSSIER, verifier: bool = True) -> int:
    existants = {m["mot"].casefold() for m in charger_base(racine)}
    fichier = _ajouts(racine)
    ajouts = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else []
    compte = 0
    for mot in nouveaux:
        if not isinstance(mot, dict) or not mot.get("mot") or mot.get("niveau") not in QUOTA:
            continue
        if mot["mot"].casefold() in existants:
            continue
        if verifier and mot_existe_cnrtl(mot["mot"]) is False:
            continue  # mot introuvable dans le TLFi : on ne l'imprime pas
        ajouts.append({k: str(mot.get(k, "")) for k in
                       ("mot", "nature", "niveau", "domaine", "definition", "exemple")})
        existants.add(mot["mot"].casefold())
        compte += 1
    fichier.write_text(json.dumps(ajouts, ensure_ascii=False, indent=1), encoding="utf-8")
    return compte
