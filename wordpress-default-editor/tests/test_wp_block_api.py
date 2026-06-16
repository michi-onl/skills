import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import scripts.wp_block_api as api


@pytest.fixture(scope="module")
def mock_server():
    """Start the Flask mock server for the duration of the test module."""
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "scripts/mock_wp_server.py"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(50):
        try:
            urllib.request.urlopen(
                "http://127.0.0.1:5001/wp-json/wp/v2/pages",
                timeout=1,
            )
            break
        except urllib.error.HTTPError:
            # Server responded (e.g. 401 unauthenticated) -> it is up.
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("Mock server did not start")
    yield
    proc.terminate()
    proc.wait()


@pytest.fixture(autouse=True)
def restore_pages(request):
    """Snapshot mock page state and restore it after each server-backed test, so
    a test that mutates a page can't change the outcome of any other, in any order.
    No-ops for unit tests that don't start the server."""
    if "mock_server" not in request.fixturenames:
        yield
        return
    snapshot = {
        p["id"]: (p["content"]["raw"], p["status"]) for p in api.list_content("pages")
    }
    yield
    for pid, (raw, status) in snapshot.items():
        api.save_content("pages", pid, raw, status)


def test_fetch_raw_returns_blocks_and_status(mock_server):
    data = api.fetch_raw("pages", 1)
    assert data["id"] == 1
    assert data["status"] == "publish"
    assert "Welcome to our site" in data["content"]["raw"]


def test_backup_writes_content_and_status(mock_server):
    api.backup("pages", 1)
    site_dir = api.backup_dir()
    with open(f"{site_dir}/1_original.txt", encoding="utf-8") as f:
        assert "Welcome to our site" in f.read()
    with open(f"{site_dir}/1_status.txt", encoding="utf-8") as f:
        assert f.read().strip() == "publish"


def test_backup_namespaces_by_site(mock_server):
    """Two sites with the same page id must not share a backup file."""
    import shutil

    shutil.rmtree("/tmp/wp_backup", ignore_errors=True)
    api.backup("pages", 1)
    assert os.path.exists(f"{api.backup_dir()}/1_original.txt")
    # The flat, site-agnostic path must not be the write target.
    assert not os.path.exists("/tmp/wp_backup/1_original.txt")


def test_backup_dir_distinguishes_same_host_installs(monkeypatch):
    """Two installs sharing one host (subdir multisite, or http vs https) must
    not share a backup directory, or the same page id collides across sites."""
    monkeypatch.setenv("WP_SITE", "https://example.com/blog")
    blog = api.backup_dir()
    monkeypatch.setenv("WP_SITE", "https://example.com/shop")
    shop = api.backup_dir()
    monkeypatch.setenv("WP_SITE", "http://example.com")
    insecure = api.backup_dir()
    assert blog != shop
    assert blog != insecure


def test_update_block_text_changes_only_targeted_block():
    raw = (
        '<!-- wp:heading -->\n<h1>Welcome</h1>\n<!-- /wp:heading -->\n'
        '<!-- wp:paragraph -->\n<p>Hello</p>\n<!-- /wp:paragraph -->'
    )
    new = api.update_block_text(raw, "paragraph", "Hello", "Hola")
    assert "Hola" in new
    assert "Welcome" in new
    assert "Hello" not in new


def test_update_block_text_refuses_ambiguous_match():
    raw = (
        '<!-- wp:paragraph -->\n<p>Save now</p>\n<!-- /wp:paragraph -->\n'
        '<!-- wp:paragraph -->\n<p>Save now</p>\n<!-- /wp:paragraph -->'
    )
    with pytest.raises(ValueError, match="2 .*paragraph"):
        api.update_block_text(raw, "paragraph", "Save now", "Buy now")


def test_verify_only_text_changed_passes_and_fails():
    old = (
        '<!-- wp:heading -->\n<h1>Welcome</h1>\n<!-- /wp:heading -->\n'
        '<!-- wp:paragraph -->\n<p>Hello</p>\n<!-- /wp:paragraph -->'
    )
    new = api.update_block_text(old, "paragraph", "Hello", "Hola")
    assert api.verify_only_text_changed(old, new, "paragraph", "Hello")

    bad = old.replace("Welcome", "Goodbye")
    assert not api.verify_only_text_changed(old, bad, "paragraph", "Hello")


def test_save_content_preserves_status(mock_server):
    data = api.fetch_raw("pages", 1)
    updated = api.update_block_text(
        data["content"]["raw"],
        "paragraph",
        "placeholder text",
        "new copy",
    )
    api.save_content("pages", 1, updated, data["status"])
    after = api.fetch_raw("pages", 1)
    assert "new copy" in after["content"]["raw"]
    assert after["status"] == "publish"


def test_save_content_does_not_publish_draft(mock_server):
    data = api.fetch_raw("pages", 2)
    updated = api.update_block_text(
        data["content"]["raw"],
        "paragraph",
        "Draft placeholder",
        "Updated draft copy",
    )
    api.save_content("pages", 2, updated, data["status"])
    after = api.fetch_raw("pages", 2)
    assert after["status"] == "draft"


def test_update_block_text_refuses_non_leaf_block():
    raw = (
        '<!-- wp:buttons -->\n<div class="wp-block-buttons"><!-- wp:button -->\n'
        '<a class="wp-block-button__link">Click me</a>\n'
        '<!-- /wp:button --></div>\n<!-- /wp:buttons -->'
    )
    with pytest.raises(ValueError):
        api.update_block_text(raw, "buttons", "Click me", "Press me")


def test_rollback_restores_content_and_status(mock_server):
    import scripts.rollback as rb

    original = api.backup("pages", 2)
    orig_raw = original["content"]["raw"]
    orig_status = original["status"]

    # Mutate both content and status away from the original.
    api.save_content(
        "pages",
        2,
        "<!-- wp:paragraph -->\n<p>Temp mutation</p>\n<!-- /wp:paragraph -->",
        "publish",
    )
    mutated = api.fetch_raw("pages", 2)
    assert "Temp mutation" in mutated["content"]["raw"]

    # Roll back from /tmp/wp_backup/.
    rb.rollback(2, "pages")
    restored = api.fetch_raw("pages", 2)
    assert restored["content"]["raw"] == orig_raw
    assert restored["status"] == orig_status
    assert "Temp mutation" not in restored["content"]["raw"]


def test_rollback_preserves_trailing_newline(mock_server):
    import scripts.rollback as rb

    original = "<!-- wp:paragraph -->\n<p>Keep newline</p>\n<!-- /wp:paragraph -->\n"
    api.save_content("pages", 1, original, "publish")
    api.backup("pages", 1)
    api.save_content(
        "pages",
        1,
        "<!-- wp:paragraph -->\n<p>changed</p>\n<!-- /wp:paragraph -->",
        "publish",
    )
    rb.rollback(1, "pages")
    restored = api.fetch_raw("pages", 1)
    assert restored["content"]["raw"] == original
