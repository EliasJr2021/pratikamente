"""Renderização dos slides (Pillow, 1080x1350, JPEG sRGB) — resumo de artigo."""
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import config
from .models import Carousel
from .plan import Plan

W, H, M = 1080, 1350, 84
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

BG = (14, 16, 32)
INK = (244, 242, 250)
BODY = (222, 224, 236)
MUTED = (150, 156, 184)
LINE = (44, 48, 78)
CATEGORIES = {
    "ciencia": ((46, 196, 182), "CIÊNCIA"),
    "curiosidades": ((245, 166, 35), "CURIOSIDADES"),
    "misterios": ((155, 107, 255), "MISTÉRIOS"),
    "tecnologia": ((59, 130, 246), "TECNOLOGIA"),
    "outros": ((46, 196, 182), "PRATIKAMENTE"),
}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.load_default(size)


def anton(s): return font("Anton-Regular.ttf", s)
def lato(s): return font("Lato-Regular.ttf", s)
def lato_b(s): return font("Lato-Bold.ttf", s)
def lato_k(s): return font("Lato-Black.ttf", s)


def wrap(draw, text: str, f, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, make_font, max_w, max_h, start, minimum, spacing=1.28, max_lines=None):
    """Maior fonte (start..minimum) em que o texto cabe em max_w x max_h."""
    size = start
    while True:
        f = make_font(size)
        lines = wrap(draw, text, f, max_w)
        lh = int(size * spacing)
        ok = len(lines) * lh <= max_h and (max_lines is None or len(lines) <= max_lines)
        if ok or size <= minimum:
            return f, lines, lh
        size -= 2


def draw_lines(draw, x, y, lines, f, lh, fill):
    for ln in lines:
        draw.text((x, y), ln, font=f, fill=fill, anchor="la")
        y += lh
    return y


def base(accent):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=accent)
    return im, d


def footer(d, idx: int, total: int):
    d.text((M, H - 80), config.IG_HANDLE, font=lato_b(30), fill=MUTED, anchor="la")
    d.text((W - M, H - 80), f"{idx}/{total}", font=lato_b(30), fill=MUTED, anchor="ra")


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    out = img.convert("RGB")
    out.putalpha(mask)
    return out


def chip(d, x, y, label, color, text_color=(14, 16, 32), size=28):
    f = lato_b(size)
    w = int(d.textlength(label, font=f)) + 44
    d.rounded_rectangle([x, y, x + w, y + 52], radius=26, fill=color)
    d.text((x + 22, y + 26), label, font=f, fill=text_color, anchor="lm")
    return w


def arrow(d, x, y, color):
    d.line([(x, y), (x + 70, y)], fill=color, width=6)
    d.polygon([(x + 84, y), (x + 62, y - 16), (x + 62, y + 16)], fill=color)


# ───────────────────────── slides ─────────────────────────

def slide_cover(c: Carousel, plan: Plan, cover: Image.Image | None) -> Image.Image:
    accent, label = CATEGORIES[c.category]
    im, d = base(accent)
    if cover is not None:
        bg = ImageOps.fit(cover.convert("RGB"), (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
        im = Image.blend(bg, Image.new("RGB", (W, H), (6, 8, 18)), 0.66)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 10], fill=accent)

    d.text((M, 92), config.BRAND, font=lato_k(36), fill=INK, anchor="la")
    cw = int(d.textlength(label, font=lato_b(28))) + 44
    chip(d, W - M - cw, 84, label, accent)

    py = 190
    title_h = 230
    if cover is not None:
        max_w = W - 2 * M
        max_h = max(380, min(700, H - py - 190 - title_h - 44))
        cw_, ch_ = cover.size
        scale = min(max_w / cw_, max_h / ch_)
        iw, ih = int(cw_ * scale), int(ch_ * scale)           # sem recorte: 1:1, 3:2 ou 16:9
        photo = rounded(cover.convert("RGB").resize((iw, ih), Image.LANCZOS), 28)
        px = (W - iw) // 2
        im.paste(photo, (px, py), photo)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([px, py, px + iw, py + ih], radius=28, outline=accent, width=3)
        y = py + ih + 44
        f, lines, lh = fit(d, c.cover_title, lato_k, W - 2 * M, max(H - 190 - y, 120), 58, 36, spacing=1.2, max_lines=4)
    else:
        y = 330
        f, lines, lh = fit(d, c.cover_title, anton, W - 2 * M, 640, 120, 60, spacing=1.15, max_lines=6)
    draw_lines(d, M, y, lines, f, lh, INK)

    d.text((M, H - 80), "DESLIZE", font=lato_k(34), fill=accent, anchor="la")
    arrow(d, M + 150, H - 62, accent)
    d.text((W - M, H - 80), f"{len(plan.points)} pontos", font=lato_b(30), fill=MUTED, anchor="ra")
    return im


