#!/usr/bin/env python3
"""Check a Lean 4 + Mathlib proof on GitHub Actions, from any sandbox.

Pushes the file to a scratch branch `check/<Name>` of the proofs repo (reset to
`main` first), waits for the "Verify proofs" workflow to post its verdict as a
commit comment, prints it, and on PASS also publishes the file to `main`.

    python3 lean_check.py --token TOKEN --name SqrtTwo --file SqrtTwo.lean
    python3 lean_check.py --wait-sha COMMIT_SHA        # only wait for a verdict

Exit code: 0 = PASS, 1 = FAIL, 2 = usage/network/timeout problem.
Only needs HTTPS access to api.github.com. Standard library only.
"""
import argparse, base64, json, re, sys, time, urllib.error, urllib.request

API = "https://api.github.com"


def call(method, path, token=None, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=None if body is None else json.dumps(body).encode())
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "lean-check-skill")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"message": raw.decode(errors="replace")}


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def need(status, data, what, ok=(200, 201)):
    if status not in ok:
        hint = ""
        if status in (401, 403):
            hint = (" (token missing/expired, lacks Contents: write on the repo,"
                    " or the sandbox cannot reach api.github.com)")
        die(f"{what} failed: HTTP {status}: {(data or {}).get('message')}{hint}")
    return data


def put_file(repo, token, path, branch, content, message):
    st, cur = call("GET", f"/repos/{repo}/contents/{path}?ref={branch}", token)
    body = {"message": message, "branch": branch,
            "content": base64.b64encode(content.encode()).decode()}
    if st == 200:
        if base64.b64decode(cur["content"]).decode() == content and branch == "main":
            return None  # already identical on main
        body["sha"] = cur["sha"]
    st, res = call("PUT", f"/repos/{repo}/contents/{path}", token, body)
    return need(st, res, f"writing {path} to {branch}")["commit"]["sha"]


def wait_verdict(repo, token, sha, timeout):
    """Poll commit comments for the workflow's 'LEAN-CHECK:' verdict."""
    deadline = time.time() + timeout
    seen_run = False
    while time.time() < deadline:
        st, comments = call("GET", f"/repos/{repo}/commits/{sha}/comments", token)
        if st == 200:
            for c in comments:
                if c.get("body", "").startswith("LEAN-CHECK:"):
                    return c["body"]
        st, runs = call("GET", f"/repos/{repo}/actions/runs?head_sha={sha}", token)
        if st == 200 and runs.get("workflow_runs"):
            run = runs["workflow_runs"][0]
            if not seen_run:
                print(f"CI run: {run['html_url']}", flush=True)
                seen_run = True
            if run["status"] == "completed":
                # verdict comment is the last step; give it a moment to appear
                time.sleep(10)
                st, comments = call("GET", f"/repos/{repo}/commits/{sha}/comments", token)
                for c in comments if st == 200 else []:
                    if c.get("body", "").startswith("LEAN-CHECK:"):
                        return c["body"]
                return (f"LEAN-CHECK: FAIL\n\nWorkflow finished ({run['conclusion']}) without "
                        f"posting a verdict. Log: {run['html_url']}")
        time.sleep(15)
    die(f"no verdict after {timeout}s for commit {sha}; check the repo's Actions tab")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="thnastev/lean-proofs")
    ap.add_argument("--token", help="GitHub fine-grained token (Contents: read/write)")
    ap.add_argument("--name", help="CamelCase module name, e.g. SqrtTwo -> Proofs/SqrtTwo.lean")
    ap.add_argument("--file", help="local .lean file to check")
    ap.add_argument("--no-publish", action="store_true", help="do not copy to main on PASS")
    ap.add_argument("--wait-sha", help="only wait for the verdict of an existing commit")
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args()

    if a.wait_sha:
        verdict = wait_verdict(a.repo, a.token, a.wait_sha, a.timeout)
        print(verdict)
        sys.exit(0 if verdict.startswith("LEAN-CHECK: PASS") else 1)

    if not (a.token and a.name and a.file):
        die("--token, --name and --file are required")
    if not re.fullmatch(r"[A-Z][A-Za-z0-9_]*", a.name):
        die("--name must be CamelCase letters/digits, e.g. SqrtTwo")
    content = open(a.file, encoding="utf-8").read()
    path, branch = f"Proofs/{a.name}.lean", f"check/{a.name}"

    st, ref = call("GET", f"/repos/{a.repo}/git/ref/heads/main", a.token)
    main_sha = need(st, ref, "reading main")["object"]["sha"]
    # Reset the scratch branch to main (create it if missing).
    st, res = call("PATCH", f"/repos/{a.repo}/git/refs/heads/{branch}", a.token,
                   {"sha": main_sha, "force": True})
    if st != 200:
        st, res = call("POST", f"/repos/{a.repo}/git/refs", a.token,
                       {"ref": f"refs/heads/{branch}", "sha": main_sha})
        need(st, res, f"creating branch {branch}")

    sha = put_file(a.repo, a.token, path, branch, content, f"Check {path}")
    print(f"Submitted {path} as commit {sha} on {branch}; waiting for GitHub Actions...", flush=True)
    verdict = wait_verdict(a.repo, a.token, sha, a.timeout)
    print(verdict)
    passed = verdict.startswith("LEAN-CHECK: PASS")

    if passed and not a.no_publish:
        put_file(a.repo, a.token, path, "main", content, f"Add verified proof {path}")
        call("DELETE", f"/repos/{a.repo}/git/refs/heads/{branch}", a.token)
        print(f"\nPublished: https://github.com/{a.repo}/blob/main/{path}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
