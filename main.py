from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil
from pathlib import Path

import config
from encrypt import encrypt_message, encrypt_file_stream
from decrypt import decrypt_message, decrypt_file

app = FastAPI(title="Nava Dark Cryptography Web", version="2.0")

# تخصيص مجلد الملفات الثابتة للواجهة
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_html=True)
def read_index():
    return FileResponse("static/index.html")

@app.post("/api/encrypt-text")
def api_encrypt_text(message: str = Form(...), secret_key: str = Form(...)):
    try:
        encrypted_msg = encrypt_message(message, secret_key)
        return {"status": "success", "result": encrypted_msg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/decrypt-text")
def api_decrypt_text(encrypted_message: str = Form(...), secret_key: str = Form(...)):
    try:
        decrypted_msg, mode = decrypt_message(encrypted_message, secret_key)
        return {"status": "success", "result": decrypted_msg, "mode": mode}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/encrypt-file")
async def api_encrypt_file(file: UploadFile = File(...), secret_key: str = Form(...)):
    try:
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        input_path = temp_dir / file.filename
        output_path = temp_dir / f"{file.filename}.nava"

        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # حساب عدد الكلمات وطريقة المعالجة
        mode = 'binary'
        file_size = input_path.stat().st_size
        num_real_words = (file_size + 2) // 3 * 4

        def input_generator():
            import base64
            with open(input_path, "rb") as f:
                while True:
                    chunk = f.read(3 * 1024)
                    if not chunk: break
                    yield from base64.b64encode(chunk).decode('ascii')

        with open(output_path, "w", encoding='utf-8') as f_out:
            encrypt_file_stream(input_generator(), f_out, secret_key, mode, num_real_words)

        # تنظيف ملف الإدخال المؤقت
        input_path.unlink(missing_ok=True)
        return FileResponse(output_path, filename=output_path.name, media_type='application/octet-stream')
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))