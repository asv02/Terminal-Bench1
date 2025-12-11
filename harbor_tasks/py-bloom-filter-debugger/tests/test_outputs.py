from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Iterable

import pytest


_MODULE_PATH = Path("/app/bloom_filter.py")
assert _MODULE_PATH.exists(), f"Expected file {_MODULE_PATH} to exist"
_SPEC = importlib.util.spec_from_file_location("bloom_filter", str(_MODULE_PATH))
assert _SPEC is not None and _SPEC.loader is not None
bloom_filter = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bloom_filter)


def _normalize_ref(item: str) -> str:
    """Reference normalization that mirrors instruction.md byte-for-byte."""
    # remove zero-width chars everywhere
    for zw in ("\u200b", "\ufeff"):
        item = item.replace(zw, "")
    item = item.strip()

    if "<" in item and ">" in item and item.index("<") < item.index(">"):
        inner = item.split("<", 1)[1]
        item = inner.split(">", 1)[0].strip()

    if "@" not in item:
        return item

    lowered = item.lower()
    local, domain = lowered.split("@", 1)
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    if domain in ("gmail.com", "googlemail.com"):
        domain = "gmail.com"
        local = local.replace(".", "")
        plus_idx = local.find("+")
        if plus_idx != -1:
            local = local[:plus_idx]
    return f"{local}@{domain}"


def _reference_bits(
    m_bits: int, k_hashes: int, salt: str, items: Iterable[str]
) -> set[int]:
    bits: set[int] = set()
    for item in items:
        norm = _normalize_ref(item)
        for i in range(k_hashes):
            key = f"{salt}|{i}|{norm}"
            digest = hashlib.sha256(key.encode("utf-8")).digest()
            index = int.from_bytes(digest, "big") % m_bits
            bits.add(index)
    return bits


def _snapshot_bits(bf: bloom_filter.BloomFilter, m_bits: int) -> set[int]:
    return {i for i in range(m_bits) if bf._get_bit(i)}


def _membership_by_reference(
    universe_bits: set[int], m_bits: int, k_hashes: int, salt: str, item: str
) -> bool:
    norm = _normalize_ref(item)
    for i in range(k_hashes):
        key = f"{salt}|{i}|{norm}"
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        idx = int.from_bytes(digest, "big") % m_bits
        if idx not in universe_bits:
            return False
    return True


def test_constructor_validation_matrix_and_type_barriers():
    invalid = [
        (0, 1, "s"),
        (-1, 1, "s"),
        (8, 0, "s"),
        (8, -2, "s"),
        (8.5, 1, "s"),
        (8, 1.1, "s"),
        (8, 1, None),
        ("1024", 1, "s"),
        (8, "2", "s"),
    ]
    for m_bits, k_hashes, salt in invalid:
        with pytest.raises(ValueError):
            bloom_filter.BloomFilter(m_bits, k_hashes, salt)

    bf = bloom_filter.BloomFilter(1, 1, "ok")
    assert bf.contains("any") is False  # empty filter must start cleared


def test_create_email_filter_contract_and_exact_parameters():
    items = [
        "User.Name+Promo@GMAIL.com",
        "user.name+tag@googlemail.com",
        "user.name+tag@outlook.com",
        "  mixedCaseId  ",
        ".+tag@gmail.com",
        "测试@测试.com",
        "user@domain@extra.com",
        "",
    ]
    ref_bits = _reference_bits(1024, 4, "email-filter-v1", items)
    bf = bloom_filter.create_email_filter(items)
    assert _snapshot_bits(bf, 1024) == ref_bits

    probes = [
        "USER.name+promo@gmail.com",  # same gmail canonical form
        "user.name+tag@googlemail.com",
        "user.name+tag@GMAIL.com",
        "user.name+tag@outlook.com",  # non-gmail must keep plus
        "mixedcaseid",  # lowercased non-email should NOT be forced present
        "   ",
        "NOT@inserted.com",
    ]
    for probe in probes:
        expected = _membership_by_reference(ref_bits, 1024, 4, "email-filter-v1", probe)
        assert bf.contains(probe) == expected, f"Probe {probe!r} mismatched reference expectation"


