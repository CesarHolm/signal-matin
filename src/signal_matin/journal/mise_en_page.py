"""Remplissage exact du journal en quarts de page.

Unite de mesure : le quart de page.
- article long  = 2 quarts (une demi-page)
- article court = 1 quart
- breves d'un bloc (2 ou 3) = 1 quart
- solutions d'hier = 1 quart
Un journal de P pages offre 4P - 6 quarts de contenu : la une occupe la moitie
haute de la page 1 et la page Jeux est la derniere.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SEUIL_LONG = 2400        # caracteres de synthese a partir desquels l'article tient une demi-page
PLAFOND_LONG = 2800
PLAFOND_COURT = 1100
PLANCHER_COURT = 1000    # un quart de page doit etre plein
RATIO = 0.40
SCORE_ESSENTIEL = 9
TEXTE_MINIMUM = 2500     # en dessous (article payant, extrait partiel), seulement une breve :
                         # 40 % de 2500 = 1000 caracteres, de quoi remplir un quart de page


# Version numerique (telephone) : pas de pagination, donc des articles plus complets.
# Deux formats seulement (decision du 04/11/2026) : article long et breve. La longueur
# du long suit la matiere disponible : la moitie du texte source, 4 500 caracteres au plus.
# Regle du 06/11/2026 : 80 % de la source, entre 2 500 et 4 500 caracteres ; une source de
# moins de 6 000 caracteres est d'abord completee par d'autres sources (meme fait).
NUM_RATIO = 0.80
NUM_PLANCHER_LONG = 2500
NUM_PLAFOND_LONG = 4500
NUM_SEUIL_COMPLEMENT = 6000
NUM_LONGS_PAR_BLOC = 3     # plafonds par defaut ; chaque bloc peut fixer max_longs / max_breves
NUM_BREVES_PAR_BLOC = 3


def quarts_de_contenu(pages: int) -> int:
    return 4 * pages - 6


def gabarit(longueur_source: int, ratio: float = RATIO) -> tuple[str, int]:
    """Retourne ("long"|"court", limite de caracteres) selon la longueur du texte source."""
    possible = int(longueur_source * ratio)
    if possible >= SEUIL_LONG:
        return "long", min(PLAFOND_LONG, possible)
    # Article court : quart de page ; on evite les quarts a moitie vides sans
    # jamais reprendre plus de 70 % d'un texte deja bref.
    limite = min(PLAFOND_COURT, max(PLANCHER_COURT, possible))
    return "court", max(300, min(limite, int(longueur_source * 0.70)))


@dataclass
class Choix:
    id: str
    bloc: str
    score: int
    format: str
    limite: int

    @property
    def taille(self) -> int:
        return 2 if self.format == "long" else 1


@dataclass
class Plan:
    pages: int
    articles: list[Choix]
    quarts_breves: dict[str, int] = field(default_factory=dict)  # bloc -> nb de quarts de breves
    quarts_libres: int = 0


def planifier(classements: dict[str, list[Choix]], breves_disponibles: dict[str, int], *,
              avec_solutions: bool, pages_defaut: int = 8, pages_possibles=(6, 8, 10),
              minimum_par_bloc: int = 2) -> Plan:
    """Choisit le nombre de pages puis les articles qui remplissent exactement le journal.

    classements : par bloc, candidats dans l'ordre de priorite de l'IA (avec score et format).
    breves_disponibles : par bloc, nombre de breves redigees (3 par quart).
    """
    fixes_breves = {b: 1 for b, n in breves_disponibles.items() if n >= 2}
    fixes = sum(fixes_breves.values()) + (1 if avec_solutions else 0)
    tous = [c for liste in classements.values() for c in liste]
    disponible = sum(c.taille for c in tous)
    essentiels = sum(c.taille for c in tous if c.score >= SCORE_ESSENTIEL)

    pages = pages_defaut
    if essentiels + fixes > quarts_de_contenu(pages_defaut) and max(pages_possibles) > pages_defaut:
        pages = max(pages_possibles)
    while disponible + fixes + _reserve_breves(breves_disponibles) < quarts_de_contenu(pages) \
            and pages > min(pages_possibles):
        pages = max(p for p in pages_possibles if p < pages)

    budget = quarts_de_contenu(pages) - fixes
    retenus: list[Choix] = []

    def prendre(c: Choix) -> bool:
        nonlocal budget
        if c in retenus or c.taille > budget:
            return False
        retenus.append(c)
        budget -= c.taille
        return True

    # 1. Les deux premiers de chaque bloc (si la place le permet).
    for liste in classements.values():
        for c in liste[:minimum_par_bloc]:
            prendre(c)
    # 2. Les meilleurs restants, tous blocs confondus.
    reste = sorted((c for c in tous if c not in retenus), key=lambda c: -c.score)
    for c in reste:
        if budget == 0:
            break
        prendre(c)
    # 3. Quart orphelin : un long peut ceder sa place a deux courts, sinon des breves en plus.
    quarts_breves = dict(fixes_breves)
    if budget == 1:
        courts = [c for c in reste if c not in retenus and c.format == "court"]
        longs = [c for c in retenus if c.format == "long"]
        if len(courts) >= 3 and longs:
            dernier_long = sorted(longs, key=lambda c: c.score)[0]
            retenus.remove(dernier_long)
            budget += 2
            for c in courts[:3]:
                prendre(c)
    if budget > 0:
        for bloc, n in sorted(breves_disponibles.items(), key=lambda kv: -kv[1]):
            while budget > 0 and n >= 3 * (quarts_breves.get(bloc, 0) + 1) - 1:
                quarts_breves[bloc] = quarts_breves.get(bloc, 0) + 1
                budget -= 1
    return Plan(pages=pages, articles=retenus, quarts_breves=quarts_breves, quarts_libres=budget)


def _reserve_breves(breves_disponibles: dict[str, int]) -> int:
    return sum(max(0, (n - 3 + 1) // 3) for n in breves_disponibles.values())


def assembler(unites: list[dict]) -> list[list[dict]]:
    """Range les unites (taille 1 ou 2) en demi-pages, dans l'ordre, en appariant les quarts.

    Un quart sans partenaire attend le quart suivant, quitte a passer apres un article long :
    l'ordre des blocs peut donc legerement varier pour que chaque demi-page soit pleine.
    """
    demis: list[list[dict]] = []
    en_attente: dict | None = None
    for unite in unites:
        if unite["taille"] == 2:
            demis.append([unite])
        elif en_attente is None:
            en_attente = unite
        else:
            demis.append([en_attente, unite])
            en_attente = None
    if en_attente is not None:
        demis.append([en_attente])
    return demis


def gabarit_numerique(longueur_source: int) -> tuple[str, int]:
    """Version telephone : toujours un article long, d'autant plus court que la source est mince."""
    return "long", max(NUM_PLANCHER_LONG, min(NUM_PLAFOND_LONG, int(longueur_source * NUM_RATIO)))


def planifier_numerique(classements: dict[str, list[Choix]], breves_disponibles: dict[str, int],
                        plafonds: dict[str, tuple[int, int]] | None = None) -> Plan:
    """Sans contrainte de page : par bloc, les mieux classes et les breves, dans la limite
    des plafonds du bloc (articles longs, breves)."""
    plafonds = plafonds or {}
    articles: list[Choix] = []
    for bloc, liste in classements.items():
        longs = plafonds.get(bloc, (NUM_LONGS_PAR_BLOC, NUM_BREVES_PAR_BLOC))[0]
        articles.extend(Choix(c.id, c.bloc, c.score, "long", c.limite) for c in liste[:longs])
    quarts = {}
    for bloc, n in breves_disponibles.items():
        n = min(n, plafonds.get(bloc, (NUM_LONGS_PAR_BLOC, NUM_BREVES_PAR_BLOC))[1])
        if n:
            quarts[bloc] = -(-n // 3)
    return Plan(pages=0, articles=articles, quarts_breves=quarts)
