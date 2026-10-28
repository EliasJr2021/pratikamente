"""Token do Instagram: armazenado cifrado (Fernet) em state/state.json e renovado antes dos 60 dias."""
import base64
import functools
import hashlib
import os
from datetime import datetime, timedelta, timezone

import requests
from cryptography.fernet import Fernet, InvalidToken

from . import state as st


def normalize_key(raw: str) -> bytes | None:
    """Aceita uma chave Fernet válida (44 caracteres). Qualquer outro valor não vazio é transformado
    em uma chave por PBKDF2, para que um STATE_KEY colado com aspas, espaços ou outro formato não quebre o robô."""
    raw = (raw or "").strip()
    if raw.startswith(("b'", 'b"')):
        raw = raw[2:]
    raw = raw.strip("'\" \t\r\n")
    if not raw:
        return None
    try:
        if len(base64.urlsafe_b64decode(raw.encode())) == 32:
            return raw.encode()
    except Exception:  # noqa: BLE001
        pass
    dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), b"carrossel-ig-state", 200_000, dklen=32)
    return base64.urlsafe_b64encode(dk)


def is_fernet_key(raw: str) -> bool:
    """True se o valor (após limpar aspas/espaços) é uma chave Fernet real: 32 bytes em base64 url-safe."""
    raw = (raw or "").strip()
    if raw.startswith(("b'", 'b"')):
        raw = raw[2:]
    raw = raw.strip("'\" \t\r\n")
    try:
        return len(base64.urlsafe_b64decode(raw.encode())) == 32 and len(raw) == 44
    except Exception:  # noqa: BLE001
        return False


@functools.lru_cache(maxsize=4)
def _fernet_for(raw: str):
    key = normalize_key(raw)
    if key is None:
        return None
    if key != (raw or "").strip().encode():
        print("[token] STATE_KEY não está no formato de chave Fernet; usando uma chave derivada do valor "
              "informado. Para gerar uma válida: python scripts/gerar_chave.py")
    return Fernet(key)


def _fernet():
    return _fernet_for(os.getenv("STATE_KEY", ""))


def get_token(state: dict) -> str:
    f = _fernet()
    enc = state["ig"].get("token_enc")
    boot = os.getenv("IG_TOKEN_INICIAL", "")
    if enc and f:
        try:
            return f.decrypt(enc.encode()).decode()
        except InvalidToken:
            print("[token] Não foi possível decifrar o token salvo (STATE_KEY mudou?); usando IG_TOKEN_INICIAL.")
    if not boot:
        raise RuntimeError("Sem token do Instagram: defina o segredo IG_TOKEN_INICIAL (e STATE_KEY).")
    return boot


def refresh(state: dict) -> dict:
    """Renova o token de longa duração (válido por 60 dias) e guarda o novo valor cifrado."""
    f = _fernet()
    if not f:
        raise RuntimeError("Defina o segredo STATE_KEY (gere com scripts/gerar_chave.py).")
    if not is_fernet_key(os.getenv("STATE_KEY", "")):
        # O token renovado é commitado (cifrado) em um repositório público: exige chave aleatória de verdade.
        raise RuntimeError(
            "STATE_KEY inválida para proteger o token no repositório. Gere uma chave aleatória com "
            "`python scripts/gerar_chave.py` e salve SOMENTE a linha impressa no segredo STATE_KEY.")
    token = get_token(state)
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    if r.status_code != 200:
        msg = r.text[:300]
        # Token com menos de 24 h não pode ser renovado ainda: não é falha.
        if "24" in msg or "recent" in msg.lower():
            print("[token] token muito recente para renovar; mantendo o atual.")
            if not state["ig"].get("token_enc"):
                state["ig"]["token_enc"] = f.encrypt(token.encode()).decode()
            return state
        raise RuntimeError(f"Falha ao renovar o token: {msg}")
    data = r.json()
    state["ig"]["token_enc"] = f.encrypt(data["access_token"].encode()).decode()
    state["ig"]["refreshed_at"] = st.now_iso()
    state["ig"]["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in", 5184000)))).isoformat(timespec="seconds")
    return state
