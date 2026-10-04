#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KuGou Unlocker — integrity self-verification (Ed25519 asymmetric signatures)
============================================================================

This project ships with tamper protection: both the graphical interface and
the command-line entry verify every protected file against the signed
integrity manifest (integrity_manifest.json) that was issued by the
developer. The manifest is signed with the developer's Ed25519 private key;
the signature is anchored in integrity_anchor.py and verified in this module
with the embedded public key.

Ed25519 (RFC 8032) is an asymmetric scheme: the private key is held by the
developer only and is never distributed with the software. Therefore nobody —
not even someone holding every shipped file — can forge a valid signature for
a modified manifest. Tampered copies are exposed mathematically at launch.

The software refuses to run whenever any of the following happens:
  - a protected file was modified, replaced or deleted (docs, license,
    installer scripts, the manual, the logo...)
  - the integrity manifest or the anchor file was altered (signature
    verification fails)
  - this verification module itself was tampered with

Per the LICENSE terms this module, the attribution and the disclaimer must
not be removed or altered. When repackaging a release, the developer must
regenerate the manifest and signature with _internal/generate_manifest.py
(a developer-only tool, not distributed with the software).

Author: shushuu (鼠鼠shushuu) — https://github.com/p2109220548-ctrl
Personal non-commercial use only
"""

import hashlib
import json
import os

__author__ = "shushuu (https://github.com/p2109220548-ctrl)"
__license__ = "Personal-NonCommercial-Use-Only (see LICENSE file)"

AUTHOR_LINE = "Developed by shushuu (鼠鼠shushuu) · https://github.com/p2109220548-ctrl"
DISCLAIMER = "Personal use only · No commercial use · Do not redistribute"
OFFICIAL_URL = "https://github.com/p2109220548-ctrl/kugou-unlock-en"

MANIFEST_FILE = "integrity_manifest.json"
ANCHOR_FILE = "integrity_anchor.py"

# Files covered by the integrity check (relative to the app root)
PROTECTED_FILES = [
    "kugou_unlock.py",
    "kugou_unlock_gui.py",
    "kugou_integrity.py",
    "README.md",
    "SKILL.md",
    "LICENSE",
    "requirements.txt",
    "install_windows.bat",
    "install_windows.ps1",
    "start_kugou_unlocker.bat",
    "install_mac.command",
    "docs/python-download-page.png",
    "docs/logo.png",
    "KuGou Unlocker User Manual.pdf",
]

# Ed25519 public key (paired with the developer's _internal/ed25519_secret.key;
# public information — distributing it with the software is safe, since no one
# without the private key can produce a valid manifest signature).
# Changing this constant breaks signature verification and the app refuses to run.
_ED25519_PUBKEY_HEX = "851ed600971745087fabb077569b01711bdc1b1cf4414273fa2ab3a57c1f2a33"

# Branding (banner / about dialog / CLI)
LOGO_TEXT = "shushuu (鼠鼠shushuu)"
ASCII_LOGO = r"""
      (\_._/)     KuGou Unlocker
      ( o.o )     by shushuu (鼠鼠shushuu)
      ( > ^ <)>   Personal use only · No commercial use · Do not redistribute
