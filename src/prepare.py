"""Rotina diária: descobre a próxima página, gera o carrossel e abre o Issue de aprovação
(ou publica direto no modo automático, quando a revisão não aponta risco)."""
import sys
from pathlib import Path

from . import config, discover, github_api, state as st
from .caption import build_caption
from .extract import extract
from .instagram import Instagram
from .media import push_media, wait_for_urls
from .plan import make_plan
from .publish import do_publish, record_posted
from .render import build_slides, save_jpegs
from .review import review
from .token import get_token

ROOT = Path(__file__).resolve().parent.parent


def alert(title: str, body: str) -> None:
    try:
        github_api.create_issue(title, body, ["falha"])
    except Exception as e:  # noqa: BLE001
        print(f"[alert] não foi possível abrir o Issue de falha: {e}", file=sys.stderr)


def get_cover(slug: str, page: dict) -> bytes | None:
    override = ROOT / "overrides" / f"{slug}.jpg"
    if override.exists():
        print("[prepare] usando imagem de override.")
        return override.read_bytes()
    return discover.download_image(page["cover_url"]) if page.get("cover_url") else None


def run() -> int:
    state = st.load()
    if state.get("pending"):
        print(f"Já existe um carrossel pendente ({state['pending']['slug']}). Nada a fazer.")
        return 0

    # Saúde do token antes de gastar chamadas ao Claude.
    ig_check = Instagram(get_token(state)).whoami()
    print(f"[prepare] Instagram ok: @{ig_check.get('username')}")

    done = {p["slug"] for p in state["posted"] + state["skipped"]}
    post = discover.next_post(done)
    if not post:
        print("Nada novo no site. Fila em dia.")
        return 0
    print(f"[prepare] próxima página: {post['slug']}")

    page = discover.fetch_page(post["link"], post["id"])
    page["category"] = post.get("category", "Outros")
    if len(page["text"]) < config.MIN_TEXT_CHARS:
        raise RuntimeError(
            f"Texto da página insuficiente ({len(page['text'])} caracteres, fonte: {page.get('text_source')}) em "
            f"{post['link']}. O robô não gera carrossel sem conteúdo suficiente para evitar informações inventadas.")
    cover = get_cover(post["slug"], page)

    carousel = extract(page)
    rev = review(page, carousel, cover)
    for _ in range(2):
        if rev.verdict != "ajustar":
            break
        print(f"[prepare] ajustando: {rev.fixes}")
        carousel = extract(page, feedback=rev.fixes)
        rev = review(page, carousel, cover)
    verdict = rev.verdict
    if verdict == "ajustar":
        verdict = "reter"
    if carousel.risk.level == "alto" or not rev.image_ok:
        verdict = "reter"

    plan = make_plan(carousel)
    caption = build_caption(carousel, plan, post["link"])
    slides = build_slides(carousel, plan, cover)
    out_dir = ROOT / "out" / post["slug"]
    files = save_jpegs(slides, out_dir)
    urls = push_media(post["slug"], files)
    wait_for_urls(urls)

    reasons = "; ".join(rev.reasons + rev.image_flags + carousel.risk.reasons) or "sem observações"
    summary = {"ok": f"✅ ok ({reasons})", "reter": f"⚠️ RETIDO para decisão humana: {reasons}"}[verdict]
    pending = {
        "slug": post["slug"], "wp_id": post["id"], "link": post["link"], "title": page["title"],
        "title": carousel.cover_title, "category": carousel.category, "slides": urls, "caption": caption,
        "verdict": verdict, "status": "awaiting", "issue": None, "created_at": st.now_iso(),
    }

    if config.APPROVAL_MODE == "auto" and verdict == "ok":
        state["pending"] = pending
        res = do_publish(state, pending, caption)
        record_posted(state, pending, res)
        print(f"[prepare] publicado automaticamente: {res.get('permalink')}")
        return 0

    labels = ["pendente"] if verdict == "ok" else ["pendente", "retido"]
    pending["issue"] = github_api.create_issue(
        f"[Aprovar] {carousel.cover_title[:80]}", github_api.issue_body(pending, summary), labels)
    state["pending"] = pending
    st.commit(state, f"pendente: {post['slug']}")
    print(f"[prepare] Issue #{pending['issue']} aberto para aprovação.")
    return 0


def main() -> int:
    try:
        return run()
    except Exception as e:  # noqa: BLE001
        alert("[Falha] preparo diário do carrossel", f"```\n{str(e)[:1500]}\n```\nVeja o log da execução no Actions.")
        raise


if __name__ == "__main__":
    sys.exit(main())
