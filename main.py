# main.py

import os
import base64
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import config
from encrypt import encrypt_message, encrypt_file_stream
from decrypt import decrypt_message, decrypt_file
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
import pyperclip
from rich.progress import Progress
from rich.text import Text
from pathlib import Path

# --- سيرفر وهمي لإرضاء فحص Render للمنافذ (Port Binding) مجاناً ---
class FreePortHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Nava Encryption Server is Running OK")

    def log_message(self, format, *args):
        pass

def start_free_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), FreePortHandler)
    server.serve_forever()

# تشغيل السيرفر في الخلفية فور تشغيل الملف
threading.Thread(target=start_free_server, daemon=True).start()
# -------------------------------------------------------------------

console = Console()

TEXT_EXTENSIONS = [
    '.txt', '.html', '.css', '.js', '.xml', '.json', '.md', 
    '.py', '.c', '.cpp', '.h', '.log', '.ini', '.cfg', '.rtf'
]

def clear_screen():
    """يمسح الشاشة لتجربة أنظف."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_file_dialog(dialog_type: str, title: str, default_ext: str = "", file_types: list = None, initial_dir: Path = None, initial_file: str = ""):
    """يطلب مسار الملف عبر الترمنل بدلاً من النافذة الرسومية ليعمل بدون أخطاء في السيرفرات."""
    start_dir = initial_dir or Path.cwd()
    
    console.print(f"\n[bold yellow]-- {title} --[/bold yellow]")
    
    try:
        if dialog_type == 'open':
            path_str = Prompt.ask("[cyan]📂 أدخل مسار الملف (يمكنك سحب وإفلات الملف في الترمنل)[/cyan]")
        else: # save
            suggested_path = start_dir / (initial_file if initial_file else f"output{default_ext}")
            path_str = Prompt.ask("[cyan]💾 أدخل مسار حفظ الملف (أو اضغط Enter للمسار الافتراضي)[/cyan]", default=str(suggested_path))
    except EOFError:
        return None
        
    if not path_str:
        return None
        
    path_str = path_str.strip('\'"& ') 
    path = Path(path_str)
    
    if dialog_type == 'open' and not path.is_file():
        console.print("[bold red]❌ خطأ: الملف غير موجود أو المسار غير صحيح![/bold red]")
        return None
        
    return path

def main_menu():
    """يعرض القائمة الرئيسية للتطبيق."""
    clear_screen()
    menu_text = """
[bold]اختر العملية التي تريد تنفيذها:[/bold]

