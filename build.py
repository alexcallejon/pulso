"""Genera la web estática en site/ a partir de data/topics.json."""
import html, json, os
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlparse
from util import slugify

ROOT = Path(__file__).parent
DATA = Path(os.getenv("DATA_FILE", ROOT / "data" / "topics.json"))
OUT = Path(os.getenv("OUT_DIR", ROOT / "site"))
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")
BASE = urlparse(SITE_URL).path.rstrip("/")
ADSENSE = os.getenv("ADSENSE_ID", "")  # ej. ca-pub-1234567890123456
NAME, TAGLINE = "Pulso", "Lo que se mueve en tecnología e IA, explicado en español"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
e = html.escape

CSS = """
:root{--bg:#F3F6F8;--ink:#0F1C2E;--mut:#56677A;--line:#D3DCE4;--acc:#1747D6;--heat:#E4572E;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#0C141F;--ink:#E8EEF4;--mut:#93A3B5;--line:#223246;--acc:#7FA2FF;--heat:#FF8A5C;--card:#121D2B}}
*{box-sizing:border-box}html{scroll-padding-top:1rem}
body{margin:0;background:var(--bg);color:var(--ink);font:1.125rem/1.65 "Newsreader",Georgia,serif}
a{color:inherit}a:focus-visible{outline:3px solid var(--acc);outline-offset:3px}
.w{max-width:46rem;margin:0 auto;padding:0 1.25rem}
h1,h2,h3,.brand,nav,.meta{font-family:"Bricolage Grotesque",system-ui,sans-serif}
header.top{padding:1.5rem 0 1rem;border-bottom:1px solid var(--line)}
.brand{font-size:1.6rem;font-weight:800;text-decoration:none;letter-spacing:-.02em}
.tag{color:var(--mut);margin:.15rem 0 .9rem;font-size:1rem}
nav{display:flex;flex-wrap:wrap;gap:.4rem .5rem;font-size:.95rem}
nav a{text-decoration:none;padding:.15rem .7rem;border:1px solid var(--line);border-radius:99px}
nav a:hover{border-color:var(--acc);color:var(--acc)}
.hero{padding:2.5rem 0 2rem;border-bottom:1px solid var(--line)}
.hero h1{font-size:clamp(2rem,6vw,3.1rem);line-height:1.08;letter-spacing:-.03em;margin:.4rem 0 1rem}
.hero h1 a{text-decoration:none}.hero h1 a:hover{color:var(--acc)}
.meta{color:var(--mut);font-size:.9rem}
.list{list-style:none;margin:0;padding:0}
.list li{padding:1.1rem 0;border-bottom:1px solid var(--line)}
.list h3{margin:0 0 .3rem;font-size:1.25rem;line-height:1.25;letter-spacing:-.01em}
.list a{text-decoration:none}.list h3 a:hover{color:var(--acc)}
.bar{height:4px;background:var(--line);border-radius:2px;margin-top:.6rem;overflow:hidden}
.bar i{display:block;height:100%;background:var(--heat)}
h2.sec{font-size:1.1rem;margin:2rem 0 0;color:var(--mut);font-weight:600}
article h1{font-size:clamp(1.9rem,5vw,2.7rem);line-height:1.1;letter-spacing:-.025em;margin:2rem 0 .6rem}
article h2{font-size:1.2rem;margin:2rem 0 .4rem}
.btn{display:inline-block;margin:.5rem .6rem .5rem 0;padding:.6rem 1.1rem;border-radius:.4rem;background:var(--acc);color:#fff;text-decoration:none;font-family:"Bricolage Grotesque",system-ui,sans-serif;font-weight:600}
.btn.alt{background:none;color:var(--ink);border:1px solid var(--line)}
footer{margin:3rem 0 2rem;padding-top:1.2rem;border-top:1px solid var(--line);color:var(--mut);font-size:.9rem}
.empty{padding:3rem 0;color:var(--mut)}
"""

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">'

def fecha(iso):
    d = datetime.fromisoformat(iso)
    return f"{d.day} {MESES[d.month - 1]} {d.year}"

def url(path=""):
    return f"{BASE}/{path}" if path else f"{BASE}/"

def page(title, desc, body, path, cats, jsonld=""):
    ads = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(ADSENSE)}" crossorigin="anonymous"></script>' if ADSENSE else ""
    nav = "".join(f'<a href="{url("categoria/" + slugify(c) + "/")}">{e(c)}</a>' for c in cats)
    full_title = f"{title} | {NAME}" if path else f"{NAME}: {TAGLINE}"
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="google-site-verification" content="wTLn-ib0hh-Qyzt8CxIecS4HFY691S4ULLLzTWA4nb0" />
<title>{e(full_title)}</title><meta name="description" content="{e(desc[:155])}">
<link rel="canonical" href="{SITE_URL}/{path}"><link rel="alternate" type="application/rss+xml" title="{NAME}" href="{url('rss.xml')}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc[:155])}"><meta property="og:type" content="website">
{FONTS}<style>{CSS}</style>{ads}{jsonld}</head><body>
<div class="w"><header class="top"><a class="brand" href="{url()}">{NAME}</a><p class="tag">{TAGLINE}</p><nav aria-label="Categorías">{nav}</nav></header>
{body}
<footer>Los resúmenes se generan con IA a partir de fuentes públicas y siempre enlazan al artículo original. Actualizado varias veces al día.</footer></div></body></html>"""

def row(t, top):
    pct = max(6, round(t["score"] / top * 100))
    return f"""<li><h3><a href="{url('t/' + t['slug'] + '/')}">{e(t['titulo'])}</a></h3>
