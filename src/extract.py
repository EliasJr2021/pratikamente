"""Etapa 1: o Claude lê a página e devolve o carrossel estruturado."""
import json
from pathlib import Path

from pydantic import ValidationError

from . import llm
from .models import CAROUSEL_SCHEMA, Carousel

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def _prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def extract(page: dict, feedback: list[str] | None = None, max_attempts: int = 3) -> Carousel:
    system = _prompt("sistema.md")
    task = _prompt("extracao.md")
    user = (f"{task}\n\ncategoria_do_site: {page.get('category', 'Outros')}\n\n"
            f"<pagina url=\"{page['link']}\" titulo=\"{page['title']}\">\n{page['text']}\n</pagina>")
    if feedback:
        user += "\n\nCORREÇÕES OBRIGATÓRIAS apontadas pela revisão anterior:\n" + "\n".join(f"- {f}" for f in feedback)
    last_error = ""
    for attempt in range(max_attempts):
        content = user if not last_error else (
            user + "\n\nA resposta anterior violou os limites de tamanho/formato. Corrija e reduza os textos:\n" + last_error)
        data = llm.call_tool(system, content, "registrar_carrossel",
                             "Registra o carrossel final de Instagram extraído da página.", CAROUSEL_SCHEMA)
        try:
            return Carousel.model_validate(data)
        except ValidationError as e:
            last_error = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())[:900]
            print(f"[extract] validação falhou (tentativa {attempt + 1}): {last_error}")
    raise RuntimeError("Extração inválida após várias tentativas: " + last_error)


def carousel_json(c: Carousel) -> str:
    return json.dumps(c.model_dump(), ensure_ascii=False, indent=1)
