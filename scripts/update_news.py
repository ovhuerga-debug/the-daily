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
("Moda","es","GQ España",google_news("site:revistagq.com moda masculina when:14d","es")),
("Moda","es","Esquire España",google_news("site:esquire.com/es moda hombre when:14d","es")),
("Cuidado personal","es","Mensencia",google_news("site:mensencia.com moda belleza hombre when:30d","es")),
("Estilo de vida","es","GQ España Lifestyle",google_news("site:revistagq.com estilo de vida relojes when:7d","es")),
("Moda","en","GQ EN",google_news("site:gq.com menswear style trends when:7d","en")),
("Estilo de vida","en","Esquire EN",google_news("site:esquire.com style menswear grooming when:7d","en")),
("Moda","es","Moda masculina España",google_news("moda masculina tendencias hombre GQ Esquire Mensencia when:7d","es")),
("Cuidado personal","es","Grooming España",google_news("cuidado masculino belleza hombre perfume afeitado when:7d","es")),
("Moda","en","Menswear International",google_news("menswear fashion men style grooming when:7d","en"))]}
SPECIAL_LIMITS={"cultura":5,"viral":12,"tecnologia":12,"estilo":8}
EXTRA_FEEDS={
 "espana":[("English coverage", "en", google_news("Spain politics economy news when:3d","en"))],
 "mundo":[("Noticias internacionales", "es", google_news("noticias internacionales mundo actualidad when:2d","es"))],
 "television":[("Televisión España", "es", google_news("audiencias televisión estrenos formatos televisión when:3d","es"))]
}