def test_normalization_equivalence_partitions_and_boundaries():
    inserted = [
        "User.Name+Promo@GMAIL.com",
        "user.name+tag@outlook.com",
        "CAFÉ@example.com",
        "cafe\u0301@example.com",  # NFD should remain distinct
        "raw-id",
    ]
    bf = bloom_filter.create_email_filter(inserted)
    ref_bits = _reference_bits(1024, 4, "email-filter-v1", inserted)

    positive_pairs = [
        ("User.Name+Promo@GMAIL.com", "u.s.e.r.n.a.m.e+anything@googlemail.com"),
        ("User.Name+Promo@GMAIL.com", "username+spam@gmail.com"),
    ]
    for base, variant in positive_pairs:
        assert _normalize_ref(base) == _normalize_ref(variant)
        base_bits = _reference_bits(1024, 4, "email-filter-v1", [base])
        variant_bits = _reference_bits(1024, 4, "email-filter-v1", [variant])
        assert base_bits == variant_bits
        assert bf.contains(variant)

    negative = [
        "user.name@mail.gmail.com",  # subdomain must not collapse
        "user.name+promo@gmailcom",  # missing dot
        "cafE@example.com",  # different casing for non-email should not auto-match
        "cafe@example.com",  # different from NFD/NFC inserted
    ]
    for candidate in negative:
        expected = _membership_by_reference(ref_bits, 1024, 4, "email-filter-v1", candidate)
        assert expected is False, f"Reference unexpectedly marked {candidate!r} present"
        assert bf.contains(candidate) is False


def test_non_email_case_sensitivity_and_unicode_preservation():
    m_bits, k_hashes, salt = 311, 4, "non-email-v1"
    items = [
        "CaseSensitive",
        "casesensitive",
        "CAFÉ",
        "cafe\u0301",  # combining acute
        "user+tag",
    ]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    lower_variant = "casesensitive"
    assert bf.contains(lower_variant) is True  # explicitly inserted
    assert bf.contains("casesensitive ".strip()) is True
    expected_upper = _membership_by_reference(ref_bits, m_bits, k_hashes, salt, "casesensitive".upper())
    assert expected_upper is False
    assert bf.contains("casesensitive".upper()) is False

    assert _membership_by_reference(ref_bits, m_bits, k_hashes, salt, "café") is False
    assert bf.contains("café") is False
    assert bf.contains("CAFÉ") is True
    assert bf.contains("cafe\u0301") is True


def test_hash_key_format_endianness_and_separator_discipline():
    m_bits, k_hashes, salt = 257, 3, "byte-precision"
    items = ["User.Name+Tag@GMAIL.com", "CaseSensitiveID", "user@domain@extra.com"]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    for item in items:
        norm = _normalize_ref(item)
        for i in range(k_hashes):
            key = f"{salt}|{i}|{norm}"
            digest = hashlib.sha256(key.encode("utf-8")).digest()
            idx = int.from_bytes(digest, "big") % m_bits
            assert bf._get_bit(idx), f"Canonical bit missing for {item!r} hash {i}"

            # Wrong separators or order must not light up extra bits.
            alt_keys = [f"{salt}:{i}:{norm}", f"{salt}|{norm}|{i}", f"{salt} | {i} | {norm}"]
            for alt_key in alt_keys:
                alt_idx = int.from_bytes(hashlib.sha256(alt_key.encode("utf-8")).digest(), "big") % m_bits
                if alt_idx not in ref_bits:
                    assert bf._get_bit(alt_idx) is False

            little_idx = int.from_bytes(digest, "little") % m_bits
            if little_idx not in ref_bits:
                assert bf._get_bit(little_idx) is False


def test_order_idempotence_and_incremental_union():
    m_bits, k_hashes, salt = 4096, 6, "order-union"
    phase_one = [
        " \tUser.Name+Tag@GMAIL.com\n",
        "user.name+tag@googlemail.com",
        "User.Name+Tag@Gmail.Com",
    ]
    phase_two = [
        "user.name+tag@outlook.com",
        "CAFÉ@example.com",
        "cafe\u0301@example.com",
        " raw-id ",
        "+@gmail.com",
        "user+tag",
        "a.b.c+d+e",
    ]

    bf_a = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in phase_one + phase_two:
        bf_a.add(item)

    bf_b = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in reversed(phase_two + phase_one):
        bf_b.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, phase_one + phase_two)
    assert _snapshot_bits(bf_a, m_bits) == ref_bits == _snapshot_bits(bf_b, m_bits)

    for item in phase_one + phase_two:
        norm = _normalize_ref(item)
        assert bf_a.contains(item) and bf_b.contains(item)
        assert bf_a.contains(norm) and bf_b.contains(norm)

    # Re-adding must not mutate the bitset.
    before = _snapshot_bits(bf_a, m_bits)
    for item in phase_one:
        bf_a.add(item)
    assert _snapshot_bits(bf_a, m_bits) == before

    negatives = [
        "user.name+tag@mail.gmail.com",
        "user.name+tag@gmailcom",
        "user.name+tag@outlook.com.",
    ]
    for neg in negatives:
        expected = _membership_by_reference(ref_bits, m_bits, k_hashes, salt, neg)
        assert expected is False
        assert bf_a.contains(neg) is False


