import json
from pathlib import Path


def read_report():
    path = Path("/app/gauntlet_report.txt")
    assert path.is_file(), "gauntlet_report.txt does not exist"
    lines = path.read_text().strip().splitlines()
    rep = {}
    for line in lines:
        cid, val = line.split()
        rep[cid] = int(val)
    return rep


def read_scenarios():
    with open("/app/gauntlet_scenarios.json") as f:
        return json.load(f)["scenarios"]


def test_sorted_ids():
    scenarios = read_scenarios()
    expected = sorted(sc["id"] for sc in scenarios)

    report_lines = Path("/app/gauntlet_report.txt").read_text().strip().splitlines()
    ids = [line.split()[0] for line in report_lines]

    assert ids == expected, f"Expected sorted ids {expected}, got {ids}"


def test_alpha():
    rep = read_report()
    assert rep["alpha"] == 3278191906


def test_beta():
    rep = read_report()
    assert rep["beta"] == 2338493466


def test_gamma():
    rep = read_report()
    assert rep["gamma"] == 481228776


def test_epsilon():
    rep = read_report()
    assert rep["epsilon"] == 1136810403


def test_zeta():
    rep = read_report()
    assert rep["zeta"] == 1625273379


def test_eta():
    rep = read_report()
    assert rep["eta"] == 2375913711


def test_theta():
    rep = read_report()
    assert rep["theta"] == 354511878


def test_iota():
    rep = read_report()
    assert rep["iota"] == 434343601


def test_kappa():
    rep = read_report()
    assert rep["kappa"] == 1482398889


def test_lambda():
    rep = read_report()
    assert rep["lambda"] == 378386295