"""Estado persistido em state/state.json (commitado pelo workflow)."""
import json
import os
import subprocess
from datetime import datetime, timezone

from . import config

DEFAULT = {
    "version": 1,
    "posted": [],
    "skipped": [],
    "pending": None,
    "ig": {"token_enc": None, "refreshed_at": None, "expires_at": None},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load() -> dict:
    try:
        with open(config.STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    merged = json.loads(json.dumps(DEFAULT))
    merged.update(data)
    merged["ig"] = {**DEFAULT["ig"], **(data.get("ig") or {})}
    return merged


def save(state: dict) -> None:
    os.makedirs(os.path.dirname(config.STATE_PATH), exist_ok=True)
    tmp = config.STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, config.STATE_PATH)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def commit(state: dict, message: str) -> None:
    """Salva e, dentro do GitHub Actions, commita e envia o estado para a branch atual."""
    save(state)
    if os.getenv("GITHUB_ACTIONS") != "true":
        return
    _git("config", "user.name", "historia-em-dia-bot")
    _git("config", "user.email", "bot@users.noreply.github.com")
    _git("add", config.STATE_PATH)
    if _git("diff", "--cached", "--quiet").returncode == 0:
        return
    _git("commit", "-m", message)
    for attempt in range(4):
        _git("pull", "--rebase", "--autostash")
        res = _git("push")
        if res.returncode == 0:
            return
    raise RuntimeError("Não foi possível enviar o estado ao repositório: " + res.stderr[-400:])


def is_done(state: dict, slug: str) -> bool:
    return any(p["slug"] == slug for p in state["posted"] + state["skipped"])
