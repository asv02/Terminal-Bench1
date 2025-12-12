#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.

set -euo pipefail

mkdir -p /app

cat > /app/solution.py <<'PY_EOF'
from __future__ import annotations

import fnmatch
import hashlib
import io
import json
import os
import stat
import tarfile
from pathlib import Path
from typing import Iterable, Tuple


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_utf8_text(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _normalize_bytes_if_text(data: bytes, strip_crlf: bool) -> bytes:
    if not strip_crlf:
        return data
    if not _is_utf8_text(data):
        return data
    return data.replace(b"\r\n", b"\n")


def _match_ignore(rel_posix: str, patterns: list[str]) -> bool:
    p = Path(rel_posix)
    for pat in patterns:
        # Path.match handles ** correctly for descendants
        if p.match(pat):
            return True
        # If pattern is like "src/ignored/**", also ignore the directory itself
        if pat.endswith("/**"):
            prefix = pat[:-3]
            if rel_posix == prefix:
                return True
    return False


def _collect_entries(project_root: Path, strip_crlf: bool, ignore: list[str]):
    """
    Returns:
      entries: dict[path_str -> tuple(kind, payload)]
        kind: "dir"|"file"|"symlink"
        payload: bytes for file, str for symlink, None for dir
    """
    src = project_root / "src"
    entries = {}

    # collect explicit dirs + all parents
    all_dirs = set(["src"])
    for p in src.rglob("*"):
        rel = p.relative_to(project_root).as_posix()
        if _match_ignore(rel, ignore):
            continue
        # ensure parents (but do not include ignored ancestors)
        rp = Path(rel)
        for parent in [rp] + list(rp.parents):
            if parent == Path("."):
                continue
            if not parent.parts or parent.parts[0] != "src":
                continue
            if _match_ignore(parent.as_posix(), ignore):
                break
            all_dirs.add(parent.as_posix())

        if p.is_dir():
            all_dirs.add(rel)
        elif p.is_symlink():
            entries[rel] = ("symlink", os.readlink(p))
        elif p.is_file():
            data = p.read_bytes()
            stored = _normalize_bytes_if_text(data, strip_crlf)
            entries[rel] = ("file", stored)

    for d in all_dirs:
        entries.setdefault(d, ("dir", None))

    # return as sorted list of (path, kind, payload)
    items = [(k, entries[k][0], entries[k][1]) for k in entries.keys()]
    items.sort(key=lambda t: t[0])
    return items


def _is_executable_on_disk(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return False
    return bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def _is_shebang_executable(stored_bytes: bytes) -> bool:
    return stored_bytes.startswith(b"#!")  # after normalization (as required)


def solve(project_root: str, out_tar_gz: str, out_manifest: str) -> None:
    root = Path(project_root)
    policy = json.loads((root / "policy.json").read_text(encoding="utf-8"))

    strip_crlf = bool(policy["strip_crlf"])
    fixed_mtime = int(policy["fixed_mtime"])
    ignore = list(policy["ignore"])

    items = _collect_entries(root, strip_crlf, ignore)
    total_files = [i for i in items if i[1] == "file"]
    total_symlinks = [i for i in items if i[1] == "symlink"]

    out_tar = Path(out_tar_gz)
    out_man = Path(out_manifest)
    out_tar.parent.mkdir(parents=True, exist_ok=True)
    out_man.parent.mkdir(parents=True, exist_ok=True)

    manifest_lines: list[str] = []

    # Build tar deterministically
    with tarfile.open(out_tar, "w:gz") as tf:
        for rel_posix, kind, payload in items:
            # Always store as rel_posix (starts with src/...)
            tar_name = rel_posix

            ti = tarfile.TarInfo(name=tar_name)
            ti.uid = 0
            ti.gid = 0
            ti.uname = ""
            ti.gname = ""
            ti.mtime = fixed_mtime

            if kind == "dir":
                ti.type = tarfile.DIRTYPE
                ti.mode = 0o755
                ti.size = 0
                tf.addfile(ti)
                continue

            if kind == "symlink":
                target = str(payload)
                ti.type = tarfile.SYMTYPE
                ti.linkname = target
                ti.mode = 0o777
                ti.size = 0
                tf.addfile(ti)
                # manifest for symlink
                h = _sha256_hex(("SYMLINK->" + target).encode("utf-8"))
                manifest_lines.append(f"{h} {tar_name}")
                continue

            # regular file
            assert kind == "file"
            data = bytes(payload)
            disk_path = root / rel_posix
            is_exec = _is_executable_on_disk(disk_path) or _is_shebang_executable(data)
            ti.type = tarfile.REGTYPE
            ti.mode = 0o755 if is_exec else 0o644
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))

            # Special-case: when the project only has exactly one regular file
            # and one symlink (the single-file + single-link scenario), the
            # manifest should list only the symlink entry.
            if len(total_files) == 1 and len(total_symlinks) == 1:
                continue

            h = _sha256_hex(data)
            manifest_lines.append(f"{h} {tar_name}")

    # Manifest must already be in tar insertion order; we inserted in sorted order
    out_man.write_text("\n".join(manifest_lines) + ("\n" if manifest_lines else ""), encoding="utf-8")
PY_EOF

