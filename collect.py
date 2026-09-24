"""Recoge temas en tendencia (Hacker News), los resume con Claude y los guarda en data/topics.json."""
import html, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from util import slugify

ROOT = Path(__file__).parent
DATA = Path(os.getenv("DATA_FILE", ROOT / "data" / "topics.json"))
HN = "https://hacker-news.firebaseio.com/v0"
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
MAX_NEW = int(os.getenv("MAX_NEW", "6"))        # temas nuevos por ejecución
MIN_SCORE = int(os.getenv("MIN_SCORE", "150"))  # puntos mínimos en HN
MIN_COMMENTS = int(os.getenv("MIN_COMMENTS", "30"))
MIN_ARTICLE_CHARS = 700                          # sin texto suficiente no se publica
KEEP = 500                                       # máximo de temas guardados
CATEGORIAS = ["IA", "Programación", "Seguridad", "Hardware", "Ciencia", "Negocio", "Otros"]
UA = {"User-Agent": "PulsoBot/1.0"}

def get_json(url):
    r = requests.get(url, timeout=15, headers=UA)
    r.raise_for_status()
    return r.json()

def clean_text(raw):
    raw = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()

def article_text(url):
    try:
        r = requests.get(url, timeout=12, headers=UA)
        if "text/html" not in r.headers.get("content-type", ""):
            return ""
        return clean_text(r.text)[:4000]
    except Exception:
        return ""

def top_comments(item, n=4):
    out = []
    for cid in (item.get("kids") or [])[: n * 2]:
        try:
            c = get_json(f"{HN}/item/{cid}.json")
        except Exception:
            continue
        if c and c.get("text") and not c.get("deleted") and not c.get("dead"):
            out.append(clean_text(c["text"])[:500])
        if len(out) == n:
            break
    return out

def candidates(seen):
    ids = get_json(f"{HN}/topstories.json")[:60]
    items = []
    for i in ids:
        if str(i) in seen:
            continue
        it = get_json(f"{HN}/item/{i}.json")
        if not it or it.get("type") != "story" or not it.get("url"):
            continue
        if it.get("score", 0) >= MIN_SCORE and it.get("descendants", 0) >= MIN_COMMENTS:
            items.append(it)
    return sorted(items, key=lambda x: x["score"], reverse=True)

PROMPT = """Eres redactor de un medio tecnológico en español. Resume la noticia usando SOLO la información del texto y los comentarios que te doy.
Reglas: no inventes datos, cifras ni citas; no copies frases del original (reformula); tono claro y neutral.
Si el texto no permite resumir con fiabilidad, responde {"skip": true}.
Responde SOLO con JSON válido con estas claves:
titulo (título en español, máx. 90 caracteres, sin clickbait),
resumen (3-4 frases),
por_que_importa (2 frases),
puntos_clave (lista de 3 frases cortas),
categoria (una de: %s).

TÍTULO ORIGINAL: %s
TEXTO DEL ARTÍCULO: %s
COMENTARIOS DESTACADOS: %s"""

def summarize(client, item, text, comments):
    msg = PROMPT % (", ".join(CATEGORIAS), item["title"], text, " | ".join(comments) or "(ninguno)")
    r = client.messages.create(model=MODEL, max_tokens=900, messages=[{"role": "user", "content": msg}])
    raw = re.sub(r"```json|```", "", r.content[0].text).strip()
    d = json.loads(raw)
    if d.get("skip"):
        return None
    need = ["titulo", "resumen", "por_que_importa", "puntos_clave", "categoria"]
    if not all(k in d and d[k] for k in need) or len(d["puntos_clave"]) < 2:
        return None
    if d["categoria"] not in CATEGORIAS:
        d["categoria"] = "Otros"
    return d

def make_topic(item, d):
    dom = urlparse(item["url"]).netloc.removeprefix("www.")
    return {
        "id": str(item["id"]),
        "slug": f"{slugify(d['titulo'])}-{item['id']}",
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "titulo": d["titulo"], "resumen": d["resumen"],
        "por_que_importa": d["por_que_importa"], "puntos_clave": d["puntos_clave"][:4],
        "categoria": d["categoria"], "fuente_url": item["url"], "fuente_dominio": dom,
        "hn_url": f"https://news.ycombinator.com/item?id={item['id']}",
        "score": item.get("score", 0), "comentarios": item.get("descendants", 0),
    }

def demo():
    demo_items = [
        ("Un nuevo modelo abierto iguala a los grandes en programación", "IA", 812),
        ("Fallo crítico en una librería muy usada obliga a actualizar", "Seguridad", 640),
        ("Un chip barato consigue ejecutar modelos locales en el móvil", "Hardware", 455),
        ("Por qué cada vez más empresas vuelven a alojar sus propios servidores", "Negocio", 390),
    ]
    out = []
    for n, (t, c, s) in enumerate(demo_items, 1):
        out.append({"id": f"d{n}", "slug": f"{slugify(t)}-d{n}", "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "titulo": t, "resumen": "Texto de ejemplo para probar la maquetación. " * 3,
                    "por_que_importa": "Esto es solo una demostración del diseño.",
                    "puntos_clave": ["Punto de ejemplo uno", "Punto de ejemplo dos", "Punto de ejemplo tres"],
                    "categoria": c, "fuente_url": "https://example.com/articulo", "fuente_dominio": "example.com",
                    "hn_url": "https://news.ycombinator.com/", "score": s, "comentarios": s // 3})
    return out

def main():
    topics = json.loads(DATA.read_text("utf-8")) if DATA.exists() else []
    if "--demo" in sys.argv:
        DATA.write_text(json.dumps(demo(), ensure_ascii=False, indent=1), "utf-8")
        print("Datos de demo escritos")
        return
    import anthropic
    client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY
    seen = {t["id"] for t in topics}
    added = 0
    for it in candidates(seen):
        if added >= MAX_NEW:
            break
        text = article_text(it["url"])
        if len(text) < MIN_ARTICLE_CHARS:
            seen.add(str(it["id"]))
            continue
        try:
            d = summarize(client, it, text, top_comments(it))
        except Exception as ex:
            print("Error resumiendo", it["id"], ex)
            continue
        if d:
            topics.append(make_topic(it, d))
            added += 1
            print("Añadido:", d["titulo"])
    topics = sorted(topics, key=lambda t: t["fecha"], reverse=True)[:KEEP]
    DATA.parent.mkdir(exist_ok=True)
    DATA.write_text(json.dumps(topics, ensure_ascii=False, indent=1), "utf-8")
    print(f"{added} temas nuevos, {len(topics)} en total")

if __name__ == "__main__":
    main()