"""


# ============ Pure-Python Ed25519 implementation (RFC 8032) ============
# Deliberately dependency-free: users never need to install any crypto
# library just for the integrity check (double-click-and-run principle).
# The big-integer implementation takes ~0.1-0.3 s per verification, run
# once at startup. Validated against the official RFC 8032 test vectors
# and cross-checked with the cryptography library.

_Q = 2**255 - 19                                      # field prime (edwards25519)
_L = 2**252 + 27742317777372353535851937790883648493  # group order
_D = (-121665 * pow(121666, _Q - 2, _Q)) % _Q         # curve constant d
_I = pow(2, (_Q - 1) // 4, _Q)                        # sqrt(-1) mod q

_IDENT = (0, 1)                                       # group identity (affine)
_BY = (4 * pow(5, _Q - 2, _Q)) % _Q                   # base point y = 4/5


def _xrecover(y):
    """Recover x from y (RFC 8032 5.1.3)."""
    xx = (y * y - 1) * pow(_D * y * y + 1, _Q - 2, _Q) % _Q
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


_BX = _xrecover(_BY)
_B = (_BX % _Q, _BY % _Q)


def _isoncurve(P):
    """Whether P satisfies -x² + y² = 1 + d·x²·y²."""
    x, y = P
    return (-x * x + y * y - 1 - _D * x * x * y * y) % _Q == 0


def _edwards(P, Q):
    """Edwards curve point addition."""
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * pow(1 + _D * x1 * x2 * y1 * y2, _Q - 2, _Q)
    y3 = (y1 * y2 + x1 * x2) * pow(1 - _D * x1 * x2 * y1 * y2, _Q - 2, _Q)
    return (x3 % _Q, y3 % _Q)


def _scalarmult(P, e):
    """Scalar multiplication [e]P (double-and-add, MSB first)."""
    Q = _IDENT
    for bit in bin(e)[2:]:
        Q = _edwards(Q, Q)
        if bit == "1":
            Q = _edwards(Q, P)
    return Q


def _encodepoint(P):
    """Point encoding: 255-bit y (little-endian) + x parity in the MSB."""
    x, y = P
    ba = bytearray(y.to_bytes(32, "little"))
    ba[31] = (ba[31] & 0x7F) | ((x & 1) << 7)
    return bytes(ba)


def _decodepoint(s):
    """Point decoding (with on-curve check); raises ValueError on bad input."""
    if len(s) != 32:
        raise ValueError("bad point length")
    y = int.from_bytes(s, "little") & ((1 << 255) - 1)
    sign_x = (s[31] >> 7) & 1
    x = _xrecover(y)
    if x & 1 != sign_x:
        x = _Q - x
    P = (x, y)
    if not _isoncurve(P):
        raise ValueError("point not on curve")
    return P


def _secret_expand(seed):
    """Derive scalar a and prefix from the 32-byte seed (RFC 8032 5.1.5/5.1.6)."""
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    h = hashlib.sha512(seed).digest()
    a = 1 << 254
    for i in range(3, 254):
        a += ((h[i >> 3] >> (i & 7)) & 1) << i
    return a, h[32:]


def ed25519_publickey(seed):
    """Derive the 32-byte public key from the seed."""
    a, _prefix = _secret_expand(seed)
    return _encodepoint(_scalarmult(_B, a))


def ed25519_sign(msg, seed):
    """Ed25519 signing (RFC 8032 5.1.6); returns a 64-byte signature."""
    a, prefix = _secret_expand(seed)
    pub = _encodepoint(_scalarmult(_B, a))
    r = int.from_bytes(hashlib.sha512(prefix + msg).digest(), "little")
    R = _encodepoint(_scalarmult(_B, r))
    k = int.from_bytes(hashlib.sha512(R + pub + msg).digest(), "little")
    S = (r + k * a) % _L
    return R + S.to_bytes(32, "little")


def ed25519_verify(sig, msg, pubkey):
    """Ed25519 verification (RFC 8032 5.1.7). Returns bool; malformed input -> False."""
    if len(sig) != 64 or len(pubkey) != 32:
        return False
    try:
        R_pt = _decodepoint(sig[:32])
        A_pt = _decodepoint(pubkey)
    except Exception:
        return False
    S = int.from_bytes(sig[32:], "little")
    if S >= _L:
        return False
    k = int.from_bytes(hashlib.sha512(sig[:32] + pubkey + msg).digest(), "little")
    left = _scalarmult(_B, S)
    right = _edwards(R_pt, _scalarmult(A_pt, k))
    return _encodepoint(left) == _encodepoint(right)


# ============ Integrity verification ============


def sha256_file(path):
    """SHA-256 of a file; returns None when the file cannot be read."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _load_anchor(base_dir):
    """Read the manifest Ed25519 signature from the anchor file (no sys.path import)."""
    path = os.path.join(base_dir, ANCHOR_FILE)
    if not os.path.isfile(path):
        return None, "Integrity anchor file is missing (%s)" % ANCHOR_FILE
    ns = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            exec(f.read(), ns)  # noqa: S102 - reads our own constant file only
    except Exception:
        return None, "Integrity anchor file is corrupted (%s)" % ANCHOR_FILE
    sig_hex = ns.get("ANCHOR_SIGNATURE")
    if not isinstance(sig_hex, str):
        return None, "Integrity anchor content is invalid (%s)" % ANCHOR_FILE
    try:
        sig = bytes.fromhex(sig_hex)
    except ValueError:
        return None, "Integrity anchor content is invalid (%s)" % ANCHOR_FILE
    if len(sig) != 64:
        return None, "Integrity anchor content is invalid (%s)" % ANCHOR_FILE
    return sig, None


def verify(base_dir=None):
    """Full verification. Returns (ok, problems) with English problem strings."""
    base = base_dir or os.path.dirname(os.path.abspath(__file__))

    # 1. Manifest must exist and must pass the Ed25519 signature check
    #    (unforgeable without the developer's private key)
    manifest_path = os.path.join(base, MANIFEST_FILE)
    if not os.path.isfile(manifest_path):
        return False, ["Integrity manifest is missing (%s)" % MANIFEST_FILE]
    try:
        with open(manifest_path, "rb") as f:
            data = f.read()
    except OSError:
        return False, ["Integrity manifest could not be read (%s)" % MANIFEST_FILE]

    signature, err = _load_anchor(base)
    if err:
        return False, [err]
    pubkey = bytes.fromhex(_ED25519_PUBKEY_HEX)
    if not ed25519_verify(signature, data, pubkey):
        return False, ["Manifest signature verification failed (manifest or anchor altered)"]

    try:
        manifest = json.loads(data.decode("utf-8"))
    except Exception:
        return False, ["Integrity manifest is corrupted"]

    # 2. Compare every protected file
    problems = []
    for rel, expect in manifest.get("files", {}).items():
        path = os.path.join(base, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            problems.append("Missing file: %s" % rel)
            continue
        actual = sha256_file(path)
        if actual is None:
            problems.append("File cannot be read: %s" % rel)
        elif actual != expect.get("sha256"):
            problems.append("File has been modified: %s" % rel)
    return (not problems), problems


def fail_text(problems):
    """User-facing message shown when verification fails."""
    lines = [
        "⚠ Integrity check FAILED — program files have been modified or damaged. "
        "The software refuses to run.",
        "",
    ]
    lines += ["  · " + p for p in problems]
    lines += [
        "",
        "To protect your safety and the developer's rights, this software stops "
        "working when its files are altered.",
        "Please download a fresh original copy from the official project page:",
        "  " + OFFICIAL_URL,
        "",
        "—— " + AUTHOR_LINE + " ——",
        "—— " + DISCLAIMER + " ——",
    ]
    return "\n".join(lines)


def banner(version):
    """Startup banner (CLI output / About dialog): logo + attribution + disclaimer."""
    return "%s\n  Version v%s\n%s" % (
        ASCII_LOGO.strip("\n"),
        version,
        "  " + AUTHOR_LINE + "\n  " + DISCLAIMER,
    )
