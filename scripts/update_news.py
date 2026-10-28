#!/usr/bin/env python3
"""THE DAILY: RSS headlines with attributed source excerpts; no AI summaries."""
import datetime as dt
import email.utils
import html
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEEDS = {
 "espana":[("RTVE","https://www.rtve.es/rss/portada.xml"),("El País","https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),("Europa Press","https://www.europapress.es/rss/rss.aspx")],
 "mundo":[("BBC World","https://feeds.bbci.co.uk/news/world/rss.xml"),("The Guardian World","https://www.theguardian.com/world/rss"),("ABC Australia","https://www.abc.net.au/news/feed/51120/rss.xml"),("DW","https://rss.dw.com/rdf/rss-en-world"),("NPR World","https://feeds.npr.org/1004/rss.xml")],
 "cultura":[("The Guardian Culture","https://www.theguardian.com/culture/rss"),("The Guardian Books","https://www.theguardian.com/books/rss"),("The Guardian Film","https://www.theguardian.com/film/rss"),("The Guardian Stage","https://www.theguardian.com/stage/rss")],
 "television":[("Variety TV","https://variety.com/v/tv/feed/"),("Deadline TV","https://deadline.com/category/tv/feed/"),("The Guardian Television","https://www.theguardian.com/tv-and-radio/rss")]
}
LIMITS={"espana":20,"mundo":30,"cultura":40,"television":30}
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
def fetch(section,source,url):
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
  if not title or not link.startswith("https://") and not link.startswith("http://"):continue
  excerpt=clean(child(item,["description","a:summary","a:content","{http://purl.org/rss/1.0/modules/content/}encoded"]))
  published=dateparse(child(item,["pubDate","a:updated","a:published","{http://purl.org/dc/elements/1.1/}date"]))
  result.append({"id":section+"|"+link,"section":section,"category":source,"title":title[:250],
   "summary":(excerpt[:360].rstrip()+"…" if len(excerpt)>360 else excerpt) or "Lee la noticia completa en la fuente original.",
   "publishedAt":published[:16].replace("T"," ")+" UTC" if published else "",
   "_sort":published,"sources":[{"name":source,"url":link}]})
 return result
def main():
 now=dt.datetime.now(dt.timezone.utc)
 hour=int(os.environ.get("EDITION_HOUR", "8"))
 allstories=[]
 for section,feeds in FEEDS.items():
  pool=[]
  for source,url in feeds:
   try:
    got=fetch(section,source,url)
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
 if not allstories:
  raise RuntimeError("No feeds available; keeping previous edition unchanged")
 local=now.astimezone(__import__("zoneinfo").ZoneInfo("Europe/Madrid"))
 edition="THE DAILY · "+("Mañana" if hour==8 else "Noche")+" · "+local.strftime("%d/%m/%Y %H:%M")
 out={"edition":edition,"generatedAt":now.isoformat(),"mode":"rss-excerpts","stories":allstories}
 Path("editions").mkdir(exist_ok=True)
 Path("editions/latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Published",len(allstories),"stories")
if __name__=="__main__":main()
