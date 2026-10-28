"""Modelos e esquemas (JSON Schema escrito à mão para as ferramentas do Claude)."""
from typing import Literal

from pydantic import BaseModel, Field, ValidationError  # noqa: F401

CATEGORIES = ["ciencia", "curiosidades", "misterios", "tecnologia", "outros"]


class Point(BaseModel):
    heading: str = Field(max_length=60)
    text: str = Field(max_length=270)


class Risk(BaseModel):
    level: Literal["baixo", "medio", "alto"]
    reasons: list[str] = []


class Carousel(BaseModel):
    category: Literal["ciencia", "curiosidades", "misterios", "tecnologia", "outros"]
    cover_title: str = Field(max_length=100)
    hook: str = Field(max_length=150)
    points: list[Point] = Field(min_length=3, max_length=8)
    takeaway: str = Field(max_length=250)
    hashtags: list[str] = Field(default=[], max_length=10)
    health_disclaimer: bool = False
    risk: Risk


class Review(BaseModel):
    verdict: Literal["ok", "ajustar", "reter"]
    reasons: list[str] = []
    fixes: list[str] = []
    image_ok: bool = True
    image_flags: list[str] = []


CAROUSEL_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES,
                     "description": "Categoria principal do artigo."},
        "cover_title": {"type": "string",
                        "description": "Título da capa, fiel ao artigo e sem exagero (até 90 caracteres)."},
        "hook": {"type": "string",
                 "description": "Primeira linha da legenda: resume o assunto em até 140 caracteres, sem prometer mais que o artigo."},
        "points": {
            "type": "array",
            "description": "Resumo do artigo em 4 a 6 pontos, na ordem lógica do texto.",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string", "description": "Até 55 caracteres."},
                    "text": {"type": "string", "description": "Até 250 caracteres, 2 a 3 frases curtas."},
                },
                "required": ["heading", "text"],
            },
        },
        "takeaway": {"type": "string",
                     "description": "Fechamento 'Em resumo': a ideia central em até 230 caracteres."},
        "hashtags": {"type": "array", "items": {"type": "string"}, "description": "5 a 8 hashtags em português."},
        "health_disclaimer": {"type": "boolean",
                              "description": "true se o tema envolve saúde, medicamentos, nutrição ou tratamentos."},
        "risk": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["baixo", "medio", "alto"]},
                "reasons": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["level", "reasons"],
        },
    },
    "required": ["category", "cover_title", "hook", "points", "takeaway", "hashtags", "health_disclaimer", "risk"],
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ok", "ajustar", "reter"]},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "fixes": {"type": "array", "items": {"type": "string"},
                  "description": "Correções objetivas e específicas, quando verdict = ajustar."},
        "image_ok": {"type": "boolean"},
        "image_flags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "reasons", "fixes", "image_ok", "image_flags"],
}
