# Task: Email Bloom Filter Debugger

Goal: implement a tiny Bloom filter at `/app/bloom_filter.py` with Gmail-style email normalization. Tests import `import bloom_filter` and expect `BloomFilter`, `create_email_filter`, and a `_get_bit` helper.

What to build (keep names exact):
- `class BloomFilter(m_bits: int, k_hashes: int, salt: str)` with `add`, `contains`, and `_get_bit`.
- `create_email_filter(items)` that makes a filter with `m_bits=1024`, `k_hashes=4`, `salt="email-filter-v1"`, then adds all items.

Core behavior (no step-by-step hand-holding):
 - Validate ctor args: `m_bits`/`k_hashes` must be positive ints; `salt` must be str; else `ValueError`.
- Hashing: for each i in `[0, k_hashes)`, make key `"{salt}|{i}|{normalized}"`, SHA-256 it, big-endian int, index = `h % m_bits`. `add` sets bits; `contains` checks that all are set. `_get_bit` returns `True`/`False` for the bit state; raise `IndexError` out of range, `TypeError` for non-int indices.

Normalization (the tricky part):
- Drop zero-width `\u200b` and `\ufeff`; strip outer spaces.
- If there's `Name <addr@dom>`, keep only the first `<...>` content.
- If no `"@"`, return the stripped text as-is (case preserved).
- If email: lowercase, split at first `"@"`; IDNA-encode domain if possible (otherwise keep lowercased).
- If domain is `gmail.com` or `googlemail.com`: canonicalize to `gmail.com`, remove dots from local part, drop `+tag`.
- Other domains: keep dots and `+tag`.
- Rejoin as `<local>@<domain>`.

That’s it—fill in the logic yourself.

