"""Verify Python modules are symlinked into src/ for Cloudflare Worker."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

MODULE_MAP = {
    "scrape": ROOT / "scrape",
    "proxy": ROOT / "v2" / "proxy",
    "ontology": ROOT / "v2" / "ontology",
}
FILES = ["email_shield.py"]

ok = True
for name, target in MODULE_MAP.items():
    link = SRC / name
    if not link.is_symlink():
        if link.exists():
            link.unlink()
        rel_target = os.path.relpath(target, SRC)
        os.symlink(rel_target, link)
        print(f"created symlink: {name} -> {rel_target}")
    else:
        resolved = (link.parent / os.readlink(link)).resolve()
        if resolved != target.resolve():
            link.unlink()
            rel_target = os.path.relpath(target, SRC)
            os.symlink(rel_target, link)
            print(f"updated symlink: {name} -> {rel_target}")
        elif not target.is_dir():
            print(f"MISSING SOURCE DIR: {target}")
            ok = False
        else:
            print(f"ok: {name}/")

for name in FILES:
    link = SRC / name
    target = ROOT / name
    if not link.is_symlink():
        print(f"MISSING FILE SYMLINK: {link}")
        ok = False
        continue
    resolved = (link.parent / os.readlink(link)).resolve()
    if resolved != target.resolve():
        print(f"WRONG TARGET: {link} -> {resolved} (expected {target})")
        ok = False
    elif not target.is_file():
        print(f"MISSING SOURCE FILE: {target}")
        ok = False
    else:
        print(f"ok: {name}")

if not ok:
    raise SystemExit(1)
print("All worker module symlinks verified.")
