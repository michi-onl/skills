
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import scripts.deploy as deploy
import scripts.wp_block_api as wp

BALANCED = "<!-- wp:paragraph -->\n<p>Hallo</p>\n<!-- /wp:paragraph -->"


def test_global_styles_css_injection(tmp_path, monkeypatch):
    captured = {}

    def fake_apply(settings, styles, *, confirm):
        captured["settings"] = settings
        captured["styles"] = styles
        captured["confirm"] = confirm
        return {"id": 7}

    monkeypatch.setattr(wp, "apply_global_styles", fake_apply)
    (tmp_path / "tokens.json").write_text(json.dumps(
        {"settings": {"layout": {}},
         "styles": {"typography": {"fontFamily": "x"}}}))
    (tmp_path / "c.css").write_text(".stuv-card{color:red}")
    t = {"type": "global-styles", "tokens": "tokens.json", "css": "c.css"}
    deploy._deploy_global_styles("global-styles", t, tmp_path, dry_run=False)
    assert captured["styles"]["css"] == ".stuv-card{color:red}"
    assert captured["styles"]["typography"]["fontFamily"] == "x"
    assert captured["confirm"] is True


def test_dir_source_joined_in_name_order(tmp_path):
    d = tmp_path / "sections"
    d.mkdir()
    (d / "02-b.html").write_text("zwei")
    (d / "01-a.html").write_text("eins")
    assert deploy._read_source(tmp_path, "sections") == "eins\n\nzwei"


def test_main_resolves_sources_relative_to_manifest(tmp_path, capsys):
    (tmp_path / "page.html").write_text(BALANCED)
    manifest = {"kontakt": {"type": "structural", "endpoint": "pages",
                            "id": 39, "source": "page.html", "status": "publish"}}
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest))
    deploy.main(["--manifest", str(mpath), "all", "--dry-run"])
    out = capsys.readouterr().out
    assert "[dry-run] pages/39 <- page.html" in out
    assert "balanced OK" in out