# Curated sources from the reader's preferred publications. Site-scoped Google News RSS
# is used when no confirmed free publisher RSS is available.
CURATED_SOURCES={
 "espana":[
 ("El Español","elespanol.com","es"),("NIUS","niusdiario.es","es"),
 ("La Vanguardia","lavanguardia.com","es"),("20minutos","20minutos.es","es"),
 ("CNN en Español","cnnespanol.cnn.com","es"),("OKDIARIO","okdiario.com","es"),
 ("Noticias.com","noticias.com","es"),("La Información","lainformacion.com","es"),
 ("Qué! Madrid","que.madrid","es"),("El Confidencial Digital","elconfidencialdigital.com","es")],
 "television":[
 ("Yotele","elperiodico.com/es/yotele/","es"),("Bluper","elespanol.com/bluper/","es"),
 ("El Televisero","eltelevisero.com","es"),("Vaya Tele","vayatele.com","es"),
 ("TodoTVNews","todotvnews.com","es"),("Audiovisual451","audiovisual451.com","es"),
 ("Objetivo TV","objetivotv.com","es"),("Telemanía","telecinco.es","es"),
 ("TV by the Numbers","tvbythenumbers.com","en"),("DavideMaggio","davidemaggio.it","it"),
 ("JustWatch","justwatch.com","es"),("Cveintiuno","cveintiuno.com","es"),
 ("Entertainment Weekly","ew.com","en"),("TV Insider","tvinsider.com","en"),
 ("BroadcastPro ME","broadcastprome.com","en"),("Screen Daily","screendaily.com","en"),
 ("The Hollywood Reporter","hollywoodreporter.com","en"),
 ("Digital Spy","digitalspy.com","en"),("Media Play News","mediaplaynews.com","en"),
 ("Broadband TV News","broadbandtvnews.com","en")],
 "tecnologia":[
 ("Applesfera","applesfera.com","es"),("Xataka","xataka.com","es"),
 ("Xataka Móvil","xatakamovil.com","es"),("Apple Newsroom","apple.com/es/newsroom/","es"),
 ("MacRumors","macrumors.com","en"),("iPhone Diario","iphonediario.com","es"),
 ("Hoy iPad","hoyipad.com","es"),("AppleWeblog","hipertextual.com","es")],
 "estilo":[
 ("Men's Health España","menshealth.com/es/","es"),
 ("MADMENMAG","madmenmag.com","es"),
 ("FashionBeans","fashionbeans.com","en")],
 "cultura":[
 ("Espinof","espinof.com","es","Cine"),("Los Lunes Seriéfilos","loslunesseriefilos.com","es","Cine"),
 ("Series Adictos","seriesadictos.com","es","Cine"),("SensaCine","sensacine.com","es","Cine"),
 ("El Blog de Cine Español","elblogdecineespanol.com","es","Cine"),
 ("Cinemanía","20minutos.es/cinemania/","es","Cine"),("Serielizados","serielizados.com","es","Cine"),
 ("Kinótico","kinotico.es","es","Cine"),
 ("Indie Rocks!","indierocks.mx","es","Música"),("Jenesaispop","jenesaispop.com","es","Música"),
 ("La Fonoteca","lafonoteca.net","es","Música"),("Música Crónica","musicacronica.com","es","Música"),
 ("MondoSonoro","mondosonoro.com","es","Música"),
 ("Hipersonica","hipersonica.com","es","Música"),("El Remix","elremix.com","es","Música"),
 ("Dentro Música","dentrodemusica.com","es","Música")]
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
def story_image(item):
 # Only publisher-provided RSS imagery; never use a generic unrelated photo.
 candidates=[]
 for element in item.iter():
  tag=element.tag.rsplit("}",1)[-1].lower()
  if tag in ("thumbnail","content","enclosure","image"):
   u=element.attrib.get("url","") or element.attrib.get("href","")
   mime=element.attrib.get("type","")
   if u and (tag!="enclosure" or mime.startswith("image/")):
    candidates.append(u)
  if tag=="image":
   v=element.findtext("url")
   if v:candidates.append(v)
 for u in candidates:
  if u.startswith("https://") or u.startswith("http://"):
   if not re.search(r"\\.(svg|gif)(?:[?#]|$)",u,re.I):return u
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
  if "news.google.com/rss/search" in url and section!="estilo" and "site%3A" not in url and not approved_aggregated_title(title):
   continue
  excerpt=clean(child(item,["description","a:summary","a:content","{http://purl.org/rss/1.0/modules/content/}encoded"]))
  published=dateparse(child(item,["pubDate","a:updated","a:published","{http://purl.org/dc/elements/1.1/}date"]))
  result.append({"id":section+"|"+link,"section":section,"category":source,"title":title[:250],
   "summary":(excerpt[:360].rstrip()+"…" if len(excerpt)>360 else excerpt) or "Lee la noticia completa en la fuente original.",
   "image":story_image(item),
   "publishedAt":published[:16].replace("T"," ")+" UTC" if published else "",
   "_sort":published,"language":language,"topic":topic,"verification":"fuente identificada; no contrastada independientemente","sources":[{"name":source,"url":link}]})
 return result
CULTURE_MADRID_TERMS=("madrid","madrileñ","matadero","teatros del canal","teatro real","filmoteca española","cineteca","cines princesa","festival de otoño","reina sofía","thyssen","museo del prado","caixaforum madrid","condeduque","la riviera","movistar arena","ifema","alcobendas","alcorcón")
CULTURE_SPAIN_TERMS=("españa","español","española","españoles","españolas","premios goya","academia de cine","cine español","festival de san sebastián","festival de málaga","semana de cine de valladolid","seminci","barcelona","valencia","sevilla","bilbao","zaragoza","galicia","andalucía","cataluña","canarias","málaga","san sebastián","valladolid","almodóvar","bayona","sorogoyen","carla simón","isabel coixet","penélope cruz","javier bardem","blanca suárez","úrsula corberó")
def culture_region(story):
 text=(story.get("title","")+" "+story.get("summary","")).lower()
 if any(term in text for term in CULTURE_MADRID_TERMS):return "Madrid"
 if any(term in text for term in CULTURE_SPAIN_TERMS):return "España"
 return "Internacional"
def spanish_cinema_relevant(story):
 # Exclude Spanish-language cinema coverage lacking a visible Spanish connection.
 return culture_region(story)!="Internacional"


# Agenda is a separate editorial view, not a claim that tickets or dates are verified.
AGENDA_SIGNALS=("entradas","cartelera","programación","programacion","agenda","dónde ver","donde ver","cuándo","cuando","fechas","concierto","conciertos","exposición","exposicion","exposiciones","musical","musicales","festival","festivales","estreno","estrenos","recital","gira","teatro","museo","museos")
def culture_view(story):
 title=(story.get("title") or "").lower()
 text=title+" "+(story.get("summary") or "").lower()
 if story.get("agendaSource"):return "agenda"
 # An article about an artist is not necessarily a plan; require event context.
 if any(word in title for word in ("agenda","cartelera","entradas","dónde ver","donde ver","programación","programacion","exposición","exposicion","concierto","conciertos","musical","festival")):
  return "agenda"
 if any(word in title for word in ("estrena","estreno","estrenos","actuará","actuara","llega a madrid","en madrid")) and any(word in text for word in AGENDA_SIGNALS):
  return "agenda"
 return "noticias"

AGENDA_QUERIES=[
 ("Música","Madrid conciertos entradas fechas programación when:14d"),
 ("Teatro","Madrid teatro musicales cartelera estrenos entradas when:14d"),
 ("Cultura general","Madrid exposiciones museos agenda inauguraciones when:14d"),
 ("Cine","Madrid festivales cine ciclos proyecciones cartelera when:14d"),
]

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
   accepted=0
   for story in sorted(pool,key=lambda x:x["_sort"],reverse=True):
    if accepted>=cap:break
    if section=="cultura" and language=="es" and topic=="Cine" and not spanish_cinema_relevant(story):continue
    if section=="viral" and story["_sort"]:
     try:
      age=dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(story["_sort"])
      if age.total_seconds()>48*3600:continue
     except ValueError:pass
    if section=="cultura":
     story["region"]=culture_region(story)
    accepted+=1
    story.pop("_sort",None)
    url=story["sources"][0]["url"]
    if section=="viral" and any(marker in url.lower() for marker in ["youtube.com/watch","youtu.be/","tiktok.com/","instagram.com/reel/"]):
     story["videoUrl"]=url
    allstories.append(story)
 # Add a small, balanced selection from the preferred outlets without letting
 # any single publisher overwhelm the section.
 for section,sources in CURATED_SOURCES.items():
  for entry in sources:
   name,domain,language=entry[:3]
   topic=entry[3] if len(entry)>3 else None
   if language=="it":continue # Italian-language feeds are not part of the ES/EN UI.
   query="site:"+domain+" when:7d"
   if section=="cultura" and topic=="Cine" and language=="es":
    query+=" (España OR español OR Madrid OR Goya OR Málaga OR San Sebastián)"
   try:
    items=fetch(section,name,google_news(query,language),language,topic)
   except Exception as e:
    print("Curated source unavailable:",name,str(e)[:120])
    continue
   count=0
   for story in items:
    if section=="cultura" and topic=="Cine" and language=="es" and not spanish_cinema_relevant(story):continue
    if section=="cultura":story["region"]=culture_region(story)
    story.pop("_sort",None)
    allstories.append(story)
    count+=1
    if count>=3:break
   print("Curated",name,count)
 # Curated Madrid agenda: retain source attribution, never invent dates or availability.
 for topic,query in AGENDA_QUERIES:
  try:
   candidates=fetch("cultura","Agenda Madrid",google_news(query,"es"),"es",topic)
   for story in candidates[:8]:
    if culture_region(story)!="Madrid":continue
    story["region"]="Madrid"
    story["agendaSource"]=True
    story["cultureView"]="agenda"
    story.pop("_sort",None)
    allstories.append(story)
  except Exception as e:print("Agenda unavailable:",topic,str(e)[:120])
 for story in allstories:
  if story["section"]=="cultura":
   story["region"]=story.get("region") or culture_region(story)
   story["cultureView"]=story.get("cultureView") or culture_view(story)
   story.pop("agendaSource",None)
 # Avoid duplicate articles when a publication also appears in another feed.
 seen_links=set()
 unique=[]
 for story in allstories:
  link=story["sources"][0]["url"]
  key=link.split("?")[0].rstrip("/")
  if key in seen_links:continue
  seen_links.add(key)
  unique.append(story)
 allstories=unique
 culture=[story for story in allstories if story["section"]=="cultura"]
 other=[story for story in allstories if story["section"]!="cultura"]
 rank={"Madrid":0,"España":1,"Internacional":2}
 culture.sort(key=lambda story:story.get("publishedAt") or "",reverse=True)
 culture.sort(key=lambda story:rank.get(story.get("region"),2))
 allstories=other+culture
 if not allstories:
  raise RuntimeError("No feeds available; keeping previous edition unchanged")
 local=now.astimezone(__import__("zoneinfo").ZoneInfo("Europe/Madrid"))
 edition="THE DAILY · "+("Mañana" if hour==8 else "Noche")+" · "+local.strftime("%d/%m/%Y %H:%M")
 out={"edition":edition,"generatedAt":now.isoformat(),"mode":"rss-excerpts","stories":allstories}
 Path("editions").mkdir(exist_ok=True)
 Path("editions/latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Published",len(allstories),"stories")
if __name__=="__main__":main()
