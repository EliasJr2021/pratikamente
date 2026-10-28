"""Renova o token do Instagram e persiste cifrado. Executado semanalmente."""
import sys

from . import state as st
from .instagram import Instagram
from .token import get_token, refresh


def main() -> int:
    state = st.load()
    state = refresh(state)
    print("Token renovado; expira em:", state["ig"].get("expires_at"))
    print("Teste de acesso:", Instagram(get_token(state)).whoami().get("username"))
    st.commit(state, "renova token do Instagram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