def test_salt_isolation_and_negative_membership_certificate():
    items = [
        "User.Name+Promo@GMAIL.com",
        "user.name+tag@outlook.com",
        "../etc/passwd",
        "CAFÉ@example.com",
    ]
    bf1 = bloom_filter.BloomFilter(1024, 4, "salt-one")
    bf2 = bloom_filter.BloomFilter(1024, 4, "salt-two")
    for item in items:
        bf1.add(item)
        bf2.add(item)

    bits1 = _snapshot_bits(bf1, 1024)
    bits2 = _snapshot_bits(bf2, 1024)
    assert bits1 != bits2, "Different salts must produce different bit patterns"

    neg = "intruder@example.net"
    assert _membership_by_reference(bits1, 1024, 4, "salt-one", neg) is False
    assert bf1.contains(neg) is False


def test_pathlike_and_multi_at_handling():
    items = [
        "../etc/passwd",
        "user@../../gmail.com",
        "user@@gmail.com",
        "user..name@gmail.com",
        "\u200Buser@outlook.com",
    ]
    m_bits, k_hashes, salt = 2048, 4, "path-matrix"
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    # Split at first @ only; gmail canonicalization only when domain matches exactly.
    assert bf.contains("USER@@gmail.COM")  # lowercased gmail canonicalization applies
    assert bf.contains("user@../../gmail.com")
    assert bf.contains("../etc/passwd")
    assert bf.contains("\u200buser@outlook.com")
    assert bf.contains("user..name@gmail.com")
    assert bf.contains("user@mail.gmail.com") is False


def test_idna_display_name_and_zero_width_stripping():
    m_bits, k_hashes, salt = 509, 5, "idna-and-display"
    items = [
        " Name <User@例子.测试> ",
        "ZW\u200bSP",
        "\ufeffUser.Name+tag@GMAIL.com",
        "user@sub.例子.com",
    ]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    # Display names and zero-width characters are stripped; IDNA applied to domain.
    assert bf.contains("User@xn--fsqu00a.xn--0zwm56d")  # 例子.测试
    assert bf.contains("user@sub.xn--fsqu00a.com")
    assert bf.contains("ZWSP")
    assert bf.contains("username@gmail.com")  # gmail canonicalization after zero-width removal

    negatives = [
        "Name <User@例子.测试2>",  # different domain after IDNA
        "ZW\u200bspx",
    ]
    for neg in negatives:
        expected = _membership_by_reference(ref_bits, m_bits, k_hashes, salt, neg)
        assert expected is False
        assert bf.contains(neg) is False


def test_get_bit_bounds_and_argument_guardrails():
    bf = bloom_filter.BloomFilter(16, 2, "bounds")
    bf.add("a")
    assert isinstance(bf._get_bit(0), bool)
    for bad in (-1, 16, 1000):
        with pytest.raises(IndexError):
            bf._get_bit(bad)
    with pytest.raises(TypeError):
        bf._get_bit("0")  # type discipline for helper


def test_edge_case_empty_and_whitespace_only_inputs():
    bf_empty = bloom_filter.create_email_filter([""])
    assert bf_empty.contains("")
    assert bf_empty.contains("   ")  # whitespace normalizes to empty

    bf_space = bloom_filter.create_email_filter(["   "])
    assert bf_space.contains("   ")
    assert bf_space.contains("")

    # Both filters should have identical bit layouts because normalization collapses to "".
    bits_empty = _snapshot_bits(bf_empty, 1024)
    bits_space = _snapshot_bits(bf_space, 1024)
    assert bits_empty == bits_space


