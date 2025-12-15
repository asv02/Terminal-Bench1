# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

import json
from pathlib import Path

def read_report():
    path = Path("cargo_report.txt")
    assert path.is_file(), "cargo_report.txt does not exist"

    lines = path.read_text().strip().splitlines()
    result = {}
    for line in lines:
        parts = line.split()
        assert len(parts) == 2, f"Invalid line format: {line}"
        result[parts[0]] = int(parts[1])
    return result


def read_scenarios():
    path = Path("cargo_balance.json")
    assert path.is_file(), "cargo_balance.json missing"
    with open(path) as f:
        return json.load(f)["scenarios"]

EXPECTED = {
    "house_A1": 50000000000000,
    "house_B7": 2500000000000,
    "house_C3": -1,
    "house_D9": 312697570016415356,
    "house_E2": 2500000000,
    "house_F8": 1000000000,
    "house_G4": 312722749758567714,
    "house_H6": 311715411588707948,
    "house_J5": 312934202611631552,
    "house_K0": 314104209265937576,
    "house_L10": 313457061472842014,
}

def test_ids_in_correct_alphabetical_order():
    scenarios = read_scenarios()
    expected_ids = sorted(sc["id"] for sc in scenarios)

    report_path = Path("cargo_report.txt")
    assert report_path.is_file(), "cargo_report.txt missing"

    lines = report_path.read_text().strip().splitlines()
    report_ids = [line.split()[0] for line in lines]

    assert report_ids == expected_ids, (
        f"Scenario IDs not in correct order.\nExpected: {expected_ids}\nGot: {report_ids}"
    )


def test_output_formatting_clean():
    path = Path("cargo_report.txt")
    lines = path.read_text().splitlines()

    for line in lines:
        assert line.strip() == line, f"Extraneous whitespace in line: {line!r}"
        assert line.count(" ") == 1, f"Line must contain exactly one space: {line!r}"

def _test_house(sid):
    report = read_report()
    assert sid in report, f"{sid} missing in cargo_report.txt"
    assert report[sid] == EXPECTED[sid], (
        f"Incorrect result for {sid}. "
        f"Expected {EXPECTED[sid]}, got {report[sid]}"
    )


def test_house_A1():
    _test_house("house_A1")

def test_house_B7():
    _test_house("house_B7")

def test_house_C3():
    _test_house("house_C3")

def test_house_D9():
    _test_house("house_D9")

def test_house_E2():
    _test_house("house_E2")

def test_house_F8():
    _test_house("house_F8")

def test_house_G4():
    _test_house("house_G4")

def test_house_H6():
    _test_house("house_H6")

def test_house_J5():
    _test_house("house_J5")

def test_house_K0():
    _test_house("house_K0")

def test_house_L10():
    _test_house("house_L10")

