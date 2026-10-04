#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KuGou Unlocker — core decryption library & command-line tool
============================================================

Restore encrypted audio downloaded from the KuGou desktop client
(.kgm / .kgma / .vpr / .kgg) back to standard audio files
(FLAC / MP3 / WAV / OGG / M4A), with optional transcoding to a
target format when FFmpeg is installed.

Decryption is a **lossless unwrap**: the audio payload is recovered
byte-for-byte, never re-encoded, identical to the original file served
by KuGou. Everything runs locally — nothing is uploaded.

IMPORTANT — personal use only:
    Only process files you legitimately own (downloaded with your own
    account/subscription). Keep decrypted copies for private playback;
    do not redistribute them.

Graphical interface: see kugou_unlock_gui.py in the same folder —
no command-line knowledge required.

Usage (command line)
    python kugou_unlock.py <file-or-folder> <output-dir> [--fmt auto|flac|mp3|wav]
                           [--db PATH] [--keyfile PATH] [--procs N] [--only kgm,kgg]

Dependencies
    Python >= 3.11 (sqlite3.Connection.deserialize)
    numpy        optional, ~20x faster KGM path (pure-Python fallback)
    pycryptodome required only for .kgg (AES page decryption of the key database)
    FFmpeg       optional, only for transcoding (--fmt other than auto)
