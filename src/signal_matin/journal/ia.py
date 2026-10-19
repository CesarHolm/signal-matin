"""Appels a l'API Anthropic : tri (Haiku), syntheses (Sonnet), quiz et mots (Haiku).

- Traitement differe (Batch API, -50 %) avec bascule en appels directs si le
  lot n'est pas termine a l'heure limite (par defaut 6 h 40).
- Consignes systeme marquees pour la mise en cache (identiques chaque jour).
- Aucune cle API : le module signale l'indisponibilite et le journal sort en
  mode secours (titres et chapos bruts des flux).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from dataclasses import dataclass

MODELE_TRI = "claude-haiku-5-5"
MODELE_SYNTHESE = "claude-sonnet-5-5"

# --------------------------------------------------------------------------- Consignes

SYSTEME_TRI = """Tu es le secrétaire de rédaction d'un journal personnel imprimé chaque matin pour un lecteur francophone exigeant (consultant en conformité réglementaire et gestion des risques).

Pour un bloc du journal, tu reçois une liste d'articles candidats (identifiant, rubrique, source, nature, titre, date, résumé du flux RSS). Tu dois :
1. Classer, par ordre de priorité décroissante, jusqu'à 6 articles à développer (synthèse d'un quart ou d'une demi-page selon leur longueur). Le journal en publiera au moins 2 par bloc, et davantage selon la place disponible ; attribue à chacun un « score » de 1 à 10 (9 ou 10 : sujet essentiel du jour, à ne pas manquer).
2. Choisir jusqu'à 6 autres articles pour des brèves, classés par priorité, et rédiger chaque brève (le journal en publie 3 par bloc, davantage s'il reste de la place).

