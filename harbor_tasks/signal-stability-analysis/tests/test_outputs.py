import json
from pathlib import Path

def read_report():
    path = Path("/app/stability_report.txt")
    assert path.is_file(), "stability_report.txt does not exist"
    
    lines = path.read_text().strip().splitlines()
    rep = {}
    for line in lines:
        parts = line.split()
        assert len(parts) == 2, f"Malformed line in report: {line}"
        cid, val = parts
        rep[cid] = int(val)
    return rep

def read_scenarios():
    with open("/app/transmission_logs.json") as f:
        return json.load(f)

def test_sorted_ids():
    scenarios = read_scenarios()
    expected = sorted(sc["id"] for sc in scenarios)

    report_lines = Path("/app/stability_report.txt").read_text().strip().splitlines()
    ids = [line.split()[0] for line in report_lines]

    assert ids == expected, f"Expected sorted ids {expected}, but got {ids}"

def test_net_log_buffer_bloat():
    rep = read_report()
    assert rep["net-log-buffer-bloat"] == 54266

def test_net_log_collision_dups():
    rep = read_report()
    assert rep["net-log-collision-dups"] == 19495950

def test_net_log_jitter_high():
    rep = read_report()
    assert rep["net-log-jitter-high"] == 3123750

def test_net_log_latency_spike():
    rep = read_report()
    assert rep["net-log-latency-spike"] == 49995000

def test_net_log_packet_storm():
    rep = read_report()
    assert rep["net-log-packet-storm"] == 2026240237

def test_net_log_saturation_heavy():
    rep = read_report()
    assert rep["net-log-saturation-heavy"] == 154311019

def test_net_log_sequence_drift():
    rep = read_report()
    assert rep["net-log-sequence-drift"] == 98988709

def test_net_log_signal_decay():
    rep = read_report()
    assert rep["net-log-signal-decay"] == 0