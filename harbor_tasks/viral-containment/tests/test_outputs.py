import json
from pathlib import Path

def read_report():
    path = Path("/app/restoration_report.txt")
    assert path.is_file(), "restoration_report.txt does not exist"
    lines = path.read_text().strip().splitlines()
    rep = {}
    for line in lines:
        parts = line.split()
        assert len(parts) == 2, "Each line must contain exactly: ID VALUE"
        cid, val = parts
        rep[cid] = int(val)
    return rep

def read_batches():
    with open("/app/restoration_batches.json") as f:
        return json.load(f)

def test_sorted_ids():
    batches = read_batches()
    expected = sorted(b["id"] for b in batches)

    report_lines = Path("/app/restoration_report.txt").read_text().strip().splitlines()
    ids = [line.split()[0] for line in report_lines]

    assert ids == expected, f"Expected sorted ids {expected}, got {ids}"

def test_alpha():
    rep = read_report()
    assert rep["alpha"] == 8634

def test_beta():
    rep = read_report()
    assert rep["beta"] == 6986

def test_gamma():
    rep = read_report()
    assert rep["gamma"] == 7982

def test_delta():
    rep = read_report()
    assert rep["delta"] == 7458

def test_epsilon():
    rep = read_report()
    assert rep["epsilon"] == 5656

def test_zeta():
    rep = read_report()
    assert rep["zeta"] == 5775

def test_eta():
    rep = read_report()
    assert rep["eta"] == 5767

def test_theta():
    rep = read_report()
    assert rep["theta"] == 6504

def test_iota():
    rep = read_report()
    assert rep["iota"] == 5877

def test_kappa():
    rep = read_report()
    assert rep["kappa"] == 5524