<div class="meta">{e(t['categoria'])} · {fecha(t['fecha'])} · {t['comentarios']} comentarios</div>
<div class="bar" role="img" aria-label="Interés {pct} de 100"><i style="width:{pct}%"></i></div></li>"""

def write(path, content):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, "utf-8")

def main():
    topics = json.loads(DATA.read_text("utf-8")) if DATA.exists() else []
    topics.sort(key=lambda t: t["fecha"], reverse=True)
    cats = sorted({t["categoria"] for t in topics})
    if OUT.exists():
        import shutil; shutil.rmtree(OUT)
    top = max((t["score"] for t in topics), default=1)

    # Portada
    if topics:
        limit = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        recent = [t for t in topics if t["fecha"] >= limit] or topics
        hero = max(recent, key=lambda t: t["score"])
        rest = [t for t in topics if t is not hero][:40]
        body = f"""<section class="hero"><div class="meta">Lo más comentado ahora · {e(hero['categoria'])}</div>
<h1><a href="{url('t/' + hero['slug'] + '/')}">{e(hero['titulo'])}</a></h1><p>{e(hero['resumen'])}</p></section>
<h2 class="sec">Últimas historias</h2><ul class="list">{''.join(row(t, top) for t in rest)}</ul>"""
    else:
        body = '<p class="empty">Aún no hay historias. La primera actualización automática las publicará.</p>'
    write("index.html", page(NAME, TAGLINE, body, "", cats))

    # Temas
    for t in topics:
        rel = [r for r in topics if r["categoria"] == t["categoria"] and r is not t][:4]
        related = f'<h2>Más de {e(t["categoria"])}</h2><ul class="list">{"".join(row(r, top) for r in rel)}</ul>' if rel else ""
        ld = json.dumps({"@context": "https://schema.org", "@type": "NewsArticle", "headline": t["titulo"],
                         "datePublished": t["fecha"], "description": t["resumen"],
                         "mainEntityOfPage": f"{SITE_URL}/t/{t['slug']}/", "publisher": {"@type": "Organization", "name": NAME}}, ensure_ascii=False)
        body = f"""<article><h1>{e(t['titulo'])}</h1>
<div class="meta">{e(t['categoria'])} · {fecha(t['fecha'])} · Fuente: {e(t['fuente_dominio'])}</div>
<p>{e(t['resumen'])}</p><h2>Por qué importa</h2><p>{e(t['por_que_importa'])}</p>
<h2>Claves</h2><ul>{''.join(f'<li>{e(p)}</li>' for p in t['puntos_clave'])}</ul>
<p><a class="btn" href="{e(t['fuente_url'])}" rel="noopener nofollow">Leer el original en {e(t['fuente_dominio'])}</a>
<a class="btn alt" href="{e(t['hn_url'])}" rel="noopener nofollow">Ver el debate</a></p>{related}</article>"""
        write(f"t/{t['slug']}/index.html", page(t["titulo"], t["resumen"], body, f"t/{t['slug']}/", cats,
                                                  f'<script type="application/ld+json">{ld}</script>'))

    # Categorías
    for c in cats:
        items = [t for t in topics if t["categoria"] == c]
        body = f'<h2 class="sec">{e(c)}</h2><ul class="list">{"".join(row(t, top) for t in items[:60])}</ul>'
        write(f"categoria/{slugify(c)}/index.html",
              page(f"{c}: últimas noticias", f"Noticias y resúmenes de {c} en tecnología, en español.", body, f"categoria/{slugify(c)}/", cats))

    # SEO y feed
    urls = [""] + [f"t/{t['slug']}/" for t in topics] + [f"categoria/{slugify(c)}/" for c in cats]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{SITE_URL}/{u}</loc></url>" for u in urls) + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    items = "".join(f"<item><title>{e(t['titulo'])}</title><link>{SITE_URL}/t/{t['slug']}/</link><guid>{SITE_URL}/t/{t['slug']}/</guid>"
                    f"<pubDate>{format_datetime(datetime.fromisoformat(t['fecha']))}</pubDate><description>{e(t['resumen'])}</description></item>" for t in topics[:30])
    write("rss.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{NAME}</title><link>{SITE_URL}/</link><description>{e(TAGLINE)}</description>{items}</channel></rss>')
    write("404.html", page("No encontrada", "Página no encontrada", f'<p class="empty">Esta página no existe. <a href="{url()}">Volver a la portada</a>.</p>', "404.html", cats))
    print(f"Web generada: {len(topics)} temas, {len(cats)} categorías → {OUT}")

if __name__ == "__main__":
    main()
