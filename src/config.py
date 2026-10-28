"""Configuração central. Valores vêm de variáveis de ambiente (Actions secrets/variables)."""
import os


def _get(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def resolve_media_base(raw: str, default: str) -> str:
    """Usa MEDIA_BASE_URL só se for uma URL completa; valores como 'raw.githubusercontent.com/…/media' são ignorados."""
    raw = (raw or "").strip()
    if raw and (not raw.startswith(("http://", "https://")) or "…" in raw or "..." in raw):
        print(f"[config] MEDIA_BASE_URL inválida ({raw!r}); usando o padrão {default}.")
        raw = ""
    return (raw or default).rstrip("/")


REPO = _get("GITHUB_REPOSITORY", "EliasJr2021/pratikamente")
OWNER, REPO_NAME = REPO.split("/", 1)

SITE_BASE = _get("SITE_BASE", "https://pratikamente.com.br").rstrip("/")
SITE_HOST = SITE_BASE.replace("https://", "").replace("http://", "")
BRAND = "PRATIKAMENTE"
IG_HANDLE = _get("IG_HANDLE", "@pratikamente.ofc")

APPROVAL_MODE = _get("APPROVAL_MODE", "manual").lower()  # manual | auto
CLAUDE_MODEL = _get("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_SLIDES = max(5, min(10, int(_get("MAX_SLIDES", "10"))))
MIN_TEXT_CHARS = int(_get("MIN_TEXT_CHARS", "1500"))
AI_IMAGE_NOTICE = _get("AI_IMAGE_NOTICE", "false").lower() == "true"

IG_API_VERSION = _get("IG_API_VERSION", "v26.0")
IG_USER_ID = _get("IG_USER_ID", "me")

# JPEGs públicos para a Meta baixar: branch `media` servida pelo raw.githubusercontent.com (validado no projeto
# História em Dia). Alternativa: GitHub Pages, definindo MEDIA_BASE_URL.
MEDIA_BASE_URL = resolve_media_base(_get("MEDIA_BASE_URL"), f"https://raw.githubusercontent.com/{REPO}/media")

GITHUB_TOKEN = _get("GITHUB_TOKEN")
USER_AGENT = "PratikamenteBot/1.0 (+https://pratikamente.com.br)"
STATE_PATH = "state/state.json"
