# main.py

import os
import base64
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
import tkinter as tk
from tkinter import filedialog

console = Console()

TEXT_EXTENSIONS = [
    '.txt', '.html', '.css', '.js', '.xml', '.json', '.md', 
    '.py', '.c', '.cpp', '.h', '.log', '.ini', '.cfg', '.rtf'
]

def clear_screen():
    """يمسح الشاشة لتجربة أنظف."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_file_dialog(dialog_type: str, title: str, default_ext: str = "", file_types: list = None, initial_dir: Path = None, initial_file: str = ""):
    """يفتح نافذة اختيار/حفظ ملف رسومية."""
    root = tk.Tk()
    root.withdraw()  # إخفاء النافذة الرئيسية لـ tkinter
    root.attributes('-topmost', True) # إظهار النافذة في المقدمة
    
    # استخدم المجلد المبدئي المحدد أو مجلد المستخدم الرئيسي كخيار افتراضي
    start_dir = initial_dir or Path.home()

    if dialog_type == 'open':
        path = filedialog.askopenfilename(title=title, filetypes=file_types or [], initialdir=start_dir)
    else: # save
        path = filedialog.asksaveasfilename(title=title, defaultextension=default_ext, filetypes=file_types or [], initialdir=start_dir, initialfile=initial_file)
    root.destroy()
    return Path(path) if path else None

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
    # Create a Text object from the content.
    renderable = Text.from_markup(f"[b]{content}[/b]")
    # Set the no_wrap property if needed. This is compatible with older versions.
    if no_wrap:
        renderable.no_wrap = True
    console.print(Panel(renderable, title=f"{emoji} {title}", border_style=style, padding=(1, 2)))

def run_application():
    """الدالة الرئيسية لتشغيل التطبيق وحلقة الأوامر."""
    while True:
        did_encrypt = False
        encrypted_text_to_copy = ""

        main_menu()
        choice = Prompt.ask("[bold yellow]>> أدخل رقم اختيارك[/bold yellow]", choices=['1', '2', '3', '4', '5'], default='1')

        if choice == '1':
            # --- قسم التشفير ---
            try:
                console.print("\n[yellow]--==[ 1. التشفير ]==--[/yellow]")
                message = Prompt.ask("[cyan]📝 أدخل الرسالة المراد تشفيرها[/cyan]")
                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")
                processed_message = message # استخدام الرسالة مباشرة لدعم الأحرف الصغيرة والكبيرة

                # حساب عدد الأحرف المدعومة فقط لشريط التقدم
                supported_chars_count = sum(1 for char in processed_message if char in config.SUPPORTED_CHARS)

                with Progress(console=console) as progress:
                    task = progress.add_task("[green]جاري التشفير...[/green]", total=supported_chars_count)
                    def progress_callback():
                        progress.update(task, advance=1)
                    encrypted_msg = encrypt_message(processed_message, secret_key, progress_callback=progress_callback)

                # عرض النص المشفر مع السماح بتقسيمه على عدة أسطر لسهولة القراءة
                show_result("تم تحويل الرسالة إلى تعويذة بنجاح!", encrypted_msg, "green", "✅")

                did_encrypt = True
                encrypted_text_to_copy = encrypted_msg

            except Exception as e:
                show_result("حدث خطأ أثناء التشفير", str(e), "red", "❌")

        elif choice == '2':
            # --- قسم فك التشفير ---
            try:
                console.print("\n[yellow]--==[ 2. فك التشفير ]==--[/yellow]")
                encrypted_msg = Prompt.ask("[cyan]📝 الصق الشفرة هنا[/cyan]")
                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر لكسر التعويذة[/cyan]")

                # بما أن عدد الخطوات الحقيقي (الكلمات) غير معروف إلا بعد فك تشفير الترويسة،
                # سنجعل شريط التقدم غير محدد في البداية، وسيتم تحديثه من دالة فك التشفير.
                with Progress(console=console) as progress:
                    task = progress.add_task("[cyan]جاري فك التشفير...[/cyan]", total=None)
                    # نمرر كائن شريط التقدم والمهمة مباشرة للدالة
                    decrypted_msg, _ = decrypt_message(encrypted_msg, secret_key, progress=progress, task_id=task)

                show_result("تم فك التشفير واستخراج النص بنجاح!", decrypted_msg, "green", "✅")
            except ValueError as e:
                show_result("فشل فك التشفير", str(e), "red", "❌")
            except Exception as e:
                show_result("خطأ غير متوقع", f"حدث خطأ: {e}\nتأكد من أن الشفرة وكلمة السر صحيحتان.", "red", "❌")

        elif choice == '3': # تشفير ملف
            try:
                console.print("\n[yellow]--==[ 3. تشفير ملف ]==--[/yellow]")
                input_file = get_file_dialog('open', "اختر الملف المراد تشفيره")
                if not input_file:
                    console.print("[yellow]تم إلغاء العملية.[/yellow]")
                    continue

                is_text_file = input_file.suffix.lower() in TEXT_EXTENSIONS

                if is_text_file:
                    # التعامل مع الملفات النصية: تشفير المحتوى فقط بنفس الامتداد
                    mode = 'text'
                    suggested_name = f"{input_file.stem}.encrypted{input_file.suffix}"
                    output_file = get_file_dialog('save', "حفظ الملف المشفر باسم",
                                                  default_ext=input_file.suffix,
                                                  file_types=[(f"Encrypted {input_file.suffix.upper()} file", f"*{input_file.suffix}"), ("All files", "*.*")],
                                                  initial_dir=input_file.parent,
                                                  initial_file=suggested_name)
                else:
                    # التعامل مع الملفات الثنائية: تشفير الملف بالكامل بامتداد .nava
                    mode = 'binary'
                    suggested_name = input_file.name + ".nava"
                    output_file = get_file_dialog('save', "حفظ الملف المشفر باسم",
                                                  default_ext=".nava",
                                                  file_types=[("Nava Encrypted File", "*.nava"), ("All files", "*.*")],
                                                  initial_dir=input_file.parent,
                                                  initial_file=suggested_name)

                if not output_file:
                    console.print("[yellow]تم إلغاء العملية.[/yellow]")
                    continue

                if input_file.resolve() == output_file.resolve():
                    show_result("خطأ في العملية", "لا يمكن تشفير الملف في نفس مكانه. الرجاء اختيار ملف وجهة مختلف.", "red", "❌")
                    continue

                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")

                # --- Pass 1: Count characters for progress bar and header ---
                num_real_words = 0
                if mode == 'text':
                    # This is still not perfectly efficient for huge text files, but avoids loading all content.
                    with input_file.open('r', encoding='utf-8', errors='ignore') as f:
                        num_real_words = sum(1 for line in f for char in line if char in config.SUPPORTED_CHARS)
                else:  # binary
                    # For binary, all base64 chars are supported. Length can be calculated from file size.
                    file_size = input_file.stat().st_size
                    num_real_words = (file_size + 2) // 3 * 4

                # --- Pass 2: Create generator and encrypt stream ---
                def input_generator():
                    if mode == 'text':
                        with input_file.open('r', encoding='utf-8', errors='ignore') as f:
                            while True:
                                char = f.read(4096) # Read in chunks
                                if not char: break
                                yield from char
                    else:  # binary
                        with input_file.open('rb') as f:
                            while True:
                                chunk = f.read(3 * 1024)  # Read in chunks of 3k bytes for efficient base64 encoding
                                if not chunk: break
                                yield from base64.b64encode(chunk).decode('ascii')

                with Progress(console=console) as progress:
                    task = progress.add_task("[green]جاري تشفير الملف...[/green]", total=num_real_words)
                    def progress_callback():
                        progress.update(task, advance=1)
                    
                    with output_file.open('w', encoding='utf-8') as f_out:
                        encrypt_file_stream(input_generator(), f_out, secret_key, mode, num_real_words, progress_callback)

                show_result("تم تشفير الملف بنجاح!", f"تم حفظ الملف المشفر في:\n{output_file.resolve()}", "green", "✅")

            except Exception as e:
                show_result("حدث خطأ أثناء تشفير الملف", str(e), "red", "❌")

        elif choice == '4': # فك تشفير ملف
            try:
                console.print("\n[yellow]--==[ 4. فك تشفير ملف ]==--[/yellow]")
                input_file = get_file_dialog('open', "اختر الملف المشفر", file_types=[("All files", "*.*")])
                if not input_file:
                    console.print("[yellow]تم إلغاء العملية.[/yellow]")
                    continue

                # اقتراح اسم ملف الإخراج بناءً على اسم ملف الإدخال
                if input_file.name.endswith('.nava'):
                    suggested_name = input_file.name[:-5] # إزالة .nava
                elif '.encrypted' in input_file.name:
                    suggested_name = input_file.name.replace('.encrypted', '', 1)
                else:
                    suggested_name = f"decrypted_{input_file.name}"

                output_file = get_file_dialog('save', "حفظ الملف الأصلي باسم",
                                              initial_dir=input_file.parent,
                                              initial_file=suggested_name,
                                              file_types=[("All files", "*.*")])
                if not output_file:
                    console.print("[yellow]تم إلغاء العملية.[/yellow]")
                    continue

                if input_file.resolve() == output_file.resolve():
                    show_result("خطأ في العملية", "لا يمكن فك تشفير الملف في نفس مكانه. الرجاء اختيار ملف وجهة مختلف.", "red", "❌")
                    continue

                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")

                with Progress(console=console) as progress:
                    task = progress.add_task("[cyan]جاري فك تشفير الملف...[/cyan]", total=None) # Total will be set inside
                    decrypt_file(input_file, output_file, secret_key, progress=progress, task_id=task)

                show_result("تم فك تشفير الملف بنجاح!", f"تم حفظ الملف الأصلي في:\n{output_file.resolve()}", "green", "✅")

            except Exception as e:
                show_result("حدث خطأ أثناء فك تشفير الملف", str(e), "red", "❌")

        elif choice == '5':
            console.print("\n[bold magenta]👋 إلى اللقاء![/bold magenta]")
            break
        
        # انتظار المستخدم قبل العودة للقائمة الرئيسية
        prompt_message = "\n[dim yellow]اضغط على Enter للعودة إلى القائمة الرئيسية...[/dim yellow]"
        if did_encrypt:
            prompt_message = "\n[cyan]اضغط [bold]'a'[/bold] لنسخ النص، أو [bold]Enter[/bold] للعودة...[/cyan]"

        user_action = Prompt.ask(prompt_message, default="")

        if did_encrypt and user_action.lower() == 'a':
            try:
                pyperclip.copy(encrypted_text_to_copy)
                console.print("[bold green]📋 تم النسخ إلى الحافظة.[/bold green]")
                # انتظر المستخدم ليقرأ الرسالة قبل مسح الشاشة
                Prompt.ask("\n[dim yellow]اضغط على Enter للمتابعة...[/dim yellow]")
            except pyperclip.PyperclipException:
                error_message = (
                    "[yellow]⚠️ لم نتمكن من الوصول إلى الحافظة.[/yellow]\n"
                    "[dim]قد تحتاج إلى تثبيت أداة مساعدة مثل 'xclip' على نظام Linux.[/dim]\n"
                    "[dim]جرب الأمر: [bold]sudo apt install xclip[/bold][/dim]"
                )
                console.print(error_message)
                Prompt.ask("\n[dim yellow]اضغط على Enter للمتابعة...[/dim yellow]")

if __name__ == "__main__":
    run_application()
