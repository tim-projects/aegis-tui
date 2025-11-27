import hmac
import hashlib
import time
import base64
import binascii
from typing import Union, Protocol
import math

import pyotp

# Define the OTP interface
class OTP(Protocol):
    def code(self) -> Union[int, str]:
        ...

    def digits(self) -> int:
        ...

    def string(self) -> str:
        ...

# Helper to map algorithm names to hashlib functions
def _get_hash_algo(algo: str):
    algo = algo.upper()
    if algo == "SHA1":
        return hashlib.sha1
    elif algo == "SHA256":
        return hashlib.sha256
    elif algo == "SHA512":
        return hashlib.sha512
    elif algo == "MD5":
        return hashlib.md5
    else:
        raise ValueError(f"Unsupported algorithm: {algo}")

def get_hash(secret: bytes, algo: str, counter: int) -> bytes:
    hash_algo = _get_hash_algo(algo)
    h = hmac.new(secret, bytearray(), hash_algo)
    h.update(counter.to_bytes(8, 'big'))
    return h.digest()

def get_digest(algo: str, to_digest: bytes) -> bytes:
    hash_algo = _get_hash_algo(algo)
    h = hash_algo()
    h.update(to_digest)
    return h.digest()


class PyTOTP(pyotp.TOTP, OTP):
    def __init__(self, secret: str, digits: int, period: int, algo: str):
        super().__init__(secret, digits=digits, interval=period, digest=_get_hash_algo(algo))
        self._digits = digits # Store digits for consistency with Go interface

    def code(self) -> int:
        return int(self.at(time.time()))

    def digits(self) -> int:
        return self._digits

    def string(self) -> str:
        return self.at(time.time())


class PyHOTP(pyotp.HOTP, OTP):
    def __init__(self, secret: str, digits: int, counter: int, algo: str):
        super().__init__(secret, digits=digits, digest=_get_hash_algo(algo))
        self._digits = digits
        self._counter = counter # Store counter for consistency with Go interface

    def code(self) -> int:
        return int(self.at(self._counter))

    def digits(self) -> int:
        return self._digits

    def string(self) -> str:
        return self.at(self._counter)


class SteamOTP(OTP):
    STEAM_ALPHA = "23456789BCDFGHJKMNPQRTVWXY"

    def __init__(self, secret_b32_str: str, algo: str, digits: int, period: int, seconds: int = None):
        self._seconds = seconds if seconds is not None else int(time.time())
        self._totp_secret_bytes = base64.b32decode(secret_b32_str.encode('utf-8'), casefold=True)
        self._numeric_code = self._generate_numeric_code()

    def _generate_numeric_code(self) -> int:
        counter = int(math.floor(self._seconds / self._period))
        secret_hash = get_hash(self._totp_secret_bytes, self._algo, counter)

        offset = secret_hash[len(secret_hash) - 1] & 0xf
        otp = (
            ((secret_hash[offset] & 0x7f) << 24) |
            ((secret_hash[offset + 1] & 0xff) << 16) |
            ((secret_hash[offset + 2] & 0xff) << 8) |
            (secret_hash[offset + 3] & 0xff)
        )
        return otp

    def code(self) -> int:
        return self._numeric_code

    def digits(self) -> int:
        return self._digits

    def string(self) -> str:
        steam_alphabet = list(self.STEAM_ALPHA)
        alphabet_len = len(steam_alphabet)
        
        code = self._numeric_code
        builder = []

        for _ in range(self._digits):
            char = steam_alphabet[code % alphabet_len]
            builder.append(char)
            code //= alphabet_len
        
        return "".join(builder)


class MOTP(OTP):
    def __init__(self, secret: bytes, algo: str, digits: int, period: int, pin: str, seconds: int = None):
        self._secret = secret
        self._algo = algo
        self._digits = digits
        self._period = period
        self._pin = pin
        self._seconds = seconds if seconds is not None else int(time.time())
        self._code_str = self._generate_code_str()

    def _generate_code_str(self) -> str:
        time_counter = self._seconds // self._period
        secret_str = binascii.hexlify(self._secret).decode('utf-8')
        to_digest = str(time_counter) + secret_str + self._pin

        digest = get_digest(self._algo, to_digest.encode('utf-8'))
        code = binascii.hexlify(digest).decode('utf-8')
        return code

    def code(self) -> str:
        return self._code_str

    def digits(self) -> int:
        return self._digits

    def string(self) -> str:
        return self._code_str[0:self._digits]


def generate_totp(secret: str, algo: str, digits: int, period: int) -> PyTOTP:
    return PyTOTP(secret, digits, period, algo)

def generate_hotp(secret: str, algo: str, digits: int, counter: int) -> PyHOTP:
    # Note: The original Go HOTP was a placeholder. This uses pyotp's actual HOTP.
    return PyHOTP(secret, digits, counter, algo)

def generate_steam_otp(secret: str, algo: str, digits: int, period: int, seconds: int = None) -> SteamOTP:
    return SteamOTP(secret, algo, digits, period, seconds)

def generate_motp(secret: bytes, algo: str, digits: int, period: int, pin: str, seconds: int = None) -> MOTP:
    return MOTP(secret, algo, digits, period, pin, seconds)
