#!/usr/bin/env python3
"""
Creates a simulated IoT firmware image with obfuscated encryption keys.

This creates a challenging reverse engineering task that requires:
1. Understanding firmware structure (header, segments, checksums)
2. Finding key derivation functions scattered across segments
3. Reconstructing master key from multiple key fragments
4. Decrypting the hidden configuration blob

Ground Truth:
- Master Key: "SecureIoT_M@ster_2024!"
- Device ID: "IOT-7A3F-B2E1-9D4C"
- API Endpoint: "api.iot-secure.internal:8443"
- Auth Token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aW90X2RldmljZQ"
"""

import struct
import json
import zlib

# Ground truth
MASTER_KEY = "SecureIoT_M@ster_2024!"
DEVICE_ID = "IOT-7A3F-B2E1-9D4C"
API_ENDPOINT = "api.iot-secure.internal:8443"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aW90X2RldmljZQ"

# Key fragments (master key split into 4 parts, each transformed)
KEY_FRAGMENTS = [
    "SecureI",      # Fragment 0: XOR with 0x11
    "oT_M@st",      # Fragment 1: ROT13 + XOR with 0x22
    "er_2024",      # Fragment 2: Reversed + XOR with 0x33
    "!",            # Fragment 3: In checksum field (hidden)
]


def create_firmware_header():
    """Create firmware header with metadata."""
    header = bytearray()

    # Magic bytes
    header.extend(b'FWIMG\x00\x00\x00')

    # Version (major.minor.patch as bytes)
    header.extend(struct.pack('<BBB', 2, 5, 1))

    # Padding
    header.extend(b'\x00' * 5)

    # Timestamp (fake)
    header.extend(struct.pack('<I', 1699900800))

    # Number of segments
    header.extend(struct.pack('<I', 5))

    # Total size placeholder (will update)
    header.extend(struct.pack('<I', 0))

    # Header checksum placeholder
    header.extend(struct.pack('<I', 0))

    return header


def create_key_fragment_segment(frag_idx, fragment, transform_type):
    """Create a segment containing a transformed key fragment."""
    segment = bytearray()

    # Segment header: [type:1][flags:1][size:2][offset:4]
    seg_type = 0x10 + frag_idx  # Types 0x10-0x13 for key fragments
    flags = transform_type

    # Transform the fragment
    if transform_type == 0x01:  # XOR only
        data = bytes([b ^ 0x11 for b in fragment.encode()])
    elif transform_type == 0x02:  # ROT13 + XOR
        rot13 = fragment.translate(str.maketrans(
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
            'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'
        ))
        data = bytes([b ^ 0x22 for b in rot13.encode()])
    elif transform_type == 0x03:  # Reverse + XOR
        data = bytes([b ^ 0x33 for b in fragment[::-1].encode()])
    else:  # Hidden in padding
        data = fragment.encode()

    # Segment header
    segment.append(seg_type)
    segment.append(flags)
    segment.extend(struct.pack('<H', len(data)))
    segment.extend(struct.pack('<I', 0))  # Offset (filled later)

    # Segment data with padding
    segment.extend(data)
    while len(segment) % 16 != 0:
        segment.append(0xFF)

    return segment


def create_decoy_segment():
    """Create segment with fake keys to mislead analysis."""
    decoys = [
        b"AES_KEY=0123456789abcdef\x00",
        b"PASSWORD=admin123\x00",
        b"SECRET=totally_fake_key\x00",
        b"API_KEY=sk_test_fake_1234567890\x00",
        b"ENCRYPTION_KEY=ThisIsNotTheRealKey!\x00",
    ]

    segment = bytearray()
    segment.append(0x20)  # Decoy segment type
    segment.append(0x00)
    segment.extend(struct.pack('<H', sum(len(d) for d in decoys)))
    segment.extend(struct.pack('<I', 0))

    for decoy in decoys:
        segment.extend(decoy)

    while len(segment) % 16 != 0:
        segment.append(0x00)

    return segment


