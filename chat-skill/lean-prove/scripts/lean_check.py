#!/usr/bin/env python3
"""Check Lean 4 + Mathlib proofs inside a sandbox, with no build tools.

    python3 lean_check.py setup [--background]   # install ~/lean (once per sandbox)
    python3 lean_check.py status                 # READY / progress / FAILED
    python3 lean_check.py check File.lean ...    # strict verdict

`setup` streams a prebuilt minimal Lean + Mathlib tree (GitHub release
`bundle-<version>` of thnastev/lean-proofs, ~2 GB download, ~8 GB unpacked)
straight into ~/lean, verifying sha256 checksums. Only needs read access to
github.com / api.github.com / release-assets.githubusercontent.com.

`check` passes a file only if it compiles with no errors, contains no
sorry/admit, and every declaration in it depends only on the axioms
propext, Classical.choice, Quot.sound (asked from Lean itself, so `sorry`,
`native_decide` and custom `axiom`s are all caught). Exit code 0 = PASS.
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, threading, time
import urllib.request

REPO = "thnastev/lean-proofs"
HOME = os.environ.get("LEAN_BUNDLE_HOME", os.path.expanduser("~/lean"))
LOG = HOME + ".setup.log"
DONE = os.path.join(HOME, ".complete")
STANDARD = {"propext", "Classical.choice", "Quot.sound"}
UA = {"User-Agent": "lean-prove-skill"}


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- setup
def get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)


def find_release():
    """Newest `bundle-*` release of the repo -> (tag, manifest dict)."""
    tag = None
    try:
        rel = json.load(get(f"https://api.github.com/repos/{REPO}/releases?per_page=20"))
        tags = [r["tag_name"] for r in rel if r["tag_name"].startswith("bundle-")]
        tag = tags[0] if tags else None
    except Exception as e:  # API blocked/rate-limited: fall back to the pinned version
        log(f"(release list unavailable: {e}; using pinned version)")
    tag = tag or "bundle-v4.36.0"
    base = f"https://github.com/{REPO}/releases/download/{tag}"
    return tag, base, json.load(get(f"{base}/manifest.json"))


class PartsReader:
    """File-like object: concatenation of the release parts, sha256-verified."""

    def __init__(self, base, parts):
        self.base, self.parts, self.i, self.resp, self.h = base, parts, -1, None, None
        self.total = sum(p["size"] for p in parts)
        self.read_bytes, self.t0, self.last = 0, time.time(), 0

    def _next(self):
        if self.resp is not None:
            if self.h.hexdigest() != self.parts[self.i]["sha256"]:
                raise IOError(f"checksum mismatch in {self.parts[self.i]['name']}")
            self.resp.close()
        self.i += 1
        if self.i >= len(self.parts):
            self.resp = None
            return False
        for attempt in range(4):
            try:
                self.resp = get(f"{self.base}/{self.parts[self.i]['name']}", timeout=120)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        self.h = hashlib.sha256()
        return True

    def read(self, n=1 << 20):
        while True:
            if self.resp is None and not self._next():
                return b""
            b = self.resp.read(n)
            if b:
                self.h.update(b)
                self.read_bytes += len(b)
                if time.time() - self.last > 5:
                    self.last = time.time()
                    mb = self.read_bytes / 1e6
                    log(f"PROGRESS {100 * self.read_bytes / self.total:.0f}% "
                        f"({mb:.0f}/{self.total / 1e6:.0f} MB, {mb / (time.time() - self.t0):.0f} MB/s)")
                return b
            self._next()
            if self.resp is None:
                return b""


def setup():
    if os.path.exists(DONE):
        log("READY (already installed)")
        return 0
    tag, base, man = find_release()
    log(f"Installing {tag}: {len(man['parts'])} part(s), "
        f"{sum(p['size'] for p in man['parts']) / 1e9:.2f} GB download")
    shutil.rmtree(HOME, ignore_errors=True)
    parent = os.path.dirname(HOME)
    staging = tempfile.mkdtemp(prefix=".lean-staging-", dir=parent)
    src = PartsReader(base, man["parts"])

    if shutil.which("zstd") and shutil.which("tar"):
        z = subprocess.Popen(["zstd", "-dc", "--long=27"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        t = subprocess.Popen(["tar", "-x", "-C", staging], stdin=z.stdout)
        z.stdout.close()
        err = []

        def pump():
            try:
                while True:
                    b = src.read()
                    if not b:
                        break
                    z.stdin.write(b)
            except Exception as e:
                err.append(e)
            finally:
                z.stdin.close()

        th = threading.Thread(target=pump)
        th.start()
        th.join()
        if err or z.wait() or t.wait():
            raise SystemExit(f"FAILED: {err or 'zstd/tar error'}")
    else:
        try:
            import zstandard
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "zstandard"], check=True)
            import zstandard
        import tarfile
        dctx = zstandard.ZstdDecompressor(max_window_size=1 << 27)
        with dctx.stream_reader(src, read_size=1 << 20) as zr:
            with tarfile.open(fileobj=zr, mode="r|") as tf:
                tf.extractall(staging)
    os.replace(os.path.join(staging, "lean"), HOME)
    shutil.rmtree(staging, ignore_errors=True)
    open(DONE, "w").write(tag)
    log(f"READY ({tag}, {time.time() - src.t0:.0f}s)")
    return 0


def status():
    if os.path.exists(DONE):
        print("READY")
        return 0
    if os.path.exists(LOG):
        lines = open(LOG).read().strip().splitlines()
        last = lines[-1] if lines else ""
        if "FAILED" in last or "Traceback" in "".join(lines[-5:]) or "Error" in last:
            print("FAILED\n" + "\n".join(lines[-15:]))
            return 2
        print("IN PROGRESS: " + last)
        return 1
    print("NOT STARTED (run: setup --background)")
    return 1


# ---------------------------------------------------------------- check
AXIOM_PROBE = r"""

