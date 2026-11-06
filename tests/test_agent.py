"""Version numerique fabriquee par un agent : demandes, reprise, verification (sans reseau)."""
import datetime as dt
import json

import pytest

from signal_matin.journal import agent as ag
from signal_matin.journal import edition as ed
from signal_matin.journal.articles import Bloc, Candidat
from signal_matin.journal.rendu_mobile import rendre_mobile

MAINTENANT = dt.datetime(2026, 11, 5, 4, tzinfo=dt.timezone.utc)


def _candidat(i, bloc, source="Source"):
    return Candidat(f"a{i}", bloc, "Rubrique", f"{source} {i}", f"Titre {i}", f"Résumé {i}.",
                    f"https://exemple.fr/{i}", MAINTENANT)


def _blocs():
    return [Bloc(id="ia", titre="IA", rubriques=["IA"], max_longs=2, max_breves=1,
                 candidats=[_candidat(i, "ia") for i in range(1, 6)]),
            Bloc(id="veille", titre="Veille réglementaire", rubriques=["RGPD"], max_longs=2, max_breves=2,
                 candidats=[_candidat(i, "veille") for i in range(6, 9)])]


@pytest.fixture
def monde(monkeypatch):
    appels = {"collecte": 0, "textes": []}

    def collecter(*a, **k):
        appels["collecte"] += 1
        return _blocs(), []

    def texte_integral(url, repli=""):
        appels["textes"].append(url)
        return ("court" if url.endswith("/1") else "Texte intégral de l'article. " * 300), "Jane Doe"

    monkeypatch.setattr(ed.art, "collecter", collecter)
    monkeypatch.setattr(ed.art, "texte_integral", texte_integral)
    monkeypatch.setattr(ed.art, "completer_par_autres_sources", lambda *a, **k: False)
    return appels


def _ecrire(dossier, ident, donnees):
    (dossier / "faits" / f"{ident}.json").write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")


def _avancer(dossier, cache, racine, final=False):
    client = ag.ClientAgent(dossier, final=final, journal=lambda *a: None)
    resultat = ed.produire({"journal": {"numerique": True}}, MAINTENANT, racine=racine,
                           journal=lambda *a: None, client=client, cache=cache)
    if client.en_attente:
        raise ag.EnAttente(client.en_attente)
    return resultat


def test_aller_retour_complet(tmp_path, monde):
    dossier, racine, cache = tmp_path / "ed", tmp_path / "data", {}

    # 1. Collecte puis demandes de tri, avec les consignes et les plafonds de la section.
    with pytest.raises(ag.EnAttente) as attente:
        _avancer(dossier, cache, racine)
    assert {"tri-ia", "tri-veille"} <= set(attente.value.ids)
    demande = json.loads((dossier / "a_faire" / "tri-ia.json").read_text(encoding="utf-8"))
    assert demande["modele"] == "haiku" and demande["sortie"] == "faits/tri-ia.json"
    assert "secrétaire de rédaction" in demande["systeme"]
    assert "au plus 2 article(s) long(s) et 1 brève(s)" in demande["contenu"]
    if (dossier / "a_faire" / "mots.json").is_file():
        _ecrire(dossier, "mots", {"mots": []})

    # 2. Tri : a1 a un texte trop court (devient une brève), a2 et a3 sont publiés en long.
    _ecrire(dossier, "tri-ia", {"developpes": [{"id": "a1", "score": 9}, {"id": "a2", "score": 8},
                                               {"id": "a3", "score": 7}, {"id": "a4", "score": 6}],
                                "breves": [{"id": "a5", "titre": "Brève 5", "texte": "Texte."}]})
    _ecrire(dossier, "tri-veille", {"developpes": [], "breves": []})
    with pytest.raises(ag.EnAttente) as attente:
        _avancer(dossier, cache, racine)
    assert set(attente.value.ids) == {"breves", "syn-a2", "syn-a3"}
    assert "https://exemple.fr/4" not in monde["textes"]  # réserve inutile : pas récupérée
    syn = json.loads((dossier / "a_faire" / "syn-a2.json").read_text(encoding="utf-8"))
    assert syn["modele"] == "sonnet" and syn["limite_caracteres"] == 4500  # 80 % de la source, plafonné

    # 3. Rédaction, puis édition terminée sans nouvelle collecte ni nouveau téléchargement.
    textes_avant = len(monde["textes"])
    _ecrire(dossier, "breves", {"breves": [{"id": "a1", "titre": "Brève 1", "texte": "Texte."}]})
    for ident in ("a2", "a3"):
        _ecrire(dossier, f"syn-{ident}", {"titre": f"Titre {ident}", "chapo": "Chapô.", "synthese": "Fin.",
                                         "sections": [{"intertitre": "I", "texte": "x" * 4000}]})
    resultat = _avancer(dossier, cache, racine)
    assert monde["collecte"] == 1 and len(monde["textes"]) == textes_avant
    ia_bloc, veille = resultat["edition"]["blocs"]
    assert [d["titre"] for d in ia_bloc["developpes"]] == ["Titre a2", "Titre a3"]
    assert {d["format"] for d in ia_bloc["developpes"]} == {"long"}
    assert [b["id"] for b in ia_bloc["breves"]] == ["a1"]  # plafond d'une brève
    assert veille["developpes"] == [] and not resultat["edition"]["indisponibles"]
    assert "Rien de notable" in rendre_mobile(resultat["edition"])
    assert ag.verifier(dossier) == []


