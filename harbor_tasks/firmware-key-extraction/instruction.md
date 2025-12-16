We obtained a firmware dump from a compromised IoT device at /app/firmware.bin. 
The device uses encrypted communication but the encryption keys are embedded somewhere in the firmware.

Your objectives:
1. Extract the master encryption key and save it as plaintext ASCII to /app/master_key.txt
2. Use the key to decrypt the embedded configuration and save it to /app/config.json

The config.json should be valid JSON containing: device_id, api_endpoint, auth_token

IMPORTANT: The firmware contains DECOY keys like "AES_KEY=0123456789abcdef" and "PASSWORD=admin123" - these are FALSE!

Technical details discovered so far:
- Firmware has magic header "FWIMG" and footer "FWEND"
- Contains multiple segments with different types and transformation flags
- The master key is NOT stored as a single string - it's split into fragments across segments
- Each fragment uses different obfuscation (XOR, ROT13, reversal, etc.)

Here are some hints to help you:
Binary structure:
- Header is 32 bytes: magic(8) + version(3) + padding(5) + timestamp(4) + num_segments(4) + size(4) + checksum(4)
- Segment headers are 8 bytes.
- Segments are padded to 16-byte alignment
