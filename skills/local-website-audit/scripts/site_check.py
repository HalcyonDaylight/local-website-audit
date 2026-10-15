#!/usr/bin/env python3
"""Collect objective facts about a local business website (stdlib only).

Usage: python3 site_check.py https://example.com [--max-links 40] > facts.json
Checks: HTTPS/SSL cert, redirects, response time & page weight, viewport/mobile
hints, title/meta, LocalBusiness schema (JSON-LD), phone/address/hours found on
page, tap-to-call links, calls to action, copyright year, image weight, and
internal/external broken links. Prints JSON; the agent interprets it.
"""
import sys, json, re, ssl, socket, time, datetime, argparse
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser

UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129 Mobile Safari/537.36 LocalWebsiteAudit/1.0"

class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.title=""; s._t=False; s.meta={}; s.links=[]; s.imgs=[]; s.scripts=[]; s._ld=False; s.ld=[]; s.text=[]; s._skip=0; s.h1=[]; s._h1=False; s.buttons=[]; s._a=None
    def handle_starttag(s,t,a):
        a=dict(a)
        if t=="title" and not s.title: s._t=True
        if t in ("svg","body"): s._t=False
        if t=="meta":
            k=(a.get("name") or a.get("property") or "").lower()
            if k: s.meta[k]=a.get("content","")
        if t=="a" and a.get("href"): s.links.append(a["href"]); s._a=[a["href"],""]
        if t=="img": s.imgs.append(a.get("src") or a.get("data-src") or "")
        if t=="script":
            if (a.get("type") or "").lower()=="application/ld+json": s._ld=True; s.ld.append("")
            else: s._skip+=1
        if t=="style": s._skip+=1
        if t=="h1": s._h1=True; s.h1.append("")
    def handle_endtag(s,t):
        if t=="title": s._t=False
        if t=="script":
            if s._ld: s._ld=False
            elif s._skip: s._skip-=1
        if t=="style" and s._skip: s._skip-=1
        if t=="h1": s._h1=False
        if t=="a" and s._a: s.buttons.append(tuple(s._a)); s._a=None
    def handle_data(s,d):
        if s._t: s.title+=d
        if s._ld: s.ld[-1]+=d; return
        if s._skip: return
        if s._h1: s.h1[-1]+=d
        if s._a: s._a[1]+=d
        if d.strip(): s.text.append(d.strip())

def fetch(url, method="GET", timeout=20):
    req=urllib.request.Request(url, method=method, headers={"User-Agent":UA,"Accept":"text/html,*/*"})
    t=time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body=r.read() if method=="GET" else b""
        return r.status, r.geturl(), dict(r.headers), body, time.time()-t

def rendered_dom(url):
    import shutil, subprocess
    ch=next((shutil.which(c) for c in ("google-chrome","chromium","chromium-browser","google-chrome-stable") if shutil.which(c)),None)
    if not ch: return None
    try:
        r=subprocess.run([ch,"--headless=new","--no-sandbox","--disable-gpu","--virtual-time-budget=10000","--dump-dom",url],
                         capture_output=True,timeout=60)
        return r.stdout.decode("utf-8","replace") or None
    except Exception: return None

def cert(host):
    try:
        ctx=ssl.create_default_context()
        with socket.create_connection((host,443),timeout=10) as sock:
            with ctx.wrap_socket(sock,server_hostname=host) as ss:
                c=ss.getpeercert()
        exp=datetime.datetime.strptime(c["notAfter"],"%b %d %H:%M:%S %Y %Z")
        return {"valid":True,"expires":exp.date().isoformat(),"days_left":(exp-datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)).days,
                "issuer":dict(x[0] for x in c.get("issuer",[])).get("organizationName")}
    except Exception as e:
        return {"valid":False,"error":str(e)[:200]}

def status(url):
    for m in ("HEAD","GET"):
        try: return fetch(url,m,timeout=12)[0]
        except urllib.error.HTTPError as e:
            if m=="HEAD" and e.code in (403,405,501): continue
            return e.code
        except Exception as e:
            if m=="HEAD": continue
            return "error: "+str(e)[:80]

