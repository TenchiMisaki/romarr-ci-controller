"""Check direct dispatch response and independently retrieved advisory run."""
from stage6_pr_identity_v32 import CONTROLLER_REPO, IdentityRejected
from stage6_pr_live_run_v41 import verify_advisory_run


def dispatch_run_id(status, body):
    """Read a direct authenticated response. Missing evidence leaves uncertainty."""
    if status != 200 or type(body) is not dict:
        raise IdentityRejected("DISPATCH_RESPONSE_UNCERTAIN")
    run_id = body.get("workflow_run_id")
    if type(run_id) is not int or not 0 < run_id <= 2**63 - 1:
        raise IdentityRejected("DISPATCH_RESPONSE_ID_INVALID")
    path = f"{CONTROLLER_REPO}/actions/runs/{run_id}"
    if (body.get("run_url") != f"https://api.github.com/repos/{path}"
            or body.get("html_url") != f"https://github.com/{path}"):
        raise IdentityRejected("DISPATCH_RESPONSE_TARGET_MISMATCH")
    return run_id


def verify_dispatch_observation(status, body, run, *, controller_sha):
    """Check the first run attempt only. Source inputs need separate evidence."""
    run_id = dispatch_run_id(status, body)
    return verify_advisory_run(
        run, controller_sha=controller_sha, run_id=run_id, attempt=1,
        workflow_path=".github/workflows/stage6-pr-manual-candidate.yml",
    )
