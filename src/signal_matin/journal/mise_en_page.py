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
NUM_RATIO = 0.50
NUM_PLAFOND_LONG = 4500
NUM_PLAFOND_COURT = 1800
NUM_LONGS_PAR_BLOC = 4
NUM_ARTICLES_PAR_BLOC = 6
NUM_BREVES_PAR_BLOC = 6


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
    """Gabarit de la version telephone : longs jusqu'a 4 500 caracteres, courts jusqu'a 1 800."""
    possible = int(longueur_source * NUM_RATIO)
    if possible >= SEUIL_LONG:
        return "long", min(NUM_PLAFOND_LONG, possible)
    limite = min(NUM_PLAFOND_COURT, max(PLANCHER_COURT, possible))
    return "court", max(300, min(limite, int(longueur_source * 0.70)))


def planifier_numerique(classements: dict[str, list[Choix]], breves_disponibles: dict[str, int]) -> Plan:
    """Sans contrainte de page : par bloc, les mieux classes (4 longs au plus, 6 articles au plus)
    et toutes les breves redigees (6 au plus)."""
    articles: list[Choix] = []
    for liste in classements.values():
        longs = 0
        for choix in liste[:NUM_ARTICLES_PAR_BLOC]:
            if choix.format == "long":
                if longs >= NUM_LONGS_PAR_BLOC:
                    choix = Choix(choix.id, choix.bloc, choix.score, "court", NUM_PLAFOND_COURT)
                else:
                    longs += 1
            articles.append(choix)
    quarts = {b: -(-min(n, NUM_BREVES_PAR_BLOC) // 3) for b, n in breves_disponibles.items() if n}
    return Plan(pages=0, articles=articles, quarts_breves=quarts)
