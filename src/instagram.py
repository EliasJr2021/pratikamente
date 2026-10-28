"""Publicação de carrossel pela Instagram API (Instagram Login)."""
import time

import requests

from . import config


class IGError(RuntimeError):
    pass


class Instagram:
    def __init__(self, token: str, user_id: str | None = None):
        self.token = token
        self.uid = user_id or config.IG_USER_ID
        self.base = f"https://graph.instagram.com/{config.IG_API_VERSION}"

    def _call(self, method: str, path: str, retries: int = 3, **params):
        params["access_token"] = self.token
        for attempt in range(retries):
            try:
                if method == "GET":
                    r = requests.get(f"{self.base}/{path}", params=params, timeout=60)
                else:
                    r = requests.post(f"{self.base}/{path}", data=params, timeout=60)
            except requests.RequestException as e:
                if attempt == retries - 1:
                    raise IGError(f"Rede: {e}") from e
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code >= 500 and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code >= 400:
                raise IGError(f"{r.status_code} {path}: {r.text[:500]}")
            return r.json()
        raise IGError("Tentativas esgotadas")

    # ── diagnóstico ──
    def whoami(self) -> dict:
        return self._call("GET", "me", fields="user_id,username,account_type")

    def quota(self) -> dict:
        return self._call("GET", f"{self.uid}/content_publishing_limit", fields="quota_usage,config")

    def recent_media(self, limit: int = 10) -> list[dict]:
        return self._call("GET", f"{self.uid}/media", fields="id,caption,permalink,timestamp", limit=limit).get("data", [])

    # ── publicação ──
    def _wait(self, container_id: str, timeout: int = 180):
        deadline = time.time() + timeout
        while time.time() < deadline:
            info = self._call("GET", container_id, fields="status_code,status")
            code = info.get("status_code")
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise IGError(f"Contêiner {container_id} em estado {code}: {info.get('status')}")
            time.sleep(5)
        raise IGError(f"Tempo esgotado aguardando o contêiner {container_id}")

    def create_carousel(self, image_urls: list[str], caption: str, ai_generated: bool = False) -> str:
        if not 2 <= len(image_urls) <= 20:
            raise IGError("Carrossel precisa de 2 a 20 imagens.")
        children = []
        for url in image_urls:
            res = self._call("POST", f"{self.uid}/media", image_url=url, is_carousel_item="true")
            children.append(res["id"])
        for cid in children:
            self._wait(cid)
        extra = {"is_ai_generated": "true"} if ai_generated else {}  # só no contêiner do carrossel
        parent = self._call("POST", f"{self.uid}/media", media_type="CAROUSEL",
                            children=",".join(children), caption=caption, **extra)["id"]
        self._wait(parent)
        return parent

    def publish(self, creation_id: str) -> dict:
        # Sem retentativa automática: evita publicar em duplicidade.
        res = self._call("POST", f"{self.uid}/media_publish", retries=1, creation_id=creation_id)
        media_id = res["id"]
        try:
            info = self._call("GET", media_id, fields="permalink")
        except IGError:
            info = {}
        return {"id": media_id, "permalink": info.get("permalink", "")}

    def find_recent_by_caption(self, caption: str) -> dict | None:
        head = caption.strip()[:80]
        for m in self.recent_media():
            if (m.get("caption") or "").strip().startswith(head):
                return m
        return None