def create_encrypted_config():
    """Create the encrypted configuration blob."""
    config = {
        "device_id": DEVICE_ID,
        "api_endpoint": API_ENDPOINT,
        "auth_token": AUTH_TOKEN,
        "firmware_version": "2.5.1",
        "update_channel": "stable"
    }

    config_json = json.dumps(config, separators=(',', ':')).encode()

    # Encrypt with master key (XOR with repeating key)
    key_bytes = MASTER_KEY.encode()
    encrypted = bytes([
        config_json[i] ^ key_bytes[i % len(key_bytes)]
        for i in range(len(config_json))
    ])

    # Add CRC32 for verification
    crc = zlib.crc32(config_json) & 0xFFFFFFFF

    segment = bytearray()
    segment.append(0x30)  # Config segment type
    segment.append(0x80)  # Encrypted flag
    segment.extend(struct.pack('<H', len(encrypted)))
    segment.extend(struct.pack('<I', crc))
    segment.extend(encrypted)

    while len(segment) % 16 != 0:
        segment.append(0xAA)

    return segment


def create_key_derivation_hint():
    """Create segment with hints about key reconstruction."""
    # This segment contains the algorithm description (obfuscated)
    hint_data = b"""
KEY_DERIVE_v2:
  FRAG[0] = SEGMENT[0x10] ^ 0x11
  FRAG[1] = ROT13(SEGMENT[0x11]) ^ 0x22
  FRAG[2] = REVERSE(SEGMENT[0x12]) ^ 0x33
  FRAG[3] = HEADER_CHECKSUM[3]
  MASTER = CONCAT(FRAG[0..3])
"""

    # XOR obfuscate the hint itself
    obfuscated = bytes([b ^ 0x5A for b in hint_data])

    segment = bytearray()
    segment.append(0x40)  # Hint segment type
    segment.append(0x5A)  # XOR key stored in flags
    segment.extend(struct.pack('<H', len(obfuscated)))
    segment.extend(struct.pack('<I', 0))
    segment.extend(obfuscated)

    while len(segment) % 16 != 0:
        segment.append(0x00)

    return segment


def create_firmware():
    """Assemble the complete firmware image."""
    header = create_firmware_header()

    segments = []

    # Key fragment segments
    segments.append(create_key_fragment_segment(0, KEY_FRAGMENTS[0], 0x01))
    segments.append(create_key_fragment_segment(1, KEY_FRAGMENTS[1], 0x02))
    segments.append(create_key_fragment_segment(2, KEY_FRAGMENTS[2], 0x03))

    # Decoy segment
    segments.append(create_decoy_segment())

    # Key derivation hint
    segments.append(create_key_derivation_hint())

    # Encrypted config (must be last)
    segments.append(create_encrypted_config())

    # Calculate total size
    total_size = len(header) + sum(len(s) for s in segments)

    # Update header with size
    struct.pack_into('<I', header, 24, total_size)

    # Calculate header checksum (include fragment 3 hidden in it!)
    # The last byte of checksum is actually the final key fragment
    checksum_base = sum(header[:28]) & 0xFFFFFF00
    checksum = checksum_base | ord(KEY_FRAGMENTS[3])  # Hide '!' (0x21) in LSB
    struct.pack_into('<I', header, 28, checksum)

    # Assemble firmware
    firmware = bytearray(header)
    for segment in segments:
        firmware.extend(segment)

    # Footer
    firmware.extend(b'FWEND\x00\x00\x00')
    firmware.extend(struct.pack('<I', zlib.crc32(bytes(firmware)) & 0xFFFFFFFF))

    return bytes(firmware)


def main():
    firmware = create_firmware()

    with open('/app/firmware.bin', 'wb') as f:
        f.write(firmware)

    print(f"Created firmware.bin ({len(firmware)} bytes)")
    print(f"Master Key: {MASTER_KEY}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"API Endpoint: {API_ENDPOINT}")
    print("Key fragments hidden in segments 0x10-0x12 + header checksum LSB")


if __name__ == "__main__":
    main()

