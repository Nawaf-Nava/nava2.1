# decrypt.py

import base64
import config
import hashlib
import random

# --- الإعداد المسبق للخرائط لزيادة الكفاءة ---
CODE_INFO_MAP = {}
for group_id in range(1, len(config.CHAR_GROUPS) + 1):
    for char, base_code in config.lists[group_id].items():
        CODE_INFO_MAP[base_code] = char

def get_key_sequence(secret_key, salt):
    """يولد تسلسل أرقام معقد من كلمة السر والملح."""
    if not secret_key:
        secret_key = "default"
    key_bytes = secret_key.encode('utf-8')
    dk = hashlib.pbkdf2_hmac('sha256', key_bytes, salt, 100000, dklen=128)
    return list(dk)

def _remove_junk_words(all_words_iterator, num_real_words, key_sequence):
    """
    A generator that filters out junk words from an iterator.
    It yields only the real encrypted words.
    """
    prng_seed = hashlib.sha256(bytes(key_sequence)).digest()
    rng = random.Random(prng_seed)

    junk_chance = 0.15 + (rng.random() * 0.2)
    max_junk_words = 1 + rng.randint(0, 2)
    max_junk_len = 2 + rng.randint(0, 2)

    words_processed = 0
    while words_processed < num_real_words:
        try:
            yield next(all_words_iterator)
            words_processed += 1
            if rng.random() < junk_chance:
                num_junk_to_add = rng.randint(1, max_junk_words)
                for _ in range(num_junk_to_add):
                    junk_len = rng.randint(1, max_junk_len)
                    _ = rng.choices(config.JUNK_SYMBOLS, k=junk_len)
                    next(all_words_iterator)
        except StopIteration:
            raise ValueError("Word mismatch: file is truncated or password is wrong.")

def decrypt_message(encrypted_message, secret_key, progress=None, task_id=None, progress_callback=None):
    """يفك تشفير الرسالة، ويعيد المحتوى المفكوك ووضع التشفير (text/binary)."""
    if not encrypted_message:
        return "", "text"

    encrypted_message = encrypted_message.strip()
    mode = 'text' # قيمة افتراضية للتوافق مع الإصدارات الأقدم

    try:
        # --- فحص صيغة التشفير ---
        if encrypted_message.startswith(('N2:', 'N3:')):
            # --- التعامل مع الصيغ القديمة (N2, N3) ---
            parts = encrypted_message.split(':', 3)
            version = parts[0]
            salt_hex = parts[1]
            salt = bytes.fromhex(salt_hex)

            if version == 'N2':
                body = parts[2]
                num_real_words = -1  # علامة للإشارة إلى عدم وجود فايض
            else:  # N3
                num_real_words = int(parts[2])
                body = parts[3]
        else:
            # --- التعامل مع الصيغة الجديدة (N4) ذات الترويسة المشفرة ---
            encoded_header, body = encrypted_message.split(' ', 1)

            header_int = config.symbols_to_number(encoded_header)
            # إعادة بناء الترويسة من الرقم بطريقة موثوقة عبر Hex
            header_hex = hex(header_int)[2:]
            if len(header_hex) % 2 != 0:
                header_hex = '0' + header_hex
            header_bytes = bytes.fromhex(header_hex)
            header_string = header_bytes.decode('utf-8')

            header_parts = header_string.split(':')
            version = header_parts[0]
            if version != 'N4':
                raise ValueError("ترويسة الشفرة غير معروفة أو تالفة.")

            salt_hex = header_parts[1]
            salt = bytes.fromhex(salt_hex)
            num_real_words = int(header_parts[2])
            # استخراج وضع التشفير إذا كان موجودًا
            if len(header_parts) > 3:
                mode = header_parts[3]

            # تحديث شريط التقدم بالعدد الفعلي للكلمات
            if progress and task_id is not None:
                progress.update(task_id, total=num_real_words)

    except (ValueError, IndexError, UnicodeDecodeError):
        # خطأ عام يغطي فشل التقسيم، التحويل من hex، فك التشفير، الخ.
        # غالبًا ما يكون السبب هو كلمة سر خاطئة تؤدي إلى فك تشفير خاطئ للترويسة.
        raise ValueError("الشفرة غير صالحة أو تالفة، أو كلمة السر غير صحيحة.")

    key_sequence = get_key_sequence(secret_key, salt)
    key_len = len(key_sequence)

    all_words_iterator = iter(body.split(' '))

    if num_real_words != -1:  # Covers N3 and N4
        real_words_gen = _remove_junk_words(all_words_iterator, num_real_words, key_sequence)
    else:  # For N2 (no junk)
        real_words_gen = all_words_iterator

    decrypted_chars = []
    for i, enc_char in enumerate(real_words_gen):
        if not enc_char: continue

        code = config.symbols_to_number(enc_char)

        key_val = key_sequence[i % key_len]
        level = (key_val + i) % 4
        base_code = code - (level * 100)

        original_char = CODE_INFO_MAP.get(base_code)
        if original_char is None:
            raise ValueError("Decryption failed. Wrong password or corrupted data.")

        decrypted_chars.append(original_char)

        # تحديث شريط التقدم
        if progress and task_id is not None:
            progress.update(task_id, advance=1)
        elif progress_callback:
            progress_callback()

    return "".join(decrypted_chars), mode

