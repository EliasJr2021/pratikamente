"""Token do Instagram: armazenado cifrado (Fernet) em state/state.json e renovado antes dos 60 dias."""
import os
from datetime import datetime, timedelta, timezone

import requests
from cryptography.fernet import Fernet

from . import state as st


def _fernet():
    key = os.getenv("STATE_KEY", "")
    return Fernet(key.encode()) if key else None


def get_token(state: dict) -> str:
    f = _fernet()
    enc = state["ig"].get("token_enc")
    if enc and f:
        return f.decrypt(enc.encode()).decode()
    boot = os.getenv("IG_TOKEN_INICIAL", "")
    if not boot:
        raise RuntimeError("Sem token do Instagram: defina o segredo IG_TOKEN_INICIAL (e STATE_KEY).")
    return boot


def refresh(state: dict) -> dict:
    """Renova o token de longa duração (válido por 60 dias) e guarda o novo valor cifrado."""
    f = _fernet()
    if not f:
        raise RuntimeError("Defina o segredo STATE_KEY (gere com scripts/gerar_chave.py).")
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
