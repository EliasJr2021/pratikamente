"""Hospedagem dos JPEGs: branch órfã `media` + GitHub Pages (URL pública para a Meta)."""
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import requests

from . import config


def _run(args, cwd, secret=""):
    res = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        err = (res.stderr + res.stdout).replace(secret, "***") if secret else res.stderr
        raise RuntimeError(f"git falhou: {' '.join(a for a in args[:3])} -> {err[-500:]}")
    return res


def push_media(slug: str, files: list[Path]) -> list[str]:
    """Recria a branch `media` com um único commit contendo apenas este carrossel."""
    tmp = Path(tempfile.mkdtemp())
    dest = tmp / slug
    dest.mkdir()
    for f in files:
        shutil.copy(f, dest / f.name)
    (tmp / ".nojekyll").write_text("")
    _run(["git", "init", "-q", "-b", "media"], tmp)
    _run(["git", "config", "user.name", "historia-em-dia-bot"], tmp)
    _run(["git", "config", "user.email", "bot@users.noreply.github.com"], tmp)
    _run(["git", "add", "-A"], tmp)
    _run(["git", "commit", "-q", "-m", f"media: {slug}"], tmp)
    tok = config.GITHUB_TOKEN
    remote = f"https://x-access-token:{tok}@github.com/{config.REPO}.git"
    _run(["git", "push", "-q", "--force", remote, "media"], tmp, secret=tok)
    shutil.rmtree(tmp, ignore_errors=True)
    return [f"{config.MEDIA_BASE_URL}/{slug}/{f.name}" for f in files]


def wait_for_urls(urls: list[str], timeout: int = 480, interval: int = 15) -> None:
    """Espera cada URL responder 200 com image/jpeg e mostra o status a cada tentativa."""
    deadline = time.time() + timeout
    pending = list(urls)
    last: dict[str, str] = {}
    attempt = 0
    while pending and time.time() < deadline:
        attempt += 1
        still = []
        for u in pending:
            try:
                r = requests.get(u, timeout=20, headers={"User-Agent": config.USER_AGENT})
                ok = r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image/jpeg")
                last[u] = f"HTTP {r.status_code} ({r.headers.get('Content-Type', '?')})"
            except requests.RequestException as e:
                ok = False
                last[u] = f"erro de rede: {type(e).__name__}"
            if not ok:
                still.append(u)
        pending = still
        if pending:
            print(f"[media] tentativa {attempt}: {len(pending)} URL(s) indisponível(is) — {last[pending[0]]}", flush=True)
            time.sleep(interval)
    if pending:
        raise RuntimeError(
            f"As imagens não ficaram públicas a tempo (último status: {last.get(pending[0])}; URL: {pending[0]}). "
            "Se for 404: confirme que o repositório é PÚBLICO (o raw.githubusercontent.com não serve repositórios "
            "privados) e que a branch `media` existe. Alternativa: GitHub Pages via MEDIA_BASE_URL.")
