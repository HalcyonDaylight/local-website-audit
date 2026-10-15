#!/usr/bin/env python3
"""Optional: phone/desktop screenshots + local Lighthouse mobile speed score.

Usage: python3 capture.py https://example.com --out ./shots
Needs Chrome/Chromium; Lighthouse via `npx lighthouse` (Node 18+) if available,
falling back to Google's PageSpeed Insights API (free, rate-limited; set PSI_KEY to use a key).
Note: phone.png is a 390px-wide window, not true device emulation (a fixed-width page looks cut off there,
while a real phone zooms it out). phone-emulated.jpg comes from Lighthouse's mobile emulation and is the truer view.
Prints JSON with screenshot paths and speed metrics. Every step degrades gracefully.
"""
import sys, os, json, shutil, subprocess, argparse, urllib.request, urllib.parse, tempfile
def chrome():
    for c in ("google-chrome","chromium","chromium-browser","google-chrome-stable"):
        if shutil.which(c): return shutil.which(c)
def shot(url,path,w,h,ch):
    try:
        subprocess.run([ch,"--headless=new","--no-sandbox","--disable-gpu","--hide-scrollbars",f"--window-size={w},{h}",
            "--virtual-time-budget=8000","--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148" if w<600 else "--user-agent=Mozilla/5.0",
            "--screenshot="+path,url],capture_output=True,timeout=60)
        return path if os.path.exists(path) and os.path.getsize(path)>5000 else None
    except Exception: return None
SHOTDIR="."
def summarize(lh,source):
    a=lh["audits"]
    try:
        import base64
        data=a["final-screenshot"]["details"]["data"].split(",",1)[1]
        fp=os.path.join(SHOTDIR,"phone-emulated.jpg"); open(fp,"wb").write(base64.b64decode(data))
    except Exception: fp=None
    g=lambda k:a.get(k,{}).get("displayValue")
    return {"source":source,"performance_score":round((lh["categories"]["performance"]["score"] or 0)*100),
            "first_contentful_paint":g("first-contentful-paint"),"largest_contentful_paint":g("largest-contentful-paint"),
            "total_blocking_time":g("total-blocking-time"),"cumulative_layout_shift":g("cumulative-layout-shift"),
            "page_weight":g("total-byte-weight"),"mobile_viewport_ok":a.get("viewport",{}).get("score")==1,
            "phone_emulated_screenshot":fp}
def lighthouse(url,ch):
    if not shutil.which("npx"): return None,"npx not found"
    out=os.path.join(tempfile.mkdtemp(),"lh.json"); env=dict(os.environ,CHROME_PATH=ch or "")
    try:
        subprocess.run(["npx","-y","lighthouse@12",url,"--form-factor=mobile","--only-categories=performance",
            "--output=json","--output-path="+out,"--quiet","--chrome-flags=--headless=new --no-sandbox"],capture_output=True,timeout=240,env=env)
        return summarize(json.load(open(out)),"Lighthouse 12 (local, mobile, simulated throttling)"),None
    except Exception as e: return None,f"lighthouse failed: {str(e)[:120]}"
def psi(url):
    q={"url":url,"strategy":"mobile","category":"performance"}
    if os.environ.get("PSI_KEY"): q["key"]=os.environ["PSI_KEY"]
    try:
        d=json.load(urllib.request.urlopen("https://www.googleapis.com/pagespeedonline/v5/runPagespeed?"+urllib.parse.urlencode(q),timeout=120))
        return summarize(d["lighthouseResult"],"PageSpeed Insights API (mobile)"),None
    except Exception as e: return None,f"PageSpeed API failed: {str(e)[:120]}"
def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]); ap.add_argument("url"); ap.add_argument("--out",default=".")
    ap.add_argument("--no-speed",action="store_true"); a=ap.parse_args()
    url=a.url if "://" in a.url else "https://"+a.url; os.makedirs(a.out,exist_ok=True); global SHOTDIR; SHOTDIR=a.out; ch=chrome(); r={"url":url,"errors":[]}
    if not ch: r["errors"].append("Chrome/Chromium not found: no screenshots or local Lighthouse")
    else:
        r["phone_width_screenshot"]=shot(url,os.path.join(a.out,"phone.png"),390,844,ch)
        r["desktop_screenshot"]=shot(url,os.path.join(a.out,"desktop.png"),1366,900,ch)
    if not a.no_speed:
        sp,err=lighthouse(url,ch) if ch else (None,"no chrome")
        if not sp:
            r["errors"].append(err); sp,err=psi(url)
            if not sp: r["errors"].append(err)
        r["speed"]=sp
    print(json.dumps(r,indent=2))
if __name__=="__main__": main()
