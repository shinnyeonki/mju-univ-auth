"""
암호화 유틸리티
===============
RSA/AES 하이브리드 암호화 구현 (명지대 SSO 호환)

JavaScript 원본 (bandiJS):
- genKey(length): 세션키 생성 + PBKDF2로 AES 키 파생
- encryptJavaPKI(data): RSA로 암호화
- encryptBase64AES(data, keyInfo): AES로 암호화
"""

import base64
import os
from typing import Dict

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


def generate_session_key(length: int = 32) -> Dict[str, any]:
    """
    세션키 생성 (JavaScript bandiJS.genKey 대응)
    
    Returns:
        dict: { 'keyStr': str, 'key': bytes, 'iv': bytes }
    """
    # 64바이트 랜덤 데이터를 Base64로 인코딩
    random_bytes = os.urandom(64)
    key_str = base64.b64encode(random_bytes).decode('utf-8')
    
    # salt = keyStr의 마지막 16자
    salt = key_str[-16:]
    
    # PBKDF2로 키 파생 (iterations=1024, dkLen=length)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),  # forge.pkcs5.pbkdf2 기본값은 SHA1
        length=length,
        salt=salt.encode('utf-8'),
        iterations=1024,
        backend=default_backend()
    )
    key_bytes = kdf.derive(key_str.encode('utf-8'))
    
    # IV = 키의 마지막 16바이트
    iv_bytes = key_bytes[-16:]
    
    return {
        'keyStr': key_str,
        'key': key_bytes,
        'iv': iv_bytes
    }


def encrypt_with_rsa(data: str, public_key_str: str) -> str:
    """
    RSA-PKCS1-v1.5로 데이터 암호화 (JavaScript bandiJS.encryptJavaPKI 대응)
    
    Args:
        data: 암호화할 데이터 (예: "keyStr,타임스탬프")
        public_key_str: Base64로 인코딩된 RSA 공개키
    
    Returns:
        Base64로 인코딩된 암호문
    """
    # PEM 형식으로 변환
    pem_key = f"-----BEGIN PUBLIC KEY-----\n{public_key_str}\n-----END PUBLIC KEY-----"
    
    # RSA 키 로드
    rsa_key = serialization.load_pem_public_key(
        pem_key.encode('utf-8'),
        backend=default_backend()
    )
    
    # PKCS1_v1_5 암호화 (Java 호환)
    encrypted = rsa_key.encrypt(
        data.encode('utf-8'),
        padding.PKCS1v15()
    )
    
    return base64.b64encode(encrypted).decode('utf-8')


def encrypt_with_aes(plain_text: str, key_info: Dict[str, any]) -> str:
    """
    AES-256-CBC로 데이터 암호화 (JavaScript bandiJS.encryptBase64AES 대응)
    
    Args:
        plain_text: 암호화할 평문
        key_info: generate_session_key()에서 반환된 키 정보 dict
    
    Returns:
        Base64로 인코딩된 암호문
    """
    key_bytes = key_info['key']
    iv_bytes = key_info['iv']
    
    # 평문을 먼저 Base64 인코딩 (JS와 동일)
    input_data = base64.b64encode(plain_text.encode('utf-8'))
    
    # PKCS7 패딩 적용
    block_size = 16  # AES block size
    padding_len = block_size - (len(input_data) % block_size)
    padded = input_data + bytes([padding_len] * padding_len)
    
    # AES-CBC 암호화
    cipher = Cipher(
        algorithms.AES(key_bytes),
        modes.CBC(iv_bytes),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    
    return base64.b64encode(encrypted).decode('utf-8')
