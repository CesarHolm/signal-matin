"""Fabrication de la version numerique par un agent Claude (abonnement), sans l'API.

Principe : `edition.produire` tourne a l'identique, mais ses appels IA passent par
`ClientAgent`, qui lit les reponses deja ecrites par l'agent dans le dossier de
l'edition. Tant qu'une reponse manque, la demande est deposee dans `a_faire/` et
l'execution s'arrete (`EnAttente`). L'agent ecrit les reponses dans `faits/`, puis
relance l'etape : les candidats et les textes deja recuperes sont relus depuis
`cache.json`, rien n'est collecte deux fois.

Dossier d'une edition :
    cache.json        candidats, textes recuperes, date et heure de reference, essai
    a_faire/<id>.json demande : modele, consigne systeme, contenu, schema, fichier de sortie
    faits/<id>.json   reponse JSON de l'agent
    resultat.json     edition terminee, prete a publier (mise en page, memoire, e-mail)

Les consignes sont celles de `ia.py`, reprises telles quelles : l'agent recoit
exactement ce que recevait l'API.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path

from . import articles as art
from . import ia

MODELES = {"tri": "haiku", "synthese": "sonnet"}

CONSIGNE_VERIFICATION_SOURCES = (
    "Vérification des sources complémentaires : avant de rédiger, vérifie que chaque SOURCE "
    "numérotée à partir de 2 traite bien du MÊME fait que la SOURCE 1 (même événement, mêmes "
    "acteurs). Ignore entièrement celles qui n'en traitent pas et donne leurs numéros dans "
    "« sources_ecartees ». Si, sans elles, la matière ne suffit pas pour un article fiable, "
    "réponds seulement {\"insuffisant\": true, \"titre\": \"…\", \"texte\": \"…\"} : une brève "
    "en français (titre de 90 caractères au plus, 2 à 3 phrases d'environ 450 caractères), "
    "uniquement d'après la SOURCE 1.")

_EXTRAS_SYNTHESE = {"sources_ecartees": {"type": "array", "items": {"type": "integer"}},
                    "insuffisant": {"type": "boolean"}, "texte": {"type": "string"}}


class EnAttente(RuntimeError):
    """Des reponses de l'agent manquent : les demandes sont dans a_faire/."""

    def __init__(self, ids: list[str]):
        super().__init__(f"{len(ids)} demande(s) en attente : " + ", ".join(ids))
        self.ids = ids


class ClientAgent:
    """Remplace ia.ClientIA : les reponses viennent des fichiers ecrits par l'agent."""

    agent = True

    def __init__(self, dossier: Path, *, final: bool = False, journal=print):
        self.dossier = Path(dossier)
        self.final = final
        self.journal = journal
        self.modele_tri = MODELES["tri"]
        self.modele_synthese = MODELES["synthese"]
        self.en_attente: list[str] = []
        (self.dossier / "a_faire").mkdir(parents=True, exist_ok=True)
        (self.dossier / "faits").mkdir(parents=True, exist_ok=True)

    def lot(self, requetes: list[ia.Requete], echeance=None) -> dict[str, str]:
        reponses = self._repondre(requetes)
        if self.en_attente and not self.final:
            raise EnAttente(self.en_attente)
        return reponses

    def direct(self, requetes: list[ia.Requete]) -> dict[str, str]:
        # Pas d'arret ici : la demande attend avec celles du lot suivant (un seul aller-retour).
        return self._repondre(requetes)

    def _repondre(self, requetes: list[ia.Requete]) -> dict[str, str]:
        reponses = {}
        for requete in requetes:
            fichier = self.dossier / "faits" / f"{requete.id}.json"
            if fichier.is_file():
                reponses[requete.id] = fichier.read_text(encoding="utf-8")
            elif self.final:
                self.journal(f"  ! {requete.id} : aucune réponse de l'agent")
            else:
                deposer(self.dossier, requete)
                self.en_attente.append(requete.id)
        return reponses


