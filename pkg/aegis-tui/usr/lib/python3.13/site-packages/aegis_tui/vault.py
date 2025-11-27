import json
import base64
import binascii
from dataclasses import dataclass, field, is_dataclass
from typing import List, Optional, Union, get_origin, get_args

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

@dataclass
class Params:
    nonce: str
    tag: str

@dataclass
class Slot:
    type: int
    uuid: str
    key: str
    key_params: Params = field(metadata={"field_name": "key_params"})
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
    algo: str
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
    icon: str
    icon_mime: Optional[str] = field(default=None, metadata={"field_name": "icon_mime"})
    icon_hash: Optional[str] = field(default=None, metadata={"field_name": "icon_hash"})
    favorite: bool = False
    info: Optional[Info] = None
    groups: List[str] = field(default_factory=list)

@dataclass
class Group:
    uuid: str
    name: str

@dataclass
class Db:
    version: int
    entries: List[Entry]
    groups: List[Group]

@dataclass
class Vault:
    version: int
    header: Header
    db: Db

@dataclass
class VaultEncrypted:
    version: int
    header: Header
    db: str

    def find_master_key(self, pwd: str) -> bytes:
        master_key = b""
        for slot in self.header.slots:
            if slot.type != 1:  # Only consider password-based slots
                continue

            try:
                salt = binascii.unhexlify(slot.salt)
                
                # Scrypt key derivation
                kdf = Scrypt(
                    salt=salt,
                    length=32,  # 32 bytes for AES-256 key
                    n=slot.n,
                    r=slot.r,
                    p=slot.p,
                    backend=default_backend()
                )
                key = kdf.derive(pwd.encode('utf-8'))

                nonce = binascii.unhexlify(slot.key_params.nonce)
                tag = binascii.unhexlify(slot.key_params.tag)
                slot_key_encrypted = binascii.unhexlify(slot.key)

                # AES-GCM decryption
                cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
                decryptor = cipher.decryptor()
                
                master_key = decryptor.update(slot_key_encrypted) + decryptor.finalize()
                
                # If decryption is successful, master_key will not be empty
                if master_key:
                    break
            except Exception as e:
                # print(f"Error decrypting slot: {e}") # For debugging
                continue
        
        if not master_key:
            raise ValueError("No master key found or unable to decrypt with provided password.")
        return master_key

    def decrypt_contents(self, master_key: bytes) -> bytes:
        db_encrypted_b64 = self.db
        params = self.header.params

        nonce = binascii.unhexlify(params.nonce)
        tag = binascii.unhexlify(params.tag)
        db_data_encrypted = base64.b64decode(db_encrypted_b64)

        cipher = Cipher(algorithms.AES(master_key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        
        content = decryptor.update(db_data_encrypted) + decryptor.finalize()
        
        return content

    def decrypt_vault(self, master_key: bytes) -> Vault:
        content = self.decrypt_contents(master_key)
        
        db_data = json.loads(content.decode('utf-8'))
        db = Db(
            version=db_data['version'],
            entries=[from_dict(Entry, e) for e in db_data['entries']],
            groups=[from_dict(Group, g) for g in db_data['groups']]
        )
        return Vault(
            version=self.version,
            header=self.header,
            db=db
        )

# Helper to deserialize JSON into dataclasses
def from_dict(cls, data):
    if isinstance(data, list):
        return [from_dict(cls, item) for item in data]
    if not isinstance(data, dict):
        return data
    
    # Handle field_name metadata for fields that differ from JSON keys
    field_names = {f.metadata.get("field_name", f.name): f.name for f in cls.__dataclass_fields__.values()}
    
    init_args = {}
    for json_key, field_name in field_names.items():
        if json_key in data:
            field_type = cls.__dataclass_fields__[field_name].type
            origin = get_origin(field_type)
            args = get_args(field_type)

            if origin is list:
                # Handle List types
                item_type = args[0]
                init_args[field_name] = [from_dict(item_type, item) for item in data[json_key]]
            elif origin is Union and type(None) in args:
                # Handle Optional types (e.g., Optional[Info])
                # Extract the non-None type from the Union
                non_none_args = [arg for arg in args if arg is not type(None)]
                if non_none_args and is_dataclass(non_none_args[0]):
                    item_type = non_none_args[0]
                    init_args[field_name] = from_dict(item_type, data[json_key])
                else:
                    init_args[field_name] = data[json_key] # Fallback for Optional non-dataclass types
            elif is_dataclass(field_type):
                # Handle non-Optional nested dataclasses
                init_args[field_name] = from_dict(field_type, data[json_key])
            else:
                init_args[field_name] = data[json_key]
    return cls(**init_args)

# Custom deserialization for VaultEncrypted to handle nested dataclasses
def deserialize_vault_encrypted(data: dict) -> VaultEncrypted:
    header_data = data['header']
    header_params = Params(nonce=header_data['params']['nonce'], tag=header_data['params']['tag'])
    
    slots = []
    for s_data in header_data['slots']:
        slot_key_params = Params(nonce=s_data['key_params']['nonce'], tag=s_data['key_params']['tag'])
        slot = Slot(
            type=s_data['type'],
            uuid=s_data['uuid'],
            key=s_data['key'],
            key_params=slot_key_params,
            n=s_data['n'],
            r=s_data['r'],
            p=s_data['p'],
            salt=s_data['salt'],
            repaired=s_data['repaired'],
            is_backup=s_data['is_backup']
        )
        slots.append(slot)
    
    header = Header(slots=slots, params=header_params)
    
    return VaultEncrypted(
        version=data['version'],
        header=header,
        db=data['db']
    )

# Custom deserialization for Vault to handle nested dataclasses
def deserialize_vault(data: dict) -> Vault:
    header_data = data['header']
    header_params = Params(nonce=header_data['params']['nonce'], tag=header_data['params']['tag'])
    
    slots = []
    for s_data in header_data['slots']:
        slot_key_params = Params(nonce=s_data['key_params']['nonce'], tag=s_data['key_params']['tag'])
        slot = Slot(
            type=s_data['type'],
            uuid=s_data['uuid'],
            key=s_data['key'],
            key_params=slot_key_params,
            n=s_data['n'],
            r=s_data['r'],
            p=s_data['p'],
            salt=s_data['salt'],
            repaired=s_data['repaired'],
            is_backup=s_data['is_backup']
        )
        slots.append(slot)
    
    header = Header(slots=slots, params=header_params)

    db_data = data['db']
    entries = [from_dict(Entry, e) for e in db_data['entries']]
    groups = [from_dict(Group, g) for g in db_data['groups']]
    db = Db(version=db_data['version'], entries=entries, groups=groups)
    
    return Vault(
        version=data['version'],
        header=header,
        db=db
    )