PHONE=re.compile(r"(?:\+?1[\s.-]?)?\(?\b(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})\b")
ADDR=re.compile(r"\b\d{2,6}\s+[A-Z0-9][\w .'-]{2,40}\b(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Pkwy|Parkway|Hwy|Highway|Ct|Court|Pl|Place|Trl|Cir|Ter)\b\.?[^\n]{0,60}",re.I)
HOURS=re.compile(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?\s*(?:[-–to]+\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?)?\s*:?\s*\d{1,2}(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)?\s*[-–to]+\s*\d{1,2}(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)?",re.I)
CTA=re.compile(r"\b(call|book|schedule|order|reserve|quote|estimate|contact|get started|request|appointment|menu|directions|buy|shop)\b",re.I)

def main():
    ap=argparse.ArgumentParser(description="Collect public facts about a business website as JSON."); ap.add_argument("url"); ap.add_argument("--max-links",type=int,default=40); a=ap.parse_args()
    url=a.url if "://" in a.url else "https://"+a.url
    out={"input":url,"checked_at":datetime.datetime.now().astimezone().isoformat(timespec="minutes")}
    host=urlparse(url).hostname
    out["ssl"]=cert(host)
    try:
        st,final,hd,body,secs=fetch(url)
    except urllib.error.HTTPError as e:
        out["fetch_error"]=f"HTTP {e.code} {e.reason}"; out["hint"]="403/429/503 often means bot protection; check the site in a real browser"
        print(json.dumps(out,indent=2)); sys.exit(2)
    except Exception as e:
        out["fetch_error"]=str(e)[:300]
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            out["hint"]="SSL certificate problem: browsers will show a 'Not secure' warning. This is a top finding."
            print(json.dumps(out,indent=2)); sys.exit(2)
        out["hint"]="Site unreachable (DNS, timeout or TLS). Confirm the URL; report 'site down' only after a browser check."
        print(json.dumps(out,indent=2)); sys.exit(2)
    ctype=hd.get("Content-Type","")
    if "html" not in ctype.lower(): out["warning"]=f"Not an HTML page (Content-Type: {ctype})"
    if re.search(rb"cf-challenge|challenge-platform|Just a moment|One more step|captcha",body[:20000],re.I):
        out["bot_challenge_suspected"]=True
    out.update(status=st,final_url=final,response_seconds=round(secs,2),html_kb=round(len(body)/1024,1),
               server=hd.get("Server"),https=final.startswith("https://"))
    try:
        st2,f2,*_=fetch("http://"+host,timeout=12); out["http_redirects_to_https"]=f2.startswith("https://")
    except Exception as e: out["http_redirects_to_https"]=f"unknown ({str(e)[:60]})"
    cs=re.search(r"charset=([\w-]+)",ctype); 
    try: html=body.decode(cs.group(1) if cs else "utf-8","replace")
    except LookupError: html=body.decode("utf-8","replace")
    p=P()
    try: p.feed(html)
    except Exception as e: out["parse_warning"]=str(e)[:120]
    thin=len(" ".join(p.text).split())<60 or re.search(r"one moment, please|just a moment|checking your browser",p.title,re.I)
    if thin:
        dom=rendered_dom(final)
        if dom and len(dom)>len(html):
            out["rendered_with_browser"]=True
            out["note_raw_html"]=f"Plain fetch returned a near-empty or challenge page (title: {p.title.strip()!r}); facts below come from a headless-browser render."
            html=dom; p=P(); p.feed(html)
    text=" ".join(p.text)
    vp=p.meta.get("viewport","")
    out["mobile"]={"viewport_meta":vp or None,"responsive_hint":"width=device-width" in vp,
                   "media_queries_inline":html.count("@media"),"tap_to_call_links":sorted({l for l in p.links if l.lower().startswith("tel:")})}
    out["seo"]={"title":p.title.strip(),"title_len":len(p.title.strip()),"meta_description":p.meta.get("description"),
                "h1":[h.strip() for h in p.h1 if h.strip()][:3],"og_image":p.meta.get("og:image"),
                "robots":p.meta.get("robots")}
    for path in ("/robots.txt","/sitemap.xml"):
        out["seo"][path]=status(urljoin(final,path))
    types=[]; ld_nap=[]
    for blob in p.ld:
        try:
            d=json.loads(blob); items=d if isinstance(d,list) else d.get("@graph",[d]) if isinstance(d,dict) else []
            for it in items:
                if not isinstance(it,dict): continue
                t=it.get("@type"); types+= t if isinstance(t,list) else [t]
                if any(k in it for k in ("telephone","address","openingHours","openingHoursSpecification")):
                    ld_nap.append({k:it.get(k) for k in ("@type","name","telephone","address","openingHours","openingHoursSpecification","url") if it.get(k)})
        except Exception: types.append("unparseable JSON-LD")
    out["schema"]={"jsonld_types":types,"nap_in_schema":ld_nap[:3]}
    phones=sorted({f"({m[0]}) {m[1]}-{m[2]}" for m in PHONE.findall(text)})
    out["nap_on_page"]={"phones":phones[:8],"addresses":list(dict.fromkeys(m.group(0).strip() for m in ADDR.finditer(text)))[:5],
                        "hours_snippets":list(dict.fromkeys(m.group(0) for m in HOURS.finditer(text)))[:8],
                        "mentions_pdf_menu":any(l.lower().endswith(".pdf") for l in p.links)}
    yrs=[int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})",html,re.I)]
    out["copyright_year"]=max(yrs) if yrs else None
    ctas=[(h,t.strip()) for h,t in p.buttons if t.strip() and CTA.search(t)]
    out["calls_to_action"]=[t for _,t in ctas][:12]
    out["images"]={"count":len(p.imgs),"sample_sizes_kb":{}}
    for src in [i for i in p.imgs if i and not i.startswith("data:")][:6]:
        u=urljoin(final,src)
        try:
            r=urllib.request.urlopen(urllib.request.Request(u,method="HEAD",headers={"User-Agent":UA}),timeout=10)
            cl=r.headers.get("Content-Length"); out["images"]["sample_sizes_kb"][u[-80:]]=round(int(cl)/1024) if cl else None
        except Exception: pass
    seen=[]
    for l in p.links:
        if l.strip().lower().startswith(("#","mailto:","tel:","javascript:","sms:","data:")): continue
        try: u=urljoin(final,l.strip()).split("#")[0]
        except ValueError: continue
        if u not in seen and u.startswith("http"): seen.append(u)
    with ThreadPoolExecutor(8) as ex: sts=list(ex.map(status,seen[:a.max_links]))
    bad=[]
    for u,s in zip(seen,sts):
        if isinstance(s,int) and s<400: continue
        if not isinstance(s,int) and u.startswith("http://"):
            s2=status("https://"+u[7:])
            if isinstance(s2,int) and s2<400: continue
        social=re.search(r"facebook|instagram|linkedin|x\.com|twitter|yelp|tiktok",u)
        kind=("likely broken" if isinstance(s,int) and s in (404,410) else
              "blocked by platform (bots), check in browser" if social or s in (400,401,403,429,999) else
              "unreachable from checker, verify in browser")
        bad.append({"url":u,"status":s,"verdict":kind})
    out["links"]={"checked":min(len(seen),a.max_links),"found":len(seen),"broken":bad,
                  "note":"timeouts/403s can be bot-blocking, not real breakage; recheck in a browser",
                  "social":sorted({u for u in seen if re.search(r"facebook|instagram|yelp|google\.com/maps|g\.page|tiktok|linkedin|x\.com|twitter",u)})}
    out["word_count"]=len(text.split())
    print(json.dumps(out,indent=2,default=str))

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: sys.exit(130)
