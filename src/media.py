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
    """Espera cada URL responder 200 com image/jpeg (o Pages leva de segundos a alguns minutos)."""
    deadline = time.time() + timeout
    pending = list(urls)
    while pending and time.time() < deadline:
        still = []
        for u in pending:
            try:
                r = requests.get(u, timeout=20, headers={"User-Agent": config.USER_AGENT})
                ok = r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image/jpeg")
            except requests.RequestException:
                ok = False
            if not ok:
                still.append(u)
        pending = still
        if pending:
            time.sleep(interval)
    if pending:
        raise RuntimeError(
            "As imagens não ficaram públicas a tempo. Verifique: Settings > Pages > Source = branch `media` "
            f"(pasta /root), ou defina MEDIA_BASE_URL para raw.githubusercontent.com. Exemplo: {pending[0]}")
