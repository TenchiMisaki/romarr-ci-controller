"""Bounded, exact-PR, read-only GitHub receipt collector (not a scheduler).

This code accesses only public GitHub metadata for an explicitly pinned ROMarr
PR and its controller run. No GitHub write API is available, no source is
executed, no local repository is modified, and no artifact content is printed.
The verified archive exists only within a temporary directory and is deleted.

This candidate is intentionally NOT connected to a scheduled workflow.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import time
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from public_evidence import inspect
from receipt_acceptance import verify_receipt, ReceiptError

SOURCE = "TenchiMisaki/romarr"
CONTROLLER = "TenchiMisaki/romarr-ci-controller"
API_ROOT = "https://api.github.com/"
SHA = re.compile(r"[0-9a-f]{40}\Z")
RUN_ID = re.compile(r"[1-9][0-9]{0,18}\Z")
MAX_JSON = 2 * 1024 * 1024
MAX_ARCHIVE = 16 * 1024 * 1024
API_VERSION = "2026-03-10"


class CollectionError(ValueError):
    """An exact-target, source, API, redirect, or evidence gate failed."""


class _NeverFollow(HTTPRedirectHandler):
    """Forbid transparent redirects, especially redirects carrying credentials."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _must(ok, reason):
    if not ok:
        raise CollectionError(reason)


def _positive(x):
    return type(x) is int and 0 < x <= 9999999999999999999


def _sha(x):
    return isinstance(x, str) and SHA.fullmatch(x) is not None


def _host_is_artifact_storage(url):
    """Only GitHub's documented Actions artifact storage network domains."""
    if not isinstance(url, str) or len(url) > 4096:
        return False
    try:
        u = urlsplit(url)
        hostname = u.hostname
        return (u.scheme == "https" and isinstance(hostname, str)
                and u.port in (None, 443) and not u.username and not u.password
                and bool(u.path) and not u.fragment
                and (hostname == "results-receiver.actions.githubusercontent.com"
                     or hostname.endswith(".actions.githubusercontent.com")
                     or hostname.endswith(".blob.core.windows.net")))
    except ValueError:
        return False


def _unique_pairs(pairs):
    o = {}
    for k, v in pairs:
        if k in o:
            raise CollectionError("Duplicate GitHub metadata JSON field")
        o[k] = v
    return o


