#!/usr/bin/env python3
"""
Creates a simulated network capture with custom encrypted protocol.

This creates a challenging reverse engineering task that requires:
1. Understanding custom binary protocol structure
2. Extracting session key from handshake
3. Decrypting command payloads
4. Reconstructing fragmented messages

Ground Truth:
- Session Key: "N3tw0rk_S3ss10n_K3y!"
- Command Sequence: ["INIT", "AUTH", "EXFIL", "CLEANUP"]
- Exfiltrated Data: {"target": "192.168.50.100", "files": ["/etc/passwd", "/etc/shadow"], "timestamp": 1699900800}
"""

import struct
import json
import hashlib

# Ground truth
SESSION_KEY = "N3tw0rk_S3ss10n_K3y!"
COMMAND_SEQUENCE = ["INIT", "AUTH", "EXFIL", "CLEANUP"]
EXFIL_DATA = {
    "target": "192.168.50.100",
    "files": ["/etc/passwd", "/etc/shadow"],
    "timestamp": 1699900800
}

# Protocol constants
PROTO_MAGIC = b'\xCA\xFE\xBA\xBE'
PROTO_VERSION = 0x02

# Message types
MSG_HANDSHAKE = 0x01
MSG_HANDSHAKE_RESP = 0x02
MSG_COMMAND = 0x03
MSG_DATA = 0x04
MSG_ACK = 0x05


def create_handshake():
    """Create initial handshake packet with session key derivation."""
    packet = bytearray()

    # Header: magic(4) + version(1) + type(1) + length(2) + seq(4)
    packet.extend(PROTO_MAGIC)
    packet.append(PROTO_VERSION)
    packet.append(MSG_HANDSHAKE)

    # Client random (used for key derivation)
    client_random = b'\x4E\x33\x74\x77\x30\x72\x6B\x5F'  # "N3tw0rk_" XOR'd

    # Server random hint
    server_random = b'\x53\x33\x73\x73\x31\x30\x6E\x5F'  # "S3ss10n_" XOR'd

    # Key hint (last part of session key)
    key_hint = b'\x4B\x33\x79\x21'  # "K3y!" XOR'd

    payload = client_random + server_random + key_hint
    packet.extend(struct.pack('<H', len(payload)))
    packet.extend(struct.pack('<I', 1))  # Sequence number
    packet.extend(payload)

    # Checksum
    packet.extend(struct.pack('<H', sum(payload) & 0xFFFF))

    return bytes(packet)


def create_handshake_response():
    """Create handshake response with encrypted session confirmation."""
    packet = bytearray()

    packet.extend(PROTO_MAGIC)
    packet.append(PROTO_VERSION)
    packet.append(MSG_HANDSHAKE_RESP)

    # Session ID (derived from key)
    session_id = hashlib.md5(SESSION_KEY.encode()).digest()[:8]

    # Encrypted confirmation
    confirm = b'SESSION_ESTABLISHED'
    key_bytes = SESSION_KEY.encode()
    encrypted_confirm = bytes([
        confirm[i] ^ key_bytes[i % len(key_bytes)]
        for i in range(len(confirm))
    ])

    payload = session_id + encrypted_confirm
    packet.extend(struct.pack('<H', len(payload)))
    packet.extend(struct.pack('<I', 2))
    packet.extend(payload)
    packet.extend(struct.pack('<H', sum(payload) & 0xFFFF))

    return bytes(packet)


def create_command_packet(cmd_name, seq_num):
    """Create encrypted command packet."""
    packet = bytearray()

    packet.extend(PROTO_MAGIC)
    packet.append(PROTO_VERSION)
    packet.append(MSG_COMMAND)

    # Command payload
    cmd_data = {
        "cmd": cmd_name,
        "timestamp": 1699900800 + seq_num * 10
    }
    cmd_json = json.dumps(cmd_data, separators=(',', ':')).encode()

    # Encrypt with session key + sequence number
    key_bytes = SESSION_KEY.encode()
    encrypted = bytes([
        cmd_json[i] ^ key_bytes[i % len(key_bytes)] ^ (seq_num & 0xFF)
        for i in range(len(cmd_json))
    ])

    # Add command type hint (first byte is command type XOR'd)
    cmd_type_map = {"INIT": 0x10, "AUTH": 0x20, "EXFIL": 0x30, "CLEANUP": 0x40}
    cmd_type = cmd_type_map.get(cmd_name, 0x00) ^ 0x55

    payload = bytes([cmd_type]) + encrypted
    packet.extend(struct.pack('<H', len(payload)))
    packet.extend(struct.pack('<I', seq_num))
    packet.extend(payload)
    packet.extend(struct.pack('<H', sum(payload) & 0xFFFF))

    return bytes(packet)


