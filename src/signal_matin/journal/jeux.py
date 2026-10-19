"""Grilles du jour, toutes a solution unique, generees localement (sans IA).

Chaque grille est deterministe pour une date donnee : relancer la generation
le meme jour produit les memes jeux, et les solutions publiees le lendemain
correspondent exactement aux grilles imprimees la veille.
"""
from __future__ import annotations

import datetime as dt
import random
from dataclasses import asdict, dataclass

# --------------------------------------------------------------------------- Sudoku


def _voisins(i: int) -> set[int]:
    r, c = divmod(i, 9)
    s = {r * 9 + k for k in range(9)} | {k * 9 + c for k in range(9)}
    br, bc = 3 * (r // 3), 3 * (c // 3)
    s |= {(br + dr) * 9 + bc + dc for dr in range(3) for dc in range(3)}
    s.discard(i)
    return s


VOISINS = [_voisins(i) for i in range(81)]
UNITES = (
    [[r * 9 + c for c in range(9)] for r in range(9)]
    + [[r * 9 + c for r in range(9)] for c in range(9)]
    + [[(br + dr) * 9 + bc + dc for dr in range(3) for dc in range(3)]
       for br in (0, 3, 6) for bc in (0, 3, 6)]
)


def _compter_solutions(grille: list[int], limite: int = 2) -> int:
    g = grille[:]

    def candidats(i: int) -> list[int]:
        pris = {g[p] for p in VOISINS[i]}
        return [d for d in range(1, 10) if d not in pris]

    def recurse() -> int:
        meilleur, cands = None, None
        for i in range(81):
            if g[i] == 0:
                c = candidats(i)
                if not c:
                    return 0
                if meilleur is None or len(c) < len(cands):
                    meilleur, cands = i, c
                    if len(c) == 1:
                        break
        if meilleur is None:
            return 1
        total = 0
        for d in cands:
            g[meilleur] = d
            total += recurse()
            if total >= limite:
                break
        g[meilleur] = 0
        return total

    return recurse()


def _grille_pleine(rng: random.Random) -> list[int]:
    g = [0] * 81

    def recurse(i: int = 0) -> bool:
        if i == 81:
            return True
        chiffres = list(range(1, 10))
        rng.shuffle(chiffres)
        pris = {g[p] for p in VOISINS[i]}
        for d in chiffres:
            if d not in pris:
                g[i] = d
                if recurse(i + 1):
                    return True
        g[i] = 0
        return False

    recurse()
    return g


def _resoluble_simplement(grille: list[int]) -> bool:
    """Vrai si la grille cede aux seuls singletons nus et caches (niveau facile)."""
    g = grille[:]
    while True:
        cand = {i: {d for d in range(1, 10) if d not in {g[p] for p in VOISINS[i]}}
                for i in range(81) if g[i] == 0}
        if not cand:
            return True
        progres = False
        for i, c in cand.items():
            if len(c) == 1:
                g[i] = c.pop()
                progres = True
        if not progres:
            for unite in UNITES:
                for d in range(1, 10):
                    places = [i for i in unite if g[i] == 0 and d in cand.get(i, ())]
                    if len(places) == 1:
                        g[places[0]] = d
                        progres = True
        if not progres:
            return False


def sudoku_difficile(rng: random.Random, mini: int = 26, maxi: int = 29) -> dict:
    while True:
        solution = _grille_pleine(rng)
        grille = solution[:]
        cases = list(range(81))
        rng.shuffle(cases)
        for i in cases:
            if sum(1 for v in grille if v) <= mini:
                break
            garde, grille[i] = grille[i], 0
            if _compter_solutions(grille) != 1:
                grille[i] = garde
        donnes = sum(1 for v in grille if v)
        if mini <= donnes <= maxi and not _resoluble_simplement(grille):
            return {"grille": grille, "solution": solution}


# --------------------------------------------------------------------------- Shikaku


def shikaku(rng: random.Random, largeur: int = 10, hauteur: int = 10, aire_max: int = 12) -> dict:
    def decouper() -> list[tuple[int, int, int, int]]:
        proprio = [[-1] * largeur for _ in range(hauteur)]
        rects: list[tuple[int, int, int, int]] = []
        for r in range(hauteur):
            for c in range(largeur):
                if proprio[r][c] != -1:
                    continue
                options = []
                for h in range(1, hauteur - r + 1):
                    for w in range(1, largeur - c + 1):
                        if h * w > aire_max or h * w < 2:
                            continue
                        if all(proprio[r + dr][c + dc] == -1 for dr in range(h) for dc in range(w)):
                            options.append((h, w))
                if not options:
                    options = [(1, 1)]
                h, w = rng.choices(options, [(a * b) ** 1.3 for a, b in options])[0]
                k = len(rects)
                rects.append((r, c, h, w))
                for dr in range(h):
                    for dc in range(w):
                        proprio[r + dr][c + dc] = k
        return rects

    def solutions(indices: list[tuple[int, int, int]], limite: int = 2) -> int:
        options = []
        for r, c, aire in indices:
            possibles = []
            for h in range(1, aire + 1):
                if aire % h:
                    continue
                w = aire // h
                for r0 in range(r - h + 1, r + 1):
                    for c0 in range(c - w + 1, c + 1):
                        if r0 < 0 or c0 < 0 or r0 + h > hauteur or c0 + w > largeur:
                            continue
                        cases = {(r0 + dr, c0 + dc) for dr in range(h) for dc in range(w)}
                        if any((ir, ic) in cases for ir, ic, _ in indices if (ir, ic) != (r, c)):
                            continue
                        possibles.append(cases)
            options.append(possibles)
        ordre = sorted(range(len(indices)), key=lambda i: len(options[i]))
        prises: set = set()
        compte = [0]

        def recurse(k: int) -> None:
            if compte[0] >= limite:
                return
            if k == len(ordre):
                if len(prises) == largeur * hauteur:
                    compte[0] += 1
                return
            for cases in options[ordre[k]]:
                if cases & prises:
                    continue
                prises.update(cases)
                recurse(k + 1)
                prises.difference_update(cases)

        recurse(0)
        return compte[0]

    for _ in range(600):
        rects = decouper()
        if sum(1 for *_, h, w in rects if h * w == 1) > 1:
            continue
        indices = [(r + rng.randrange(h), c + rng.randrange(w), h * w) for r, c, h, w in rects]
        if solutions(indices) == 1:
            return {"largeur": largeur, "hauteur": hauteur,
                    "indices": [list(i) for i in indices], "rectangles": [list(r) for r in rects]}
    raise RuntimeError("Shikaku introuvable")


# --------------------------------------------------------------------------- Futoshiki


def futoshiki(rng: random.Random, n: int = 6, nb_signes: int = 16) -> dict:
    def carre_latin() -> list[list[int]]:
        base = [[(r + c) % n + 1 for c in range(n)] for r in range(n)]
        lignes, colonnes, perm = list(range(n)), list(range(n)), list(range(1, n + 1))
        rng.shuffle(lignes)
        rng.shuffle(colonnes)
        rng.shuffle(perm)
        return [[perm[base[r][c] - 1] for c in colonnes] for r in lignes]

    def compter(donnes: dict, signes: list, limite: int = 2) -> int:
        g = [[donnes.get((r, c), 0) for c in range(n)] for r in range(n)]
        cases = [(r, c) for r in range(n) for c in range(n)]

        def possible(r: int, c: int, v: int) -> bool:
            if any(g[r][k] == v for k in range(n)) or any(g[k][c] == v for k in range(n)):
                return False
            for a, b in signes:  # a < b
                if (r, c) == a and g[b[0]][b[1]] and not v < g[b[0]][b[1]]:
                    return False
                if (r, c) == b and g[a[0]][a[1]] and not g[a[0]][a[1]] < v:
                    return False
            return True

        total = [0]

        def recurse(i: int) -> None:
            if total[0] >= limite:
                return
            while i < len(cases) and g[cases[i][0]][cases[i][1]]:
                i += 1
            if i == len(cases):
                total[0] += 1
                return
            r, c = cases[i]
            for v in range(1, n + 1):
                if possible(r, c, v):
                    g[r][c] = v
                    recurse(i + 1)
                    g[r][c] = 0

        recurse(0)
        return total[0]

    while True:
        solution = carre_latin()
        paires = []
        for r in range(n):
            for c in range(n):
                if c + 1 < n:
                    paires.append(((r, c), (r, c + 1)))
                if r + 1 < n:
                    paires.append(((r, c), (r + 1, c)))
        rng.shuffle(paires)
        signes = []
        for a, b in paires[:nb_signes]:
            signes.append((a, b) if solution[a[0]][a[1]] < solution[b[0]][b[1]] else (b, a))
        donnes: dict = {}
        cases = [(r, c) for r in range(n) for c in range(n)]
        rng.shuffle(cases)
        for case in cases:
            if compter(donnes, signes) == 1:
                break
            donnes[case] = solution[case[0]][case[1]]
        if compter(donnes, signes) == 1 and len(donnes) <= 7:
            for case in list(donnes):
                valeur = donnes.pop(case)
                if compter(donnes, signes) != 1:
                    donnes[case] = valeur
            return {"n": n, "donnes": [[r, c, v] for (r, c), v in donnes.items()],
                    "signes": [[list(a), list(b)] for a, b in signes], "solution": solution}


# --------------------------------------------------------------------- Le compte est bon


def compte_est_bon(rng: random.Random) -> dict:
    """Tire 6 plaques et une cible atteignable (au moins 4 operations, dont une x)."""
    while True:
        reserve = list(range(1, 11)) * 2 + [25, 50, 75, 100]
        plaques = rng.sample(reserve, 6)
        ordre = plaques[:]
        rng.shuffle(ordre)
        courant, etapes = ordre[0], []
        for valeur in ordre[1:rng.randint(5, 6)]:
            operation = rng.choice("+-*")
            if operation == "-" and courant <= valeur:
                operation = "+"
            nouveau = {"+": courant + valeur, "-": courant - valeur, "*": courant * valeur}[operation]
            symbole = {"+": "+", "-": "−", "*": "×"}[operation]
            etapes.append(f"{courant} {symbole} {valeur} = {nouveau}")
            courant = nouveau
        if 101 <= courant <= 999 and len(etapes) >= 4 and any("×" in e for e in etapes):
            return {"plaques": plaques, "cible": courant, "solution": etapes}


# --------------------------------------------------------------------------- Edition


@dataclass
class JeuxDuJour:
    sudoku: dict
    shikaku: dict
    futoshiki: dict
    compte: dict

    def en_dict(self) -> dict:
        return asdict(self)


def jeux_du_jour(jour: dt.date) -> JeuxDuJour:
    graine = int(jour.strftime("%Y%m%d"))
    return JeuxDuJour(
        sudoku=sudoku_difficile(random.Random(graine)),
        shikaku=shikaku(random.Random(graine + 1)),
        futoshiki=futoshiki(random.Random(graine + 2)),
        compte=compte_est_bon(random.Random(graine + 3)),
    )