class GitHubReadClient:
    """GET-only, pinned GitHub REST transport; never follows API redirects."""

    def __init__(self, token="", opener=None, sleep=time.sleep):
        self.token = token
        self.opener = opener if opener is not None else build_opener(_NeverFollow())
        self.sleep = sleep

    def _open(self, req, *, timeout):
        try:
            return self.opener.open(req, timeout=timeout)
        except HTTPError as exc:
            # Do not include URLs, headers, query strings or raw response data.
            raise CollectionError("GitHub GET HTTP " + str(exc.code)) from None
        except (URLError, TimeoutError, ConnectionError, OSError):
            raise CollectionError("GitHub GET transport failed") from None

    def _url(self, path):
        _must(isinstance(path, str) and path.startswith("repos/")
              and ".." not in path and ":" not in path and "#" not in path
              and "\\" not in path and not path.startswith("//"),
              "Invalid API path")
        _must(path.startswith("repos/" + SOURCE + "/") or
              path.startswith("repos/" + CONTROLLER + "/"),
              "Unapproved GitHub repository")
        return API_ROOT + path

    def get(self, path):
        """Read bounded JSON from an exact GitHub API URL; never disclose data."""
        url = self._url(path)
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": API_VERSION,
                   "User-Agent": "romarr-receipt-collector-v01"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = Request(url, headers=headers, method="GET")
        # Bounded retries ONLY for transient read failures. Never retry auth,
        # invalid source/JSON, missing refs or rate limits without a known wait.
        for attempt in range(1, 4):
            try:
                with self.opener.open(req, timeout=15) as response:
                    _must(response.status == 200, "Unexpected GitHub GET response")
                    raw = response.read(MAX_JSON + 1)
                break
            except HTTPError as exc:
                if exc.code not in (408, 500, 502, 503, 504) or attempt == 3:
                    raise CollectionError("GitHub GET HTTP " + str(exc.code)) from None
                label = "HTTP_" + str(exc.code)
            except (URLError, TimeoutError, ConnectionError):
                if attempt == 3:
                    raise CollectionError("GitHub GET transport failed") from None
                label = "TRANSPORT"
            delay = 2 * attempt
            print(f"GITHUB_READ_RETRY attempt={attempt}/3 interval={delay}s cause={label}", file=sys.stderr)
            self.sleep(delay)
        _must(len(raw) <= MAX_JSON, "GitHub metadata exceeds size bound")
        try:
            return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
        except (UnicodeError, ValueError) as exc:
            if isinstance(exc, CollectionError):
                raise
            raise CollectionError("Malformed GitHub metadata") from None

    def artifact(self, artifact_id, destination):
        """GET the exact artifact ID, follow exactly one vetted HTTPS redirect.

        The GitHub token is sent only to api.github.com. Azure/Actions storage
        gets a second *unauthenticated* request to GitHub's signed URL. The
        private signed URL is never printed or returned.
        """
        _must(_positive(artifact_id), "Invalid artifact ID")
        target = Path(destination)
        _must(target.parent.is_dir() and not target.exists() and not target.is_symlink(),
              "Unsafe artifact destination")
        api_url = self._url(f"repos/{CONTROLLER}/actions/artifacts/{artifact_id}/zip")
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": API_VERSION,
                   "User-Agent": "romarr-receipt-collector-v01"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = Request(api_url, headers=headers, method="GET")
        try:
            self.opener.open(req, timeout=15)
        except HTTPError as exc:
            if exc.code != 302:
                raise CollectionError("Artifact redirect HTTP " + str(exc.code)) from None
            signed = exc.headers.get("Location")
            try:
                exc.close()
            except OSError:
                pass
        except (URLError, TimeoutError, ConnectionError, OSError):
            raise CollectionError("Artifact redirect transport failed") from None
        else:
            raise CollectionError("Artifact endpoint did not issue expected 302 redirect")
        _must(_host_is_artifact_storage(signed), "Unapproved artifact redirect host")
        # The second request intentionally has NO authorization header.
        artifact_request = Request(signed, headers={"User-Agent": "romarr-receipt-collector-v01"}, method="GET")
        with self._open(artifact_request, timeout=60) as response:
            _must(response.status == 200, "Artifact storage returned unexpected response")
            declared = response.headers.get("Content-Length")
            if declared is not None:
                _must(declared.isdecimal() and int(declared) <= MAX_ARCHIVE,
                      "Artifact declared size exceeds bound")
            size = 0
            # Exclusive creation: do not overwrite a previous or linked file.
            with target.open("xb") as output:
                while True:
                    chunk = response.read(min(65536, MAX_ARCHIVE + 1 - size))
                    if not chunk:
                        break
                    size += len(chunk)
                    _must(size <= MAX_ARCHIVE, "Artifact exceeds maximum download size")
                    output.write(chunk)
        _must(0 < size <= MAX_ARCHIVE, "Empty or excessive artifact download")
        if declared is not None:
            _must(size == int(declared), "Artifact download incomplete")
        return size


def _pr_identity(pr):
    """Only source/eligibility identity; comments and timestamps can change."""
    if not isinstance(pr, dict):
        return None
    head, base = pr.get("head"), pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        return None
    head_repo, base_repo = head.get("repo"), base.get("repo")
    if not isinstance(head_repo, dict) or not isinstance(base_repo, dict):
        return None
    return (pr.get("number"), pr.get("state"), pr.get("draft"),
            head.get("sha"), base.get("sha"),
            head_repo.get("full_name"), base_repo.get("full_name"))


def _run_identity(run):
    """Ignore harmless changing timestamps, but pin run attempt and result."""
    if not isinstance(run, dict):
        return None
    return tuple(run.get(key) for key in
                 ("id", "run_attempt", "head_sha", "status", "conclusion",
                  "path", "event", "head_branch", "html_url"))


