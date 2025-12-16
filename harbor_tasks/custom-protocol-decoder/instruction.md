We captured network traffic from a suspected APT C2 channel at /app/capture.bin. The traffic uses a custom binary protocol with encryption.

Your objectives:
1. Extract the session key and save it to /app/session_key.txt (as ASCII text)
2. Decode the command sequence and save to /app/commands.json (as JSON array of command names)
3. Decrypt the exfiltrated data and save to /app/exfil_data.json
   Schema: {"target": "<IP address>", "files": ["<path>", ...], "timestamp": <unix_timestamp>}

IMPORTANT: The capture contains DECOY packets with wrong magic bytes or plaintext commands - ignore these!

Technical details discovered so far:
- Valid packets start with magic bytes: 0xCAFEBABE
- Protocol version in capture: 0x02
- Message types: 0x01=handshake, 0x02=handshake_resp, 0x03=command, 0x04=data, 0x05=ack
- All sensitive data is encrypted with session key

Hints: 
- Capture has header "PCAP_CUSTOM", packets are length-prefixed, footer is "PCAP_END"
- Valid packets: magic(4) + version(1) + type(1) + len(2) + seq(4) + payload + checksum(2)
- Session key is in handshake packet (type 0x01) - decode payload bytes as ASCII and concatenate
- Encryption uses XOR with session key, seq_num affects the XOR pattern
- Decrypted payloads are JSON