def test_get_bit_is_bool_for_all_indices_and_contains_is_pure():
    m_bits, k_hashes, salt = 97, 3, "pure-check"
    items = ["User@Example.com", "CaseID", "x@y.z", "ZW\u200bSP"]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    # _get_bit must be boolean for every position.
    for i in range(m_bits):
        val = bf._get_bit(i)
        assert isinstance(val, bool), f"_get_bit({i}) must return bool, got {type(val)}"

    before = _snapshot_bits(bf, m_bits)
    probes = [
        "user@example.com",
        "CASEID",
        "CaseID",
        "x@y.z",
        "x@y.z@extra",
        "ZWSP",
        "zwsp",
    ]
    for probe in probes:
        bf.contains(probe)
    after = _snapshot_bits(bf, m_bits)
    assert after == before, "contains() must not mutate the bitset"


def test_idna_failure_fallback_and_lowercasing_only():
    # Domain with spaces causes IDNA failure; should fall back to lowercased domain unchanged.
    m_bits, k_hashes, salt = 211, 4, "idna-fail"
    bad_domain = "User@exa mple.com"
    items = [bad_domain]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    bf.add(bad_domain)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    # Normalization should lower the domain but keep the space (IDNA failure path).
    assert bf.contains("user@exa mple.com")
    assert bf.contains("User@EXA MPLE.COM")
    assert bf.contains("User@exa mple.com")
    assert bf.contains("user@exa mple.com ")  # strip outer space only


def test_randomized_fuzz_against_reference_seeded():
    rnd_seed = 1337
    import random

    r = random.Random(rnd_seed)
    m_bits, k_hashes, salt = 4093, 5, "fuzz-v1"

    def rand_email():
        local = "".join(r.choice("abcXYZ012+._") for _ in range(r.randint(3, 12)))
        domain = r.choice(
            [
                "gmail.com",
                "googlemail.com",
                "outlook.com",
                "example.com",
                "例子.测试",
                "mail.gmail.com",
                "exa mple.com",  # IDNA failure path
            ]
        )
        prefix = r.choice(["", " Name <", " Display <"])
        suffix = ">" if prefix else ""
        pad = " " * r.randint(0, 2)
        zw = "\u200b" if r.random() < 0.3 else ""
        return f"{pad}{prefix}{local}@{domain}{suffix}{pad}{zw}"

    def rand_non_email():
        base = "".join(r.choice("AbCdef123+._") for _ in range(r.randint(3, 10)))
        if r.random() < 0.4:
            base = base + "\u200b"
        if r.random() < 0.5:
            base = " " + base + " "
        return base

    items = [rand_email() if r.random() < 0.7 else rand_non_email() for _ in range(120)]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    # Probe additional variants derived from the inserted set
    probes = []
    for item in items[:30]:
        probes.append(item)
        norm = _normalize_ref(item)
        probes.append(norm)
        if "@" in norm and norm.endswith("gmail.com"):
            probes.append(norm.replace("gmail.com", "googlemail.com"))
            probes.append(norm.replace("gmail.com", "mail.gmail.com"))
    for probe in probes:
        expected = _membership_by_reference(ref_bits, m_bits, k_hashes, salt, probe)
        assert bf.contains(probe) == expected, f"Fuzz probe mismatch for {probe!r}"


def test_high_collision_environment_has_no_false_negatives():
    # Small m_bits to force collisions; still no false negatives allowed.
    m_bits, k_hashes, salt = 32, 6, "collision-stress"
    items = [
        "User.Name+Tag@GMAIL.com",
        "user.name+tag@googlemail.com",
        "user.name+tag@outlook.com",
        "A.B.C+D",
        "CaseSensitive",
        "casesensitive",
        "cafE@example.com",
        "cafe\u0301@example.com",
        "zw\u200bsp",
        "ZWSP",
    ]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    for item in items:
        assert bf.contains(item), f"False negative for {item!r} under collisions"

    negatives = ["other@example.com", "CaseSensitiveX", "ZWspx", "user.name@mail.gmail.com"]
    for neg in negatives:
        expected = _membership_by_reference(ref_bits, m_bits, k_hashes, salt, neg)
        assert bf.contains(neg) == expected


