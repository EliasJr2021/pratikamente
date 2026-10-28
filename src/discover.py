"""Descoberta e leitura dos artigos do site (WordPress)."""
import html
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from . import config

JUNK_TITLES = ("olá, mundo", "ola, mundo", "hello world", "exemplo de página", "página de exemplo")
UNCATEGORIZED = {"uncategorized", "sem-categoria", "sem categoria"}
MIN_REST_CHARS = 1500


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})
    return s


def is_article(title: str, slug: str) -> bool:
    t = title.strip().lower()
    return bool(slug) and not any(j in t for j in JUNK_TITLES) and slug not in ("hello-world", "ola-mundo")


def list_categories(s: requests.Session) -> dict[int, dict]:
    try:
        r = s.get(f"{config.SITE_BASE}/wp-json/wp/v2/categories",
                  params={"per_page": 100, "_fields": "id,name,slug"}, timeout=30)
        r.raise_for_status()
        return {c["id"]: {"name": html.unescape(c["name"]), "slug": c["slug"]} for c in r.json()}
    except Exception as e:  # noqa: BLE001
        print(f"[discover] categorias indisponíveis ({e}).")
        return {}


def category_hint(cat_ids: list[int], cats: dict[int, dict]) -> str:
    for cid in cat_ids or []:
        c = cats.get(cid)
        if c and c["slug"] not in UNCATEGORIZED:
            return c["name"]
    return "Outros"


def list_posts_rest(s: requests.Session) -> list[dict]:
    cats = list_categories(s)
    posts, page = [], 1
    while True:
        r = s.get(
            f"{config.SITE_BASE}/wp-json/wp/v2/posts",
            params={"per_page": 100, "page": page, "orderby": "date", "order": "asc",
                    "_fields": "id,date_gmt,slug,link,title,categories"},
            timeout=30,
        )
        if r.status_code == 400:  # página além do total
            break
        r.raise_for_status()
        for p in r.json():
            posts.append({
                "id": p["id"], "date": p["date_gmt"], "slug": p["slug"], "link": p["link"],
                "title": html.unescape(p["title"]["rendered"]),
                "category": category_hint(p.get("categories"), cats),
            })
        total_pages = int(r.headers.get("X-WP-TotalPages", page))
        if page >= total_pages:
            break
        page += 1
    return posts


def list_posts_sitemap(s: requests.Session) -> list[dict]:
    """Reserva: wp-sitemap.xml (ordem por lastmod)."""
    idx = s.get(f"{config.SITE_BASE}/wp-sitemap.xml", timeout=30)
    idx.raise_for_status()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    maps = [e.text for e in ET.fromstring(idx.content).findall(".//sm:loc", ns) if "posts-post" in (e.text or "")]
    posts = []
    for m in maps:
        r = s.get(m, timeout=30)
        r.raise_for_status()
        for u in ET.fromstring(r.content).findall("sm:url", ns):
            loc = u.findtext("sm:loc", namespaces=ns)
            last = u.findtext("sm:lastmod", namespaces=ns) or ""
            slug = urlparse(loc).path.strip("/").split("/")[-1]
            posts.append({"id": 0, "date": last, "slug": slug, "link": loc, "title": slug, "category": "Outros"})
    posts.sort(key=lambda p: p["date"])
    return posts


def list_posts() -> list[dict]:
    s = _session()
    try:
        posts = list_posts_rest(s)
        if posts:
            return posts
    except Exception as e:  # noqa: BLE001
        print(f"[discover] API REST indisponível ({e}); tentando sitemap.")
    return list_posts_sitemap(s)


def next_post(done_slugs: set[str]) -> dict | None:
    for p in list_posts():
        if p["slug"] in done_slugs or not is_article(p["title"], p["slug"]):
            continue
        return p
    return None


def _blocks_to_text(root) -> str:
    for t in root.find_all(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        t.decompose()
    lines, seen = [], set()
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
        if el.name == "tr":
            txt = " | ".join(c.get_text(" ", strip=True) for c in el.find_all(["th", "td"]))
        else:
            txt = el.get_text(" ", strip=True)
        if not txt or txt in seen:
            continue
        seen.add(txt)
        if el.name in ("h1", "h2", "h3", "h4"):
            lines.append(f"\n## {txt}")
        elif el.name == "li":
            lines.append(f"- {txt}")
        else:
            lines.append(txt)
    return "\n".join(lines)[:40000]


def html_to_text(html_str: str) -> str:
    return _blocks_to_text(BeautifulSoup(html_str, "html.parser"))


CHROME_SELECTORS = [".elementor-location-header", ".elementor-location-footer", '[class*="sidebar"]',
                    '[class*="popup"]', '[id*="comment"]', '[class*="popular"]', '[class*="related"]']


def _clean_text(soup: BeautifulSoup) -> str:
    """Reserva: raspagem do HTML. Remove menus/rodapé e começa no título do artigo (h1)."""
    for sel in CHROME_SELECTORS:
        for el in soup.select(sel):
            el.decompose()
    best = ""
    for sel in ('[data-elementor-type="wp-post"]', ".entry-content", "article", "main", "body"):
        root = soup.select_one(sel)
        if root is None:
            continue
        txt = _blocks_to_text(BeautifulSoup(str(root), "html.parser"))
        if len(txt) > len(best):
            best = txt
    h1 = soup.find("h1")
    if h1:
        marker = "## " + h1.get_text(" ", strip=True)
        if marker in best:
            best = best[best.index(marker):]
    return best


def choose_text(rest_text: str, html_text: str) -> tuple[str, str]:
    """O corpo vindo da API REST contém só o artigo; o HTML inclui menu, barra lateral e rodapé."""
    if len(rest_text) >= MIN_REST_CHARS:
        return rest_text, "rest"
    return html_text, "html"


def fetch_content_rest(post_id: int) -> str:
    if not post_id:
        return ""
    try:
        r = _session().get(f"{config.SITE_BASE}/wp-json/wp/v2/posts/{post_id}",
                           params={"_fields": "id,content"}, timeout=30)
        r.raise_for_status()
        return html_to_text(r.json()["content"]["rendered"])
    except Exception as e:  # noqa: BLE001
        print(f"[discover] conteúdo via REST indisponível ({e}); usando HTML.")
        return ""


def fetch_page(link: str, post_id: int = 0) -> dict:
    s = _session()
    r = s.get(link, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    og = soup.find("meta", property="og:image")
    title = soup.find("meta", property="og:title")
    rest_text = fetch_content_rest(post_id)
    html_text = _clean_text(soup)
    text, source = choose_text(rest_text, html_text)
    return {
        "link": link,
        "title": (title["content"] if title and title.get("content") else (soup.title.string if soup.title else "")),
        "cover_url": og["content"] if og and og.get("content") else None,
        "text": text[:40000],
        "text_source": source,
        "rest_len": len(rest_text),
        "html_len": len(html_text),
    }


def download_image(url: str) -> bytes | None:
    try:
        r = _session().get(url, timeout=45)
        r.raise_for_status()
        if "image" not in r.headers.get("Content-Type", ""):
            return None
        return r.content
    except Exception as e:  # noqa: BLE001
        print(f"[discover] não foi possível baixar a imagem de capa: {e}")
        return None
