"""Gera a chave para cifrar o token do Instagram. Guarde o resultado no segredo STATE_KEY."""
from cryptography.fernet import Fernet

print(Fernet.generate_key().decode())
