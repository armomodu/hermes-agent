#!/usr/bin/env python3
"""Submit one validated Bernard decomposition without shell data plumbing."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


SERVICE_USER_AGENT = "Hermes-Mission-Control/1.0"


def load_payload(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != "decomposition_result":
        raise ValueError("payload kind must be decomposition_result")
    objective_id = payload.get("objectiveId")
    if not isinstance(objective_id, str) or not objective_id.strip():
        raise ValueError("payload objectiveId must be a non-empty string")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("payload tasks must be a non-empty list")
    return payload


def build_endpoint(api_base: str, objective_id: str) -> str:
    base = api_base.strip().rstrip("/")
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("MC_API_URL must be an absolute HTTP(S) URL")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("non-local Mission Control submissions require HTTPS")
    return f"{base}/objectives/{urllib.parse.quote(objective_id, safe='')}/decompose"


def submit(payload: dict, api_base: str, token: str, timeout: float) -> tuple[int, object]:
    endpoint = build_endpoint(api_base, str(payload["objectiveId"]))
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": SERVICE_USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return int(response.status), json.loads(body) if body.strip() else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload")
    parser.add_argument("--response", default="decomposition-response.json")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    try:
        payload = load_payload(Path(args.payload))
        api_base = os.environ.get("MC_API_URL", "").strip()
        token = os.environ.get("CRON_SERVICE_TOKEN", "").strip()
        if not api_base:
            raise ValueError("MC_API_URL is required")
        if not token:
            raise ValueError("CRON_SERVICE_TOKEN is required")
        status, response = submit(payload, api_base, token, args.timeout)
        Path(args.response).write_text(
            json.dumps(response, indent=2) + "\n",
            encoding="utf-8",
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"DECOMPOSITION SUBMIT HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(f"DECOMPOSITION SUBMIT ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({
        "ok": True,
        "status": status,
        "objectiveId": payload["objectiveId"],
        "responsePath": str(Path(args.response)),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