def test_gmail_plus_and_dot_extremes_and_non_gmail_contrast():
    m_bits, k_hashes, salt = 521, 4, "gmail-extremes"
    items = [
        "u......s.e.r+++++promo@gmail.com",
        "User.Name+Tag@googlemail.com",
        "..leading.dots..@gmail.com",
        "plain.user+tag@outlook.com",
        "plain.user+tag@gmail.com",
    ]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    # Gmail/googlemail collapse to the same normalized form; dots and plus removed.
    assert bf.contains("u.s.e.r@gmail.com")
    assert bf.contains("user@googlemail.com")
    assert bf.contains("username@gmail.com")
    assert bf.contains("USERNAME+anything@GMAIL.COM")
    assert bf.contains("username@googlemail.com")

    # Non-gmail must keep plus/dots.
    assert bf.contains("plain.user+tag@outlook.com")
    assert bf.contains("plain.user@outlook.com") is False
    assert bf.contains("plainuser+tag@outlook.com") is False
    assert bf.contains("plain.user+tag@gmail.com")  # gmail version canonicalizes differently


def test_display_name_nested_and_zero_width_everywhere():
    m_bits, k_hashes, salt = 389, 5, "display-nested"
    items = [
        "Outer <Inner <User.Name+tag@GMAIL.com>>",
        "\u200bName<\u200bUser@例子.测试\u200b>",
        "Label < raw-id >",
        "prefix<ZW\u200bSP>",
    ]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    # Ensure only the first <> pair is used and zero-width chars removed globally.
    probes = [
        "user.name@gmail.com",
        "inner <username@gmail.com",
        "User@xn--fsqu00a.xn--0zwm56d",
        "raw-id",
        "ZWSP",
    ]
    for probe in probes:
        expected = _membership_by_reference(ref_bits, m_bits, k_hashes, salt, probe)
        assert bf.contains(probe) == expected, f"Probe {probe!r} mismatched reference"


def test_first_at_split_behavior_and_unusual_domains():
    m_bits, k_hashes, salt = 257, 3, "multi-at"
    items = [
        "a@b@c",
        "user@exa mple.com",
        "name@例子..测试",
        "double@@gmail.com",
    ]
    bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
    for item in items:
        bf.add(item)

    ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
    assert _snapshot_bits(bf, m_bits) == ref_bits

    # Splitting at first @ should match the reference normalization.
    assert bf.contains("A@B@C")
    assert bf.contains("a@b@c")

    # IDNA failure path: keep lowercased domain with spaces/double dots as-is.
    assert bf.contains("user@EXA MPLE.COM")
    assert bf.contains("user@exa mple.com")
    assert bf.contains("name@例子..测试")
    assert bf.contains("double@@gmail.com")


def test_multiple_seeded_fuzz_runs():
    seeds = [1, 123, 9991]
    m_bits, k_hashes, salt = 3079, 5, "fuzz-multi"

    import random

    for rnd_seed in seeds:
        r = random.Random(rnd_seed)

        def rand_email():
            local = "".join(r.choice("abcXYZ012+._") for _ in range(r.randint(1, 14)))
            domain = r.choice(
                [
                    "gmail.com",
                    "googlemail.com",
                    "outlook.com",
                    "example.com",
                    "mail.gmail.com",
                    "例子.测试",
                    "exa mple.com",
                    "例子..测试",
                ]
            )
            prefix = r.choice(["", " Name <", " Display <"])
            suffix = ">" if prefix else ""
            pad = " " * r.randint(0, 3)
            zw = "\u200b" if r.random() < 0.4 else ""
            return f"{pad}{prefix}{local}@{domain}{suffix}{pad}{zw}"

        def rand_non_email():
            base = "".join(r.choice("AbCdef123+._") for _ in range(r.randint(1, 12)))
            if r.random() < 0.5:
                base = base + "\u200b"
            if r.random() < 0.6:
                base = " " + base + " "
            return base

        items = [rand_email() if r.random() < 0.75 else rand_non_email() for _ in range(150)]
        bf = bloom_filter.BloomFilter(m_bits, k_hashes, salt)
        for item in items:
            bf.add(item)

        ref_bits = _reference_bits(m_bits, k_hashes, salt, items)
        assert _snapshot_bits(bf, m_bits) == ref_bits

        probes = []
        for item in items[:40]:
            probes.append(item)
            norm = _normalize_ref(item)
            probes.append(norm)
            if "@" in norm and norm.endswith("gmail.com"):
                probes.append(norm.replace("gmail.com", "googlemail.com"))
                probes.append(norm.replace("gmail.com", "mail.gmail.com"))
        for probe in probes:
            expected = _membership_by_reference(ref_bits, m_bits, k_hashes, salt, probe)
            assert bf.contains(probe) == expected, f"Seed {rnd_seed} mismatch for {probe!r}"


