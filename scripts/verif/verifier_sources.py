import sys, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET, concurrent.futures as cf
from signal_matin.journal.articles import texte_integral, USER_AGENT
def tag(e): return e.tag.rsplit("}",1)[-1].lower()
def items(xml):
    root = ET.fromstring(xml); out=[]
    for e in root.iter():
        if tag(e) in ("item","entry"):
            link=None; titre=""; date=""
            for c in e:
                t=tag(c)
                if t=="link": link = c.attrib.get("href") or (c.text or "").strip()
                elif t=="title": titre=" ".join("".join(c.itertext()).split())
                elif t in ("pubdate","updated","published","date"): date=date or (c.text or "").strip()
            out.append((titre,link,date))
    return out
def pdf(url):
    import io
    try:
        if url.lower().split("?")[0].endswith(".pdf"):
            cible = url
        else:
            page = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=20).read(3_000_000).decode("utf-8","replace")
            m = re.search(r'href=["\']([^"\']+\.pdf[^"\']*)', page, re.I)
            if not m: return "aucun"
            cible = urllib.parse.urljoin(url, m.group(1))
        data = urllib.request.urlopen(urllib.request.Request(cible, headers={"User-Agent": USER_AGENT}), timeout=30).read(15_000_000)
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(data))
        return f"{len(r.pages)}p/{sum(len(p.extract_text() or '') for p in r.pages[:40])}c"
    except Exception as e:
        return f"err {type(e).__name__}"

def test(ligne):
    cat,nom,url = ligne.split("|",2)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=20)
        its = items(r.read())
    except Exception as e:
        return f"{cat}|{nom}|ECHEC flux: {type(e).__name__} {str(e)[:60]}"
    if not its: return f"{cat}|{nom}|flux vide"
    longs=[]; pdfs=[]
    for t,l,d in its[:2]:
        txt,_ = texte_integral(l or "", "") if l else ("",None)
        longs.append(len(txt)); pdfs.append(pdf(l) if l and len(txt) < 2500 else "-")
    return f"{cat}|{nom}|{len(its)} items | dernier {its[0][2][:16]} | texte {longs} | pdf {pdfs} | ex: {its[0][0][:70]}"
lignes=[l.strip() for l in open(sys.argv[1]) if l.strip()]
with cf.ThreadPoolExecutor(10) as ex:
    for res in ex.map(test, lignes): print(res, flush=True)
