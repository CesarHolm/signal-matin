"""Démo avant/après : un papier de recherche rédigé avec 40 000 puis 20 000 caractères de texte source."""
import json, os, sys, datetime as dt, yaml
sys.path.insert(0, "src")
from signal_matin.journal import articles as art, ia, mise_en_page as mep
from signal_matin.connectors import rss
URL = "https://www.ecb.europa.eu//pub/pdf/scpwps/ecb.wp3306~028a82bc67.en.pdf"
cfg = yaml.safe_load(open("config.cesar.example.yaml"))["journal"]
client = ia.ClientIA(cfg.get("ia", {}))
consommation = []
create = client.client.messages.create
def espion(*a, **k):
    r = create(*a, **k); u = r.usage
    consommation.append({k2: getattr(u, k2, None) for k2 in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")})
    return r
client.client.messages.create = espion
# titre d'origine depuis le flux de la BCE
titre, resume, publie = "", "", None
items, _ = rss.collect_rss([{"name": "BCE", "url": "https://www.ecb.europa.eu/rss/wppub.html"}], dt.datetime.now(dt.timezone.utc), limit=40, max_age_hours=24 * 30)
for it in items:
    if "wp3306" in str(it.source.url):
        titre, resume, publie = it.title, it.summary, it.source.published_at
_, auteur = art.texte_integral(URL, resume)
texte40 = art.texte_pdf(URL)  # chemin réel de l'édition pour un papier de recherche
texte20 = art.texte_pdf(URL, plafond=20_000)
sortie = {"titre_origine": titre, "auteur": auteur, "versions": []}
for nom, texte in (("actuel_40000", texte40), ("propose_20000", texte20)):
    fmt, limite = mep.gabarit_numerique(len(texte))
    cand = art.Candidat("a1", "recherche", "Économie", "BCE (documents de travail)", titre, resume, URL, publie, texte=texte, auteur=auteur)
    req = ia.requete_synthese(client, cand, limite, fmt, numerique=True, recherche=True)
    n0 = len(consommation)
    rep = client.direct([req]).get(req.id)
    sortie["versions"].append({"nom": nom, "car_source": len(texte), "format": fmt, "limite": limite,
                               "consommation": consommation[n0:], "reponse": rep})
os.makedirs("demo", exist_ok=True)
json.dump(sortie, open("demo/demo_recherche.json", "w"), ensure_ascii=False, indent=1)
import base64, zlib
print("DEMO-DEBUT" + base64.b64encode(zlib.compress(json.dumps(sortie, ensure_ascii=False).encode())).decode() + "DEMO-FIN")