open Lean Elab Command in
#eval show CommandElabM Unit from do
  let env ← getEnv
  for (n, _) in env.constants.map₂.toList do
    unless n.isInternal do
      let axs ← liftCoreM (collectAxioms n)
      IO.println s!"@@AXIOMS {n} :: {axs.toList}"
"""


def strip_comments(src):
    src = re.sub(r"/-.*?-/", " ", src, flags=re.S)
    return re.sub(r"--[^\n]*", " ", src)


def check(files):
    if not os.path.exists(DONE):
        print("Lean is not installed yet: run `setup` (or check `status`).")
        return 2
    lean = os.path.join(HOME, "bin", "lean")
    pk = os.path.join(HOME, "pkgs")
    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "/tmp"),
           "LEAN_PATH": ":".join(os.path.join(pk, p) for p in sorted(os.listdir(pk)))}
    all_ok = True
    for f in files:
        print(f"== {f}")
        src = open(f, encoding="utf-8").read()
        problems = []
        code = strip_comments(src)
        if re.search(r"(?<![\w.])(sorry|admit)(?![\w])", code):
            problems.append("contains sorry/admit")
        if re.search(r"^\s*(private\s+)?axiom\s", code, re.M):
            problems.append("declares its own axiom")
        if "skipKernelTC" in code or "debug.skip" in code:
            problems.append("disables kernel checking")
        d = tempfile.mkdtemp()
        probe = os.path.join(d, os.path.basename(f))
        open(probe, "w", encoding="utf-8").write(src.rstrip() + "\n" + AXIOM_PROBE)
        try:
            r = subprocess.run([lean, probe], capture_output=True, text=True, env=env,
                               cwd=d, timeout=900)
            out = (r.stdout + r.stderr).replace(probe, f)
            rc = r.returncode
        except subprocess.TimeoutExpired:
            out, rc = "lean timed out after 900s", 1
        shutil.rmtree(d, ignore_errors=True)
        user_out, axioms = [], {}
        for ln in out.splitlines():
            m = re.match(r"@@AXIOMS (\S+) :: \[(.*)\]$", ln)
            if m:
                axioms[m.group(1)] = [a.strip() for a in m.group(2).split(",") if a.strip()]
            else:
                user_out.append(ln)
        if rc != 0 or re.search(r":\d+:\d+: error", out):
            problems.append("compile errors")
        if not axioms and "compile errors" not in problems:
            problems.append("no declarations found (or axiom probe failed)")
        bad = {n: [a for a in ax if a not in STANDARD] for n, ax in axioms.items()}
        bad = {n: ax for n, ax in bad.items() if ax}
        if bad:
            problems.append("non-standard axioms: " + "; ".join(f"{n} uses {', '.join(a)}" for n, a in bad.items()))
        for ln in user_out:
            if ln.strip():
                print("  | " + ln)
        for n, ax in sorted(axioms.items()):
            print(f"  axioms {n}: {', '.join(ax) if ax else '(none)'}")
        if problems:
            all_ok = False
            for p in problems:
                print("  FAIL: " + p)
        else:
            print("  PASS: compiles, no sorry, standard axioms only")
    print("LEAN-CHECK: " + ("PASS" if all_ok else "FAIL"))
    return 0 if all_ok else 1


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("setup", "status", "check"):
        print(__doc__)
        return 2
    if a[0] == "setup":
        if "--background" in a:
            if os.path.exists(DONE):
                print("READY (already installed)")
                return 0
            with open(LOG, "w") as lf:
                subprocess.Popen([sys.executable, os.path.abspath(__file__), "setup"],
                                 stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
            print(f"setup started in background; poll with: python3 {sys.argv[0]} status")
            return 0
        try:
            return setup()
        except BaseException as e:
            log(f"FAILED: {e!r}")
            raise
    if a[0] == "status":
        return status()
    return check(a[1:])


if __name__ == "__main__":
    sys.exit(main())
