# Silver Key Challenge: Breaking Weak RSA

## Problem Statement

You intercepted an RSA-encrypted message that uses a **very small public exponent** (e=3). This is a known vulnerability that can be exploited.

## Given Information

The encryption parameters are stored in `/app/challenges/silver_rsa.txt`:
```
N = <large number>
e = 3
ciphertext = <encrypted message>
```

## Vulnerability

When the public exponent `e` is small and the plaintext `m` is also small such that `m^e < N`, the ciphertext `c = m^e mod N` is simply `c = m^e` (without the modular reduction).

In this case, you can recover the plaintext by simply computing the **e-th root** of the ciphertext.

## Task

1. Read the RSA parameters from `/app/challenges/silver_rsa.txt`
2. Exploit the small exponent to recover the plaintext message
3. The plaintext is an integer that represents an ASCII string
4. Convert the integer to a string
5. Write the recovered message to `/app/solutions/silver_plaintext.txt`

## Output Format

Write the recovered plaintext message (as a string) to `/app/solutions/silver_plaintext.txt`.

For example, if the plaintext decodes to "SILVER_KEY", write:
```
SILVER_KEY
```

## Hints

- Since e=3, you need to compute the cube root of the ciphertext
- Python's integer arithmetic can handle large numbers
- For cube root of large integers, you can use: `int(c ** (1/3))` with rounding adjustment
- Or use binary search or Newton's method for exact integer cube roots
- Convert the resulting integer to bytes, then to ASCII string

**WARNING: Wrong answer = INSTANT DEATH!**
