import io
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

from src import caption, discover, github_api, plan as plan_mod, render
from src.models import Carousel
from tests.fixtures import SAMPLE, sample

ROOT = Path(__file__).resolve().parent.parent


def test_article_filter():
    assert discover.is_article("Decifrado após 4.000 anos", "origem-geologica-devils-arrows")
    assert not discover.is_article("Olá, mundo!", "ola-mundo")
    assert not discover.is_article("Hello world!", "hello-world")


def test_category_hint_skips_uncategorized():
    cats = {1: {"name": "Uncategorized", "slug": "uncategorized"}, 2: {"name": "Ciência", "slug": "ciencia"}}
    assert discover.category_hint([1, 2], cats) == "Ciência"
    assert discover.category_hint([1], cats) == "Outros"
    assert discover.category_hint([], {}) == "Outros"


def test_plan_caps_points():
    data = json.loads(json.dumps(SAMPLE))
    data["points"] = data["points"] + [dict(data["points"][0], heading=f"Extra {i}") for i in range(3)]
    c = Carousel.model_validate(data)
    p = plan_mod.make_plan(c, max_slides=10)
    assert len(p.points) == 7 and p.total_slides == 10
    assert plan_mod.make_plan(c, max_slides=6).total_slides == 6


def test_caption_limits_link_and_tags():
    c = sample()
    p = plan_mod.make_plan(c)
    cap = caption.build_caption(c, p, "https://pratikamente.com.br/origem-geologica-devils-arrows/")
    assert len(cap) <= 2200
    assert "utm_source=instagram" in cap
    assert cap.splitlines()[0] == c.hook
    assert "hoje" not in cap.lower()
    assert cap.splitlines()[-1].count("#") <= 8


def test_health_disclaimer_in_caption():
    data = json.loads(json.dumps(SAMPLE))
    data["health_disclaimer"] = True
    c = Carousel.model_validate(data)
    cap = caption.build_caption(c, plan_mod.make_plan(c), "https://x/y/")
    assert "profissional de saúde" in cap


@pytest.mark.parametrize("size", [None, (1024, 1024), (1536, 1024), (1344, 768), (1376, 768)])
def test_render_any_cover(size, tmp_path):
    c = sample()
    p = plan_mod.make_plan(c)
    cover = None
    if size:
        buf = io.BytesIO()
        Image.new("RGB", size, (50, 70, 100)).save(buf, "JPEG")
        cover = buf.getvalue()
    slides = render.build_slides(c, p, cover)
    assert len(slides) == p.total_slides
    paths = render.save_jpegs(slides, tmp_path)
    for f in paths:
        im = Image.open(f)
        assert im.size == (1080, 1350) and im.format == "JPEG"
        assert f.stat().st_size < 8 * 1024 * 1024


@pytest.mark.parametrize("cat", ["ciencia", "curiosidades", "misterios", "tecnologia", "outros"])
def test_all_categories_render(cat):
    data = json.loads(json.dumps(SAMPLE))
    data["category"] = cat
    c = Carousel.model_validate(data)
    assert render.build_slides(c, plan_mod.make_plan(c), None)


def test_caption_roundtrip_from_issue_body():
    pending = {"title": "Título", "link": "https://x", "slides": ["https://a/1.jpg"], "caption": "Linha 1\nLinha 2 #tag"}
    body = github_api.issue_body(pending, "ok")
    assert github_api.parse_caption(body) == "Linha 1\nLinha 2 #tag"
    assert "Linha editada" in github_api.parse_caption(body.replace("Linha 2", "Linha editada"))


def test_text_source_prefers_rest():
    art = "artigo " * 400
    chrome = "menu popular posts " * 2000
    assert discover.choose_text(art, art + chrome) == (art, "rest")
    assert discover.choose_text("curto", chrome)[1] == "html"


def test_workflows_valid_and_owner_guard():
    for f in (ROOT / ".github" / "workflows").glob("*.yml"):
        assert "jobs" in yaml.safe_load(f.read_text())
    publish = (ROOT / ".github" / "workflows" / "publish.yml").read_text()
    assert "author_association == 'OWNER'" in publish and "pull_request_target" not in publish


def test_validation_rejects_long_heading():
    data = json.loads(json.dumps(SAMPLE))
    data["points"][0]["heading"] = "x" * 90
    with pytest.raises(Exception):
        Carousel.model_validate(data)
