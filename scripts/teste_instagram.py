"""Teste manual de publicação com imagens JPEG já públicas.

  python -m scripts.teste_instagram --check
  python -m scripts.teste_instagram --publicar URL1 URL2 URL3      # PUBLICA DE VERDADE na conta
"""
import argparse

from src import state as st
from src.instagram import Instagram
from src.token import get_token

ap = argparse.ArgumentParser()
ap.add_argument("--check", action="store_true")
ap.add_argument("--publicar", nargs="+", metavar="URL")
a = ap.parse_args()

ig = Instagram(get_token(st.load()))
print("Conta:", ig.whoami())
print("Cota:", ig.quota())
if a.publicar:
    cid = ig.create_carousel(a.publicar, "Teste de automação — pode apagar. #teste")
    print("Publicado:", ig.publish(cid))