def test_reponses_manquantes_signalees_sans_secours(tmp_path, monde):
    dossier, racine, cache = tmp_path / "ed", tmp_path / "data", {}
    with pytest.raises(ag.EnAttente):
        _avancer(dossier, cache, racine)
    _ecrire(dossier, "tri-ia", {"developpes": [{"id": "a2", "score": 8}], "breves": []})
    resultat = _avancer(dossier, cache, racine, final=True)
    edition = resultat["edition"]
    assert edition["indisponibles"] == ["Veille réglementaire"]
    assert edition["non_rediges"] == {"IA": 1}
    assert not edition["secours"] and edition["blocs"][0]["developpes"] == []
    assert "Édition incomplète" in rendre_mobile(edition)


def test_sources_complementaires_verifiees(tmp_path, monde, monkeypatch):
    def completer(candidat, autres, minimum, journal=print, cible=None):
        candidat.texte = "SOURCE 1 (A) :\ncourt\n\nSOURCE 2 (B) :\n" + "y" * 5000
        candidat.sources_complementaires = [{"source": "B", "url": "https://b.fr"}]
        return True
    monkeypatch.setattr(ed.art, "completer_par_autres_sources", completer)
    dossier, racine, cache = tmp_path / "ed", tmp_path / "data", {}
    with pytest.raises(ag.EnAttente):
        _avancer(dossier, cache, racine)
    _ecrire(dossier, "tri-ia", {"developpes": [{"id": "a1", "score": 9}], "breves": []})
    _ecrire(dossier, "tri-veille", {"developpes": [], "breves": []})
    if (dossier / "a_faire" / "mots.json").is_file():
        _ecrire(dossier, "mots", {"mots": []})
    with pytest.raises(ag.EnAttente):
        _avancer(dossier, cache, racine)
    demande = json.loads((dossier / "a_faire" / "syn-a1.json").read_text(encoding="utf-8"))
    assert demande["contenu"].startswith("Vérification des sources complémentaires")
    assert "sources_ecartees" in demande["schema"]["properties"]
    # L'agent écarte la source 2 et juge la matière insuffisante : l'article devient une brève.
    _ecrire(dossier, "syn-a1", {"insuffisant": True, "titre": "Brève 1", "texte": "Texte."})
    edition = _avancer(dossier, cache, racine)["edition"]
    assert edition["blocs"][0]["developpes"] == []
    assert [b["titre"] for b in edition["blocs"][0]["breves"]] == ["Brève 1"]


def test_verification_des_reponses(tmp_path):
    dossier = tmp_path
    (dossier / "a_faire").mkdir()
    (dossier / "faits").mkdir()
    from signal_matin.journal import ia
    requete = ia.Requete(id="syn-a9", modele="sonnet", systeme="s", schema=ia.SCHEMA_SYNTHESE,
                         contenu="Format : long\nLimite de longueur : 2000 caractères au total.")
    ag.deposer(dossier, requete)
    assert ag.verifier(dossier) == ["syn-a9 : réponse absente (faits/syn-a9.json)"]
    _ecrire(dossier, "syn-a9", {"titre": "T", "chapo": "C", "synthese": "S",
                                "sections": [{"intertitre": "I", "texte": "x" * 500}]})
    assert "trop court" in ag.verifier(dossier)[0]
    _ecrire(dossier, "syn-a9", {"titre": "T"})
    assert "schéma" in ag.verifier(dossier)[0]


