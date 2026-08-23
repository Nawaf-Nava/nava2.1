# utils.py
import hashlib
import os

def derive_key_from_password(password: str, salt: bytes, iterations: int = 100000) -> int:
    """
    يشتق مفتاحًا رقميًا من كلمة مرور وملح باستخدام PBKDF2-HMAC-SHA256.
    هذه الطريقة أكثر أمانًا ضد هجمات القوة الغاشمة.
    """
    password_bytes = password.encode('utf-8')
    # dklen=32 means we get a 256-bit key
    key_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt, iterations, dklen=32)
    return int.from_bytes(key_bytes, 'big')