def slide_point(c: Carousel, p, n: int, total_points: int, idx: int, total: int) -> Image.Image:
    accent, _ = CATEGORIES[c.category]
    im, d = base(accent)
    d.rectangle([0, 0, 16, H], fill=accent)
    y = M
    chip(d, M, y, f"PONTO {n} DE {total_points}", accent)
    y += 52 + 30
    num = f"{n:02d}"
    nf = anton(260)
    bbox = d.textbbox((M, y), num, font=nf, anchor="la")
    d.text((M, y), num, font=nf, fill=accent, anchor="la")
    y = bbox[3] + 40
    tf, tl, tlh = fit(d, p.heading, lato_k, W - 2 * M, 250, 64, 42, spacing=1.2, max_lines=3)
    y = draw_lines(d, M, y, tl, tf, tlh, INK) + 20
    d.rectangle([M, y, M + 120, y + 6], fill=accent)
    y += 6 + 36
    avail = (H - 140) - y
    sf, sl, slh = fit(d, p.text, lato, W - 2 * M, avail, 46, 32, spacing=1.38)
    draw_lines(d, M, y, sl, sf, slh, BODY)
    footer(d, idx, total)
    return im


def slide_takeaway(c: Carousel, plan: Plan, idx: int, total: int) -> Image.Image:
    accent, _ = CATEGORIES[c.category]
    im, d = base(accent)
    d.rectangle([0, 0, 16, H], fill=accent)
    d.text((M, 170), "EM RESUMO", font=anton(150), fill=INK, anchor="la")
    y = 170 + 230
    d.rectangle([M, y, M + 120, y + 6], fill=accent)
    y += 6 + 50
    f, lines, lh = fit(d, plan.takeaway, lato_b, W - 2 * M, (H - 170) - y, 56, 34, spacing=1.36)
    draw_lines(d, M, y, lines, f, lh, BODY)
    footer(d, idx, total)
    return im


def slide_closing(c: Carousel, idx: int, total: int) -> Image.Image:
    accent, _ = CATEGORIES[c.category]
    im, d = base(accent)
    d.rectangle([0, 0, 16, H], fill=accent)
    y = 170
    f, lines, lh = fit(d, "LEIA O ARTIGO COMPLETO", anton, W - 2 * M, 300, 120, 70, spacing=1.12, max_lines=2)
    y = draw_lines(d, M, y, lines, f, lh, INK) + 24
    d.rectangle([M, y, M + 120, y + 6], fill=accent)
    y += 6 + 56
    d.text((M, y), "Todos os detalhes estão no site:", font=lato(42), fill=BODY, anchor="la")
    y += 96
    box_h = 120
    d.rounded_rectangle([M, y, W - M, y + box_h], radius=24, fill=accent)
    uf, _, _ = fit(d, config.SITE_HOST, lato_k, W - 2 * M - 60, box_h, 56, 34, max_lines=1)
    d.text((W // 2, y + box_h // 2), config.SITE_HOST, font=uf, fill=(14, 16, 32), anchor="mm")
    y += box_h + 70
    f2, l2, lh2 = fit(d, f"Siga {config.IG_HANDLE} e descubra algo novo sobre ciência, curiosidades e mistérios.",
                      lato_b, W - 2 * M, 200, 44, 32)
    y = draw_lines(d, M, y, l2, f2, lh2, INK) + 40
    notes = ["Fonte: " + config.SITE_HOST,
             "Conteúdo informativo, não substitui orientação de um profissional de saúde."
             if c.health_disclaimer else "Conteúdo informativo e de divulgação."]
    if config.AI_IMAGE_NOTICE:
        notes.append("Imagem ilustrativa gerada por IA.")
    for n in notes:
        for ln in wrap(d, n, lato(30), W - 2 * M):
            d.text((M, y), ln, font=lato(30), fill=MUTED, anchor="la")
            y += 42
    footer(d, idx, total)
    return im


def build_slides(c: Carousel, plan: Plan, cover_bytes: bytes | None) -> list[Image.Image]:
    cover = None
    if cover_bytes:
        try:
            cover = Image.open(io.BytesIO(cover_bytes))
            cover.load()
        except Exception as e:  # noqa: BLE001
            print(f"[render] capa ilegível, usando capa tipográfica: {e}")
    n = plan.total_slides
    slides = [slide_cover(c, plan, cover)]
    for i, p in enumerate(plan.points, start=1):
        slides.append(slide_point(c, p, i, len(plan.points), i + 1, n))
    slides.append(slide_takeaway(c, plan, len(slides) + 1, n))
    slides.append(slide_closing(c, len(slides) + 1, n))
    return slides


def save_jpegs(slides: list[Image.Image], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, im in enumerate(slides, start=1):
        p = out_dir / f"slide_{i:02d}.jpg"
        im.convert("RGB").save(p, "JPEG", quality=90, optimize=True)
        if p.stat().st_size > 8 * 1024 * 1024:
            im.convert("RGB").save(p, "JPEG", quality=75, optimize=True)
        paths.append(p)
    return paths