[bold magenta]1.[/bold magenta] [cyan]تشفير رسالة[/cyan]
[bold magenta]2.[/bold magenta] [cyan]فك تشفير رسالة[/cyan] (قراءة الطلاسم)
[bold magenta]3.[/bold magenta] [green]تشفير ملف[/green]
[bold magenta]4.[/bold magenta] [green]فك تشفير ملف[/green]
[bold magenta]5.[/bold magenta] [red]الخروج[/red] من البرنامج
"""
    console.print(Panel(menu_text, title="[bold yellow]👁️‍🗨️ نظام التشفير المظلم 👁️‍🗨️[/bold yellow]", border_style="green", expand=False))

def show_result(title, content, style, emoji, no_wrap=False):
    """يعرض نتيجة العملية داخل لوحة منسقة."""
    renderable = Text.from_markup(f"[b]{content}[/b]")
    if no_wrap:
        renderable.no_wrap = True
    console.print(Panel(renderable, title=f"{emoji} {title}", border_style=style, padding=(1, 2)))

def run_application():
    """الدالة الرئيسية لتشغيل التطبيق وحلقة الأوامر."""
    while True:
        did_encrypt = False
        encrypted_text_to_copy = ""

        main_menu()
        
        try:
            choice = Prompt.ask("[bold yellow]>> أدخل رقم اختيارك[/bold yellow]", choices=['1', '2', '3', '4', '5'], default='1')
        except EOFError:
            console.print("\n[bold cyan]ℹ️ البيئة الحالية غير تفاعلية (Non-interactive Server Environment).[/bold cyan]")
            console.print("[bold green]✔ تم تشغيل وحدة التشفير والسيرفر الوهمي بنجاح، الخدمة تعمل الآن في الخلفية بدون مشاكل...[/bold green]")
            while True:
                time.sleep(3600)

        if choice == '1':
            # --- 1. تشفير رسالة ---
            try:
                console.print("\n[yellow]--==[ 1. التشفير ]==--[/yellow]")
                message = Prompt.ask("[cyan]📝 أدخل الرسالة المراد تشفيرها[/cyan]")
                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")
                
                supported_chars_count = sum(1 for char in message if char in config.SUPPORTED_CHARS)

                with Progress(console=console) as progress:
                    task = progress.add_task("[green]جاري التشفير...[/green]", total=supported_chars_count)
                    def progress_callback():
                        progress.update(task, advance=1)
                    encrypted_msg = encrypt_message(message, secret_key, progress_callback=progress_callback)
                
                show_result("الرسالة المشفرة (الطلاسم)", encrypted_msg, "green", "🔐", no_wrap=True)
                did_encrypt = True
                encrypted_text_to_copy = encrypted_msg
            except Exception as e:
                console.print(f"[bold red]❌ حدث خطأ أثناء التشفير: {e}[/bold red]")

        elif choice == '2':
            # --- 2. فك تشفير رسالة ---
            try:
                console.print("\n[yellow]--==[ 2. فك التشفير ]==--[/yellow]")
                encrypted_msg = Prompt.ask("[cyan]🔮 أدخل النص المشفر (الطلاسم)[/cyan]")
                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")

                with Progress(console=console) as progress:
                    task = progress.add_task("[cyan]جاري فك التشفير...[/cyan]", total=None)
                    def progress_callback():
                        progress.update(task, advance=1)
                    decrypted_msg, mode = decrypt_message(encrypted_msg, secret_key, progress_callback=progress_callback)

                show_result("الرسالة بعد فك التشفير", decrypted_msg, "cyan", "🔓")
            except Exception as e:
                console.print(f"[bold red]❌ خطأ: {e}[/bold red]")

        elif choice == '3':
            # --- 3. تشفير ملف ---
            try:
                console.print("\n[yellow]--==[ 3. تشفير ملف ]==--[/yellow]")
                input_path = get_file_dialog('open', 'اختر الملف المراد تشفيره')
                if not input_path: continue

                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")
                
                is_text = input_path.suffix.lower() in TEXT_EXTENSIONS
                mode = 'text' if is_text else 'binary'

                output_path = get_file_dialog('save', 'اختر مسار حفظ الملف المشفر', default_ext=".enc", initial_file=input_path.name + ".enc")
                if not output_path: continue

                with open(input_path, 'rb') as f_in_raw:
                    content_bytes = f_in_raw.read()

                if mode == 'binary':
                    file_data_str = base64.b64encode(content_bytes).decode('utf-8')
                else:
                    file_data_str = content_bytes.decode('utf-8', errors='ignore')

                num_real_words = sum(1 for char in file_data_str if char in config.CHAR_GROUPS.get(1, {}) or any(char in g for g in config.CHAR_GROUPS.values()))

                with Progress(console=console) as progress:
                    task = progress.add_task("[green]جاري تشفير الملف...[/green]", total=num_real_words)
                    def file_progress():
                        progress.update(task, advance=1)
                    
                    with open(output_path, 'w', encoding='utf-8') as f_out:
                        encrypt_file_stream(iter(file_data_str), f_out, secret_key, mode, num_real_words, progress_callback=file_progress)

                console.print(f"[bold green]✔ تم تشفير الملف بنجاح وحفظه في: {output_path}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]❌ خطأ أثناء تشفير الملف: {e}[/bold red]")

        elif choice == '4':
            # --- 4. فك تشفير ملف ---
            try:
                console.print("\n[yellow]--==[ 4. فك تشفير ملف ]==--[/yellow]")
                input_path = get_file_dialog('open', 'اختر الملف المشفر لفك تشفيره')
                if not input_path: continue

                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")
                output_path = get_file_dialog('save', 'اختر مسار حفظ الملف المفكوك', initial_file="decrypted_output")
                if not output_path: continue

                with Progress(console=console) as progress:
                    task = progress.add_task("[cyan]جاري فك تشفير الملف...[/cyan]", total=0)
                    decrypt_file(str(input_path), str(output_path), secret_key, progress=progress, task_id=task)

                console.print(f"[bold green]✔ تم فك تشفير الملف بنجاح وحفظه في: {output_path}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]❌ خطأ أثناء فك تشفير الملف: {e}[/bold red]")

        elif choice == '5':
            console.print("[bold yellow]إلى اللقاء![/bold yellow]")
            break

        if did_encrypt and encrypted_text_to_copy:
            try:
                pyperclip.copy(encrypted_text_to_copy)
                console.print("[dim green]📋 تم نسخ النص المشفر إلى الحافظة تلقائياً![/dim green]")
            except Exception:
                pass

        Prompt.ask("\n[bold dim]اضغط Enter للمتابعة والعودة للقائمة الرئيسية...[/bold dim]")

if __name__ == "__main__":
    run_application()
