import argparse
import json
import os
import uuid
import random
import base64
import binascii
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Cryptography imports
try:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import hashes, hmac
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("Error: 'cryptography' library not found. Please install it using 'pip install cryptography'.")
    exit(1)


# --- Dataclasses from vault.py (copied for self-containment) ---
@dataclass
class Params:
    nonce: str
    tag: str

@dataclass
class Slot:
    type: int
    uuid: str
    key: str
    key_params: Params
    n: int
    r: int
    p: int
    salt: str
    repaired: bool
    is_backup: bool = field(metadata={"field_name": "is_backup"})

@dataclass
class Header:
    slots: List[Slot]
    params: Params

@dataclass
class Info:
    secret: str
    algo: str # Changed to str
    digits: int
    period: Optional[int] = None
    counter: Optional[int] = None
    pin: Optional[str] = None

@dataclass
class Entry:
    type: str
    uuid: str
    name: str
    issuer: str
    note: str
    icon: str = "" # Default to empty string
    icon_mime: Optional[str] = field(default=None, metadata={"field_name": "icon_mime"})
    icon_hash: Optional[str] = field(default=None, metadata={"field_name": "icon_hash"})
    favorite: bool = False
    info: Optional[Info] = None
    groups: List[str] = field(default_factory=list)

@dataclass
class Group:
    uuid: str
    name: str
    note: str = "" # Added default empty string

@dataclass
class Db:
    version: int
    entries: List[Entry]
    groups: List[Group]

@dataclass
class Vault: # Added Vault dataclass
    version: int
    header: Header
    db: Db

@dataclass
class VaultEncrypted:
    version: int # Added version field
    header: Header
    db: str

# --- End of dataclasses from vault.py ---

# --- Helper functions for random data generation ---
def generate_random_uuid() -> str:
    return str(uuid.uuid4())

def generate_random_base32_secret(length: int = 16) -> str:
    # Generates a random byte string and then encodes it to base32
    random_bytes = os.urandom(length)
    return base64.b32encode(random_bytes).decode('utf-8').rstrip('=')

def generate_random_string(length: int = 10) -> str:
    import random
    import string
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))
# --- End of helper functions ---

# --- Functions to construct dataclasses ---
def create_random_info() -> Info:
    return Info(
        secret=generate_random_base32_secret(),
        algo="SHA1", # SHA1
        digits=6,
        period=30,
        counter=0
    )

def create_random_group() -> Group:
    return Group(
        uuid=generate_random_uuid(),
        name=generate_random_string(8),
        note=generate_random_string(20)
    )

def create_random_entry(groups_uuids: List[str]) -> Entry:
    return Entry(
        type="totp", # Added 'type' field
        uuid=generate_random_uuid(),
        name=generate_random_string(12),
        issuer=generate_random_string(10),
        note=generate_random_string(25),
        info=create_random_info(),
        groups=[random.choice(groups_uuids)] if groups_uuids else []
    )
# --- End of dataclass construction functions ---

# --- Encryption Logic ---
def encrypt_vault(db_object: Db, password: str) -> VaultEncrypted:
    # Define Scrypt and AES-GCM parameters based on Aegis's vault.py
    KDF_SALT_LENGTH = 16 # Aegis uses 16 bytes for salt in vault.py find_master_key
    KDF_N = 16384
    KDF_R = 8
    KDF_P = 1
    KEY_LENGTH = 32 # 256-bit key

    # 1. Generate a random master key
    master_key = os.urandom(KEY_LENGTH)

    # 2. Serialize Db to JSON and encode to bytes
    db_json = json.dumps(db_object, default=lambda o: o.__dict__, indent=4).encode('utf-8')

    # 3. Encrypt Db with master key (AES-GCM)
    db_nonce = os.urandom(12) # AES-GCM recommended nonce length
    aesgcm_db = AESGCM(master_key)
    db_cipher_text = aesgcm_db.encrypt(db_nonce, db_json, None) # No associated data
    db_tag = db_cipher_text[-16:] # GCM tag is 16 bytes
    db_cipher = db_cipher_text[:-16]

    # 4. Derive password key (Scrypt)
    kdf_salt = os.urandom(KDF_SALT_LENGTH)
    kdf = Scrypt(
        salt=kdf_salt,
        length=KEY_LENGTH,
        n=KDF_N,
        r=KDF_R,
        p=KDF_P,
        backend=default_backend()
    )
    password_derived_key = kdf.derive(password.encode('utf-8'))

    # 5. Encrypt master key with password key (AES-GCM)
    master_key_nonce = os.urandom(12) # Another random nonce
    aesgcm_master = AESGCM(password_derived_key)
    master_key_cipher_text = aesgcm_master.encrypt(master_key_nonce, master_key, None)
    master_key_tag = master_key_cipher_text[-16:]
    master_key_cipher = master_key_cipher_text[:-16]

    # 6. Construct Header and VaultEncrypted
    # Header.params refers to the DB decryption parameters (db_nonce, db_tag)
    db_params = Params(
        nonce=binascii.hexlify(db_nonce).decode('utf-8'),
        tag=binascii.hexlify(db_tag).decode('utf-8')
    )

    # Slot refers to the master key encryption parameters
    slot_key_params = Params(
        nonce=binascii.hexlify(master_key_nonce).decode('utf-8'),
        tag=binascii.hexlify(master_key_tag).decode('utf-8')
    )

    slot = Slot(
        type=1, # Password-based slot
        uuid=generate_random_uuid(),
        key=binascii.hexlify(master_key_cipher).decode('utf-8'),
        key_params=slot_key_params,
        n=KDF_N,
        r=KDF_R,
        p=KDF_P,
        salt=binascii.hexlify(kdf_salt).decode('utf-8'),
        repaired=False,
        is_backup=False
    )
    
    header = Header(
        slots=[slot],
        params=db_params
    )

    return VaultEncrypted(
        version=2, # VaultEncrypted also needs a version
        db=base64.b64encode(db_cipher).decode('utf-8'), # db_cipher remains base64
        header=header
    )
# --- End of Encryption Logic ---


def main():
    parser = argparse.ArgumentParser(description="Generate a test Aegis vault file.")
    parser.add_argument("output_path", help="Path to save the generated vault file (e.g., test_vault.json).")
    parser.add_argument("-p", "--password", required=True, help="Password for the new vault.")
    parser.add_argument("-n", "--num-entries", type=int, default=25, help="Number of random OTP entries to generate.")

    args = parser.parse_args()

    print(f"Generating a test vault with {args.num_entries} entries at {args.output_path}...")

    # Generate groups
    num_groups = max(1, args.num_entries // 5) # Create at least 1 group, up to num_entries/5
    groups = [create_random_group() for _ in range(num_groups)]
    group_uuids = [g.uuid for g in groups]

    # Generate entries
    entries = [create_random_entry(group_uuids) for _ in range(args.num_entries)]

    # Create Db object
    db = Db(
        version=2, # Added 'version' field
        entries=entries,
        groups=groups
    )

    # Encrypt the vault
    vault_encrypted = encrypt_vault(db, args.password)

    # Serialize and save to file
    with open(args.output_path, 'w') as f:
        json.dump(vault_encrypted, f, default=lambda o: o.__dict__, indent=4)

    print(f"Successfully generated test vault at {args.output_path}")

if __name__ == "__main__":
    main()
