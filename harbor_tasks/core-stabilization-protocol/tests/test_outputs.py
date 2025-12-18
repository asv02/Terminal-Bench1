import json
from pathlib import Path

def read_report():
    path = Path("/app/stabilization_costs.txt")
    assert path.is_file(), "stabilization_costs.txt does not exist"
    
    lines = path.read_text().strip().splitlines()
    rep = {}
    for line in lines:
        parts = line.split()
        assert len(parts) == 2, f"Malformed line in report: {line}"
        cid, val = parts
        rep[cid] = int(val)
    return rep

def read_scenarios():
    with open("/app/reactor_status.json") as f:
        return json.load(f)

def test_sorted_ids():
    data = read_scenarios()
    scenarios_list = data["scenarios"]
    
    expected = sorted(sc["id"] for sc in scenarios_list)

    report_lines = Path("/app/stabilization_costs.txt").read_text().strip().splitlines()
    ids = [line.split()[0] for line in report_lines]

    assert ids == expected, f"Expected sorted ids {expected}, but got {ids}"

def test_sector_containment_breach():
    rep = read_report()
    assert rep["sector-containment-breach"] == 71942470

def test_sector_core_critical_mass():
    rep = read_report()
    assert rep["sector-core-critical-mass"] == 31910000

def test_sector_entropy_spike():
    rep = read_report()
    assert rep["sector-entropy-spike"] == 42139714

def test_sector_field_distortion():
    rep = read_report()
    assert rep["sector-field-distortion"] == 58435000

def test_sector_harmonic_resonance():
    rep = read_report()
    assert rep["sector-harmonic-resonance"] == 0

def test_sector_magnetic_flux():
    rep = read_report()
    assert rep["sector-magnetic-flux"] == 15955000

def test_sector_plasma_instability():
    rep = read_report()
    assert rep["sector-plasma-instability"] == 104208064

def test_sector_thermal_runaway():
    rep = read_report()
    assert rep["sector-thermal-runaway"] == 72045188