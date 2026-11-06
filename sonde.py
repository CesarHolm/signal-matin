"""Sonde des sources sportives (resultats et programme), lancee sur GitHub."""
import json, re, urllib.request, datetime as dt
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
ESPN = "https://site.api.espn.com/apis/site/v2/sports/"
SOURCES = {
 "espn tennis atp": ESPN+"tennis/atp/scoreboard", "espn tennis wta": ESPN+"tennis/wta/scoreboard",
 "espn f1": ESPN+"racing/f1/scoreboard",
 "espn ligue 1": ESPN+"soccer/fra.1/scoreboard", "espn ldc": ESPN+"soccer/uefa.champions/scoreboard",
 "espn europa": ESPN+"soccer/uefa.europa/scoreboard", "espn premier league": ESPN+"soccer/eng.1/scoreboard",
 "espn liga": ESPN+"soccer/esp.1/scoreboard", "espn serie a": ESPN+"soccer/ita.1/scoreboard",
 "espn bundesliga": ESPN+"soccer/ger.1/scoreboard", "espn foot amicaux/qualifs": ESPN+"soccer/fifa.worldq.uefa/scoreboard",
 "espn rugby (toutes)": ESPN+"rugby/scoreboard", "espn rugby top 14": ESPN+"rugby/270559/scoreboard",
 "espn rugby tests": ESPN+"rugby/289234/scoreboard", "espn nba": ESPN+"basketball/nba/scoreboard",
 "lequipe une": "https://dwh.lequipe.fr/api/edito/rss?path=/",
 "lequipe tennis": "https://dwh.lequipe.fr/api/edito/rss?path=/Tennis/",
 "lequipe cyclisme": "https://dwh.lequipe.fr/api/edito/rss?path=/Cyclisme-sur-route/",
 "lequipe athletisme": "https://dwh.lequipe.fr/api/edito/rss?path=/Athletisme/",
 "lequipe rugby": "https://dwh.lequipe.fr/api/edito/rss?path=/Rugby/",
 "lequipe f1": "https://dwh.lequipe.fr/api/edito/rss?path=/Formule-1/",
 "lequipe football": "https://dwh.lequipe.fr/api/edito/rss?path=/Football/",
 "franceinfo sports": "https://www.francetvinfo.fr/sports.rss",
 "rmc sport": "https://rmcsport.bfmtv.com/rss/fil-sport/",
 "eurosport": "https://www.eurosport.fr/rss.xml",
 "bbc sport": "https://feeds.bbci.co.uk/sport/rss.xml",
 "bbc tennis": "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
 "bbc cycling": "https://feeds.bbci.co.uk/sport/cycling/rss.xml",
 "bbc athletics": "https://feeds.bbci.co.uk/sport/athletics/rss.xml",
 "cyclingnews": "https://www.cyclingnews.com/feeds.xml",
 "letsrun": "https://www.letsrun.com/feed/",
}
rapport = {}
for nom, url in SOURCES.items():
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            corps = r.read().decode("utf-8", "replace"); code = r.status
        if corps.lstrip().startswith("{"):
            d = json.loads(corps); ev = d.get("events", [])
            ex = [f"{e.get('date','')[:16]} {e.get('name') or e.get('shortName','')} [{e.get('status',{}).get('type',{}).get('description','')}]" for e in ev[:4]]
            if not ex and d.get("events") is None: ex = [str(list(d.keys()))[:120]]
            rapport[nom] = {"code": code, "elements": len(ev), "exemples": ex}
        else:
            titres = re.findall(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", corps)[1:5]
            rapport[nom] = {"code": code, "elements": corps.count("<item"), "exemples": titres}
    except Exception as e:
        rapport[nom] = {"erreur": repr(e)[:150]}
open("rapport.json", "w").write(json.dumps({"le": dt.datetime.now().isoformat(), "sources": rapport}, ensure_ascii=False, indent=1))
