"""Etapa 2: revisão independente (texto + imagem de capa)."""
import base64
import io

from PIL import Image

from . import llm
from .extract import _prompt, carousel_json
from .models import REVIEW_SCHEMA, Carousel, Review


def _image_block(cover_bytes: bytes | None):
    if not cover_bytes:
        return None
    try:
        im = Image.open(io.BytesIO(cover_bytes)).convert("RGB")
        im.thumbnail((1024, 1024))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        data = base64.standard_b64encode(buf.getvalue()).decode()
        return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}
    except Exception as e:  # noqa: BLE001
        print(f"[review] imagem de capa ilegível: {e}")
        return None


def review(page: dict, carousel: Carousel, cover_bytes: bytes | None) -> Review:
    system = _prompt("sistema.md")
    text = (f"{_prompt('revisao.md')}\n\n<pagina url=\"{page['link']}\">\n{page['text']}\n</pagina>\n\n"
            f"<carrossel>\n{carousel_json(carousel)}\n</carrossel>")
    blocks = [{"type": "text", "text": text}]
    img = _image_block(cover_bytes)
    if img:
        blocks.append(img)
        blocks.append({"type": "text", "text": "A imagem acima é a capa da página."})
    else:
        blocks.append({"type": "text", "text": "Não há imagem de capa utilizável; avalie apenas o texto."})
    data = llm.call_tool(system, blocks, "registrar_revisao", "Registra o resultado da revisão.", REVIEW_SCHEMA)
    return Review.model_validate(data)
