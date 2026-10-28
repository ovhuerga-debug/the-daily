#!/usr/bin/env python3
"""THE DAILY: RSS headlines with attributed source excerpts; no AI summaries."""
import datetime as dt
import email.utils
import html
import json
import os
import re
from urllib.parse import urlparse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEEDS = {
 "espana":[("RTVE","https://www.rtve.es/rss/portada.xml"),("El País","https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),("Europa Press","https://www.europapress.es/rss/rss.aspx"),("El Mundo","https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml"),("ABC España","https://www.abc.es/rss/feeds/abcPortada.xml"),("El Confidencial","https://rss.elconfidencial.com/espana/")],
 "mundo":[("BBC World","https://feeds.bbci.co.uk/news/world/rss.xml"),("The Guardian World","https://www.theguardian.com/world/rss"),("ABC Australia","https://www.abc.net.au/news/feed/51120/rss.xml"),("DW","https://rss.dw.com/rdf/rss-en-world"),("NPR World","https://feeds.npr.org/1004/rss.xml")],
 "television":[("Variety TV","https://variety.com/v/tv/feed/"),("Deadline TV","https://deadline.com/category/tv/feed/"),("The Guardian Television","https://www.theguardian.com/tv-and-radio/rss"),("FormulaTV","https://www.formulatv.com/rss/"),("Vertele","https://www.eldiario.es/vertele/rss/")]
}
LIMITS={"espana":20,"mundo":30,"television":30}

from urllib.parse import quote
def google_news(query,lang):
 country="ES" if lang=="es" else "US"
 return "https://news.google.com/rss/search?q="+quote(query)+"&hl="+lang+"&gl="+country+"&ceid="+country+":"+lang
SPECIAL={
"cultura":[
("Música","es","Música ES",google_news("Madrid conciertos festivales música artistas when:7d","es")),
("Música","es","Música España",google_news("España música conciertos artistas discos when:5d","es")),
("Música","en","Music EN","https://www.theguardian.com/music/rss"),
("Cine","es","Cine ES",google_news("Madrid cine estrenos festivales películas when:7d","es")),
("Cine","es","Cine España",google_news("España cine estrenos películas festivales when:5d","es")),
("Cine","en","Film EN","https://www.theguardian.com/film/rss"),
("Teatro","es","Teatro ES",google_news("Madrid teatro musicales estrenos cartelera when:7d","es")),
("Teatro","es","Teatro España",google_news("España teatro musicales estrenos when:5d","es")),
("Teatro","en","Stage EN","https://www.theguardian.com/stage/rss"),
("Cultura general","es","Cultura ES",google_news("Madrid exposiciones museos cultura arte when:7d","es")),
("Cultura general","es","Cultura España",google_news("España exposiciones libros museos arte when:5d","es")),
("Cultura general","en","Culture EN","https://www.theguardian.com/culture/rss")],
"viral":[
("Tendencias","es","Viral ES",google_news("vídeo viral redes sociales tendencia internet when:2d","es")),
("Tendencias","en","Viral EN",google_news("viral video internet social media trending when:2d","en"))],
"tecnologia":[
("Tecnología","es","Tecnología ES",google_news("tecnología inteligencia artificial móviles innovación when:2d","es")),
("Tecnología","en","Tech EN","https://www.theguardian.com/technology/rss"),
("Tecnología","en","TechCrunch EN","https://techcrunch.com/feed/")],
"estilo":[
("Moda","es","GQ España",google_news("site:revistagq.com moda masculina tendencias when:7d","es")),
("Moda","es","Esquire España",google_news("site:esquire.com/es moda hombre estilo when:7d","es")),
("Cuidado personal","es","Mensencia",google_news("site:mensencia.com estilo hombre moda belleza when:14d","es")),
("Estilo de vida","es","GQ España Lifestyle",google_news("site:revistagq.com estilo de vida relojes when:7d","es")),
("Moda","en","GQ EN",google_news("site:gq.com menswear style trends when:7d","en")),
("Estilo de vida","en","Esquire EN",google_news("site:esquire.com style menswear grooming when:7d","en"))]}
SPECIAL_LIMITS={"cultura":5,"viral":12,"tecnologia":12,"estilo":8}
EXTRA_FEEDS={
 "espana":[("English coverage", "en", google_news("Spain politics economy news when:3d","en"))],
 "mundo":[("Noticias internacionales", "es", google_news("noticias internacionales mundo actualidad when:2d","es"))],
 "television":[("Televisión España", "es", google_news("audiencias televisión estrenos formatos televisión when:3d","es"))]
}

NS={"a":"http://www.w3.org/2005/Atom"}
def clean(value):
 value=re.sub(r"<[^>]*>"," ",value or "")
 return re.sub(r"\s+"," ",html.unescape(value)).strip()
def child(el,names):
 for name in names:
  v=el.findtext(name)
  if v:return v
 return ""
def dateparse(s):
 try:
  d=email.utils.parsedate_to_datetime(s)
  return d.astimezone(dt.timezone.utc).isoformat() if d else ""
 except Exception:
  try:return dt.datetime.fromisoformat(s.replace("Z","+00:00")).isoformat()
  except Exception:return ""
TRUSTED_PUBLISHERS=("rtve","efe","europa press","el país","elpais","el mundo","abc","la vanguardia","eldiario.es","el confidencial","elconfidencial","formulatv","formula tv","vertele","vértele","gq","gq españa","esquire","mensencia","20minutos","cadena ser","cope","ondacero","bbc","reuters","associated press","ap news","the guardian","dw","npr","variety","deadline","techcrunch","timeout","time out","guía del ocio","madrid secreto","esmadrid","madrid.es","comunidad de madrid","museo del prado","teatros del canal")
def approved_aggregated_title(title):
 # Google News headlines generally end with ' - Publisher'.
 publisher=title.rsplit(" - ",1)[-1].strip().lower() if " - " in title else ""
 return bool(publisher and any(publisher==name or publisher.startswith(name+" ") for name in TRUSTED_PUBLISHERS))

def fetch(section,source,url,language=None,topic=None):
 req=urllib.request.Request(url,headers={"User-Agent":"TheDailyReader/0.1 (RSS aggregation; contact via repository)","Accept":"application/rss+xml,application/atom+xml,application/xml,text/xml"})
 with urllib.request.urlopen(req,timeout=16) as response:
  xml=response.read(3_000_000)
 root=ET.fromstring(xml)
 items=root.findall(".//item")
 atom=False
 if not items:
  items=root.findall(".//a:entry",NS)
  atom=True
 result=[]
 for item in items[:35]:
  title=clean(child(item,["title","a:title"]))
  link=child(item,["link"])
  if atom:
   link=next((e.attrib.get("href","") for e in item.findall("a:link",NS) if e.attrib.get("rel","alternate")=="alternate"),"") or next((e.attrib.get("href","") for e in item.findall("a:link",NS)),"")
  if not title or not link.startswith(("https://","http://")):continue
  if "news.google.com/rss/search" in url and not approved_aggregated_title(title):
   continue
  excerpt=clean(child(item,["description","a:summary","a:content","{http://purl.org/rss/1.0/modules/content/}encoded"]))
  published=dateparse(child(item,["pubDate","a:updated","a:published","{http://purl.org/dc/elements/1.1/}date"]))
  result.append({"id":section+"|"+link,"section":section,"category":source,"title":title[:250],
   "summary":(excerpt[:360].rstrip()+"…" if len(excerpt)>360 else excerpt) or "Lee la noticia completa en la fuente original.",
   "publishedAt":published[:16].replace("T"," ")+" UTC" if published else "",
   "_sort":published,"language":language,"topic":topic,"verification":"fuente identificada; no contrastada independientemente","sources":[{"name":source,"url":link}]})
 return result
def main():
 now=dt.datetime.now(dt.timezone.utc)
 hour=int(os.environ.get("EDITION_HOUR", "8"))
 allstories=[]
 for section,feeds in FEEDS.items():
  pool=[]
  for source,url in feeds:
   try:
    language="en" if section=="mundo" or source in ("Variety TV","Deadline TV","The Guardian Television") else "es"
    got=fetch(section,source,url,language)
    pool.extend(got)
    print(source,len(got))
   except Exception as e:print("Feed unavailable:",source,str(e)[:180])
  seen=set()
  selected=[]
  for story in sorted(pool,key=lambda x:x["_sort"],reverse=True):
   key=re.sub(r"[^a-z0-9]+","",story["title"].lower())[:110]
   if key in seen:continue
   seen.add(key)
   story.pop("_sort",None)
   selected.append(story)
   if len(selected)>=LIMITS[section]:break
  allstories.extend(selected)
 for section,feeds in EXTRA_FEEDS.items():
  for source,language,url in feeds:
   try:
    more=fetch(section,source,url,language)
    for story in more[:12]:
     story.pop("_sort",None)
     allstories.append(story)
   except Exception as e:print("Feed unavailable:",source,str(e)[:180])
 for section,feeds in SPECIAL.items():
  for topic,language,source,url in feeds:
   try:
    pool=fetch(section,source,url,language,topic)
    print(source,len(pool))
   except Exception as e:
    print("Feed unavailable:",source,str(e)[:180])
    pool=[]
   cap=8 if section=="cultura" and language=="es" and source.endswith("ES") else SPECIAL_LIMITS[section]
   for story in sorted(pool,key=lambda x:x["_sort"],reverse=True)[:cap]:
    if section=="viral" and story["_sort"]:
     try:
      age=dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(story["_sort"])
      if age.total_seconds()>48*3600:continue
     except ValueError:pass
    if section=="cultura" and language=="es":
     story["region"]="España" if source.endswith("España") else "Madrid"
    story.pop("_sort",None)
    url=story["sources"][0]["url"]
    if section=="viral" and any(marker in url.lower() for marker in ["youtube.com/watch","youtu.be/","tiktok.com/","instagram.com/reel/"]):
     story["videoUrl"]=url
    allstories.append(story)
 if not allstories:
  raise RuntimeError("No feeds available; keeping previous edition unchanged")
 local=now.astimezone(__import__("zoneinfo").ZoneInfo("Europe/Madrid"))
 edition="THE DAILY · "+("Mañana" if hour==8 else "Noche")+" · "+local.strftime("%d/%m/%Y %H:%M")
 out={"edition":edition,"generatedAt":now.isoformat(),"mode":"rss-excerpts","stories":allstories}
 Path("editions").mkdir(exist_ok=True)
 Path("editions/latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Published",len(allstories),"stories")
if __name__=="__main__":main()
