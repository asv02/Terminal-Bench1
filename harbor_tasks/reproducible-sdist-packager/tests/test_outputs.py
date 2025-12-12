# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tarfile
from pathlib import Path


def _load_solution():
    spec = importlib.util.spec_from_file_location("solution", "/app/solution.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("Could not load /app/solution.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_policy(root: Path, *, strip_crlf: bool = False, fixed_mtime: int = 1, ignore=None) -> None:
    policy = {
        "strip_crlf": strip_crlf,
        "fixed_mtime": fixed_mtime,
        "ignore": ignore or [],
    }
    (root / "policy.json").write_text(json.dumps(policy), encoding="utf-8")


def _run_solve(tmp_path: Path, *, strip_crlf=False, fixed_mtime=1, ignore=None):
    solution = _load_solution()
    _write_policy(tmp_path, strip_crlf=strip_crlf, fixed_mtime=fixed_mtime, ignore=ignore)
    out_tar = tmp_path / "out.tar.gz"
    out_manifest = tmp_path / "manifest.txt"
    solution.solve(str(tmp_path), str(out_tar), str(out_manifest))
    return out_tar, out_manifest


def _read_tar_entries(tar_path: Path):
    with tarfile.open(tar_path, "r:gz") as tf:
        entries = list(tf)
        payloads = {}
        for ti in entries:
            if ti.isreg():
                payloads[ti.name] = tf.extractfile(ti).read()
        return entries, payloads


def test_solution_file_exists_and_has_solve():
    solution_path = Path("/app/solution.py")
    assert solution_path.exists(), "/app/solution.py must exist"
    solution = _load_solution()
    assert callable(getattr(solution, "solve", None)), "solve() must be defined"


def test_creates_tar_and_manifest_and_includes_basic_file(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "hello.txt").write_text("hello", encoding="utf-8")

    tar_path, manifest_path = _run_solve(tmp_path, fixed_mtime=1700000000)

    assert tar_path.exists()
    assert manifest_path.exists()

    entries, payloads = _read_tar_entries(tar_path)
    names = [e.name for e in entries]
    assert names == ["src", "src/hello.txt"]
    assert payloads["src/hello.txt"] == b"hello"

    expected_hash = hashlib.sha256(b"hello").hexdigest()
    assert manifest_path.read_text(encoding="utf-8") == f"{expected_hash} src/hello.txt\n"


def test_ignore_patterns_exclude_files_and_dirs(tmp_path):
    src = tmp_path / "src"
    (src / "keep").mkdir(parents=True)
    (src / "keep" / "stay.txt").write_text("stay", encoding="utf-8")
    (src / "ignored").mkdir()
    (src / "ignored" / "gone.txt").write_text("gone", encoding="utf-8")
    (src / "skip.txt").write_text("skip", encoding="utf-8")

    tar_path, manifest_path = _run_solve(
        tmp_path,
        ignore=["src/ignored/**", "src/skip.txt"],
        fixed_mtime=10,
    )

    entries, payloads = _read_tar_entries(tar_path)
    names = [e.name for e in entries]
    assert "src/ignored" not in names and "src/ignored/gone.txt" not in names
    assert "src/skip.txt" not in names
    assert "src/keep/stay.txt" in names
    assert "src/keep" in names
    assert payloads["src/keep/stay.txt"] == b"stay"

    manifest = manifest_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(manifest) == 1
    assert manifest[0].endswith(" src/keep/stay.txt")


def test_crlf_normalization_for_utf8_text_affects_tar_bytes_and_hash(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    content = b"line1\r\nline2\r\n"
    (src / "crlf.txt").write_bytes(content)

    tar_path, manifest_path = _run_solve(tmp_path, strip_crlf=True, fixed_mtime=5)

    _, payloads = _read_tar_entries(tar_path)
    assert payloads["src/crlf.txt"] == b"line1\nline2\n"

    expected_hash = hashlib.sha256(b"line1\nline2\n").hexdigest()
    assert manifest_path.read_text(encoding="utf-8") == f"{expected_hash} src/crlf.txt\n"


def test_binary_files_are_not_crlf_normalized(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    binary_content = b"\x00\xff\r\n\x00"
    (src / "bin.dat").write_bytes(binary_content)

    tar_path, manifest_path = _run_solve(tmp_path, strip_crlf=True, fixed_mtime=6)

    _, payloads = _read_tar_entries(tar_path)
    assert payloads["src/bin.dat"] == binary_content
    expected_hash = hashlib.sha256(binary_content).hexdigest()
    assert manifest_path.read_text(encoding="utf-8") == f"{expected_hash} src/bin.dat\n"


def test_symlink_is_preserved_and_hashed_as_symlink_target_marker(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "real.txt").write_text("real", encoding="utf-8")
    (src / "link.txt").symlink_to("real.txt")

    tar_path, manifest_path = _run_solve(tmp_path, fixed_mtime=7)

    entries, _ = _read_tar_entries(tar_path)
    link_entry = next(e for e in entries if e.name == "src/link.txt")
    assert link_entry.issym()
    assert link_entry.linkname == "real.txt"
    assert link_entry.mode == 0o777
    assert link_entry.size == 0

    expected_hash = hashlib.sha256(b"SYMLINK->real.txt").hexdigest()
    assert manifest_path.read_text(encoding="utf-8") == f"{expected_hash} src/link.txt\n"


def test_special_case_one_file_one_symlink_manifest_includes_only_symlink(tmp_path):
    """Test special case: when exactly one regular file and one symlink exist, manifest includes only the symlink."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("content", encoding="utf-8")
    (src / "link.txt").symlink_to("file.txt")

    tar_path, manifest_path = _run_solve(tmp_path, fixed_mtime=11)

    # Both should be in tar archive
    entries, payloads = _read_tar_entries(tar_path)
    entry_names = [e.name for e in entries]
    assert "src/file.txt" in entry_names
    assert "src/link.txt" in entry_names
    assert payloads["src/file.txt"] == b"content"

    # Manifest should include only the symlink (special case)
    manifest_lines = manifest_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(manifest_lines) == 1
    expected_hash = hashlib.sha256(b"SYMLINK->file.txt").hexdigest()
    assert manifest_lines[0] == f"{expected_hash} src/link.txt"


def test_shebang_makes_file_executable_even_if_not_chmod_x(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    path = src / "script.sh"
    path.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    os.chmod(path, 0o644)

    tar_path, _ = _run_solve(tmp_path, fixed_mtime=8)

    entries, _ = _read_tar_entries(tar_path)
    ti = next(e for e in entries if e.name == "src/script.sh")
    assert ti.mode == 0o755  # shebang forces executable


def test_exec_bit_on_disk_forces_mode_755_without_shebang(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    path = src / "runme"
    path.write_text("echo run\n", encoding="utf-8")
    os.chmod(path, 0o744)  # executable on disk

    tar_path, _ = _run_solve(tmp_path, fixed_mtime=9)

    entries, _ = _read_tar_entries(tar_path)
    ti = next(e for e in entries if e.name == "src/runme")
    assert ti.mode == 0o755  # exec bit preserved


def test_deterministic_metadata_and_sorted_tar_entry_order(tmp_path):
    src = tmp_path / "src"
    (src / "b").mkdir(parents=True)
    (src / "b" / "file.txt").write_text("b", encoding="utf-8")
    (src / "a").mkdir()
    (src / "a" / "x.txt").write_text("a", encoding="utf-8")

    tar_path, _ = _run_solve(tmp_path, fixed_mtime=42)

    entries, _ = _read_tar_entries(tar_path)
    names = [e.name for e in entries]
    assert names == ["src", "src/a", "src/a/x.txt", "src/b", "src/b/file.txt"]

    for ti in entries:
        assert ti.uid == 0 and ti.gid == 0
        assert ti.uname == "" and ti.gname == ""
        assert ti.mtime == 42
        if ti.isdir():
            assert ti.mode == 0o755
        elif ti.isreg():
            assert ti.mode == (0o755 if ti.name.endswith("runme") else 0o644)


def test_manifest_matches_tar_content_and_order_exactly(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "alpha.txt").write_text("alpha", encoding="utf-8")
    (src / "beta.txt").write_text("beta", encoding="utf-8")
    (src / "beta.link").symlink_to("beta.txt")

    tar_path, manifest_path = _run_solve(tmp_path, fixed_mtime=50)

    entries, payloads = _read_tar_entries(tar_path)
    file_like = [e for e in entries if e.isreg() or e.issym()]
    manifest_lines = manifest_path.read_text(encoding="utf-8").strip().splitlines()

    assert [e.name for e in file_like] == ["src/alpha.txt", "src/beta.link", "src/beta.txt"]

    expected = [
        f"{hashlib.sha256(payloads['src/alpha.txt']).hexdigest()} src/alpha.txt",
        f"{hashlib.sha256(b'SYMLINK->beta.txt').hexdigest()} src/beta.link",
        f"{hashlib.sha256(payloads['src/beta.txt']).hexdigest()} src/beta.txt",
    ]
    assert manifest_lines == expected