"""

import argparse
import base64
import hashlib
import os
import shutil
import sqlite3
import struct
import subprocess
import sys

import kugou_integrity as integrity

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

try:
    from Crypto.Cipher import AES
except ImportError:  # pragma: no cover
    AES = None

# ---------------------------------------------------------------------------
# Project signature —— must be kept per the LICENSE terms
# Author: shushuu (鼠鼠shushuu) — https://github.com/p2109220548-ctrl
# Personal non-commercial use only
# ---------------------------------------------------------------------------
__author__ = "shushuu (https://github.com/p2109220548-ctrl)"
__license__ = "Personal-NonCommercial-Use-Only (see LICENSE file)"
__version__ = "2.3.0"
__title__ = "KuGou Unlocker"

AUDIO_EXTS = ("kgm", "kgma", "vpr", "kgg")    # supported encrypted inputs
TARGET_FMTS = ("auto", "flac", "mp3", "wav")  # 'auto' = keep the decrypted original format

# ---------------------------------------------------------------------------
# Part 1: KGM V2 XOR mask (.kgm / .kgma / .vpr)
#
#   fileKey   = header[0x1C:0x2C] + 0x00          (17 bytes)
#   headerLen = uint32 LE at header[0x10]
#   audio     = file bytes starting at headerLen
#   out[i]    = T( maskV2(i) ^ audio[i] ^ fileKey[i % 17] )
#   T(x)      = x ^ ((x & 0x0f) << 4)
#   maskV2(i) = tableV2[i % 272] ^ maskV1(i >> 4)
#   maskV1(o) = while o >= 0x11: v ^= table1[o % 272]; o >>= 4;
#                             v ^= table2[o % 272]; o >>= 4
#   (.vpr additionally XORs vprKey[i % 17] after T)
#
# Constants are the well-known community values used by unlock-music & co.,
# cross-checked against reference implementations.
# ---------------------------------------------------------------------------
TABLE_SIZE = 272

table1 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 33, 1, 97, 1, 33, 1, 225, 1, 33, 1, 97, 1, 33, 1, 210, 35, 2, 2, 66, 66, 2, 2, 194, 194, 2, 2, 66, 66, 2, 2, 211, 211, 2, 3, 99, 67, 99, 3, 227, 195, 227, 3, 99, 67, 99, 3, 148, 180, 148, 101, 4, 4, 4, 4, 132, 132, 132, 132, 4, 4, 4, 4, 149, 149, 149, 149, 4, 5, 37, 5, 229, 133, 165, 133, 229, 5, 37, 5, 214, 182, 150, 182, 214, 39, 6, 6, 198, 198, 134, 134, 198, 198, 6, 6, 215, 215, 151, 151, 215, 215, 6, 7, 231, 199, 231, 135, 231, 199, 231, 7, 24, 56, 24, 120, 24, 56, 24, 233, 8, 8, 8, 8, 8, 8, 8, 8, 25, 25, 25, 25, 25, 25, 25, 25, 8, 9, 41, 9, 105, 9, 41, 9, 218, 58, 26, 58, 90, 58, 26, 58, 218, 43, 10, 10, 74, 74, 10, 10, 219, 219, 27, 27, 91, 91, 27, 27, 219, 219, 10, 11, 107, 75, 107, 11, 156, 188, 156, 124, 28, 60, 28, 124, 156, 188, 156, 109, 12, 12, 12, 12, 157, 157, 157, 157, 29, 29, 29, 29, 157, 157, 157, 157, 12, 13, 45, 13, 222, 190, 158, 190, 222, 62, 30, 62, 222, 190, 158, 190, 222, 47, 14, 14, 223, 223, 159, 159, 223, 223, 31, 31, 223, 223, 159, 159, 223, 223, 14, 15, 0, 32, 0, 96, 0, 32, 0, 224, 0, 32, 0, 96, 0, 32, 0, 241]
table2 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 35, 1, 103, 1, 35, 1, 239, 1, 35, 1, 103, 1, 35, 1, 223, 33, 2, 2, 70, 70, 2, 2, 206, 206, 2, 2, 70, 70, 2, 2, 222, 222, 2, 3, 101, 71, 101, 3, 237, 207, 237, 3, 101, 71, 101, 3, 157, 191, 157, 99, 4, 4, 4, 4, 140, 140, 140, 140, 4, 4, 4, 4, 156, 156, 156, 156, 4, 5, 39, 5, 235, 141, 175, 141, 235, 5, 39, 5, 219, 189, 159, 189, 219, 37, 6, 6, 202, 202, 142, 142, 202, 202, 6, 6, 218, 218, 158, 158, 218, 218, 6, 7, 233, 203, 233, 143, 233, 203, 233, 7, 25, 59, 25, 127, 25, 59, 25, 231, 8, 8, 8, 8, 8, 8, 8, 8, 24, 24, 24, 24, 24, 24, 24, 24, 8, 9, 43, 9, 111, 9, 43, 9, 215, 57, 27, 57, 95, 57, 27, 57, 215, 41, 10, 10, 78, 78, 10, 10, 214, 214, 26, 26, 94, 94, 26, 26, 214, 214, 10, 11, 109, 79, 109, 11, 149, 183, 149, 123, 29, 63, 29, 123, 149, 183, 149, 107, 12, 12, 12, 12, 148, 148, 148, 148, 28, 28, 28, 28, 148, 148, 148, 148, 12, 13, 47, 13, 211, 181, 151, 181, 211, 61, 31, 61, 211, 181, 151, 181, 211, 45, 14, 14, 210, 210, 150, 150, 210, 210, 30, 30, 210, 210, 150, 150, 210, 210, 14, 15, 0, 34, 0, 102, 0, 34, 0, 238, 0, 34, 0, 102, 0, 34, 0, 254]
tableV2 = [184, 213, 61, 178, 233, 175, 120, 140, 131, 51, 113, 81, 118, 160, 205, 55, 47, 62, 53, 141, 169, 190, 152, 183, 231, 140, 34, 206, 90, 97, 223, 104, 105, 137, 254, 165, 182, 222, 169, 119, 252, 200, 189, 189, 229, 109, 62, 90, 54, 239, 105, 78, 190, 225, 233, 102, 28, 243, 217, 2, 182, 242, 18, 155, 68, 208, 111, 185, 53, 137, 182, 70, 109, 115, 130, 6, 105, 193, 237, 215, 133, 194, 48, 223, 162, 98, 190, 121, 45, 98, 98, 61, 13, 126, 190, 72, 137, 35, 2, 160, 228, 213, 117, 81, 50, 2, 83, 253, 22, 58, 33, 59, 22, 15, 195, 178, 187, 179, 226, 186, 58, 61, 19, 236, 246, 1, 69, 132, 165, 112, 15, 147, 73, 12, 100, 205, 49, 213, 204, 76, 7, 1, 158, 0, 26, 35, 144, 191, 136, 30, 59, 171, 166, 62, 196, 115, 71, 16, 126, 59, 94, 188, 227, 0, 132, 255, 9, 212, 224, 137, 15, 91, 88, 112, 79, 251, 101, 216, 92, 83, 27, 211, 200, 198, 191, 239, 152, 176, 80, 79, 15, 234, 229, 131, 88, 140, 40, 44, 132, 103, 205, 208, 158, 71, 219, 39, 80, 202, 244, 99, 99, 232, 151, 127, 27, 75, 12, 194, 193, 33, 76, 204, 88, 245, 148, 82, 163, 243, 211, 224, 104, 244, 0, 35, 243, 94, 10, 123, 147, 221, 171, 18, 178, 19, 232, 132, 215, 167, 159, 15, 50, 76, 85, 29, 4, 54, 82, 220, 3, 243, 249, 78, 66, 233, 61, 97, 239, 124, 182, 179, 147, 80]
vprKey = [37, 223, 232, 166, 117, 30, 117, 14, 47, 128, 243, 45, 184, 182, 227, 17, 0]

if np is not None:
    _t1 = np.array(table1, dtype=np.uint8)
    _t2 = np.array(table2, dtype=np.uint8)
    _tv2 = np.array(tableV2, dtype=np.uint8)
    _T_LUT = np.array([x ^ ((x & 0x0F) << 4) & 0xFF for x in range(256)], dtype=np.uint8)


def _mask_v1_scalar(offset):
    """Scalar reference implementation of mask_v1 (pure-Python fallback)."""
    value = 0
    while offset >= 0x11:
        value ^= table1[offset % TABLE_SIZE]
        offset >>= 4
        value ^= table2[offset % TABLE_SIZE]
        offset >>= 4
    return value


def _mask_v1_block(j0, count):
    """mask_v1(j) for j in [j0, j0+count) — vectorised with numpy."""
    o = np.arange(j0, j0 + count, dtype=np.uint64)
    acc = np.zeros(count, dtype=np.uint8)
    while True:
        act = o >= 0x11
        if not act.any():
            break
        oa = o[act]
        a = acc[act]
        a ^= _t1[oa % 272]
        oa = oa >> 4
        a ^= _t2[oa % 272]
        oa = oa >> 4
        acc[act] = a
        o[act] = oa
    return acc


CHUNK = 1 << 25  # 32 MB per chunk; must stay a multiple of 16 (maskV1(i>>4) boundary)


def decrypt_xor_stream(fin, fout, is_vpr=False):
    """Decrypt a .kgm/.kgma/.vpr file. Returns the detected audio format."""
    with open(fin, 'rb') as f:
        header = f.read(0x3C)
        if len(header) < 0x3C:
            raise ValueError('file too small / not a KGM container')
        fk = np.frombuffer(header[0x1C:0x2C] + b'\x00', dtype=np.uint8) if np is not None \
            else header[0x1C:0x2C] + b'\x00'
        header_len = struct.unpack_from('<I', header, 0x10)[0]
        f.seek(header_len)
        total = os.fstat(f.fileno()).st_size - header_len
        with open(fout, 'wb') as g:
            if np is not None:
                # numpy fast path: build the mask stream per chunk, XOR in bulk (C speed)
                off0 = 0
                vk = np.array(vprKey, dtype=np.uint8) if is_vpr else None
                while off0 < total:
                    n = min(CHUNK, total - off0)
                    audio = np.frombuffer(f.read(n), dtype=np.uint8)
                    rot = off0 % 272
                    t2p = np.tile(np.roll(_tv2, -rot), int(np.ceil(n / 272)) + 1)[:n]
                    rotf = off0 % 17
                    fkp = np.tile(np.roll(fk, -rotf), int(np.ceil(n / 17)) + 1)[:n]
                    cs = _mask_v1_block(off0 >> 4, (n >> 4) + 1)
                    v1p = np.repeat(cs, 16)[:n]
                    out = _T_LUT[audio ^ t2p ^ v1p ^ fkp]
                    if is_vpr:
                        out ^= np.tile(np.roll(vk, off0 % 17), int(np.ceil(n / 17)) + 1)[:n]
                    g.write(out.tobytes())
                    off0 += n
            else:
                # pure-python fallback (byte-exact, just slower)
                filekey = bytes(fk)
                offset = 0
                while True:
                    block = f.read(1 << 16)
                    if not block:
                        break
                    b = bytearray(block)
                    for i in range(len(b)):
                        x = _mask_v1_scalar((offset + i) >> 4) ^ tableV2[(offset + i) % TABLE_SIZE] \
                            ^ block[i] ^ filekey[(offset + i) % 17]
                        b[i] = (x ^ ((x & 0x0F) << 4)) & 0xFF
                    if is_vpr:
                        for i in range(len(b)):
                            b[i] ^= vprKey[(offset + i) % 17]
                    g.write(b)
                    offset += len(b)
    return detect_format_path(fout)


# ---------------------------------------------------------------------------
# Part 2: output format detection (audio magic bytes)
# ---------------------------------------------------------------------------
def detect_format_bytes(head):
    """Detect the audio format from magic bytes."""
    if head[:4] == b'fLaC':
        return 'flac'
    if head[:3] == b'ID3' or (len(head) > 1 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return 'mp3'
    if head[:4] == b'RIFF':
        return 'wav'
    if head[:4] == b'OggS':
        return 'ogg'
    if head[4:8] == b'ftyp':
        return 'm4a'
    return 'unknown'


def detect_format_path(path):
    with open(path, 'rb') as f:
        return detect_format_bytes(f.read(8))


def is_valid_audio_bytes(head):
    """Validate magic bytes. Invalid output is always discarded."""
    return detect_format_bytes(head) != 'unknown'


# ---------------------------------------------------------------------------
# Part 3: KGMusicV3.db (KGG key database) page decryption
#
# The KuGou client stores per-file ekeys in KGMusicV3.db, custom-page-encrypted
# with AES-128-CBC. Page key/iv are derived from a well-known community master
# key (same constant as unlock-music / Kugo-Music-Converter). Overridable via
# the KGG_DB_MASTER_KEY env var (hex). Decryption happens fully in memory.
# ---------------------------------------------------------------------------
DB_PAGE = 0x400
SQLITE_HDR = b'SQLite format 3\x00'
DEFAULT_MASTER_KEY = bytes([0x1D, 0x61, 0x31, 0x45, 0xB2, 0x47, 0xBF, 0x7F,
                            0x3D, 0x18, 0x96, 0x72, 0x14, 0x4F, 0xE4, 0xBF])


def _u32(x):
    return x & 0xFFFFFFFF


def _next_page_iv(seed):
    left = _u32(seed * 0x9EF4)
    right = _u32((seed // 0xCE26) * 0x7FFFFF07)
    value = _u32(left - right)
    if value & 0x80000000 == 0:
        return value
    return _u32(value + 0x7FFFFF07)


def _page_key(seed, master):
    buf = master + struct.pack('<I', seed) + struct.pack('<I', 0x546C4173)
    return hashlib.md5(buf).digest()


def _page_iv(seed):
    iv = b''
    s = _u32(seed + 1)
    for _ in range(4):
        s = _next_page_iv(s)
        iv += struct.pack('<I', s)
    return hashlib.md5(iv).digest()


def decrypt_kgg_db(db_path, master=None):
    """Decrypt KGMusicV3.db and return {audioHash: ekey}."""
    if AES is None:
        raise RuntimeError('pycryptodome is required for .kgg:  pip install pycryptodome')
    if master is None:
        env = os.environ.get('KGG_DB_MASTER_KEY', '').strip()
        master = bytes.fromhex(env) if env else DEFAULT_MASTER_KEY
    data = open(db_path, 'rb').read()
    if data[:16] == SQLITE_HDR:
        plain = data  # already a plain sqlite database
    else:
        if len(data) % DB_PAGE != 0:
            raise ValueError('kgg db: invalid database size %d' % len(data))
        buf = bytearray(data)
        p1 = bytearray(buf[:DB_PAGE])
        o10 = struct.unpack_from('<I', p1, 0x10)[0]
        o14 = struct.unpack_from('<I', p1, 0x14)[0]
        v6 = ((o10 & 0xFF) << 8) | ((o10 & 0xFF00) << 16)
        if not (o14 == 0x20204000 and _u32(v6 - 0x200) <= 0xFE00 and ((v6 - 1) & v6) == 0):
            raise ValueError('kgg db: page1 header invalid')
        expected = bytes(p1[0x10:0x18])
        p1[0x10:0x18] = p1[0x08:0x10]  # move the integrity anchor into the decrypt region
        c = AES.new(_page_key(1, master), AES.MODE_CBC, _page_iv(1))
        p1[0x10:] = c.decrypt(bytes(p1[0x10:]))
        if p1[0x10:0x18] != expected:
            raise ValueError('kgg db: page1 integrity failed (wrong master key?)')
        p1[:16] = SQLITE_HDR  # restore the standard SQLite magic
        buf[:DB_PAGE] = p1
        for pg in range(2, len(buf) // DB_PAGE + 1):
            off = (pg - 1) * DB_PAGE
            c = AES.new(_page_key(pg, master), AES.MODE_CBC, _page_iv(pg))
            buf[off:off + DB_PAGE] = c.decrypt(bytes(buf[off:off + DB_PAGE]))
        plain = bytes(buf)
    con = sqlite3.connect(':memory:')
    try:
        con.deserialize(plain)
        rows = con.execute(
            "SELECT EncryptionKeyId, EncryptionKey FROM ShareFileItems "
            "WHERE EncryptionKeyId IS NOT NULL AND EncryptionKeyId != '' "
            "AND EncryptionKey IS NOT NULL AND EncryptionKey != ''"
        ).fetchall()
    finally:
        con.close()
    return {k if isinstance(k, str) else k.decode('latin-1'):
            v if isinstance(v, str) else v.decode('latin-1') for k, v in rows}


def load_kgg_key_file(path):
    """Parse a kgg.key text file ('<audioHash>$<ekey>' per line)."""
    out = {}
    for line in open(path, 'r', encoding='utf-8', errors='replace').read().splitlines():
        if '$' in line:
            k, v = line.split('$', 1)
            if k:
                out[k] = v
    return out


def _kugou_data_dirs():
    """Collect common KuGou data directories (cross-platform):
    Windows looks in AppData, macOS in ~/Library."""
    dirs = []
    home = os.path.expanduser('~')
    if os.name == 'nt':
        for env in ('APPDATA', 'LOCALAPPDATA'):
            base = os.environ.get(env)
            if base:
                dirs.append(os.path.join(base, 'KuGou8'))
    else:
        # macOS: data lives under ~/Library/Application Support in folders
        # whose name contains "KuGou"; sandboxed clients hide inside
        # ~/Library/Containers/<App>/Data/Library/Application Support
        support = os.path.join(home, 'Library', 'Application Support')
        if os.path.isdir(support):
            try:
                for name in os.listdir(support):
                    if 'kugou' in name.lower():
                        dirs.append(os.path.join(support, name))
            except OSError:
                pass
        containers = os.path.join(home, 'Library', 'Containers')
        if os.path.isdir(containers):
            try:
                for name in os.listdir(containers):
                    if 'kugou' in name.lower():
                        dirs.append(os.path.join(containers, name, 'Data',
                                                 'Library', 'Application Support'))
            except OSError:
                pass
    return [d for d in dirs if os.path.isdir(d)]


def discover_kgg_db():
    """Best-effort auto-discovery of the local KuGou key database."""
    for base in _kugou_data_dirs():
        cand = os.path.join(base, 'KGMusicV3.db')
        if os.path.exists(cand):
            return cand
    return None


def _read_kugou_ini_download_path():
    """Read the user-configured download directory from KuGou.ini (DownloadPath).

    The ini file is UTF-16 encoded; other encodings are attempted as fallback
    for different KuGou versions. Returns None when unavailable.
    """
    for base in _kugou_data_dirs():
        ini = os.path.join(base, 'KuGou.ini')
        if not os.path.exists(ini):
            continue
        raw = open(ini, 'rb').read()
        text = None
        for enc in ('utf-16', 'utf-16-le', 'gbk', 'utf-8'):
            try:
                text = raw.decode(enc)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if not text:
            continue
        for line in text.splitlines():
            if line.strip().lower().startswith('downloadpath='):
                path = line.split('=', 1)[1].strip().strip('"')
                if path and os.path.isdir(path):
                    return path
    return None


def _dir_has_encrypted_audio(path):
    """Quick (non-recursive) check whether a folder holds encrypted audio."""
    try:
        for name in os.listdir(path):
            if os.path.splitext(name)[1].lower().lstrip('.') in AUDIO_EXTS:
                return True
    except OSError:
        return False
    return False


def discover_kugou_music_dir():
    """Auto-discover the KuGou download folder.

    Lookup order:
    1. The download directory recorded in the KuGou config (KuGou.ini,
       DownloadPath) and its KugouMusic / KGMusic sub-folders — the most
       accurate source;
    2. Common default locations: on Windows every drive letter is scanned
       (X:\\KuGou\\KugouMusic etc., plus KuGou / KuGou8 under Program Files /
       Program Files (x86)); on macOS the user's Music (~/Music/KuGou) and
       Documents folders are checked. Both platforms also look for
       KugouMusic / KGMusic inside the KuGou data directories.

    Returns the first candidate that actually contains encrypted audio;
    if none does, returns the first existing candidate; None when nothing
    is found.
    """
    candidates = []
    dl = _read_kugou_ini_download_path()
    if dl:
        candidates.append(dl)
        candidates.append(os.path.join(dl, 'KugouMusic'))
        candidates.append(os.path.join(dl, 'KGMusic'))
    # Windows: scan common default locations on every drive letter (C:, D:, …):
    # drive roots + KuGou / KuGou8 under Program Files / Program Files (x86)
    if os.name == 'nt':
        import string
        for letter in string.ascii_uppercase:
            root = letter + ':\\'
            if not os.path.exists(root):
                continue
            for sub in ('KuGou', 'KuGou8',
                        os.path.join('Program Files', 'KuGou'),
                        os.path.join('Program Files', 'KuGou8'),
                        os.path.join('Program Files (x86)', 'KuGou'),
                        os.path.join('Program Files (x86)', 'KuGou8')):
                candidates.append(os.path.join(root, sub, 'KugouMusic'))
                candidates.append(os.path.join(root, sub, 'KGMusic'))
            # Very old versions: downloads went straight into the install dir
            candidates.append(os.path.join(root, 'Program Files', 'KuGou',
                                            'KGMusic', 'DownloadMusic'))
            candidates.append(os.path.join(root, 'Program Files (x86)', 'KuGou',
                                            'KGMusic', 'DownloadMusic'))
    # The user's Music / Documents folders (modern clients default to
    # %USERPROFILE%\\Music\\KuGou)
    home = os.path.expanduser('~')
    candidates.append(os.path.join(home, 'Music', 'KuGou'))
    candidates.append(os.path.join(home, 'Music', 'KuGou', 'KugouMusic'))
    candidates.append(os.path.join(home, 'Music', 'KuGou', 'KGMusic'))
    candidates.append(os.path.join(home, 'Music', 'KugouMusic'))
    candidates.append(os.path.join(home, 'Music', 'KGMusic'))
    candidates.append(os.path.join(home, 'Documents', 'KuGou', 'KGMusic'))
    candidates.append(os.path.join(home, 'Documents', 'KuGou', 'KugouMusic'))
    # Song sub-folders inside the KuGou data directories
    # (macOS: ~/Library/Application Support/KuGou and friends)
    for base in _kugou_data_dirs():
        candidates.append(os.path.join(base, 'KugouMusic'))
        candidates.append(os.path.join(base, 'KGMusic'))
        candidates.append(os.path.join(base, 'DownloadMusic'))
    candidates = [os.path.normpath(c) for c in candidates]
    seen, unique = set(), []
    for c in candidates:
        if c not in seen and os.path.isdir(c):
            seen.add(c)
            unique.append(c)
    for c in unique:
        if _dir_has_encrypted_audio(c):
            return c
    return unique[0] if unique else None


def find_kgg_keymap(db_path=None, keyfile=None):
    """Collect the kgg key map: key database first, then keyfile on top."""
    keymap = {}
    db = db_path or discover_kgg_db()
    if db and os.path.exists(db):
        keymap.update(decrypt_kgg_db(db))
    if keyfile and os.path.exists(keyfile):
        keymap.update(load_kgg_key_file(keyfile))
    return keymap


# ---------------------------------------------------------------------------
# Part 4: ekey derivation (Tencent TEA, 32 half-rounds)
# ---------------------------------------------------------------------------
DELTA = 0x9E3779B9
RAW_KEY_PREFIX_V2 = b'QQMusic EncV2,Key:'
DERIVE_V2_KEY1 = bytes([0x33, 0x38, 0x36, 0x5A, 0x4A, 0x59, 0x21, 0x40, 0x23, 0x2A, 0x24, 0x25, 0x5E, 0x26, 0x29, 0x28])
DERIVE_V2_KEY2 = bytes([0x2A, 0x2A, 0x23, 0x21, 0x28, 0x23, 0x24, 0x25, 0x26, 0x5E, 0x61, 0x31, 0x63, 0x5A, 0x2C, 0x54])


def _tea_decrypt_block(v0, v1, k, rounds=32):
    # rounds semantics aligned with x/crypto/tea: `rounds` half-rounds,
    # i.e. rounds//2 double-rounds; initial sum = delta * (rounds//2).
    s = (DELTA * (rounds // 2)) & 0xFFFFFFFF
    for _ in range(rounds // 2):
        v1 = (v1 - ((((v0 << 4) & 0xFFFFFFFF) + k[2]) ^ ((v0 + s) & 0xFFFFFFFF) ^ (((v0 >> 5) & 0xFFFFFFFF) + k[3]))) & 0xFFFFFFFF
        v0 = (v0 - ((((v1 << 4) & 0xFFFFFFFF) + k[0]) ^ ((v1 + s) & 0xFFFFFFFF) ^ (((v1 >> 5) & 0xFFFFFFFF) + k[1]))) & 0xFFFFFFFF
        s = (s - DELTA) & 0xFFFFFFFF
    return v0, v1


def _tea_decrypt(data, key):
    """TEA ECB decrypt of a multiple of 8 bytes (big-endian blocks)."""
    k = struct.unpack('>4I', key)
    out = bytearray()
    for i in range(0, len(data), 8):
        v0, v1 = struct.unpack('>2I', data[i:i + 8])
        v0, v1 = _tea_decrypt_block(v0, v1, k)
        out += struct.pack('>2I', v0, v1)
    return bytes(out)


def _simple_make_key(salt, length):
    import math
    out = bytearray()
    for i in range(length):
        out.append(int(abs(math.tan(salt + i * 0.1)) * 100.0) & 0xFF)
    return bytes(out)


def _decrypt_tencent_tea(in_buf, key):
    """TC_TEA CBC decrypt (TarsCpp variant: plaintext[i] = D(dest) ^ ivPrev)."""
    salt_len, zero_len = 2, 7
    if len(in_buf) % 8 != 0:
        raise ValueError('tea: input not a multiple of 8')
    if len(in_buf) < 16:
        raise ValueError('tea: input too small')
    dest = bytearray(_tea_decrypt(in_buf[:8], key))
    pad_len = dest[0] & 0x7
    out_len = len(in_buf) - 1 - pad_len - salt_len - zero_len
    out = bytearray(out_len)
    iv_prev = bytearray(8)
    iv_cur = in_buf[:8]
    pos = 8
    dest_idx = 1 + pad_len

    def crypt_block():
        nonlocal iv_prev, iv_cur, pos, dest_idx, dest
        iv_prev = iv_cur
        iv_cur = in_buf[pos:pos + 8]
        for i in range(8):
            dest[i] ^= in_buf[pos + i]
        dest[:] = _tea_decrypt(bytes(dest), key)
        pos += 8
        dest_idx = 0

    i = 1
    while i <= salt_len:
        if dest_idx < 8:
            dest_idx += 1
            i += 1
        elif dest_idx == 8:
            crypt_block()
    out_pos = 0
    while out_pos < out_len:
        if dest_idx < 8:
            out[out_pos] = dest[dest_idx] ^ iv_prev[dest_idx]
            dest_idx += 1
            out_pos += 1
        elif dest_idx == 8:
            crypt_block()
    return bytes(out)


def derive_key(ekey_str):
    """ekey string -> raw QMC2 key (EncV1/EncV2)."""
    raw = base64.b64decode(ekey_str)
    if raw.startswith(RAW_KEY_PREFIX_V2):
        buf = _decrypt_tencent_tea(raw[len(RAW_KEY_PREFIX_V2):], DERIVE_V2_KEY1)
        buf = _decrypt_tencent_tea(buf, DERIVE_V2_KEY2)
        raw = base64.b64decode(buf)
    if len(raw) < 16:
        raise ValueError('ekey too short')
    simple = _simple_make_key(106, 8)
    tea_key = bytearray(16)
    for i in range(8):
        tea_key[i << 1] = simple[i]
        tea_key[i << 1 | 1] = raw[i]
    rs = _decrypt_tencent_tea(raw[8:], bytes(tea_key))
    return raw[:8] + rs


# ---------------------------------------------------------------------------
# Part 5: QMC2 stream ciphers (MAP / RC4), as used by QQ Music & KuGou kgg
# ---------------------------------------------------------------------------
class QMC2Map:
    """QMCv2 MAP cipher (key length <= 300), driven by a 0x8000 mask table."""

    def __init__(self, key):
        self.key = key
        self.size = len(key)
        masks = bytearray(0x8000)
        for o in range(0x8000):
            idx = (o * o + 71214) % self.size
            v = key[idx]
            r = ((idx & 7) + 4) % 8
            # NOTE: (v << r) | (v >> r) is NOT a rotate — both shifts use the
            # same amount and are truncated to 8 bits. Keep as-is.
            masks[o] = ((v << r) | (v >> r)) & 0xFF
        self.masks = bytes(masks)

    def _mask_stream(self, offset, n):
        out = bytearray()
        off = offset
        while len(out) < n:
            if off <= 0x7FFF:
                mo = off
                cs = 0x7FFF - off + 1
            else:
                mo = off % 0x7FFF
                cs = 0x7FFF - mo
            cs = min(cs, n - len(out))
            out += self.masks[mo:mo + cs]
            off += cs
        return bytes(out[:n])

    def decrypt(self, audio, offset=0):
        ms = self._mask_stream(offset, len(audio))
        return (int.from_bytes(audio, 'big') ^ int.from_bytes(ms, 'big')).to_bytes(len(audio), 'big')


class QMC2RC4:
    """QMCv2 RC4 cipher (key length > 300), segmented PRGA."""

    SEG = 5120
    FIRST = 128

    def __init__(self, key):
        self.key = key
        self.n = n = len(key)
        # Go: box[i] = byte(i) — wraps modulo 256 when n > 256. Keep it.
        box = [i & 0xFF for i in range(n)]
        j = 0
        for i in range(n):
            j = (j + box[i] + key[i % n]) % n
            box[i], box[j] = box[j], box[i]
        self.box = bytes(box)
        h = 1
        for i in range(n):
            v = key[i]
            if v == 0:
                continue
            nh = (h * v) & 0xFFFFFFFF
            if nh == 0 or nh <= h:
                break
            h = nh
        self.hash = h

    def _seg_skip(self, seg_id):
        seed = self.key[seg_id % self.n]
        denom = (seg_id + 1) * seed
        if denom == 0:
            # Go amd64: division by zero -> +Inf -> int64(+Inf) = INT64_MIN,
            # then uint64(bit pattern) % n. Byte-exact with unlock-music.
            return 0x8000000000000000 % self.n
        idx = int(float(self.hash) / float(denom) * 100.0)
        return (idx & 0xFFFFFFFFFFFFFFFF) % self.n

    def _enc_segment(self, buf, start, length, off):
        box = bytearray(self.box)
        j = k = 0
        n = self.n
        skip = (off % self.SEG) + self._seg_skip(off // self.SEG)
        for i in range(-skip, length):
            j = (j + 1) % n
            k = (box[j] + k) % n
            box[j], box[k] = box[k], box[j]
            if i >= 0:
                buf[start + i] ^= box[(box[j] + box[k]) % n]

    def decrypt(self, audio, offset=0):
        buf = bytearray(audio)
        off = offset
        to_process = len(buf)
        processed = 0
        if off < self.FIRST:
            bs = min(to_process, self.FIRST - off)
            for i in range(bs):
                buf[processed + i] ^= self.key[self._seg_skip(off + i)]
            off += bs; to_process -= bs; processed += bs
            if to_process == 0:
                return bytes(buf)
        if off % self.SEG != 0:
            bs = min(to_process, self.SEG - off % self.SEG)
            self._enc_segment(buf, processed, bs, off)
            off += bs; to_process -= bs; processed += bs
            if to_process == 0:
                return bytes(buf)
        while to_process > self.SEG:
            self._enc_segment(buf, processed, self.SEG, off)
            off += self.SEG; to_process -= self.SEG; processed += self.SEG
        if to_process > 0:
            self._enc_segment(buf, processed, to_process, off)
        return bytes(buf)


def make_qmc2(ekey_str):
    """Build the QMC2 decryptor matching the given ekey."""
    key = derive_key(ekey_str)
    if len(key) > 300:
        return QMC2RC4(key)
    return QMC2Map(key)


# ---------------------------------------------------------------------------
# Part 6: .kgg file decryption
# ---------------------------------------------------------------------------
KGM_MAGIC = bytes([0x7C, 0xD5, 0x32, 0xEB, 0x86, 0x02, 0x7F, 0x4B, 0xA8, 0xAF, 0xA6, 0x8E, 0x0F, 0xFF, 0x99, 0x14])
VPR_MAGIC = bytes([0x05, 0x28, 0xBC, 0x96, 0xE9, 0xE4, 0x5A, 0x43, 0x91, 0xAA, 0xBD, 0xD0, 0x7A, 0xF5, 0x36, 0x31])


def decrypt_kgg(in_path, out_path, keymap):
    """Decrypt one .kgg file using {audioHash: ekey}. Returns audio format."""
    with open(in_path, 'rb') as f:
        head = f.read(0x48 + 256)
    if len(head) < 0x48:
        raise ValueError('kgg: file too small')
    if head[:16] not in (KGM_MAGIC, VPR_MAGIC):
        raise ValueError('kgg: magic mismatch (not a kgg file?)')
    header_len = struct.unpack_from('<I', head, 0x10)[0]
    ver = struct.unpack_from('<I', head, 0x14)[0]
    if ver != 5:
        raise ValueError('kgg: unsupported crypto version %d' % ver)
    hash_len = struct.unpack_from('<I', head, 0x44)[0]
    if hash_len <= 0 or hash_len > 256:
        raise ValueError('kgg: implausible audio hash length %d' % hash_len)
    audio_hash = head[0x48:0x48 + hash_len].decode('latin-1')
    if audio_hash not in keymap:
        raise KeyError('kgg: ekey not found for this file '
                       '(play the song once in KuGou, then retry)')
    cipher = make_qmc2(keymap[audio_hash])
    with open(in_path, 'rb') as f:
        f.seek(header_len)
        audio = f.read()
    data = cipher.decrypt(audio, 0)
    fmt = detect_format_bytes(data[:8])
    if fmt == 'unknown':
        raise ValueError('kgg: decrypted output has invalid magic (wrong key?)')
    with open(out_path, 'wb') as g:
        g.write(data)
    return fmt


# ---------------------------------------------------------------------------
# Part 7: FFmpeg transcoding (optional)
# ---------------------------------------------------------------------------
def check_ffmpeg():
    """Return the FFmpeg executable path, or None if not installed."""
    return shutil.which('ffmpeg')


def transcode(src, dst, target_fmt):
    """Transcode src to target_fmt (flac / mp3 / wav) via FFmpeg. Returns dst.

    MP3 uses 320kbps CBR; FLAC/WAV are lossless transcodes.
    """
    exe = check_ffmpeg()
    if not exe:
        raise RuntimeError('FFmpeg not found — transcoding unavailable '
                           '("keep original format" works without it)')
    if target_fmt == 'flac':
        cmd = [exe, '-y', '-i', src, '-c:a', 'flac', dst]
    elif target_fmt == 'mp3':
        cmd = [exe, '-y', '-i', src, '-c:a', 'libmp3lame', '-b:a', '320k', dst]
    elif target_fmt == 'wav':
        cmd = [exe, '-y', '-i', src, '-c:a', 'pcm_s16le', dst]
    else:
        raise ValueError('unsupported transcode target: %s' % target_fmt)
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if proc.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError('FFmpeg transcode failed: %s' % proc.stderr.decode('utf-8', 'replace')[-300:])
    return dst


# ---------------------------------------------------------------------------
# Part 8: high-level API (shared by the GUI and the CLI)
# ---------------------------------------------------------------------------
def collect_files(src, only=None):
    """Collect encrypted audio. src may be a folder, a file path, or a list
    of file paths. Returns [(path, lowercase-ext)]."""
    if isinstance(src, (list, tuple)):
        out = []
        for p in src:
            ext = os.path.splitext(p)[1].lower().lstrip('.')
            if ext in AUDIO_EXTS and (not only or ext in only):
                out.append((p, ext))
        return out
    if os.path.isfile(src):
        ext = os.path.splitext(src)[1].lower().lstrip('.')
        if ext not in AUDIO_EXTS:
            raise ValueError('unsupported input: .%s (want one of %s)' % (ext, '/'.join(AUDIO_EXTS)))
        return [(src, ext)]
    picked = []
    for name in sorted(os.listdir(src)):
        ext = os.path.splitext(name)[1].lower().lstrip('.')
        if ext in AUDIO_EXTS and (not only or ext in only):
            picked.append((os.path.join(src, name), ext))
    return picked


def decrypt_file(src, out_dir, target_fmt='auto', keymap=None, db_path=None, keyfile=None):
    """Decrypt a single file into out_dir, transcoding when requested.

    target_fmt: 'auto' keeps the decrypted original format (lossless);
    'flac'/'mp3'/'wav' transcode. Returns (output-path, actual-format).
    """
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(src)[1].lower().lstrip('.')
    if ext not in AUDIO_EXTS:
        raise ValueError('unsupported input: .%s' % ext)
    base = os.path.splitext(os.path.basename(src))[0]
    tmp = os.path.join(out_dir, base + '.dec.tmp')
    if ext == 'kgg':
        if keymap is None:
            keymap = find_kgg_keymap(db_path, keyfile)
        raw_fmt = decrypt_kgg(src, tmp, keymap)
    else:
        raw_fmt = decrypt_xor_stream(src, tmp, is_vpr=(ext == 'vpr'))
    try:
        if target_fmt != 'auto' and target_fmt != raw_fmt:
            final = transcode(tmp, os.path.join(out_dir, base + '.' + target_fmt), target_fmt)
            os.remove(tmp)
            return final, target_fmt
        final = os.path.join(out_dir, base + '.' + raw_fmt)
        os.replace(tmp, final)
        return final, raw_fmt
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def batch_convert(src, out_dir, target_fmt='auto', procs=None, db_path=None,
                  keyfile=None, progress_cb=None):
    """Batch decrypt (+ optional transcode). src may be a file, folder or list.

    progress_cb(done, total, path, status, info) fires once per finished file;
    status is 'ok' or 'fail'. Returns (succeeded, failed).
    """
    os.makedirs(out_dir, exist_ok=True)
    items = collect_files(src)
    if not items:
        if progress_cb:
            progress_cb(0, 0, src, 'ok', 'no encrypted audio files found')
        return 0, 0
    if procs is None:
        procs = min(8, os.cpu_count() or 4)

    # The key database is only needed when the folder contains .kgg files
    has_kgg = any(ext == 'kgg' for _, ext in items)
    keymap = find_kgg_keymap(db_path, keyfile) if has_kgg else {}
    if has_kgg and not keymap:
        raise RuntimeError('this folder contains .kgg files but no usable key was found '
                           '(install the KuGou client and play the songs once)')

    # Same song present as both e.g. .kgma and .kgg -> the kgg copy gets a
    # " (kgg)" suffix so neither output overwrites the other.
    from collections import Counter
    base_count = Counter(os.path.splitext(os.path.basename(p))[0] for p, _ in items)

    jobs = []
    for path, ext in items:
        base = os.path.splitext(os.path.basename(path))[0]
        if ext == 'kgg' and base_count[base] > 1:
            base = base + ' (kgg)'
        jobs.append((path, base, ext))

    def run_one(job):
        path, base, ext = job
        tmp = os.path.join(out_dir, base + '.dec.tmp')
        try:
            if ext == 'kgg':
                raw_fmt = decrypt_kgg(path, tmp, keymap)
            else:
                raw_fmt = decrypt_xor_stream(path, tmp, is_vpr=(ext == 'vpr'))
            if target_fmt != 'auto' and target_fmt != raw_fmt:
                final = transcode(tmp, os.path.join(out_dir, base + '.' + target_fmt), target_fmt)
                os.remove(tmp)
                return (path, 'ok', target_fmt)
            final = os.path.join(out_dir, base + '.' + raw_fmt)
            os.replace(tmp, final)
            return (path, 'ok', raw_fmt)
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            return (path, 'fail', '%s: %s' % (type(e).__name__, e))

    done, ok_count, fail_count = 0, 0, 0
    if len(jobs) > 2 and (procs or 1) > 1:
        from multiprocessing import Pool
        with Pool(procs) as pool:
            for path, status, info in pool.imap_unordered(run_one, jobs):
                done += 1
                ok_count += status == 'ok'
                fail_count += status == 'fail'
                if progress_cb:
                    progress_cb(done, len(jobs), path, status, info)
    else:
        for job in jobs:
            path, status, info = run_one(job)
            done += 1
            ok_count += status == 'ok'
            fail_count += status == 'fail'
            if progress_cb:
                progress_cb(done, len(jobs), path, status, info)
    return ok_count, fail_count


# ---------------------------------------------------------------------------
# Part 9: command-line entry point
# ---------------------------------------------------------------------------
def main(argv=None):
    if os.name == 'nt':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    # Integrity self-verification: refuse to run when files were modified
    # (tamper protection, see kugou_integrity.py)
    ok, problems = integrity.verify()
    if not ok:
        print(integrity.fail_text(problems))
        return 2

    ap = argparse.ArgumentParser(
        prog='kugou_unlock',
        description='Unlock KuGou encrypted audio (.kgm/.kgma/.vpr/.kgg -> FLAC/MP3). Personal use only.')
    ap.add_argument('src', help='encrypted file, or a folder containing encrypted files')
    ap.add_argument('dst', help='output directory')
    ap.add_argument('--fmt', default='auto', choices=TARGET_FMTS,
                    help="output format: auto=keep original (default, lossless); flac/mp3/wav need FFmpeg")
    ap.add_argument('--db', default=None, help='path to KGMusicV3.db (default: auto-discover)')
    ap.add_argument('--keyfile', default=None, help='path to a kgg.key text file')
    ap.add_argument('--procs', type=int, default=None, help='parallel workers (default: min(8, cpu count))')
    ap.add_argument('--only', default=None, help='only process these extensions, e.g. kgm,kgg')
    ap.add_argument('--version', action='version',
                    version='KuGou Unlocker v' + __version__ + ' by shushuu | Personal use only - no commercial use')
    args = ap.parse_args(argv)

    only = set(e.strip().lower() for e in args.only.split(',')) if args.only else None
    if args.fmt != 'auto' and not check_ffmpeg():
        ap.error('output format %s requires FFmpeg (keep-original "auto" works without it)' % args.fmt)

    print(integrity.banner(__version__))
    print('-' * 60)

    def progress(done, total, path, status, info):
        mark = 'OK ' if status == 'ok' else 'FAIL'
        print('[%d/%d] %s %s (%s)' % (done, total, mark, os.path.basename(path), info))

    try:
        ok, fail = batch_convert(args.src, args.dst, target_fmt=args.fmt,
                                 procs=args.procs, db_path=args.db,
                                 keyfile=args.keyfile, progress_cb=progress)
    except RuntimeError as e:
        print('error: %s' % e, file=sys.stderr)
        return 1
    print('done: %d succeeded, %d failed -> %s' % (ok, fail, os.path.abspath(args.dst)))
    return 0 if fail == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
