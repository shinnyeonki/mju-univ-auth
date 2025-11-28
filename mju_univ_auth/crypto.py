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

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from .utils import Colors, log_info


def generate_session_key(length: int = 32) -> dict:
    """
    세션키 생성 (JavaScript bandiJS.genKey 대응)
    
    JavaScript 원본:
    ```javascript
    genKey: function(length) {
        var keyStr = forge.util.encode64(forge.random.getBytesSync(64));
        var salt = keyStr.substring(keyStr.length - 16);
        var keyBytes = forge.pkcs5.pbkdf2(keyStr, salt, 1024, length);
        var ivBytes = keyBytes.slice(keyBytes.length - 16);
        return { length, key: keyBytes, iv: ivBytes, keyStr };
    }
    ```
    
    Returns:
        dict: { 'keyStr': str, 'key': bytes, 'iv': bytes }
    """
    # 64바이트 랜덤 데이터를 Base64로 인코딩 (JS: forge.util.encode64(forge.random.getBytesSync(64)))
    # os.urandom이 random.getrandbits보다 빠르고 안전함
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


def encrypt_with_rsa(data: str, public_key_str: str, verbose: bool = False) -> str:
    """
    RSA-PKCS1-v1.5로 데이터 암호화 (JavaScript bandiJS.encryptJavaPKI 대응)
    
    Args:
        data: 암호화할 데이터 (예: "keyStr,타임스탬프")
        public_key_str: Base64로 인코딩된 RSA 공개키
        verbose: 상세 로그 출력 여부
    
    Returns:
        Base64로 인코딩된 암호문
    """
    if verbose:
        print(f"\n{Colors.CYAN}    [RSA 암호화 과정]{Colors.END}")
        log_info("Input Data", f"{data[:30]}..." if len(data) > 30 else data, 6)
    
    # PEM 형식으로 변환
    pem_key = f"-----BEGIN PUBLIC KEY-----\n{public_key_str}\n-----END PUBLIC KEY-----"
    
    # RSA 키 로드 (cryptography)
    rsa_key = serialization.load_pem_public_key(pem_key.encode('utf-8'), backend=default_backend())
    
    if verbose:
        log_info("RSA Key Size", f"{rsa_key.key_size} bits", 6)
    
    # PKCS1_v1_5 암호화 (Java 호환)
    encrypted = rsa_key.encrypt(
        data.encode('utf-8'),
        padding.PKCS1v15()
    )
    result = base64.b64encode(encrypted).decode('utf-8')
    
    if verbose:
        log_info("Encrypted (RSA)", f"{result[:30]}...({len(result)} chars)", 6)
    
    return result


def encrypt_with_aes(plain_text: str, key_info: dict, verbose: bool = False) -> str:
    """
    AES-256-CBC로 데이터 암호화 (JavaScript bandiJS.encryptBase64AES 대응)
    
    JavaScript 원본:
    ```javascript
    encryptBase64AES: function(value, keyInfo, isEncodeUri, isUtf8) {
        var encValue = value;
        // ASCII 문자인 경우
        var enc64Value = forge.util.encode64(encValue);  // Base64 인코딩
        var cipher = forge.cipher.createCipher('AES-CBC', keyInfo.key);
        cipher.start({iv: keyInfo.iv});
        cipher.update(forge.util.createBuffer(enc64Value));
        cipher.finish();
        return forge.util.encode64(cipher.output.bytes());
    }
    ```
    
    Args:
        plain_text: 암호화할 평문
        key_info: generate_session_key()에서 반환된 키 정보 dict
        verbose: 상세 로그 출력 여부
    
    Returns:
        Base64로 인코딩된 암호문
    """
    if verbose:
        print(f"\n{Colors.CYAN}    [AES 암호화 과정]{Colors.END}")
    
    key_bytes = key_info['key']
    iv_bytes = key_info['iv']
    
    if verbose:
        log_info("AES Key", f"PBKDF2 derived ({len(key_bytes)} bytes)", 6)
        log_info("IV", f"last 16 bytes of key ({len(iv_bytes)} bytes)", 6)
    
    # 평문을 먼저 Base64 인코딩 (JS와 동일)
    input_data = base64.b64encode(plain_text.encode('utf-8'))
    
    if verbose:
        log_info("Pre-encoded (Base64)", f"{input_data[:20]}...", 6)
    
    # PKCS7 패딩 적용
    block_size = 16  # AES block size
    padding_len = block_size - (len(input_data) % block_size)
    padded = input_data + bytes([padding_len] * padding_len)
    
    # AES-CBC 암호화 (cryptography)
    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    
    result = base64.b64encode(encrypted).decode('utf-8')
    
    if verbose:
        log_info("Encrypted (AES)", f"{result[:30]}...({len(result)} chars)", 6)
    
    return result
