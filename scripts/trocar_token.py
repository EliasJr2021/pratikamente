"""Troca um token de CURTA duração por um de LONGA duração (60 dias).

Use só se o token gerado no painel da Meta expirar em horas. Rode no seu computador;
o segredo do app (Instagram app secret) nunca deve ser colado em chats nem commitado.

  export IG_APP_SECRET='...'        # Painel › Instagram › API setup › Business login settings
  export IG_TOKEN_CURTO='...'
  python scripts/trocar_token.py
O token longo é impresso; guarde-o no segredo IG_TOKEN_INICIAL do GitHub.
"""
import os
import sys

import requests

secret, token = os.getenv("IG_APP_SECRET"), os.getenv("IG_TOKEN_CURTO")
if not secret or not token:
    sys.exit("Defina IG_APP_SECRET e IG_TOKEN_CURTO no ambiente.")
r = requests.get("https://graph.instagram.com/access_token",
                 params={"grant_type": "ig_exchange_token", "client_secret": secret, "access_token": token}, timeout=30)
if r.status_code != 200:
    sys.exit(f"Falha {r.status_code}: {r.text[:300]}")
d = r.json()
print("expira em (dias):", round(int(d.get("expires_in", 0)) / 86400, 1))
print("TOKEN LONGO:", d["access_token"])