Critères de sélection, par ordre de priorité :
- Importance : portée réelle de l'information, conséquences concrètes, intérêt durable.
- Nouveauté : un fait nouveau prime sur un commentaire ; écarte les republications d'articles anciens, les contenus promotionnels, les cas clients publicitaires et les annonces de numéros de magazine.
- Diversité : évite deux articles sur le même sujet (garde le meilleur) et équilibre les rubriques du bloc.
- Le FOOTBALL est TOTALEMENT EXCLU, dans tous les blocs (ni brève ni développé), y compris les transferts, les clubs et les sélections.
- Bloc avec rubrique sport : L'actualité sportive n'est traitée qu'en brèves (savoir ce qui s'est passé). Les articles de nature « methode » (méthodes d'entraînement) sont prioritaires pour les articles développés s'ils sont intéressants ; à défaut, développe des articles de science grand public.

Règles des brèves :
- « titre » : en français, factuel, 90 caractères maximum.
- « texte » : 1 à 2 phrases en français, environ 250 caractères, uniquement d'après le titre et le résumé fournis. N'ajoute aucune information extérieure. Si le résumé est trop pauvre pour une brève fiable, choisis un autre article.

Réponds uniquement en JSON, selon cette structure :
{"developpes": [{"id": "a12", "score": 8, "raison": "…"}, …], "breves": [{"id": "a7", "titre": "…", "texte": "…"}, …]}"""

SYSTEME_SYNTHESE = """Tu rédiges les articles développés d'un journal personnel imprimé, en français, à partir d'un article source complet (souvent en anglais).

Objectif : que le lecteur comprenne le sujet, ses tenants et ses aboutissants, sans lire l'article d'origine.

Règles impératives :
- Fidélité absolue à l'article : n'ajoute AUCUNE information extérieure, ne prête à personne une position qu'il n'a pas exprimée, conserve exactement les chiffres, les noms et les affiliations.
- Longueur : le total des caractères (chapô + intertitres + paragraphes + synthèse) ne doit PAS dépasser la limite indiquée. Vise 90 à 100 % de cette limite.
- Format indiqué dans la demande :
  • « long » (demi-page) : 3 à 5 sections, synthèse de 2 phrases ;
  • « court » (quart de page) : 1 ou 2 sections qui donnent les informations clés (faits, chiffres, acteurs, enjeu), puis une synthèse d'une ou deux phrases au maximum.
- Structure :
  • « titre » : titre français informatif, 80 caractères maximum.
  • « chapo » : une phrase qui pose le sujet, 200 caractères maximum.
  • « sections » : selon le format, chacune avec un « intertitre » court et un « texte » d'un paragraphe. Adapte les intertitres au type d'article, par exemple :
      débat ou controverse : Le déclencheur · De quoi parle-t-on · Les arguments pour · Les risques · Les contre-arguments
      annonce ou fait d'actualité : Ce qui est annoncé · Le contexte · Ce que ça change · Les limites
      étude ou recherche : La question · La méthode · Les résultats · Les réserves
      méthode d'entraînement : Le principe · Ce que dit la science · Comment l'appliquer · Les précautions
      réglementation : Ce qui change · Qui est concerné · Le calendrier · Les points de vigilance
  • « synthese » : 2 phrases (format long) ou 1 à 2 phrases (format court) qui résument l'ensemble.
- Style : français soigné, clair, sans tournures calquées sur l'anglais, sans emphase.
- « republication » : si l'article indique qu'il a été publié initialement à une date antérieure (republication), indique « paru initialement en <mois année> » ; sinon chaîne vide.

Réponds uniquement en JSON, selon cette structure :
{"titre": "…", "chapo": "…", "sections": [{"intertitre": "…", "texte": "…"}], "synthese": "…", "republication": ""}"""

SYSTEME_QUIZ = """Tu rédiges le quiz du jour d'un journal personnel imprimé, en français.

À partir des textes publiés dans le numéro (articles développés et brèves), écris 5 questions à choix multiples :
- chaque question porte sur un fait explicitement présent dans les textes fournis ;
- 3 propositions courtes (60 caractères maximum), une seule correcte, les deux autres plausibles ;
- varie les articles (pas plus de 2 questions sur le même texte) ;
- question de 110 caractères maximum.

Réponds uniquement en JSON, selon cette structure :
{"questions": [{"question": "…", "options": ["…", "…", "…"], "reponse": 0, "article": "titre de l'article"}]}"""

SYSTEME_MOTS = """Tu enrichis la base de vocabulaire d'un lecteur francophone cultivé qui apprend chaque jour de nouveaux mots.

Propose des mots français RÉELS, attestés dans les dictionnaires de référence (TLFi, Académie française), jamais inventés.
- Niveaux : « facile » (mot soutenu connu mais peu employé), « intermediaire » (mot littéraire ou rare), « difficile » (mot rare, savant ou technique).
- Domaines : environ 80 % « soutenu » (langue littéraire et soutenue) et 20 % « pro » (économie, finance, droit, technologie).
- Pour chaque mot : nature grammaticale abrégée (adj., n. m., n. f., v. tr., v. intr.…), définition exacte et concise (150 caractères maximum), exemple d'usage naturel (100 caractères maximum).
- N'utilise aucun mot de la liste des mots déjà connus.

Réponds uniquement en JSON, selon cette structure :
{"mots": [{"mot": "…", "nature": "…", "niveau": "facile", "domaine": "soutenu", "definition": "…", "exemple": "…"}]}"""


# --------------------------------------------------------------------------- Schemas
# L'IA repond via un outil impose : l'API garantit alors un JSON valide et conforme.

_TEXTE = {"type": "string"}
_SECTIONS = {"type": "array", "items": {"type": "object", "properties": {
    "intertitre": _TEXTE, "texte": _TEXTE}, "required": ["intertitre", "texte"]}}
SCHEMA_TRI = {"type": "object", "properties": {
    "developpes": {"type": "array", "items": {"type": "object", "properties": {
        "id": _TEXTE, "score": {"type": "integer"}, "raison": _TEXTE}, "required": ["id", "score"]}},
    "breves": {"type": "array", "items": {"type": "object", "properties": {
        "id": _TEXTE, "titre": _TEXTE, "texte": _TEXTE}, "required": ["id", "titre", "texte"]}},
}, "required": ["developpes", "breves"]}
SCHEMA_SYNTHESE = {"type": "object", "properties": {
    "titre": _TEXTE, "chapo": _TEXTE, "sections": _SECTIONS, "synthese": _TEXTE, "republication": _TEXTE,
}, "required": ["titre", "chapo", "sections", "synthese"]}
SCHEMA_QUIZ = {"type": "object", "properties": {"questions": {"type": "array", "items": {
    "type": "object", "properties": {"question": _TEXTE, "options": {"type": "array", "items": _TEXTE},
                                     "reponse": {"type": "integer"}, "article": _TEXTE},
    "required": ["question", "options", "reponse"]}}}, "required": ["questions"]}
SCHEMA_MOTS = {"type": "object", "properties": {"mots": {"type": "array", "items": {
    "type": "object", "properties": {k: _TEXTE for k in
                                     ("mot", "nature", "niveau", "domaine", "definition", "exemple")},
    "required": ["mot", "nature", "niveau", "domaine", "definition", "exemple"]}}}, "required": ["mots"]}


def _texte_reponse(contenu) -> str:
    """Texte exploitable d'une reponse : l'entree de l'outil si presente, sinon le texte."""
    for bloc in contenu:
        if getattr(bloc, "type", "") == "tool_use":
            return json.dumps(bloc.input, ensure_ascii=False)
    return "".join(getattr(b, "text", "") for b in contenu if getattr(b, "type", "") == "text")


# --------------------------------------------------------------------------- Requetes


def _strict(schema):
    """Copie du schema avec additionalProperties: false (exige par les sorties structurees)."""
    if isinstance(schema, dict):
        copie = {k: _strict(v) for k, v in schema.items()}
        if copie.get("type") == "object":
            copie.setdefault("additionalProperties", False)
        return copie
    if isinstance(schema, list):
        return [_strict(v) for v in schema]
    return schema


# Modes de reponse, du plus contraint au plus tolerant :
#   outil  : outil impose (JSON garanti) - refuse par certains modeles (ex. Sonnet 5.5)
#   format : sorties structurees (output_config json_schema)
#   texte  : consigne seule, JSON extrait du texte
MODES = ("outil", "format", "texte")


def mode_initial(modele: str) -> str:
    return "outil" if "haiku" in modele else "format"


@dataclass
class Requete:
    id: str
    modele: str
    systeme: str
    contenu: str
    max_tokens: int = 2000
    schema: dict | None = None

    def params(self, mode: str | None = None) -> dict:
        mode = mode or mode_initial(self.modele)
        params = {
            "model": self.modele,
            "max_tokens": self.max_tokens,
            "system": [{"type": "text", "text": self.systeme,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": self.contenu}],
        }
        if self.schema and mode == "outil":
            params["tools"] = [{"name": "repondre", "description": "Transmet la réponse structurée.",
                                "input_schema": self.schema}]
            params["tool_choice"] = {"type": "tool", "name": "repondre"}
        elif self.schema and mode == "format":
            params["output_config"] = {"format": {"type": "json_schema", "schema": _strict(self.schema)}}
        return params


def _mode_refuse(erreur: Exception) -> bool:
    """Erreur 400 liee au mode de reponse (outil impose ou format non pris en charge)."""
    if getattr(erreur, "status_code", None) != 400:
        return False
    message = str(erreur).lower()
    return any(m in message for m in ("tool_choice", "tools", "output_config", "format", "schema"))


class IAIndisponible(RuntimeError):
    pass


def extraire_json(texte: str) -> dict:
    """Recupere le premier objet JSON d'une reponse (tolere un bloc ```json)."""
    texte = re.sub(r"^```(?:json)?|```$", "", texte.strip(), flags=re.M).strip()
    debut = texte.find("{")
    fin = texte.rfind("}")
    if debut < 0 or fin <= debut:
        raise ValueError("aucun JSON dans la réponse")
    return json.loads(texte[debut: fin + 1])


class ClientIA:
    def __init__(self, config: dict, journal=print):
        self.config = config
        self.journal = journal
        cle = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not cle:
            raise IAIndisponible("ANTHROPIC_API_KEY absente du fichier .env")
        try:
            import anthropic
        except ImportError as erreur:
            raise IAIndisponible("paquet 'anthropic' non installé") from erreur
        self.client = anthropic.Anthropic(api_key=cle, max_retries=6)
        self._limite_debit = anthropic.RateLimitError
        self.modele_tri = config.get("modele_tri", MODELE_TRI)
        self.modele_synthese = config.get("modele_synthese", MODELE_SYNTHESE)

    # ------------------------------------------------------------------ direct
    def _mode(self, modele: str) -> str:
        if not hasattr(self, "_modes"):
            self._modes = {}
        return self._modes.get(modele, mode_initial(modele))

    def _degrader(self, modele: str, mode: str) -> bool:
        """Passe au mode suivant, plus tolerant ; False s'il n'y en a plus."""
        if mode == MODES[-1]:
            return False
        suivant = MODES[MODES.index(mode) + 1]
        self._modes[modele] = suivant
        self.journal(f"  … {modele} : mode « {mode} » refusé, passage en mode « {suivant} »")
        return True

    def _direct(self, requete: Requete) -> str:
        params = requete.params(self._mode(requete.modele))
        # output_config passe par extra_body : compatible avec toutes les versions du SDK.
        extra = {"output_config": params.pop("output_config")} if "output_config" in params else None
        if extra:
            reponse = self.client.messages.create(**params, extra_body=extra)
        else:
            reponse = self.client.messages.create(**params)
        return _texte_reponse(reponse.content)

    def direct(self, requetes: list[Requete]) -> dict[str, str]:
        resultats = {}
        for requete in requetes:
            for tentative in range(7):
                try:
                    resultats[requete.id] = self._direct(requete)
                    break
                except Exception as erreur:  # une requete en echec ne bloque pas les autres
                    if _mode_refuse(erreur) and self._degrader(requete.modele, self._mode(requete.modele)):
                        continue
                    if isinstance(erreur, getattr(self, "_limite_debit", ())) and tentative < 6:
                        # Limite de debit du compte : on patiente avant de reessayer.
                        attente = 65
                        try:
                            attente = int(float(erreur.response.headers.get("retry-after", 65))) + 5
                        except Exception:
                            pass
                        self.journal(f"  … limite de débit atteinte, pause de {attente} s ({requete.id})")
                        time.sleep(attente)
                        continue
                    self.journal(f"  ! {requete.id} : {type(erreur).__name__}: {str(erreur)[:300]}")
                    break
        return resultats

    # ------------------------------------------------------------------- batch
    def lot(self, requetes: list[Requete], echeance: dt.datetime) -> dict[str, str]:
        if not requetes:
            return {}
        if not self.config.get("traitement_differe", True):
            return self.direct(requetes)
        try:
            lot = self.client.messages.batches.create(requests=[
                {"custom_id": r.id, "params": r.params(self._mode(r.modele))} for r in requetes])
        except Exception as erreur:
            self.journal(f"  ! lot refusé ({type(erreur).__name__}), passage en direct")
            return self.direct(requetes)
        self.journal(f"  lot {lot.id} soumis ({len(requetes)} requêtes)")
        while lot.processing_status != "ended":
            if dt.datetime.now().astimezone() >= echeance:
                self.journal("  ! heure limite atteinte : annulation du lot et passage en direct")
                try:
                    self.client.messages.batches.cancel(lot.id)
                except Exception:
                    pass
                break
            time.sleep(int(self.config.get("intervalle_sondage_s", 30)))
            lot = self.client.messages.batches.retrieve(lot.id)
        resultats: dict[str, str] = {}
        erreurs_lot: list[str] = []
        try:
            for ligne in self.client.messages.batches.results(lot.id):
                if ligne.result.type == "succeeded":
                    message = ligne.result.message
                    resultats[ligne.custom_id] = _texte_reponse(message.content)
                elif ligne.result.type == "errored" and not erreurs_lot:
                    erreurs_lot.append(str(getattr(ligne.result, "error", ""))[:300])
        except Exception as erreur:
            self.journal(f"  ! lecture du lot impossible ({type(erreur).__name__})")
        if erreurs_lot:
            self.journal(f"  ! erreur dans le lot : {erreurs_lot[0]}")
        manquantes = [r for r in requetes if r.id not in resultats]
        if manquantes:
            self.journal(f"  {len(manquantes)} requête(s) relancée(s) en direct")
            resultats.update(self.direct(manquantes))
        return resultats


# --------------------------------------------------------------------------- Contenus


def requete_tri(client: ClientIA, bloc, deja: list[str]) -> Requete:
    contenu = {
        "bloc": bloc.titre,
        "rubriques": sorted({c.rubrique for c in bloc.candidats}),
        "candidats": [c.pour_tri() for c in bloc.candidats],
    }
    if deja:
        contenu["sujets_deja_publies_recemment"] = deja[:40]
    return Requete(id=f"tri-{bloc.id}", modele=client.modele_tri, systeme=SYSTEME_TRI,
                   contenu=json.dumps(contenu, ensure_ascii=False), max_tokens=4000,
                   schema=SCHEMA_TRI)


def limite_caracteres(texte: str, plafond: int = 2800, ratio: float = 0.40) -> int:
    return max(900, min(plafond, int(len(texte) * ratio)))


def requete_synthese(client: ClientIA, candidat, limite: int, format_: str = "long") -> Requete:
    lignes = [
        f"Format : {format_}",
        f"Limite de longueur : {limite} caractères au total.",
        f"Source : {candidat.source}",
        f"Rubrique : {candidat.rubrique}",
    ]
    if candidat.publie_le:
        lignes.append(f"Date du flux : {candidat.publie_le:%d/%m/%Y}")
    if candidat.auteur:
        lignes.append(f"Auteur : {candidat.auteur}")
    lignes += [f"Titre d'origine : {candidat.titre}", "", "ARTICLE :", candidat.texte]
    contenu = "\n".join(lignes)
    return Requete(id=f"syn-{candidat.id}", modele=client.modele_synthese,
                   systeme=SYSTEME_SYNTHESE, contenu=contenu, max_tokens=3000 if format_ == "long" else 1500,
                   schema=SCHEMA_SYNTHESE)


def requete_mots(client: ClientIA, besoins: dict[str, int], connus: list[str]) -> Requete:
    demande = ", ".join(f"{n} mots de niveau « {niveau} »" for niveau, n in besoins.items())
    contenu = f"Propose {demande}.\n\nMots déjà connus (à ne pas reprendre) :\n" + ", ".join(connus)
    return Requete(id="mots", modele=client.modele_tri, systeme=SYSTEME_MOTS,
                   contenu=contenu, max_tokens=8000, schema=SCHEMA_MOTS)


def requete_quiz(client: ClientIA, textes: list[dict]) -> Requete:
    return Requete(id="quiz", modele=client.modele_tri, systeme=SYSTEME_QUIZ,
                   contenu=json.dumps(textes, ensure_ascii=False), max_tokens=2000, schema=SCHEMA_QUIZ)


def longueur(article: dict) -> int:
    return (len(article.get("chapo", "")) + len(article.get("synthese", ""))
            + sum(len(s.get("intertitre", "")) + len(s.get("texte", ""))
                  for s in article.get("sections", [])))


def ajuster_longueur(article: dict, limite: int) -> dict:
    """Retire des sections en fin d'article si la synthese depasse nettement la limite."""
    sections = list(article.get("sections", []))
    minimum = 1 if limite <= 1200 else 2
    while longueur({**article, "sections": sections}) > limite * 1.08 and len(sections) > minimum:
        sections.pop()
    article["sections"] = sections
    return article
