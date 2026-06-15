#!/usr/bin/env python3
"""
Lightweight mock WordPress REST API for testing the default editor skill.
Run: WP_USER=test WP_APP_PASS=pass python3 scripts/mock_wp_server.py
"""
import base64
import json
import logging
import os
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

USER = os.environ.get("WP_USER", "test")
PASS = os.environ.get("WP_APP_PASS", "pass")
LOG_FILE = "/tmp/wp_mock_server.log"
DATA_FILE = Path(__file__).with_name("mock_data") / "pages.json"

logger = logging.getLogger("mock_wp_server")
logger.setLevel(logging.INFO)
_file_handler = logging.FileHandler(LOG_FILE)
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(_file_handler)
logger.propagate = False

with DATA_FILE.open(encoding="utf-8") as f:
    PAGES = {p["id"]: p for p in json.load(f)["pages"]}


def _check_auth():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header[6:]).decode()
        return decoded == f"{USER}:{PASS}"
    except Exception:
        return False


def _fields_filter(data, fields):
    if not fields:
        return data
    keys = fields.split(",")
    return {k: data.get(k) for k in keys}


def _log_request():
    logger.info("%s %s", request.method, request.full_path)


@app.route("/wp-json/wp/v2/pages", methods=["GET"])
def list_pages():
    _log_request()
    if not _check_auth():
        return jsonify({"code": "rest_not_logged_in"}), 401
    fields = request.args.get("_fields")
    try:
        per_page = int(request.args.get("per_page", 10))
        page = int(request.args.get("page", 1))
        if per_page <= 0 or page <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"code": "rest_invalid_param"}), 400
    items = list(PAGES.values())
    start = (page - 1) * per_page
    out = [_fields_filter(i, fields) for i in items[start:start + per_page]]
    return jsonify(out)


@app.route("/wp-json/wp/v2/pages/<int:pid>", methods=["GET", "POST", "PUT", "PATCH"])
def single_page(pid):
    _log_request()
    if not _check_auth():
        return jsonify({"code": "rest_not_logged_in"}), 401
    if pid not in PAGES:
        return jsonify({"code": "rest_post_invalid_id"}), 404
    if request.method in ("POST", "PUT", "PATCH"):
        payload = request.get_json(force=True, silent=True) or {}
        if "content" in payload:
            PAGES[pid]["content"]["raw"] = payload["content"]
            PAGES[pid]["content"]["rendered"] = payload["content"]
        if "status" in payload:
            PAGES[pid]["status"] = payload["status"]
    fields = request.args.get("_fields")
    return jsonify(_fields_filter(PAGES[pid], fields))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
