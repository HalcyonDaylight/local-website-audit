#!/usr/bin/env python3
"""Render the audit Markdown into a one-page Letter PDF (stdlib + headless Chrome/Chromium).

Usage: python3 render_report.py report.md report.pdf
Images: consecutive `![caption](path)` lines become a row of screenshots.
The plugin logo (assets/logo.svg) is added to the title bar automatically.
Supports the subset of Markdown the skill's template uses: #/## headings, paragraphs,
**bold**, _italic_, `- ` and `1. ` lists, pipe tables, and `---`. Shrinks to fit one page.
"""
import sys, re, html, os, shutil, subprocess, tempfile
FOOT="Free audit format by Halcyon Days · halcyondaylight.com"
CSS="""@page{size:Letter;margin:.4in .45in}*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:'Helvetica Neue',Arial,sans-serif;color:#22302a;font-size:9pt;line-height:1.32;margin:0;zoom:ZOOM}
.hdr{display:flex;align-items:center;gap:10px;background:#2f5d4b;color:#f8f1e4;padding:8px 12px;border-radius:5px;margin-bottom:5px}
.hdr img{width:40px;height:40px;border-radius:50%;background:#f8f1e4}
.hdr h1{margin:0;font-size:15pt;background:none;padding:0}
h1{background:#2f5d4b;color:#f8f1e4;font-size:15pt;margin:0 0 4px;padding:9px 12px;border-radius:4px}
.shots{display:flex;gap:8px;align-items:flex-start;margin:4px 0}.shots figure{margin:0;text-align:center;font-size:7pt;color:#5b6a62}
.shots{justify-content:center;gap:24px}.shots img{max-height:200px;border:1px solid #d6dccf;border-radius:3px}
td:first-child{white-space:nowrap}table tr:nth-child(even) td{background:#fbf8f1}
h2{color:#2f5d4b;font-size:10pt;margin:8px 0 3px;border-bottom:1.5px solid #c9a24a;padding-bottom:1px}
table{border-collapse:collapse;width:100%;font-size:8.4pt}td,th{border:1px solid #d6dccf;padding:2px 6px;text-align:left;vertical-align:top}
th{background:#f3efe4}ul,ol{margin:2px 0 2px 16px;padding:0}li{margin:0 0 2px}p{margin:3px 0}
.foot{margin-top:10px;background:#f8f1e4;border-top:2px solid #2f5d4b;padding:5px;font-size:8pt;color:#2f5d4b;text-align:center;font-weight:600}\n.note{color:#5b6a62}
hr{border:0;border-top:1px solid #d6dccf;margin:6px 0}"""
def inline(s):
    s=html.escape(s)
    s=re.sub(r"\*\*(.+?)\*\*",r"<b>\1</b>",s); s=re.sub(r"(?<!\w)_(.+?)_(?!\w)",r"<i>\1</i>",s)
    s=re.sub(r"`(.+?)`",r"<code>\1</code>",s)
    s=re.sub(r"\[(.+?)\]\((https?://[^)]+)\)",r'<a href="\2">\1</a>',s); return s
def md2html(md):
    md=md.split("\n### Notes for")[0]  # never print private notes
    out=[]; lines=md.splitlines(); i=0; lst=None
    def close():
        nonlocal lst
        if lst: out.append(f"</{lst}>"); lst=None
    while i<len(lines):
        l=lines[i].rstrip()
        if l.startswith("|") and i+1<len(lines) and re.match(r"^\|[\s:|-]+\|$",lines[i+1].strip()):
            close(); hdr=[c.strip() for c in l.strip("|").split("|")]; i+=2
            rows=[]
            while i<len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i+=1
            out.append("<table><tr>"+"".join(f"<th>{inline(c)}</th>" for c in hdr)+"</tr>"+"".join("<tr>"+"".join(f"<td>{inline(c)}</td>" for c in r)+"</tr>" for r in rows)+"</table>"); continue
        if re.match(r"^!\[",l.strip()):
            close(); figs=[]
            while i<len(lines) and re.match(r"^!\[",lines[i].strip()):
                m2=re.match(r"^!\[(.*?)\]\((.+?)\)",lines[i].strip())
                if m2: figs.append((m2.group(1),m2.group(2)))
                i+=1
            out.append('<div class="shots">'+"".join(f'<figure><img src="{html.escape(img_src(p))}"><figcaption>{inline(a)}</figcaption></figure>' for a,p in figs)+"</div>"); continue
        m=re.match(r"^(#{1,3})\s+(.*)",l)
        if m and m.group(1)=="#" and LOGO:
            close(); out.append(f'<div class="hdr"><img src="{LOGO}"><h1>{inline(m.group(2))}</h1></div>')
        elif m: close(); n=len(m.group(1)); out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif re.match(r"^\s*[-*]\s+",l):
            if lst!="ul": close(); out.append("<ul>"); lst="ul"
            out.append("<li>"+inline(re.sub(r"^\s*[-*]\s+","",l))+"</li>")
        elif re.match(r"^\s*\d+\.\s+",l):
            if lst!="ol": close(); out.append("<ol>"); lst="ol"
            out.append("<li>"+inline(re.sub(r"^\s*\d+\.\s+","",l))+"</li>")
        elif l.strip()=="---": close(); out.append("<hr>")
        elif l.strip()==FOOT: close(); out.append(f'<div class="foot">{html.escape(FOOT)}</div>')
        elif l.strip(): close(); out.append("<p>"+inline(l)+"</p>")
        else: close()
        i+=1
    close(); return "\n".join(out)
HERE=os.path.dirname(os.path.abspath(__file__))
_logo=os.path.normpath(os.path.join(HERE,"..","..","..","assets","logo.svg"))
LOGO="file://"+_logo if os.path.exists(_logo) else None
BASE="."
def img_src(p):
    if re.match(r"^(https?|file|data):",p): return p
    return "file://"+os.path.abspath(os.path.join(BASE,p))
def chrome():
    for c in ("google-chrome","chromium","chromium-browser","google-chrome-stable"):
        if shutil.which(c): return c
    sys.exit("Need Chrome/Chromium for PDF output (Markdown report is still valid).")
def main():
    if len(sys.argv)!=3: sys.exit("usage: render_report.py report.md report.pdf")
    global BASE
    src,dst=sys.argv[1],sys.argv[2]; BASE=os.path.dirname(os.path.abspath(src)); body=md2html(open(src,encoding="utf-8").read())
    if FOOT not in body: body+=f'<div class="foot">{html.escape(FOOT)}</div>'
    hp=os.path.join(tempfile.mkdtemp(),"r.html"); dst=os.path.abspath(dst)
    for z in (1.0,.95,.9,.85,.8,.75,.7):
        open(hp,"w").write(f"<!doctype html><meta charset=utf-8><style>{CSS.replace('ZOOM',str(z))}</style>{body}")
        subprocess.run([chrome(),"--headless=new","--no-sandbox","--disable-gpu","--no-pdf-header-footer","--allow-file-access-from-files","--print-to-pdf="+dst,"file://"+hp],capture_output=True,timeout=120)
        try:
            pages=int(re.search(r"Pages:\s+(\d+)",subprocess.run(["pdfinfo",dst],capture_output=True,text=True).stdout).group(1))
        except Exception: pages=1
        if pages==1: break
    print(f"{dst} ({pages} page{'s' if pages>1 else ''}, zoom {z})")
if __name__=="__main__": main()
