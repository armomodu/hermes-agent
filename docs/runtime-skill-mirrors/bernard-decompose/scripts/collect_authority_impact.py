#!/usr/bin/env python3
"""Collect source-reference candidates for authority-first decomposition."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def repo_relative(repo: Path, value: str) -> str:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (repo / path).resolve()
    try:
        return resolved.relative_to(repo).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {value}") from exc


def collect_matches(repo: Path, symbol: str, excluded_paths: set[str]) -> list[str]:
    result = subprocess.run(
        [
            "rg",
            "--files-with-matches",
            "--fixed-strings",
            "--glob",
            "!node_modules/**",
            "--glob",
            "!.next/**",
            "--glob",
            "!dist/**",
            "--glob",
            "!coverage/**",
            symbol,
            ".",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or f"rg failed for {symbol}")
    return sorted({
        line.removeprefix("./").strip()
        for line in result.stdout.splitlines()
        if line.strip() and line.removeprefix("./").strip() not in excluded_paths
    })


def collect(repo: Path, request: dict, excluded_paths: set[str] | None = None) -> dict:
    if request.get("kind") != "authority-impact-request.v1":
        raise ValueError("kind must be authority-impact-request.v1")
    authorities = request.get("authorities")
    if not isinstance(authorities, list) or not authorities:
        raise ValueError("authorities must be a non-empty list")

    output: list[dict] = []
    excluded = excluded_paths or set()
    for index, authority in enumerate(authorities):
        if not isinstance(authority, dict):
            raise ValueError(f"authorities[{index}] must be an object")
        authority_path = repo_relative(repo, str(authority.get("path") or ""))
        symbols = authority.get("symbols")
        if not isinstance(symbols, list) or any(
            not isinstance(symbol, str) or not symbol.strip() for symbol in symbols
        ):
            raise ValueError(f"authorities[{index}].symbols must be a string list")
        matches: dict[str, set[str]] = {}
        for symbol in symbols:
            for path in collect_matches(repo, symbol.strip(), excluded):
                if path == authority_path:
                    continue
                matches.setdefault(path, set()).add(symbol.strip())
        output.append({
            "authorityPath": authority_path,
            "changeKind": str(authority.get("changeKind") or "shared_interface"),
            "symbols": [symbol.strip() for symbol in symbols],
            "candidates": [
                {"path": path, "matchedSymbols": sorted(matched)}
                for path, matched in sorted(matches.items())
            ],
        })
    return {"kind": "authority-impact-evidence.v1", "authorities": output}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        repo = Path(args.repo).resolve()
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        excluded_paths = {
            repo_relative(repo, args.request),
            repo_relative(repo, args.output),
        }
        result = collect(repo, request, excluded_paths)
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"AUTHORITY IMPACT ERROR: {exc}")
        return 1
    print(json.dumps({"ok": True, "authorityCount": len(result["authorities"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