def create_data_packet(data, seq_num):
    """Create fragmented data packet."""
    packet = bytearray()

    packet.extend(PROTO_MAGIC)
    packet.append(PROTO_VERSION)
    packet.append(MSG_DATA)

    # Data payload
    data_json = json.dumps(data, separators=(',', ':')).encode()

    # Encrypt
    key_bytes = SESSION_KEY.encode()
    encrypted = bytes([
        data_json[i] ^ key_bytes[i % len(key_bytes)] ^ ((seq_num * 3) & 0xFF)
        for i in range(len(data_json))
    ])

    packet.extend(struct.pack('<H', len(encrypted)))
    packet.extend(struct.pack('<I', seq_num))
    packet.extend(encrypted)
    packet.extend(struct.pack('<H', sum(encrypted) & 0xFFFF))

    return bytes(packet)


def create_decoy_packets():
    """Create decoy packets with fake data."""
    decoys = []

    # Fake command
    fake_cmd = bytearray()
    fake_cmd.extend(PROTO_MAGIC)
    fake_cmd.append(PROTO_VERSION)
    fake_cmd.append(MSG_COMMAND)
    fake_payload = b'{"cmd":"FAKE","data":"decoy"}'
    fake_cmd.extend(struct.pack('<H', len(fake_payload)))
    fake_cmd.extend(struct.pack('<I', 999))
    fake_cmd.extend(fake_payload)
    fake_cmd.extend(struct.pack('<H', 0xDEAD))
    decoys.append(bytes(fake_cmd))

    # Corrupted packet
    corrupted = bytearray()
    corrupted.extend(b'\xDE\xAD\xBE\xEF')  # Wrong magic
    corrupted.extend(b'\x00' * 20)
    decoys.append(bytes(corrupted))

    return decoys


def create_capture():
    """Create the complete capture file."""
    capture = bytearray()

    # Capture file header
    capture.extend(b'PCAP_CUSTOM\x00')
    capture.extend(struct.pack('<I', 10))  # Number of packets

    packets = []

    # Handshake
    packets.append(create_handshake())
    packets.append(create_handshake_response())

    # Commands
    for i, cmd in enumerate(COMMAND_SEQUENCE):
        packets.append(create_command_packet(cmd, 3 + i))

    # Data exfiltration
    packets.append(create_data_packet(EXFIL_DATA, 7))

    # Decoys
    packets.extend(create_decoy_packets())

    # ACK
    ack = bytearray()
    ack.extend(PROTO_MAGIC)
    ack.append(PROTO_VERSION)
    ack.append(MSG_ACK)
    ack.extend(struct.pack('<H', 0))
    ack.extend(struct.pack('<I', 8))
    ack.extend(struct.pack('<H', 0))
    packets.append(bytes(ack))

    # Write packets with length prefix
    for pkt in packets:
        capture.extend(struct.pack('<I', len(pkt)))
        capture.extend(pkt)

    # Footer
    capture.extend(b'PCAP_END\x00\x00\x00\x00')

    return bytes(capture)


def main():
    capture = create_capture()

    with open('/app/capture.bin', 'wb') as f:
        f.write(capture)

    print(f"Created capture.bin ({len(capture)} bytes)")
    print(f"Session Key: {SESSION_KEY}")
    print(f"Commands: {COMMAND_SEQUENCE}")
    print(f"Exfil Data: {EXFIL_DATA}")


if __name__ == "__main__":
    main()

