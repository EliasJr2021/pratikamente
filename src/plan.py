"""Seleção dos pontos e total de slides (máximo de 10 itens no carrossel)."""
from dataclasses import dataclass

from . import config
from .models import Carousel, Point


@dataclass
class Plan:
    points: list[Point]
    takeaway: str
    total_slides: int


def make_plan(c: Carousel, max_slides: int | None = None) -> Plan:
    """Capa + pontos + 'Em resumo' + encerramento <= max_slides."""
    max_slides = max_slides or config.MAX_SLIDES
    points = c.points[: max_slides - 3]
    return Plan(points=points, takeaway=c.takeaway, total_slides=1 + len(points) + 1 + 1)
