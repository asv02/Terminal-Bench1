#!/bin/bash
# Ultimate Adversarial Test File Generator - 1000 Files
# Designed to maximize LLM agent confusion and failure

set -e
mkdir -p /app/data
cd /app/data

echo "Generating 1000 adversarial test files..."

# ============================================
# Category 1: Completely Fake/Obscure Extensions (150 files)
# ============================================
echo "[1/10] Creating fake and obscure extensions..."

# Non-existent proprietary formats
for i in {1..30}; do
    echo "fake_ext_$i" > "file$i.xqz"
    echo "fake_ext_$i" > "data$i.zzp"
    echo "fake_ext_$i" > "config$i.qwx"
    echo "fake_ext_$i" > "archive$i.pqr"
    echo "fake_ext_$i" > "binary$i.klm"
done

# ============================================
# Category 2: Extremely Long Multi-Dot Extensions (100 files)
# ============================================
echo "[2/10] Creating multi-dot extension nightmares..."

for i in {1..25}; do
    echo "multi_$i" > "file$i.v1.backup.2025.prod.final.old.archive.custom"
    echo "multi_$i" > "data$i.config.json.bak.tmp.old.v2.final.backup"
    echo "multi_$i" > "report$i.xlsx.converted.pdf.compressed.archived.final"
    echo "multi_$i" > "log$i.2025.12.01.debug.verbose.rotated.compressed"
done

# ============================================
# Category 3: Filenames That Look Like SHA256 Hashes (50 files)
# ============================================
echo "[3/10] Creating SHA256-like filenames..."

# These filenames ARE valid SHA256 hashes - extreme confusion!
echo "content1" > "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.dat"
echo "content2" > "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3.log"
echo "content3" > "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae.txt"
echo "content4" > "fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9.bin"
echo "content5" > "bef57ec7f53a6d40beb640a780a639c83bc29ac8a9816f1fc6c5c6dcd93c4721.custom"

for i in {6..50}; do
    # Generate random hex strings that look like SHA256
    hash=$(printf '%064x' $((RANDOM * RANDOM * RANDOM)))
    echo "hash_content_$i" > "$hash.data"
done

# ============================================
# Category 4: Unicode Chaos (100 files)
# ============================================
echo "[4/10] Creating unicode filename chaos..."

# Mix of different scripts
for i in {1..20}; do
    echo "unicode_$i" > "文件_$i.custom"
    echo "unicode_$i" > "файл_$i.данные"
    echo "unicode_$i" > "αρχείο_$i.conf"
    echo "unicode_$i" > "ملف_$i.txt"
    echo "unicode_$i" > "קוֹבֶץ_$i.log"
done

# Emoji madness
for i in {1..20}; do
    echo "emoji_$i" > "file_😀_$i.txt"
    echo "emoji_$i" > "data_🔥_$i.custom"
    echo "emoji_$i" > "log_💀_$i.conf"
    echo "emoji_$i" > "config_🚀_$i.data"
    echo "emoji_$i" > "report_⚡_$i.log"
done

# ============================================
# Category 5: Massive Underscore/Hyphen Chains (80 files)
# ============================================
echo "[5/10] Creating underscore/hyphen nightmares..."

for i in {1..20}; do
    echo "underscores_$i" > "file_with_many_underscores_in_the_name_$i.custom"
    echo "hyphens_$i" > "file-with-many-hyphens-in-the-name-$i.data"
    echo "mixed_$i" > "file_with-mixed_separators-and_dots.$i.custom"
    echo "extreme_$i" > "________$i.txt"
done

# ============================================
# Category 6: Special Characters Extreme (120 files)
# ============================================
echo "[6/10] Creating special character chaos..."

for i in {1..20}; do
    echo "special_$i" > "file with spaces $i.custom"
    echo "special_$i" > "file'with'quotes'$i.data"
    echo "special_$i" > "file\"double\"quotes\"$i.conf"
    echo "special_$i" > "file(parens)$i.txt"
    echo "special_$i" > "file[brackets]$i.log"
    echo "special_$i" > "file{braces}$i.custom"
done

# ============================================
# Category 7: Ambiguous Extensions (100 files)
# ============================================
echo "[7/10] Creating ambiguous extensions..."

# Extensions that MIGHT exist but are extremely rare
for i in {1..10}; do
    echo "ambiguous_$i" > "file$i.dat2"
    echo "ambiguous_$i" > "file$i.log2"
    echo "ambiguous_$i" > "file$i.bak2"
    echo "ambiguous_$i" > "file$i.old2"
    echo "ambiguous_$i" > "file$i.tmp2"
    echo "ambiguous_$i" > "file$i.cache"
    echo "ambiguous_$i" > "file$i.lock"
    echo "ambiguous_$i" > "file$i.pid"
    echo "ambiguous_$i" > "file$i.swp"
    echo "ambiguous_$i" > "file$i.swo"
done

# ============================================
# Category 8: Path-Like Filenames (60 files)
# ============================================
echo "[8/10] Creating path-confusion filenames..."

# Filenames that look like paths (but are just filenames)
for i in {1..20}; do
    echo "path_$i" > "..file$i.txt"
    echo "path_$i" > "...file$i.custom"
    echo "path_$i" > ".file$i.data"
done

# Filenames with slashes encoded
for i in {1..20}; do
    echo "slash_$i" > "file_slash_encoded_$i.txt"
    echo "slash_$i" > "file_path_like_$i.custom"
done

# ============================================
# Category 9: Duplicate Content with Different Names (80 files)
# ============================================
echo "[9/10] Creating duplicate content files..."

DUPLICATE="DUPLICATE_CONTENT_FOR_HASH_COLLISION_TEST"
for i in {1..80}; do
    echo "$DUPLICATE" > "duplicate_$i.custom"
done

# ============================================
# Category 10: Edge Case Content (80 files)
# ============================================
echo "[10/10] Creating edge case content..."

# Empty files
for i in {1..20}; do
    touch "empty_$i.custom"
done

# Null bytes
for i in {1..15}; do
    printf "\x00\x00\x00" > "nulls_$i.bin"
done

# Newline only
for i in {1..15}; do
    printf "\n\n\n" > "newlines_$i.txt"
done

# JSON-hostile content
for i in {1..15}; do
    echo 'Content with "quotes" and \backslashes and $vars' > "json_hostile_$i.conf"
done

# Shell metacharacters in content
for i in {1..15}; do
    echo '$PATH and `whoami` and $(ls) and |pipe| and ;semicolon;' > "shell_hostile_$i.sh"
done

# ============================================
# Category 11: Case Sensitivity Hell (80 files)
# ============================================
echo "[11/10] Creating case sensitivity tests..."

for i in {1..20}; do
    echo "UPPER_$i" > "FILE_$i.CUSTOM"
    echo "lower_$i" > "file_$i.custom"
    echo "Mixed_$i" > "File_$i.Custom"
    echo "mIxEd_$i" > "fIlE_$i.cUsToM"
done

# ============================================
# TOTAL: 1000+ files
# ============================================

echo "File generation complete!"
FILE_COUNT=$(find /app/data -type f | wc -l)
echo "Total files created: $FILE_COUNT"

if [ "$FILE_COUNT" -lt 1000 ]; then
    echo "WARNING: Expected at least 1000 files, got $FILE_COUNT"
fi
