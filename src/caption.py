"""Legenda do Instagram (limite de 2.200 caracteres)."""
import re
from urllib.parse import urlencode, urlparse, urlunparse

from . import config
from .models import Carousel
from .plan import Plan

DEFAULT_TAGS = ["ciência", "curiosidades", "pratikamente"]


def utm_link(link: str) -> str:
    p = urlparse(link)
    q = urlencode({"utm_source": "instagram", "utm_medium": "carrossel", "utm_campaign": "diario"})
    return urlunparse(p._replace(query=(p.query + "&" if p.query else "") + q))


def clean_tags(tags: list[str]) -> list[str]:
    out = []
    for t in tags + DEFAULT_TAGS:
        t = re.sub(r"[^\w]", "", t.lstrip("#").lower())
        if "hoje" in t:   # evita referências temporais: os artigos podem ser antigos
            continue
        if t and t not in out:
            out.append(t)
    return ["#" + t for t in out[:8]]


def build_caption(c: Carousel, plan: Plan, link: str) -> str:
    lines = [c.hook.rstrip(), "", "Deslize para o resumo ➡️", ""]
    for p in plan.points:
        lines.append(f"▪️ {p.heading}")
    lines += ["", "📖 Artigo completo no site (link na bio):", utm_link(link), ""]
    if c.health_disclaimer:
        lines.append("ℹ️ Conteúdo informativo. Não substitui a orientação de um profissional de saúde.")
    else:
        lines.append("ℹ️ Conteúdo informativo e de divulgação.")
    if config.AI_IMAGE_NOTICE:
        lines.append("Imagem ilustrativa gerada por IA.")
    lines += ["", " ".join(clean_tags(c.hashtags))]
    return "\n".join(lines)[:2200]
