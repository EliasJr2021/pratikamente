"""Gera a chave que protege o token do Instagram no repositório. Não precisa instalar nada.

Rode:  python scripts/gerar_chave.py
Copie SOMENTE a linha impressa (44 caracteres, termina em "=") para o segredo STATE_KEY do GitHub.
Não cole a chave em chats, e-mails nem no código.
"""
import base64
import os

print(base64.urlsafe_b64encode(os.urandom(32)).decode())
