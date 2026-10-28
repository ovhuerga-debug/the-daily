#!/usr/bin/env python3
"""Enrich the RSS edition from source text with optional OpenAI API key.
Never invent details to reach a sentence count. Cache previously enriched stories.
"""
import json, os, re, time, urllib.request
from pathlib import Path

PATH=Path("editions/latest.json")
def clean(s):
 return re.sub(r"\s+"," ",re.sub(r"<[^>]*>"," ",s or "")).strip()
def run():
 data=json.loads(PATH.read_text(encoding="utf-8"))
 key=os.environ.get("OPENAI_API_KEY")
 if not key:
  print("No OPENAI_API_KEY: keeping RSS excerpts; translations pending.")
  for item in data["stories"]:item["summaryStatus"]="excerpt"
  PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  return
 try:
  import trafilatura
 except ImportError:
  trafilatura=None
 old={}
 try:
  previous=json.loads(Path("editions/previous.json").read_text(encoding="utf-8"))
  old={item["id"]:item for item in previous.get("stories",[]) if item.get("id")}
 except (OSError,ValueError):pass
 max_count=int(os.environ.get("MAX_ENRICHED_PER_RUN","60"))
 count=0
 for item in data["stories"]:
  cached=old.get(item["id"],{})
  if cached.get("summaryStatus")=="enriched" and (item.get("language")!="en" or cached.get("translationEs")):
   for field in ("summary","summaryStatus","translationEs"):
    if field in cached:item[field]=cached[field]
   continue
  if count>=max_count:
   item["summaryStatus"]="excerpt"
   continue
  text=""
  if trafilatura:
   try:
    source=trafilatura.fetch_url(item["sources"][0]["url"])
    if source:text=(trafilatura.extract(source,include_comments=False,include_tables=False) or "")[:8500]
   except Exception as exc:print("Article retrieval:",str(exc)[:120])
  if len(text)<250:text=item["summary"]
  system=("You are a careful bilingual news editor. Rely ONLY on the supplied text, not general knowledge. "
          "Paraphrase in the source language. Aim for at least five substantive factual sentences ONLY "
          "when the source contains enough distinct verifiable facts. Otherwise write fewer sentences, "
          "never inventing or padding. If the source language is English, provide a faithful Spanish "
          "translation of your paraphrase. If Spanish, translationEs must be empty. "
          "Return JSON with summary (string), translationEs (string), sufficientEvidence (boolean).")
  payload={"model":os.environ.get("OPENAI_MODEL","gpt-4.1-mini"),"temperature":0.1,
           "max_tokens":800,"response_format":{"type":"json_object"},
           "messages":[{"role":"system","content":system},{"role":"user","content":json.dumps({
            "title":item["title"],"language":item.get("language") or "es",
            "sourceText":text},ensure_ascii=False)}]}
  try:
   request=urllib.request.Request("https://api.openai.com/v1/chat/completions",
      data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,
      "Content-Type":"application/json"},method="POST")
   with urllib.request.urlopen(request,timeout=45) as response:result=json.load(response)
   enriched=json.loads(result["choices"][0]["message"]["content"])
   if enriched.get("summary"):
    item["summary"]=clean(enriched["summary"])
    item["summaryStatus"]="enriched" if enriched.get("sufficientEvidence") else "excerpt"
   if item.get("language")=="en" and enriched.get("translationEs"):
    item["translationEs"]=clean(enriched["translationEs"])
   count+=1
  except Exception as exc:
   item["summaryStatus"]="excerpt"
   print("Enrichment failed:",str(exc)[:160])
  time.sleep(.1)
 PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Enriched stories:",count)
if __name__=="__main__":run()
