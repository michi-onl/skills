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


def test_fetch_raw_returns_blocks_and_status(mock_server):
    data = api.fetch_raw("pages", 1)
    assert data["id"] == 1
    assert data["status"] == "publish"
    assert "Welcome to our site" in data["content"]["raw"]


def test_backup_writes_content_and_status(mock_server):
    api.backup("pages", 1)
    with open("/tmp/wp_backup/1_original.txt", encoding="utf-8") as f:
        assert "Welcome to our site" in f.read()
    with open("/tmp/wp_backup/1_status.txt", encoding="utf-8") as f:
        assert f.read().strip() == "publish"


def test_update_block_text_changes_only_targeted_block():
    raw = (
        '<!-- wp:heading -->\n<h1>Welcome</h1>\n<!-- /wp:heading -->\n'
        '<!-- wp:paragraph -->\n<p>Hello</p>\n<!-- /wp:paragraph -->'
    )
    new = api.update_block_text(raw, "paragraph", "Hello", "Hola")
    assert "Hola" in new
    assert "Welcome" in new
    assert "Hello" not in new


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
