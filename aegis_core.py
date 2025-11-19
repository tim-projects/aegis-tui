import os
import json
import re
import time
import base64
import binascii
from typing import List, Optional, Dict

from vault import Vault, VaultEncrypted, Entry, deserialize_vault, deserialize_vault_encrypted
from otp import OTP, generate_totp, generate_hotp, generate_steam_otp, generate_motp

def_period: int = 30  # The default TOTP refresh interval

def find_vault_path(vault_dir: str) -> Optional[str]:
    vault_path = None
    try:
        files = os.listdir(vault_dir)
    except FileNotFoundError:
        return None
    except Exception:
        return None

    if not files:
        return None

    vault_files = []
    vault_file_re = re.compile(r"^aegis-(backup|export)-\d+(-\d+)*\.json$")
    for f_name in files:
        if vault_file_re.match(f_name):
            full_path = os.path.join(vault_dir, f_name)
            if os.path.isfile(full_path):
                vault_files.append(full_path)
    
    if not vault_files:
        return None

    # Find the most recently modified file
    vault_path = max(vault_files, key=os.path.getmtime)

    return vault_path

def read_vault_file(file_path: str) -> Vault:
    with open(file_path, 'r') as f:
        data = json.load(f)
    return deserialize_vault(data)

def read_vault_file_enc(file_path: str) -> VaultEncrypted:
    with open(file_path, 'r') as f:
        data = json.load(f)
    return deserialize_vault_encrypted(data)

def read_and_decrypt_vault_file(file_path: str, pwd: str) -> Vault:
    vault_data_enc = read_vault_file_enc(file_path)
    master_key = vault_data_enc.find_master_key(pwd)
    vault_data_plain = vault_data_enc.decrypt_vault(master_key)
    return vault_data_plain

def get_otp(entry: Entry) -> OTP:
    if entry.type == "totp":
        return generate_totp(entry.info.secret, entry.info.algo, entry.info.digits, entry.info.period)
    elif entry.type == "hotp":
        # Original Go code had a placeholder for HOTP. Using pyotp's actual HOTP.
        return generate_hotp(entry.info.secret, entry.info.algo, entry.info.digits, entry.info.counter)
    elif entry.type == "steam":
        return generate_steam_otp(entry.info.secret, entry.info.algo, entry.info.digits, entry.info.period)
    elif entry.type == "motp":
        secret_data = binascii.unhexlify(entry.info.secret)
        return generate_motp(secret_data, entry.info.algo, entry.info.digits, entry.info.period, entry.info.pin)
    else:
        raise ValueError(f"Unsupported OTP type {entry.type}")

def get_otps(vault_data: Vault) -> Dict[str, OTP]:
    otps: Dict[str, OTP] = {}
    for entry in vault_data.db.entries:
        try:
            pass_otp = get_otp(entry)
            otps[entry.uuid] = pass_otp
        except Exception as e:
            print(f"Error generating OTP for entry {entry.uuid}: {e}") # Log error, continue with others
            continue
    return otps

def get_ttn() -> int:
    return get_ttn_per(def_period)

def get_ttn_per(period: int) -> int:
    p = period * 1000
    return p - (int(time.time() * 1000) % p)
