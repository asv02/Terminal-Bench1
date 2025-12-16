#!/bin/bash
# setup_data.sh

BASE="/app/evidence"
mkdir -p "$BASE"

echo "User: John Doe" > "$BASE/payroll.jpg"
echo "SSN: 123-45-6789" >> "$BASE/payroll.jpg"

echo "SSN: 987-65-4321 - Critical Update" > "$BASE/employee list 2024.txt"

echo "Database Dump sequence..." > "$BASE/memory_dump.dat"
echo "Target: 555-01-9999" >> "$BASE/memory_dump.dat"

echo "id,name,ssn,status" > "$BASE/clients.csv"
echo "101,alice,111-22-3333,active" >> "$BASE/clients.csv"

echo "SSN: 888-88-8888" > "$BASE/suspicious_file[1].log"

printf "\x89\x50\x4E\x47\x0D\x0A\x1A\x0A" > "$BASE/photo.png"
echo "Contact Support: 555-123-4567" > "$BASE/contact_info.txt"
echo "Part Number: 12-345-6789" > "$BASE/inventory.list"
touch "$BASE/empty_scan.txt"
echo "# Readme" > "$BASE/readme.md"

ln -s /tmp/nonexistent "$BASE/broken_link_to_nowhere"

echo "Confidential: SSN 000-00-0000" > /tmp/external_evidence.txt
ln -s /tmp/external_evidence.txt "$BASE/external_link"