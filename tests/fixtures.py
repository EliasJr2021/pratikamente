"""Dados fictícios de teste (apenas para validar layout; não são publicados)."""
from src.models import Carousel

SAMPLE = {
    "category": "ciencia",
    "cover_title": "Cientistas identificam a origem geológica de um monumento pré-histórico de 4.000 anos",
    "hook": "Um estudo aponta de onde vieram as enormes pedras de um monumento pré-histórico inglês.",
    "points": [
        {"heading": "Um monumento que intriga há milênios",
         "text": "Três pedras gigantes alinhadas formam um monumento de cerca de 4.000 anos. Sua origem sempre foi um mistério para os estudiosos."},
        {"heading": "O que os cientistas analisaram",
         "text": "A equipe comparou a composição das pedras com rochas de afloramentos próximos, usando análises químicas e geológicas."},
        {"heading": "A origem foi identificada",
         "text": "Os resultados indicam que o material veio de uma pedreira específica, a dezenas de quilômetros do local."},
        {"heading": "Como o transporte pode ter sido feito",
         "text": "O artigo discute hipóteses sobre rotas e técnicas de transporte, ainda sem confirmação definitiva."},
        {"heading": "Por que isso importa",
         "text": "A descoberta ajuda a entender como comunidades pré-históricas se organizavam para mover blocos enormes."},
    ],
    "takeaway": "A análise geológica ligou as pedras a uma pedreira distante e reforça que povos pré-históricos coordenavam grandes obras.",
    "hashtags": ["#Ciência", "Arqueologia", "hoje na ciência", "Geologia", "Pré-história"],
    "health_disclaimer": False,
    "risk": {"level": "baixo", "reasons": ["Tema científico, sem pontos sensíveis."]},
}


def sample() -> Carousel:
    return Carousel.model_validate(SAMPLE)
