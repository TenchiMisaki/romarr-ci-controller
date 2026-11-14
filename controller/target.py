#!/usr/bin/env python3
"""Resolve an immutable public ROMarr source and independently recheck it.

The sole remote API host is api.github.com. Authentication is optional for local
checks, and the token is used *only* in the isolated metadata steps of Actions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FORK = "TenchiMisaki/romarr"
UPSTREAM = "BlizzHacker/romarr"
API = "https://api.github.com/repos/"
SHA = re.compile(r"^[0-9a-fA-F]{40}$")
PR = re.compile(r"^[1-9][0-9]{0,5}$")


class TargetError(RuntimeError):
    pass


def github_get(path: str, *, opener=urlopen, sleeper=time.sleep):
    """Read one fixed GitHub API path with bounded transient retries."""
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", path) or ".." in path:
        raise TargetError("Unsafe API path")
    url = API + path
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "romarr-ci-controller-read-only-v01",
    }
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    for attempt in range(1, 4):
        try:
            with opener(Request(url, headers=headers), timeout=12) as response:
                if response.status != 200:
                    raise TargetError(f"GitHub API returned HTTP {response.status}")
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504):
                raise TargetError(f"GitHub API HTTP {exc.code}") from None
            if attempt == 3:
                raise TargetError(f"GitHub API HTTP {exc.code}, retry limit exhausted") from None
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise TargetError("GitHub API unreachable, retry limit exhausted") from None
        sleeper(attempt * 2)
    raise TargetError("GitHub API query could not complete")


def require_sha(value, label):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise TargetError(f"{label} is not a full SHA-1 hex commit identifier")
    return value.lower()


def resolve(mode: str, pr: str, expected: str, fetch=github_get):
    if mode not in ("pull_request", "main"):
        raise TargetError("Target mode must be pull_request or main")
    if expected and not SHA.fullmatch(expected):
        raise TargetError("Expected SHA must be a complete 40-hex commit")
    expected = expected.lower()
    if mode == "main":
        fork = fetch(f"{FORK}/branches/main")
        upstream = fetch(f"{UPSTREAM}/branches/main")
        fork_sha = require_sha((fork.get("commit") or {}).get("sha"), "fork main")
        upstream_sha = require_sha((upstream.get("commit") or {}).get("sha"), "upstream main")
        if fork_sha != upstream_sha:
            raise TargetError("Fork main and upstream main differ; baseline requires identical refs")
        result = {
            "mode": "main", "repository": FORK, "number": None,
            "pr_url": None, "head_ref": "main", "base_ref": "main",
            "base_sha": upstream_sha, "sha": fork_sha,
        }
    else:
        if not PR.fullmatch(pr):
            raise TargetError("PR number must be a positive six-digit-or-shorter integer")
        data = fetch(f"{FORK}/pulls/{pr}")
        head = data.get("head") or {}
        base = data.get("base") or {}
        if data.get("state") != "open" or data.get("draft") is not False:
            raise TargetError("PR must be open and non-draft")
        if (head.get("repo") or {}).get("full_name") != FORK:
            raise TargetError("PR head is not inside the expected personal fork")
        if (base.get("repo") or {}).get("full_name") != FORK:
            raise TargetError("PR base is not inside the expected personal fork")
        if data.get("number") != int(pr):
            raise TargetError("GitHub PR number does not match the requested number")
        result = {
            "mode": mode, "repository": FORK, "number": int(pr),
            "pr_url": f"https://github.com/{FORK}/pull/{int(pr)}",
            "head_ref": head.get("ref"), "base_ref": base.get("ref"),
            "base_sha": require_sha(base.get("sha"), "PR base"),
            "sha": require_sha(head.get("sha"), "PR head"),
        }
        if not all(isinstance(result[k], str) and result[k] for k in ("head_ref", "base_ref")):
            raise TargetError("PR head or base ref is missing")
    if expected and expected != result["sha"]:
        raise TargetError("Expected SHA differs from the current source SHA")
    return result


def atomic_json(path: Path, content: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_suffix(path.suffix + ".partial")
    scratch.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scratch.replace(path)


def check_post(target: dict, checkout: Path, fetch=github_get):
    """Recheck live PR/base and local source without rewriting evidence."""
    result = {"status": "NOT_VERIFIED", "tested_sha": target["sha"], "details": []}
    try:
        if target["mode"] == "main":
            newer = resolve("main", "", "", fetch=fetch)
        else:
            newer = resolve("pull_request", str(target["number"]), "", fetch=fetch)
        if newer["sha"] != target["sha"]:
            result["details"].append("Source head changed during test; evidence is historic only")
        if newer["base_sha"] != target["base_sha"] or newer["base_ref"] != target["base_ref"]:
            result["details"].append("PR base changed during test; current-diff coverage is unconfirmed")
        if not checkout.is_dir():
            result["details"].append("Source checkout is unavailable")
        else:
            git = lambda *args: subprocess.run(
                ["git", "-C", str(checkout), *args],
                capture_output=True, text=True, timeout=15, check=False,
            )
            rev = git("rev-parse", "HEAD")
            status = git("status", "--porcelain", "--untracked-files=all")
            if rev.returncode != 0 or not SHA.fullmatch(rev.stdout.strip()):
                result["details"].append("Checkout commit read failed")
            elif rev.stdout.strip().lower() != target["sha"]:
                result["details"].append("Checked-out source SHA differs from tested SHA")
            if status.returncode != 0:
                result["details"].append("Git worktree status command failed")
            elif status.stdout.strip():
                result["details"].append("Source worktree is dirty after tests")
        result["status"] = "UNCHANGED" if not result["details"] else "STALE_OR_UNVERIFIED"
    except (TargetError, OSError, subprocess.SubprocessError) as exc:
        result["details"].append(f"Postcheck could not verify source: {type(exc).__name__}")
        result["status"] = "COLLECTION_FAILED"
    return result


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("resolve", "postcheck"):
        raise SystemExit("Usage: target.py resolve|postcheck")
    private = Path(os.environ["RUNNER_TEMP"]) / "romarr-ci-private"
    public = Path(os.environ["RUNNER_TEMP"]) / "romarr-ci-public"
    if sys.argv[1] == "resolve":
        target = resolve(os.environ["INPUT_TARGET"], os.environ.get("INPUT_PR_NUMBER", ""), os.environ.get("INPUT_EXPECTED_SHA", ""))
        atomic_json(private / "target.json", target)
        output = os.environ.get("GITHUB_OUTPUT")
        if output:
            with open(output, "a", encoding="utf-8") as handle:
                handle.write(f"sha={target['sha']}\n")
        print(f"PREFLIGHT PASS: {target['repository']} {target['mode']} commit {target['sha']}")
        return
    target = json.loads((private / "target.json").read_text(encoding="utf-8"))
    result = check_post(target, Path(os.environ["GITHUB_WORKSPACE"]) / "romarr")
    atomic_json(public / "postcheck.json", result)
    print(f"SOURCE POSTCHECK: {result['status']}; " + "; ".join(result["details"]))
    # The final evidence gate handles any non-success after artifact upload.


if __name__ == "__main__":
    try:
        main()
    except (TargetError, KeyError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"TARGET CHECK BLOCKED: {error if isinstance(error, TargetError) else type(error).__name__}", file=sys.stderr)
        raise SystemExit(2)
