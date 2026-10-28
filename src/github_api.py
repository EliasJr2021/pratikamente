"""Issues do GitHub (aprovação manual e alertas)."""
import re

import requests

from . import config

API = "https://api.github.com"


def _h() -> dict:
    return {"Authorization": f"Bearer {config.GITHUB_TOKEN}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def ensure_label(name: str, color: str = "d9a441") -> None:
    r = requests.post(f"{API}/repos/{config.REPO}/labels", headers=_h(), json={"name": name, "color": color}, timeout=30)
    if r.status_code not in (201, 422):  # 422 = já existe
        r.raise_for_status()


def create_issue(title: str, body: str, labels: list[str]) -> int:
    for lb in labels:
        ensure_label(lb)
    r = requests.post(f"{API}/repos/{config.REPO}/issues", headers=_h(),
                      json={"title": title, "body": body, "labels": labels}, timeout=30)
    r.raise_for_status()
    return r.json()["number"]


def comment(number: int, body: str) -> None:
    requests.post(f"{API}/repos/{config.REPO}/issues/{number}/comments", headers=_h(),
                  json={"body": body}, timeout=30).raise_for_status()


def set_labels(number: int, labels: list[str]) -> None:
    for lb in labels:
        ensure_label(lb)
    requests.put(f"{API}/repos/{config.REPO}/issues/{number}/labels", headers=_h(),
                 json={"labels": labels}, timeout=30).raise_for_status()


def close_issue(number: int) -> None:
    requests.patch(f"{API}/repos/{config.REPO}/issues/{number}", headers=_h(),
                   json={"state": "closed"}, timeout=30).raise_for_status()


def get_issue(number: int) -> dict:
    r = requests.get(f"{API}/repos/{config.REPO}/issues/{number}", headers=_h(), timeout=30)
    r.raise_for_status()
    return r.json()


CAPTION_RE = re.compile(r"<!-- CAPTION-START -->\s*```text\r?\n(.*?)\r?\n```\s*<!-- CAPTION-END -->", re.S)


def caption_block(caption: str) -> str:
    return f"<!-- CAPTION-START -->\n```text\n{caption}\n```\n<!-- CAPTION-END -->"


def parse_caption(body: str) -> str | None:
    m = CAPTION_RE.search(body or "")
    return m.group(1).strip() if m else None


def issue_body(pending: dict, review_summary: str) -> str:
    imgs = " ".join(f'<img src="{u}" width="200">' for u in pending["slides"])
    return (
        f"## 📰 {pending['title']}\n\n"
        f"Página de origem: {pending['link']}\n\n"
        f"**Revisão automática:** {review_summary}\n\n"
        f"### Slides ({len(pending['slides'])})\n\n{imgs}\n\n"
        f"### Legenda (pode editar aqui antes de aprovar)\n\n{caption_block(pending['caption'])}\n\n"
        "### Como responder\n"
        "- Comente **`/aprovar`** para publicar no Instagram.\n"
        "- Comente **`/rejeitar`** para pular esta página (a fila segue no próximo dia).\n"
        "- Só comentários do dono do repositório são aceitos.\n"
    )