def decrypt_file(input_path, output_path, secret_key, progress=None, task_id=None):
    """Decrypts a file using streaming to handle large files, writing the output directly."""
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f_in:
        # 1. Read and process header from the stream
        header_buffer = ""
        while True:
            char = f_in.read(1)
            if not char or char == ' ':
                break
            header_buffer += char
        
        encoded_header = header_buffer
        
        try:
            # For now, we only support the streaming-capable N4 format for files.
            if encoded_header.startswith(('N2:', 'N3:')):
                raise ValueError("Legacy formats N2/N3 are not supported for large file decryption.")
            
            header_int = config.symbols_to_number(encoded_header)
            # إعادة بناء الترويسة من الرقم بطريقة موثوقة عبر Hex
            header_hex = hex(header_int)[2:]
            if len(header_hex) % 2 != 0:
                header_hex = '0' + header_hex
            header_bytes = bytes.fromhex(header_hex)
            header_string = header_bytes.decode('utf-8')

            header_parts = header_string.split(':')
            if header_parts[0] != 'N4':
                raise ValueError("Unsupported header format for file decryption.")

            salt_hex = header_parts[1]
            salt = bytes.fromhex(salt_hex)
            num_real_words = int(header_parts[2])
            mode = header_parts[3] if len(header_parts) > 3 else 'text'

            if progress and task_id is not None:
                progress.update(task_id, total=num_real_words)
        except (ValueError, IndexError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid code, corrupted header, or wrong password. Error: {e}")

        key_sequence = get_key_sequence(secret_key, salt)
        key_len = len(key_sequence)

        def word_generator(file_handle):
            """A more efficient word generator that reads in chunks."""
            buffer = ""
            while True:
                chunk = file_handle.read(8192)
                if not chunk:
                    break
                buffer += chunk
                # The last part might be incomplete, so we keep it in the buffer
                *parts, buffer = buffer.split(' ')
                for part in parts:
                    # Filter out empty strings that result from multiple spaces
                    if part:
                        yield part

            if buffer:
                yield buffer

        output_mode = 'wb' if mode == 'binary' else 'w'
        output_encoding = None if mode == 'binary' else 'utf-8'
        with open(output_path, output_mode, encoding=output_encoding) as f_out:
            all_words_gen = word_generator(f_in)
            real_words_gen = _remove_junk_words(all_words_gen, num_real_words, key_sequence)
            
            base64_buffer = ""
            for i, enc_char_word in enumerate(real_words_gen):
                if not enc_char_word: continue
                code = config.symbols_to_number(enc_char_word)
                key_val = key_sequence[i % key_len]
                level = (key_val + i) % 4
                base_code = code - (level * 100)
                original_char = CODE_INFO_MAP.get(base_code)
                if original_char is None:
                    raise ValueError("Decryption failed. Wrong password or corrupted data.")

                if mode == 'binary':
                    base64_buffer += original_char
                    if len(base64_buffer) >= 4096:
                        to_decode = base64_buffer[:len(base64_buffer) - (len(base64_buffer) % 4)]
                        base64_buffer = base64_buffer[len(to_decode):]
                        f_out.write(base64.b64decode(to_decode))
                else:
                    f_out.write(original_char)
                
                if progress and task_id is not None:
                    progress.update(task_id, advance=1)

            if mode == 'binary' and base64_buffer:
                f_out.write(base64.b64decode(base64_buffer))