def deposer(dossier: Path, requete: ia.Requete) -> Path:
    schema = dict(requete.schema or {})
    if requete.id.startswith("syn-") and schema:
        schema = {**schema, "properties": {**schema["properties"], **_EXTRAS_SYNTHESE}}
    limite = re.search(r"Limite de longueur : (\d+)", requete.contenu)
    demande = {
        "id": requete.id,
        "modele": requete.modele,
        "sortie": f"faits/{requete.id}.json",
        "limite_caracteres": int(limite.group(1)) if limite else None,
        "systeme": requete.systeme,
        "contenu": requete.contenu,
        "schema": schema,
    }
    chemin = Path(dossier) / "a_faire" / f"{requete.id}.json"
    chemin.write_text(json.dumps(demande, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin


# --------------------------------------------------------------------------- Cache


def candidat_en_dict(c: art.Candidat) -> dict:
    d = asdict(c)
    d["publie_le"] = c.publie_le.isoformat() if c.publie_le else None
    return d


def candidat_depuis(d: dict) -> art.Candidat:
    d = dict(d)
    d["publie_le"] = dt.datetime.fromisoformat(d["publie_le"]) if d.get("publie_le") else None
    return art.Candidat(**d)


def blocs_en_dict(blocs: list[art.Bloc]) -> list[dict]:
    return [{**{k: v for k, v in asdict(b).items() if k != "candidats"},
             "candidats": [candidat_en_dict(c) for c in b.candidats]} for b in blocs]


def blocs_depuis(donnees: list[dict]) -> list[art.Bloc]:
    blocs = []
    for d in donnees:
        champs = {k: v for k, v in d.items() if k != "candidats"}
        blocs.append(art.Bloc(**champs, candidats=[candidat_depuis(c) for c in d["candidats"]]))
    return blocs


def charger_cache(dossier: Path) -> dict:
    chemin = Path(dossier) / "cache.json"
    if chemin.is_file():
        return json.loads(chemin.read_text(encoding="utf-8"))
    return {}


def enregistrer_cache(dossier: Path, cache: dict) -> None:
    Path(dossier).mkdir(parents=True, exist_ok=True)
    (Path(dossier) / "cache.json").write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                                              encoding="utf-8")


# --------------------------------------------------------------------------- Verification


def _types_ok(valeur, schema: dict) -> bool:
    attendu = schema.get("type")
    if attendu == "object":
        if not isinstance(valeur, dict):
            return False
        if any(cle not in valeur for cle in schema.get("required", [])):
            return False
        return all(_types_ok(valeur[k], s) for k, s in schema.get("properties", {}).items() if k in valeur)
    if attendu == "array":
        return isinstance(valeur, list) and all(_types_ok(v, schema.get("items", {})) for v in valeur)
    if attendu == "string":
        return isinstance(valeur, str)
    if attendu == "integer":
        return isinstance(valeur, int) and not isinstance(valeur, bool)
    if attendu == "boolean":
        return isinstance(valeur, bool)
    return True


def verifier(dossier: Path) -> list[str]:
    """Problemes des reponses de l'agent (manquantes, JSON invalide, schema, longueur)."""
    dossier = Path(dossier)
    problemes = []
    for chemin in sorted((dossier / "a_faire").glob("*.json")):
        demande = json.loads(chemin.read_text(encoding="utf-8"))
        sortie = dossier / demande["sortie"]
        ident = demande["id"]
        if not sortie.is_file():
            problemes.append(f"{ident} : réponse absente ({demande['sortie']})")
            continue
        try:
            reponse = json.loads(sortie.read_text(encoding="utf-8"))
        except json.JSONDecodeError as erreur:
            problemes.append(f"{ident} : JSON invalide ({erreur})")
            continue
        if ident.startswith("syn-") and reponse.get("insuffisant"):
            if not (isinstance(reponse.get("titre"), str) and isinstance(reponse.get("texte"), str)):
                problemes.append(f"{ident} : « insuffisant » sans brève (titre, texte)")
            continue
        if demande.get("schema") and not _types_ok(reponse, demande["schema"]):
            problemes.append(f"{ident} : réponse non conforme au schéma demandé")
            continue
        limite = demande.get("limite_caracteres")
        if ident.startswith("syn-") and limite:
            longueur = ia.longueur(reponse)
            if longueur > limite * 1.08:
                problemes.append(f"{ident} : {longueur} caractères pour une limite de {limite} (trop long)")
            elif longueur < limite * 0.85:
                problemes.append(f"{ident} : {longueur} caractères pour une limite de {limite} "
                                 "(trop court : viser 90 à 100 %)")
    return problemes


# --------------------------------------------------------------------------- Mode hybride
#
# La collecte et les textes (internet) tournent sur GitHub, la redaction dans le cloud Claude.
# L'agent pousse <dossier>/tour.json ({"tour": n, "essai": bool, "final": bool}) sur la branche
# claude/editions ; le workflow « fabrication » lance `avancer`, puis pousse les demandes et
# <dossier>/etat.json ({"tour": n, "code": c, "a_faire": [...], "termine": bool, "journal": "..."}).


def attendre(dossier: Path, tour: int, delai: int = 540, pause: int = 15) -> int:
    """Attend que GitHub ait traite le tour `tour`, puis met le dossier local a jour.

    Codes : 0 tour traite (voir etat.json), 2 echec du programme sur GitHub, 4 delai depasse.
    """
    import subprocess
    import time

    dossier = Path(dossier).resolve()
    racine = Path(subprocess.check_output(["git", "-C", str(dossier), "rev-parse", "--show-toplevel"],
                                          text=True).strip())
    chemin = f"{dossier.relative_to(racine).as_posix()}/etat.json"
    fin = time.monotonic() + delai
    while True:
        subprocess.run(["git", "-C", str(racine), "fetch", "-q", "origin", "claude/editions"], check=False)
        lu = subprocess.run(["git", "-C", str(racine), "show", f"origin/claude/editions:{chemin}"],
                            capture_output=True, text=True)
        etat = json.loads(lu.stdout) if lu.returncode == 0 and lu.stdout.strip() else {}
        if etat.get("tour", 0) >= tour:
            subprocess.run(["git", "-C", str(racine), "reset", "-q", "--hard", "origin/claude/editions"], check=True)
            print(f"TOUR {etat['tour']} code {etat.get('code')} termine={etat.get('termine', False)}")
            if etat.get("a_faire"):
                print(f"A_FAIRE {len(etat['a_faire'])} : " + " ".join(f"a_faire/{i}.json" for i in etat["a_faire"]))
            if etat.get("code") not in (0, 3):
                print((etat.get("journal") or "")[-3000:])
                return 2
            return 0
        if time.monotonic() >= fin:
            print(f"DELAI : GitHub n'a pas encore traité le tour {tour} (relancer attendre)")
            return 4
        time.sleep(pause)
