"""Decrypt Chromium cookies on Windows via DPAPI + BCrypt AES-GCM and inject into QtWebEngine."""

import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time

import win32crypt
from PyQt6.QtCore import QDateTime, QUrl
from PyQt6.QtNetwork import QNetworkCookie

bcrypt = ctypes.windll.bcrypt


class BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO(ctypes.Structure):
    """Windows CNG structure for AES-GCM authenticated decryption."""

    _fields_ = [
        ("cbSize", wintypes.ULONG),
        ("dwInfoVersion", wintypes.ULONG),
        ("pbNonce", ctypes.c_void_p),
        ("cbNonce", wintypes.ULONG),
        ("pbAuthData", ctypes.c_void_p),
        ("cbAuthData", wintypes.ULONG),
        ("pbTag", ctypes.c_void_p),
        ("cbTag", wintypes.ULONG),
        ("pbMacContext", ctypes.c_void_p),
        ("cbMacContext", wintypes.ULONG),
        ("cbAAD", wintypes.ULONG),
        ("cbData", ctypes.c_ulonglong),
        ("dwFlags", wintypes.ULONG),
    ]


def decrypt_aes_gcm(key, iv, ciphertext, tag):
    """Decrypt AES-GCM payload using Windows CNG BCrypt."""
    h_alg = wintypes.HANDLE()
    status = bcrypt.BCryptOpenAlgorithmProvider(
        ctypes.byref(h_alg), ctypes.c_wchar_p("AES"), None, 0
    )
    if status != 0:
        return None

    chain_mode = ctypes.create_unicode_buffer("ChainingModeGCM")
    status = bcrypt.BCryptSetProperty(
        h_alg, ctypes.c_wchar_p("ChainingMode"), chain_mode, len(chain_mode) * 2, 0
    )
    if status != 0:
        bcrypt.BCryptCloseAlgorithmProvider(h_alg, 0)
        return None

    h_key = wintypes.HANDLE()
    status = bcrypt.BCryptGenerateSymmetricKey(
        h_alg, ctypes.byref(h_key), None, 0, key, len(key), 0
    )
    if status != 0:
        bcrypt.BCryptCloseAlgorithmProvider(h_alg, 0)
        return None

    auth_info = BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO()
    auth_info.cbSize = ctypes.sizeof(auth_info)
    auth_info.dwInfoVersion = 1
    auth_info.pbNonce = ctypes.cast(ctypes.c_char_p(iv), ctypes.c_void_p)
    auth_info.cbNonce = len(iv)
    auth_info.pbTag = ctypes.cast(ctypes.c_char_p(tag), ctypes.c_void_p)
    auth_info.cbTag = len(tag)

    out_len = wintypes.ULONG()
    status = bcrypt.BCryptDecrypt(
        h_key, ciphertext, len(ciphertext), ctypes.byref(auth_info),
        None, 0, None, 0, ctypes.byref(out_len), 0,
    )
    if status != 0:
        bcrypt.BCryptDestroyKey(h_key)
        bcrypt.BCryptCloseAlgorithmProvider(h_alg, 0)
        return None

    out_buf = ctypes.create_string_buffer(out_len.value)
    status = bcrypt.BCryptDecrypt(
        h_key, ciphertext, len(ciphertext), ctypes.byref(auth_info),
        None, 0, out_buf, len(out_buf), ctypes.byref(out_len), 0,
    )
    bcrypt.BCryptDestroyKey(h_key)
    bcrypt.BCryptCloseAlgorithmProvider(h_alg, 0)
    if status != 0:
        return None
    return out_buf.raw[:out_len.value]


def _read_master_key(local_state_path):
    """Extract and DPAPI-decrypt the Chromium AES master key from Local State."""
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    enc_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    return win32crypt.CryptUnprotectData(enc_key[5:], None, None, None, 0)[1]


def extract_and_inject_cookies(login_dir, profile):
    """Copy cookies from a standalone browser profile into a QWebEngineProfile."""
    local_state_path = os.path.join(login_dir, "Local State")
    cookie_db_path = os.path.join(login_dir, "Default", "Network", "Cookies")
    if not os.path.exists(cookie_db_path):
        cookie_db_path = os.path.join(login_dir, "Network", "Cookies")
    if not os.path.exists(local_state_path) or not os.path.exists(cookie_db_path):
        return 0

    try:
        aes_key = _read_master_key(local_state_path)
    except Exception as e:
        print(f"Error reading master key: {e}")
        return 0

    cookie_store = profile.cookieStore()
    count = 0
    tmp_db = os.path.join(tempfile.gettempdir(), f"hub_cookies_{int(time.time() * 1000)}.db")
    try:
        shutil.copy2(cookie_db_path, tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT host_key, name, path, encrypted_value, expires_utc, is_secure, is_httponly "
            "FROM cookies"
        )
        for host, name, path, enc_val, expires_utc, is_secure, is_httponly in cursor.fetchall():
            if not enc_val or enc_val[:3] not in (b"v10", b"v20"):
                continue

            dec = decrypt_aes_gcm(aes_key, enc_val[3:15], enc_val[15:-16], enc_val[-16:])
            if dec is None:
                continue

            # Chromium 130+ prepends a 32-byte SHA-256 hash of host_key before the cookie value
            if len(dec) >= 32 and dec[:32] == hashlib.sha256(host.encode("utf-8")).digest():
                dec = dec[32:]

            try:
                cookie_val = dec.decode("utf-8")
            except UnicodeDecodeError:
                cookie_val = dec.decode("latin1")
            if not cookie_val:
                continue

            qcookie = QNetworkCookie()
            qcookie.setName(name.encode("utf-8"))
            qcookie.setValue(cookie_val.encode("utf-8"))
            qcookie.setDomain(host)
            qcookie.setPath(path if path else "/")
            qcookie.setSecure(bool(is_secure))
            qcookie.setHttpOnly(bool(is_httponly))

            if expires_utc and expires_utc > 0:
                unix_epoch_delta = 11644473600
                secs = (expires_utc / 1000000) - unix_epoch_delta
                if secs > 0:
                    qcookie.setExpirationDate(QDateTime.fromSecsSinceEpoch(int(secs)))

            clean_host = host.lstrip(".")
            origin = QUrl(f"https://{clean_host}{path}")
            cookie_store.setCookie(qcookie, origin)
            count += 1
        conn.close()
    except Exception as e:
        print(f"Error reading cookies: {e}")
    finally:
        if os.path.exists(tmp_db):
            try:
                os.remove(tmp_db)
            except OSError:
                pass
    return count
