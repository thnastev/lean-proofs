#!/usr/bin/env python3
"""Assemble the minimal tree needed to *check* proofs that `import Mathlib`.

    make_bundle.py OUT_DIR [ROOT_MODULE ...]     (run from the Lake project root)

Keeps only the import closure of the root modules (default: Mathlib), and only
the files `lean` reads when importing: .olean(.server|.private), .ir(.sig).
No lake, no sources, no C files, no caches.

Layout:  OUT/bin/lean, OUT/lib/lean/{*.so, core modules}, OUT/pkgs/<pkg>/<modules>
Run:     LEAN_PATH=$(ls -d OUT/pkgs/* | paste -sd:) OUT/bin/lean File.lean
"""
import os, shutil, subprocess, sys

EXTS = (".olean", ".olean.server", ".olean.private", ".ir", ".ir.sig")
CORE_TOPS = {"Init", "Std", "Lean", "Lake"}

out = os.path.abspath(sys.argv[1])
want = sys.argv[2:] or ["Mathlib"]
prefix = subprocess.run(["lean", "--print-prefix"], capture_output=True, text=True,
                        check=True).stdout.strip()
core_lib = os.path.join(prefix, "lib", "lean")

# Ask Lean for the exact set of modules that `import <roots>` loads.
probe = os.path.join(out + ".modules.lean")
os.makedirs(os.path.dirname(probe), exist_ok=True)
with open(probe, "w") as f:
    f.write("".join(f"import {m}\n" for m in want))
    f.write("open Lean in\n#eval show CoreM Unit from do\n"
            "  for m in (← getEnv).header.moduleNames do IO.println s!\"MOD {m}\"\n")
r = subprocess.run(["lake", "env", "lean", probe], capture_output=True, text=True)
os.remove(probe)
mods = [l[4:].strip() for l in r.stdout.splitlines() if l.startswith("MOD ")]
if r.returncode != 0 or not mods:
    sys.exit(f"module listing failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
seen = set(mods)

# top-level module name -> (package name or None for core, lib dir)
roots = {t: (None, core_lib) for t in CORE_TOPS}
pk = os.path.join(".lake", "packages")
for p in sorted(os.listdir(pk)):
    lib = os.path.join(pk, p, ".lake", "build", "lib", "lean")
    if os.path.isdir(lib):
        for f in os.listdir(lib):
            roots.setdefault(f.split(".")[0], (p, lib))


def put(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


put(os.path.join(prefix, "bin", "lean"), os.path.join(out, "bin", "lean"))
for f in os.listdir(core_lib):
    if f.endswith(".so"):
        put(os.path.join(core_lib, f), os.path.join(out, "lib", "lean", f))

n = size = 0
for mod in sorted(seen):
    top = mod.split(".")[0]
    if top not in roots:
        continue
    pkg, lib = roots[top]
    rel = os.path.join(*mod.split("."))
    dst_root = os.path.join(out, "lib", "lean") if pkg is None else os.path.join(out, "pkgs", pkg)
    for e in EXTS:
        s = os.path.join(lib, rel + e)
        if os.path.exists(s):
            put(s, os.path.join(dst_root, rel + e))
            n += 1
            size += os.path.getsize(s)
print(f"bundle {out}: {len(seen)} modules, {n} files, {size / 1e9:.2f} GB", file=sys.stderr)
