#!/bin/bash

set -euo pipefail


cat > bloom_filter.py << 'PY'
from __future__ import annotations

import hashlib
from typing import Iterable


class BloomFilter:
    def __init__(self, m_bits: int, k_hashes: int, salt: str) -> None:
        if not isinstance(m_bits, int) or m_bits <= 0:
            raise ValueError("m_bits must be a positive integer")
        if not isinstance(k_hashes, int) or k_hashes <= 0:
            raise ValueError("k_hashes must be a positive integer")
        if not isinstance(salt, str):
            raise ValueError("salt must be a string")

        self.m_bits = m_bits
        self.k_hashes = k_hashes
        self.salt = salt
        # Represent bit array as an int
        self._bits = 0

    @staticmethod
    def _normalize(item: str) -> str:
        # remove zero-width characters globally
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
            # fallback to lowercased domain unchanged on IDNA failure
            pass

        if domain in ("gmail.com", "googlemail.com"):
            domain = "gmail.com"
            local = local.replace(".", "")
            plus_idx = local.find("+")
            if plus_idx != -1:
                local = local[:plus_idx]

        return f"{local}@{domain}"

    def _indexes_for_item(self, item: str):
        norm = self._normalize(item)
        for i in range(self.k_hashes):
            key = f"{self.salt}|{i}|{norm}"
            digest = hashlib.sha256(key.encode("utf-8")).digest()
            h = int.from_bytes(digest, "big")
            index = h % self.m_bits
            yield index

    def _set_bit(self, index: int) -> None:
        self._bits |= (1 << index)

    def _get_bit(self, index: int) -> bool:
        if not isinstance(index, int):
            raise TypeError("index must be an int")
        if index < 0 or index >= self.m_bits:
            raise IndexError("index out of range")
        return bool(self._bits & (1 << index))

    def add(self, item: str) -> None:
        for idx in self._indexes_for_item(item):
            self._set_bit(idx)

    def contains(self, item: str) -> bool:
        for idx in self._indexes_for_item(item):
            if not self._get_bit(idx):
                return False
        return True


def create_email_filter(items: Iterable[str]) -> BloomFilter:
    bf = BloomFilter(m_bits=1024, k_hashes=4, salt="email-filter-v1")
    for item in items:
        bf.add(item)
    return bf
PY

# This is the oracle implementation that CI will use.
# Agents must effectively rediscover this logic via debugging.