def collect_once(*, pr_number, expected_head, expected_base, client, inspect_artifact=inspect):
    """Read and verify exactly one known PR/head/base without scheduling or writes."""
    _must(_positive(pr_number) and pr_number <= 999999 and
          _sha(expected_head) and _sha(expected_base),
          "Invalid explicit PR/head/base selection")
    _must(callable(getattr(client, "get", None)) and
          callable(getattr(client, "artifact", None)),
          "No verified read-only GitHub client")

    pr_path = f"repos/{SOURCE}/pulls/{pr_number}"
    pr = client.get(pr_path)
    _must(_pr_identity(pr) == (pr_number, "open", False, expected_head,
                              expected_base, SOURCE, SOURCE),
          "PR moved or is not exact selected source")
    claim = f"romarr-ci-v2/pr-{pr_number}-h-{expected_head}-b-{expected_base}"
    tag_prefix = f"repos/{CONTROLLER}/git/ref/tags/"
    claim_ref = client.get(tag_prefix + claim)
    refs = client.get(f"repos/{CONTROLLER}/git/matching-refs/tags/{claim}-run-")
    _must(isinstance(refs, list) and len(refs) == 1 and
          isinstance(refs[0], dict),
          "Missing or ambiguous claim run-ID ledger")
    prefix = "refs/tags/" + claim + "-run-"
    raw_ref = refs[0].get("ref")
    _must(isinstance(raw_ref, str) and raw_ref.startswith(prefix) and
          RUN_ID.fullmatch(raw_ref[len(prefix):]) is not None,
          "Invalid immutable run-ID ledger")
    run_id = int(raw_ref[len(prefix):])
    run_ref = client.get(tag_prefix + claim + "-run-" + str(run_id))
    _must(run_ref == refs[0], "Run-ID ledger changed during collection")

    run_path = f"repos/{CONTROLLER}/actions/runs/{run_id}"
    run = client.get(run_path)
    _must(isinstance(run, dict) and run.get("status") == "completed" and
          run.get("conclusion") == "success" and _sha(run.get("head_sha")),
          "Receipt run not complete and successful")
    controller_sha = run["head_sha"]
    jobs = client.get(run_path + "/jobs?filter=latest&per_page=100&page=1")
    artifacts = client.get(run_path + "/artifacts?per_page=100&page=1")
    _must(isinstance(artifacts, dict) and isinstance(artifacts.get("artifacts"), list)
          and artifacts.get("total_count") == 1 and len(artifacts["artifacts"]) == 1
          and isinstance(artifacts["artifacts"][0], dict),
          "Missing or ambiguous artifact inventory")
    artifact_id = artifacts["artifacts"][0].get("id")
    _must(_positive(artifact_id), "Artifact ID missing")
    try:
        with TemporaryDirectory(prefix="romarr-ci-receipt-") as tmp:
            archive_path = Path(tmp) / "receipt.zip"
            client.artifact(artifact_id, archive_path)
            verified = verify_receipt(
                pr=pr, run=run, jobs=jobs, artifact_listing=artifacts,
                claim_ref=claim_ref, run_ref=run_ref,
                expected_pr=pr_number, expected_head=expected_head,
                expected_base=expected_base, controller_sha=controller_sha,
                archive_path=archive_path, inspect_artifact=inspect_artifact)
    except ReceiptError as exc:
        raise CollectionError("Receipt validation blocked: " + str(exc)) from None

    # Final freshness gate: do not report current-head acceptance if source, run
    # attempt or ledger changed while the artifact was being downloaded.
    after_pr = client.get(pr_path)
    after_run = client.get(run_path)
    after_claim = client.get(tag_prefix + claim)
    after_ref = client.get(tag_prefix + claim + "-run-" + str(run_id))
    _must(_pr_identity(after_pr) == _pr_identity(pr) and
          _run_identity(after_run) == _run_identity(run) and
          after_claim == claim_ref and after_ref == run_ref,
          "Source PR, run, or immutable ledger changed during collection")
    return verified


def main():
    """Manual read-only run; no scheduled, mutating or multi-PR mode."""
    raw_number = os.environ.get("ROMARR_SELECTED_PR", "")
    _must(re.fullmatch(r"[1-9][0-9]{0,5}", raw_number) is not None,
          "Explicit PR selection is required")
    result = collect_once(pr_number=int(raw_number),
                          expected_head=os.environ.get("ROMARR_SELECTED_HEAD_SHA"),
                          expected_base=os.environ.get("ROMARR_SELECTED_BASE_SHA"),
                          client=GitHubReadClient(os.environ.get("GH_TOKEN", "")))
    # Sanitized verification only: never show GH_TOKEN, API payloads, ZIP or URLs.
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (CollectionError, ReceiptError) as exc:
        print("RECEIPT COLLECTION: BLOCKED — " + str(exc), file=sys.stderr)
        raise SystemExit(2)
