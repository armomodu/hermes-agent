#!/usr/bin/env python3
"""Fetch one governed Mission Control objective for Bernard decomposition."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable


def fetch_objective(
    objective_id: str,
    base_url: str,
    token: str,
    opener: Callable[..., object] = urllib.request.urlopen,
) -> dict:
    url = f"{base_url.rstrip('/')}/objectives/{urllib.parse.quote(objective_id, safe='')}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Hermes-Mission-Control/1.0",
        },
    )
    with opener(request, timeout=30) as response:
        objective = json.loads(response.read().decode("utf-8"))
    if not isinstance(objective, dict) or objective.get("id") != objective_id:
        raise ValueError("objective response does not match the governed objective")
    return objective


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("objective_id")
    parser.add_argument("output")
    args = parser.parse_args()

    base_url = os.environ.get("MC_API_URL", "").strip().rstrip("/")
    token = os.environ.get("CRON_SERVICE_TOKEN", "").strip()
    if not base_url or not token:
        parser.error("MC_API_URL and CRON_SERVICE_TOKEN are required")
    try:
        objective = fetch_objective(args.objective_id, base_url, token)
    except (OSError, urllib.error.HTTPError, json.JSONDecodeError, ValueError) as exc:
        parser.error(f"objective fetch failed: {exc}")
    Path(args.output).write_text(json.dumps(objective, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "objectiveId": args.objective_id, "output": args.output}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
