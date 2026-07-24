from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "docs/runtime-skill-mirrors/bernard-decompose/scripts/submit_decomposition.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("submit_decomposition", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return b'{"ok":true,"taskCount":2}'


def test_load_payload_requires_valid_decomposition(tmp_path: Path):
    module = load_module()
    payload = tmp_path / "bad.json"
    payload.write_text('{"kind":"task_repair_result"}\n', encoding="utf-8")

    try:
        module.load_payload(payload)
    except ValueError as exc:
        assert str(exc) == "payload kind must be decomposition_result"
    else:
        raise AssertionError("invalid decomposition payload was accepted")


def test_submit_uses_authenticated_json_request_without_shell():
    module = load_module()
    payload = {
        "kind": "decomposition_result",
        "objectiveId": "objective-1",
        "tasks": [{"id": "task-1"}],
    }

    with patch.object(module.urllib.request, "urlopen", return_value=FakeResponse()) as call:
        status, response = module.submit(
            payload,
            "https://app.maroncorp.com/api",
            "secret-token",
            15,
        )

    assert status == 200
    assert response == {"ok": True, "taskCount": 2}
    request = call.call_args.args[0]
    assert request.full_url.endswith("/api/objectives/objective-1/decompose")
    assert request.method == "POST"
    assert json.loads(request.data) == payload
    assert request.headers["Authorization"] == "Bearer secret-token"


def test_submit_rejects_insecure_non_local_endpoint():
    module = load_module()

    try:
        module.build_endpoint("http://app.example.com/api", "objective-1")
    except ValueError as exc:
        assert str(exc) == "non-local Mission Control submissions require HTTPS"
    else:
        raise AssertionError("insecure remote endpoint was accepted")


def test_submitter_cli_posts_exact_payload(tmp_path: Path):
    received: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received["path"] = self.path
            received["authorization"] = self.headers.get("Authorization")
            received["payload"] = json.loads(
                self.rfile.read(int(self.headers["Content-Length"])),
            )
            body = b'{"ok":true,"taskCount":1}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    payload = {
        "kind": "decomposition_result",
        "objectiveId": "objective-e2e",
        "tasks": [{"id": "task-e2e"}],
    }
    payload_path = tmp_path / "decomposition.json"
    response_path = tmp_path / "response.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    env = {
        **os.environ,
        "MC_API_URL": f"http://127.0.0.1:{server.server_port}/api",
        "CRON_SERVICE_TOKEN": "test-token",
    }

    try:
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                str(payload_path),
                "--response",
                str(response_path),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert result.returncode == 0, result.stderr
    assert received == {
        "path": "/api/objectives/objective-e2e/decompose",
        "authorization": "Bearer test-token",
        "payload": payload,
    }
    assert json.loads(response_path.read_text()) == {"ok": True, "taskCount": 1}


def test_skill_uses_submit_helper_instead_of_curl():
    skill = (
        ROOT / "docs/runtime-skill-mirrors/bernard-decompose/SKILL.md"
    ).read_text(encoding="utf-8")

    assert "scripts/submit_decomposition.py" in skill
    assert "Submit the exact validated `decomposition.json` once" in skill
