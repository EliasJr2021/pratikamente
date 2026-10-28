"""Publicação (após aprovação) e registro do resultado."""
import os
import sys

from . import config, github_api, state as st
from .instagram import IGError, Instagram
from .media import wait_for_urls
from .token import get_token


def do_publish(state: dict, pending: dict, caption: str) -> dict:
    ig = Instagram(get_token(state))
    # Idempotência: se uma tentativa anterior chegou a publicar, não publica de novo.
    if pending.get("status") == "publishing":
        found = ig.find_recent_by_caption(caption)
        if found:
            print("[publish] post já existe na conta; apenas registrando.")
            return {"id": found["id"], "permalink": found.get("permalink", "")}
    print("[publish] cota:", ig.quota())
    wait_for_urls(pending["slides"], timeout=120)
    creation = ig.create_carousel(pending["slides"], caption, ai_generated=config.AI_IMAGE_NOTICE)
    pending["status"] = "publishing"
    pending["creation_id"] = creation
    state["pending"] = pending
    st.commit(state, f"publicando {pending['slug']}")
    return ig.publish(creation)


def record_posted(state: dict, pending: dict, res: dict) -> None:
    state["posted"].append({
        "slug": pending["slug"], "wp_id": pending.get("wp_id"), "link": pending["link"],
        "title": pending["title"], "ig_media_id": res["id"],
        "permalink": res.get("permalink", ""), "posted_at": st.now_iso(),
    })
    state["pending"] = None
    st.commit(state, f"publicado: {pending['slug']}")


def main() -> int:
    state = st.load()
    pending = state.get("pending")
    if not pending:
        print("Nada pendente.")
        return 0

    event = os.getenv("EVENT_NAME", "workflow_dispatch")
    issue_no = pending.get("issue")
    if event == "issue_comment":
        if os.getenv("COMMENT_AUTHOR_ASSOCIATION") != "OWNER":
            print("Comentário ignorado: não é do dono do repositório.")
            return 0
        if int(os.getenv("ISSUE_NUMBER", "0")) != issue_no:
            print("Comentário em outro Issue; ignorado.")
            return 0
        words = (os.getenv("COMMENT_BODY", "").strip().split() or [""])
        cmd = words[0].lower()
    else:
        cmd = "/aprovar"

    if cmd == "/rejeitar":
        state["skipped"].append({"slug": pending["slug"], "reason": "rejeitado manualmente", "at": st.now_iso()})
        state["pending"] = None
        st.commit(state, f"pulado: {pending['slug']}")
        if issue_no:
            github_api.comment(issue_no, "Página pulada. A fila segue na próxima execução.")
            github_api.set_labels(issue_no, ["rejeitado"])
            github_api.close_issue(issue_no)
        return 0
    if cmd != "/aprovar":
        print("Comando não reconhecido; ignorado.")
        return 0

    caption = pending["caption"]
    if issue_no:
        parsed = github_api.parse_caption(github_api.get_issue(issue_no).get("body", ""))
        if parsed:
            caption = parsed
    try:
        res = do_publish(state, pending, caption)
    except (IGError, RuntimeError) as e:
        if issue_no:
            github_api.comment(issue_no, f"❌ Falha ao publicar:\n```\n{str(e)[:900]}\n```\nComente `/aprovar` para tentar de novo.")
            github_api.set_labels(issue_no, ["falha"])
        print(f"Falha: {e}", file=sys.stderr)
        return 1
    record_posted(state, pending, res)
    if issue_no:
        github_api.comment(issue_no, f"✅ Publicado: {res.get('permalink') or res['id']}")
        github_api.set_labels(issue_no, ["publicado"])
        github_api.close_issue(issue_no)
    return 0


if __name__ == "__main__":
    sys.exit(main())
