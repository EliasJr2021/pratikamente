"""Teste de integração com tudo externo simulado (site, Claude, GitHub, Instagram)."""
import io

import pytest
from PIL import Image

from src import prepare, publish, state as st
from src.models import Review
from tests.fixtures import sample


def _cover():
    b = io.BytesIO()
    Image.new("RGB", (1024, 1024), (60, 80, 110)).save(b, "JPEG")
    return b.getvalue()


def _patch_common(monkeypatch, tmp_path, issues):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STATE_KEY", "")
    monkeypatch.setenv("IG_TOKEN_INICIAL", "tok")
    monkeypatch.setattr(prepare, "ROOT", tmp_path)
    monkeypatch.setattr(prepare.Instagram, "whoami", lambda self: {"username": "pratikamente"})
    monkeypatch.setattr(prepare.discover, "next_post", lambda done: None if "origem-geologica" in done else
                        {"id": 7, "slug": "origem-geologica", "link": "https://site/origem-geologica/",
                         "title": "Origem geológica", "category": "Ciência"})
    monkeypatch.setattr(prepare.discover, "fetch_page", lambda link, pid=0: {
        "link": link, "title": "t", "cover_url": "u", "text": "texto " * 400, "text_source": "rest"})
    monkeypatch.setattr(prepare.discover, "download_image", lambda u: _cover())
    monkeypatch.setattr(prepare, "extract", lambda page, feedback=None: sample())
    monkeypatch.setattr(prepare, "review", lambda p, c, cv: Review(
        verdict="ok", reasons=["fiel ao artigo"], fixes=[], image_ok=True, image_flags=[]))
    monkeypatch.setattr(prepare, "push_media", lambda slug, files: [f"https://m/{slug}/{f.name}" for f in files])
    monkeypatch.setattr(prepare, "wait_for_urls", lambda urls: None)

    def fake_issue(title, body, labels):
        issues.append((title, body, labels))
        return 42
    monkeypatch.setattr(prepare.github_api, "create_issue", fake_issue)


def test_manual_mode_creates_issue_and_pending(monkeypatch, tmp_path):
    issues = []
    _patch_common(monkeypatch, tmp_path, issues)
    monkeypatch.setattr(prepare.config, "APPROVAL_MODE", "manual")
    assert prepare.run() == 0
    s = st.load()
    assert s["pending"]["issue"] == 42 and s["pending"]["status"] == "awaiting"
    assert issues and "pendente" in issues[0][2] and issues[0][0].startswith("[Aprovar]")
    assert prepare.run() == 0 and len(issues) == 1   # já há pendente: não cria outro


def test_approve_publishes_once_and_owner_only(monkeypatch, tmp_path):
    issues = []
    _patch_common(monkeypatch, tmp_path, issues)
    monkeypatch.setattr(prepare.config, "APPROVAL_MODE", "manual")
    prepare.run()
    calls = {"create": 0, "publish": 0}
    monkeypatch.setattr(publish, "wait_for_urls", lambda urls, timeout=0: None)
    monkeypatch.setattr(publish.Instagram, "quota", lambda self: {"data": []})
    monkeypatch.setattr(publish.Instagram, "recent_media", lambda self, limit=10: [])

    def create(self, urls, caption, ai_generated=False):
        calls["create"] += 1
        return "cid1"

    def pub(self, cid):
        calls["publish"] += 1
        return {"id": "m1", "permalink": "https://instagram.com/p/x"}
    monkeypatch.setattr(publish.Instagram, "create_carousel", create)
    monkeypatch.setattr(publish.Instagram, "publish", pub)
    monkeypatch.setattr(publish.github_api, "get_issue", lambda n: {"body": ""})
    for fn in ("comment", "set_labels", "close_issue"):
        monkeypatch.setattr(publish.github_api, fn, lambda *a, **k: None)
    monkeypatch.setenv("EVENT_NAME", "issue_comment")
    monkeypatch.setenv("COMMENT_BODY", "/aprovar")
    monkeypatch.setenv("COMMENT_AUTHOR_ASSOCIATION", "OWNER")
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    assert publish.main() == 0
    s = st.load()
    assert s["pending"] is None and s["posted"][0]["ig_media_id"] == "m1"
    assert s["posted"][0]["title"] == sample().cover_title
    assert calls == {"create": 1, "publish": 1}
    monkeypatch.setenv("COMMENT_AUTHOR_ASSOCIATION", "NONE")
    assert publish.main() == 0 and calls["publish"] == 1


def test_reject_skips_article(monkeypatch, tmp_path):
    issues = []
    _patch_common(monkeypatch, tmp_path, issues)
    prepare.run()
    for fn in ("comment", "set_labels", "close_issue"):
        monkeypatch.setattr(publish.github_api, fn, lambda *a, **k: None)
    monkeypatch.setenv("EVENT_NAME", "issue_comment")
    monkeypatch.setenv("COMMENT_BODY", "/rejeitar")
    monkeypatch.setenv("COMMENT_AUTHOR_ASSOCIATION", "OWNER")
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    publish.main()
    s = st.load()
    assert s["pending"] is None and s["skipped"][0]["slug"] == "origem-geologica"


def test_held_when_review_says_reter(monkeypatch, tmp_path):
    issues = []
    _patch_common(monkeypatch, tmp_path, issues)
    monkeypatch.setattr(prepare, "review", lambda p, c, cv: Review(
        verdict="reter", reasons=["imagem com logotipo"], fixes=[], image_ok=False, image_flags=["logotipo"]))
    monkeypatch.setattr(prepare.config, "APPROVAL_MODE", "auto")
    prepare.run()
    assert "retido" in issues[0][2] and st.load()["pending"]["verdict"] == "reter"


def test_short_text_is_blocked(monkeypatch, tmp_path):
    issues = []
    _patch_common(monkeypatch, tmp_path, issues)
    monkeypatch.setattr(prepare.discover, "fetch_page", lambda link, pid=0: {
        "link": link, "title": "t", "cover_url": "u", "text": "x" * 652, "text_source": "html"})
    monkeypatch.setattr(prepare.github_api, "create_issue", lambda *a, **k: 1)
    with pytest.raises(RuntimeError, match="insuficiente"):
        prepare.run()
    assert st.load()["pending"] is None
