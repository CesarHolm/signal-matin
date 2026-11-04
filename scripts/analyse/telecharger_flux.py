"""Télécharge tous les flux de config.cesar.example.yaml (analyse ponctuelle des sources)."""
import hashlib, json, os, sys, yaml
sys.path.insert(0, "src")
from signal_matin.connectors import rss
cfg = yaml.safe_load(open("config.cesar.example.yaml"))["journal"]
urls = sorted({s["url"] for k in ("blocs", "blocs_numerique") for b in cfg[k] for s in b["sources"]})
os.makedirs("flux", exist_ok=True)
index = {}
for u in urls:
    h = hashlib.sha1(u.encode()).hexdigest()[:16]
    try:
        open(f"flux/{h}.xml", "wb").write(rss._payload(u)); index[u] = {"fichier": h, "erreur": None}
    except Exception as e:
        index[u] = {"fichier": None, "erreur": repr(e)[:200]}
json.dump(index, open("flux/index.json", "w"), indent=1)
print(sum(1 for v in index.values() if v["erreur"]), "erreurs sur", len(index))
