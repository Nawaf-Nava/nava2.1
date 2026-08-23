# encrypt.py

import config
import hashlib
import os
import random

# --- الإعداد المسبق للخرائط لزيادة الكفاءة ---
CHAR_INFO_MAP = {}
for group_id in range(1, len(config.CHAR_GROUPS) + 1):
    for char, base_code in config.lists[group_id].items():
        CHAR_INFO_MAP[char] = {'group': group_id, 'code': base_code}

def get_key_sequence(secret_key, salt):
    """يولد تسلسل أرقام معقد من كلمة السر والملح."""
    if not secret_key:
        secret_key = "default"
    key_bytes = secret_key.encode('utf-8')
    # استخدام PBKDF2 لتقوية المفتاح
    dk = hashlib.pbkdf2_hmac('sha256', key_bytes, salt, 100000, dklen=128)
    return list(dk)

def encrypt_message(message, secret_key, mode='text', progress_callback=None):
    """يشفر الرسالة ويضيف فايضًا عشوائيًا لزيادة الغموض. يتجاهل الأحرف غير المدعومة."""
    if not message:
        return ""

    salt = os.urandom(16) # ملح عشوائي لكل عملية تشفير
    key_sequence = get_key_sequence(secret_key, salt)
    key_len = len(key_sequence)

    encrypted_chars = []
    supported_char_index = 0
    for char in message:
        if char not in CHAR_INFO_MAP:
            continue # تجاهل الحرف غير المدعوم

        info = CHAR_INFO_MAP[char]
        base_code = info['code']

        # تحديد "المستوى" (0-3) باستخدام المفتاح وموضع الحرف
        key_val = key_sequence[supported_char_index % key_len]
        level = (key_val + supported_char_index) % 4

        new_code = base_code + (level * 100)
        encrypted_chars.append(config.number_to_symbols(new_code))
        supported_char_index += 1

        if progress_callback:
            progress_callback()

    # --- إضافة الفايض العشوائي (Junk Data) ---
    num_real_words = len(encrypted_chars)
    output_words = []
    prng_seed = hashlib.sha256(bytes(key_sequence)).digest()
    rng = random.Random(prng_seed)
    junk_chance = 0.15 + (rng.random() * 0.2)
    max_junk_words = 1 + rng.randint(0, 2)
    max_junk_len = 2 + rng.randint(0, 2)

    for real_word in encrypted_chars:
        output_words.append(real_word)
        if rng.random() < junk_chance:
            num_junk_to_add = rng.randint(1, max_junk_words)
            for _ in range(num_junk_to_add):
                junk_len = rng.randint(1, max_junk_len)
                junk_word = "".join(rng.choices(config.JUNK_SYMBOLS, k=junk_len))
                output_words.append(junk_word)
    body = " ".join(output_words)

    # --- إنشاء الترويسة المشفرة (N4) ---
    # الترويسة تحتوي على الإصدار، الملح، عدد الكلمات الحقيقية، ووضع التشفير
    # هذا يخفي البيانات الوصفية ويجعل الإخراج بأكمله رموزًا غامضة
    header_string = f"N4:{salt.hex()}:{num_real_words}:{mode}"
    # تحويل الترويسة إلى رقم بطريقة أكثر موثوقية عبر Hex
    header_hex = header_string.encode('utf-8').hex()
    header_int = int(header_hex, 16)
    encoded_header = config.number_to_symbols(header_int)

    return f"{encoded_header} {body}"

def encrypt_file_stream(input_generator, output_handle, secret_key, mode, num_real_words, progress_callback=None):
    """Encrypts a stream of characters and writes to an output stream to handle large files."""
    salt = os.urandom(16)
    key_sequence = get_key_sequence(secret_key, salt)
    key_len = len(key_sequence)

    # 1. Create and write header
    header_string = f"N4:{salt.hex()}:{num_real_words}:{mode}"
    # تحويل الترويسة إلى رقم بطريقة أكثر موثوقية عبر Hex
    header_hex = header_string.encode('utf-8').hex()
    header_int = int(header_hex, 16)
    encoded_header = config.number_to_symbols(header_int)
    output_handle.write(encoded_header)
    output_handle.write(" ")

    # 2. Setup RNG for junk data - This must be identical to decrypt logic
    prng_seed = hashlib.sha256(bytes(key_sequence)).digest()
    rng = random.Random(prng_seed)
    junk_chance = 0.15 + (rng.random() * 0.2)
    max_junk_words = 1 + rng.randint(0, 2)
    max_junk_len = 2 + rng.randint(0, 2)

    # 3. Encrypt and write body word by word, adding junk
    supported_char_index = 0
    first_word = True
    for char in input_generator:
        if char not in CHAR_INFO_MAP:
            continue

        # Encrypt the real character
        info = CHAR_INFO_MAP[char]
        base_code = info['code']
        key_val = key_sequence[supported_char_index % key_len]
        level = (key_val + supported_char_index) % 4
        new_code = base_code + (level * 100)
        encrypted_word = config.number_to_symbols(new_code)
        
        if not first_word:
            output_handle.write(" ")
        output_handle.write(encrypted_word)
        first_word = False
        
        supported_char_index += 1
        if progress_callback:
            progress_callback()

        # Add junk words after the real word
        if rng.random() < junk_chance:
            num_junk_to_add = rng.randint(1, max_junk_words)
            for _ in range(num_junk_to_add):
                junk_len = rng.randint(1, max_junk_len)
                junk_word = "".join(rng.choices(config.JUNK_SYMBOLS, k=junk_len))
                output_handle.write(" ")
                output_handle.write(junk_word)