def test_commande_journal_agent(tmp_path, monde, monkeypatch):
    from signal_matin import cli
    from signal_matin.journal import etat
    monkeypatch.setattr(etat, "DOSSIER", tmp_path / "data")
    monkeypatch.setattr(ed, "DOSSIER", tmp_path / "data")
    monkeypatch.setattr(ed, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    dossier = tmp_path / "ed"
    commande = ["journal-agent", "avancer", str(dossier), "--config", str(tmp_path / "absent.yaml")]
    assert cli.main(commande) == 3
    for fichier in (dossier / "a_faire").glob("*.json"):
        ident = fichier.stem
        _ecrire(dossier, ident, {"mots": []} if ident == "mots" else {"developpes": [], "breves": []})
    assert cli.main(commande) == 0
    assert cli.main(["journal-agent", "verifier", str(dossier)]) == 0
    resultat = json.loads((dossier / "resultat.json").read_text(encoding="utf-8"))
    assert resultat["edition"]["numerique"] and resultat["essai"] is False


def test_tour_hybride_cote_github(tmp_path, monde, monkeypatch):
    """Côté GitHub : tour.json → avancer → etat.json ; dernier tour → publication."""
    from signal_matin import cli
    from signal_matin.journal import etat
    monkeypatch.setattr(etat, "DOSSIER", tmp_path / "data")
    monkeypatch.setattr(ed, "DOSSIER", tmp_path / "data")
    monkeypatch.setattr(ed, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    envois = []
    monkeypatch.setattr(cli, "_envoyer_edition", lambda edition, *a: envois.append(edition["date"]) or 0)
    dossier = tmp_path / "ed"
    dossier.mkdir()
    commande = ["journal-agent", "tour", str(dossier), "--config", str(tmp_path / "absent.yaml")]

    (dossier / "tour.json").write_text(json.dumps({"tour": 1, "essai": True}), encoding="utf-8")
    assert cli.main(commande) == 0
    etat1 = json.loads((dossier / "etat.json").read_text(encoding="utf-8"))
    assert etat1["tour"] == 1 and etat1["code"] == 3 and "tri-ia" in etat1["a_faire"]
    assert not etat1["termine"] and not envois

    for ident in etat1["a_faire"]:
        _ecrire(dossier, ident, {"mots": []} if ident == "mots" else {"developpes": [], "breves": []})
    (dossier / "tour.json").write_text(json.dumps({"tour": 2}), encoding="utf-8")
    assert cli.main(commande) == 0
    etat2 = json.loads((dossier / "etat.json").read_text(encoding="utf-8"))
    assert etat2 == {**etat2, "tour": 2, "code": 0, "a_faire": [], "termine": True}
    assert len(envois) == 1
    assert json.loads((dossier / "resultat.json").read_text(encoding="utf-8"))["essai"] is True


def test_attendre_lit_l_etat_pousse(tmp_path):
    import subprocess

    def git(*args, cwd):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    distant, local = tmp_path / "distant.git", tmp_path / "local"
    git("init", "-q", "--bare", str(distant), cwd=tmp_path)
    git("clone", "-q", str(distant), str(local), cwd=tmp_path)
    git("checkout", "-q", "-b", "claude/editions", cwd=local)
    dossier = local / "editions" / "j"
    dossier.mkdir(parents=True)
    (dossier / "tour.json").write_text('{"tour": 1}', encoding="utf-8")
    git("add", "-A", cwd=local)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t1", cwd=local)
    git("push", "-q", "origin", "claude/editions", cwd=local)
    assert ag.attendre(dossier, 1, delai=0, pause=0) == 4

    # « GitHub » répond depuis un autre clone.
    autre = tmp_path / "autre"
    git("clone", "-q", "-b", "claude/editions", str(distant), str(autre), cwd=tmp_path)
    (autre / "editions" / "j" / "etat.json").write_text(
        '{"tour": 1, "code": 3, "a_faire": ["tri-ia"], "termine": false}', encoding="utf-8")
    git("add", "-A", cwd=autre)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t2", cwd=autre)
    git("push", "-q", "origin", "claude/editions", cwd=autre)
    assert ag.attendre(dossier, 1, delai=0, pause=0) == 0
    assert (dossier / "etat.json").is_file()
