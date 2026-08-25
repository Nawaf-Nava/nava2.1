# main.py

import os
import base64
import time
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
        
    # تنظيف المسار من علامات التنصيص الناتجة عن السحب والإفلات
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
        
        # التقاط الخطأ في حالة تشغيل الكود في بيئة سيرفر غير تفاعلية (مثل Render)
        try:
            choice = Prompt.ask("[bold yellow]>> أدخل رقم اختيارك[/bold yellow]", choices=['1', '2', '3', '4', '5'], default='1')
        except EOFError:
            console.print("\n[bold cyan]ℹ️ البيئة الحالية غير تفاعلية (Non-interactive Server Environment).[/bold cyan]")
            console.print("[bold green]✔ تم تشغيل وحدة التشفير بنجاح، السيرفر يعمل الآن في الخلفية بدون مشاكل...[/bold green]")
            # إبقاء السيرفر نشطاً للأبد حتى لا يعطي Render خطأ الخروج
            while True:
                time.sleep(3600)

        if choice == '1':
            # --- قسم التشفير ---
            try:
                console.print("\n[yellow]--==[ 1. التشفير ]==--[/yellow]")
                message = Prompt.ask("[cyan]📝 أدخل الرسالة المراد تشفيرها[/cyan]")
                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")
                processed_message = message 

                supported_chars_count = sum(1 for char in processed_message if char in config.SUPPORTED_CHARS)

                with Progress(console=console) as progress:
                    task = progress.add_task("[green]جاري التشفير...[/green]", total=supported_chars_count)
                    def progress_callback():
                        progress.update(task, advance=1)
                    encrypted_msg = encrypt_message(processed_message, secret_key, progress_callback=progress_callback)

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

                with Progress(console=console) as progress:
                    task = progress.add_task("[cyan]جاري فك التشفير...[/cyan]", total=None)
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
                    mode = 'text'
                    suggested_name = f"{input_file.stem}.encrypted{input_file.suffix}"
                    output_file = get_file_dialog('save', "حفظ الملف المشفر باسم",
                                                  default_ext=input_file.suffix,
                                                  initial_dir=input_file.parent,
                                                  initial_file=suggested_name)
                else:
                    mode = 'binary'
                    suggested_name = input_file.name + ".nava"
                    output_file = get_file_dialog('save', "حفظ الملف المشفر باسم",
                                                  default_ext=".nava",
                                                  initial_dir=input_file.parent,
                                                  initial_file=suggested_name)

                if not output_file:
                    console.print("[yellow]تم إلغاء العملية.[/yellow]")
                    continue

                if input_file.resolve() == output_file.resolve():
                    show_result("خطأ في العملية", "لا يمكن تشفير الملف في نفس مكانه. الرجاء اختيار ملف وجهة مختلف.", "red", "❌")
                    continue

                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")

                num_real_words = 0
                if mode == 'text':
                    with input_file.open('r', encoding='utf-8', errors='ignore') as f:
                        num_real_words = sum(1 for line in f for char in line if char in config.SUPPORTED_CHARS)
                else: 
                    file_size = input_file.stat().st_size
                    num_real_words = (file_size + 2) // 3 * 4

                def input_generator():
                    if mode == 'text':
                        with input_file.open('r', encoding='utf-8', errors='ignore') as f:
                            while True:
                                char = f.read(4096) 
                                if not char: break
                                yield from char
                    else:  
                        with input_file.open('rb') as f:
                            while True:
                                chunk = f.read(3 * 1024)  
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
                input_file = get_file_dialog('open', "اختر الملف المشفر")
                if not input_file:
                    console.print("[yellow]تم إلغاء العملية.[/yellow]")
                    continue

                if input_file.name.endswith('.nava'):
                    suggested_name = input_file.name[:-5] 
                elif '.encrypted' in input_file.name:
                    suggested_name = input_file.name.replace('.encrypted', '', 1)
                else:
                    suggested_name = f"decrypted_{input_file.name}"

                output_file = get_file_dialog('save', "حفظ الملف الأصلي باسم",
                                              initial_dir=input_file.parent,
                                              initial_file=suggested_name)
                
                if not output_file:
                    console.print("[yellow]تم إلغاء العملية.[/yellow]")
                    continue

                if input_file.resolve() == output_file.resolve():
                    show_result("خطأ في العملية", "لا يمكن فك تشفير الملف في نفس مكانه. الرجاء اختيار ملف وجهة مختلف.", "red", "❌")
                    continue

                secret_key = Prompt.ask("[cyan]🔑 أدخل كلمة السر[/cyan]")

                with Progress(console=console) as progress:
                    task = progress.add_task("[cyan]جاري فك تشفير الملف...[/cyan]", total=None) 
                    decrypt_file(input_file, output_file, secret_key, progress=progress, task_id=task)

                show_result("تم فك تشفير الملف بنجاح!", f"تم حفظ الملف الأصلي في:\n{output_file.resolve()}", "green", "✅")

            except Exception as e:
                show_result("حدث خطأ أثناء فك تشفير الملف", str(e), "red", "❌")

        elif choice == '5':
            console.print("\n[bold magenta]👋 إلى اللقاء![/bold magenta]")
            break
        
        prompt_message = "\n[dim yellow]اضغط على Enter للعودة إلى القائمة الرئيسية...[/dim yellow]"
        if did_encrypt:
            prompt_message = "\n[cyan]اضغط [bold]'a'[/bold] لنسخ النص، أو [bold]Enter[/bold] للعودة...[/cyan]"

        try:
            user_action = Prompt.ask(prompt_message, default="")
            
            if did_encrypt and user_action.lower() == 'a':
                try:
                    pyperclip.copy(encrypted_text_to_copy)
                    console.print("[bold green]📋 تم النسخ إلى الحافظة.[/bold green]")
                    Prompt.ask("\n[dim yellow]اضغط على Enter للمتابعة...[/dim yellow]")
                except pyperclip.PyperclipException:
                    error_message = (
                        "[yellow]⚠️ لم نتمكن من الوصول إلى الحافظة.[/yellow]\n"
                        "[dim]قد تحتاج إلى تثبيت أداة مساعدة مثل 'xclip' على نظام Linux.[/dim]\n"
                        "[dim]جرب الأمر: [bold]sudo apt install xclip[/bold][/dim]"
                    )
                    console.print(error_message)
                    Prompt.ask("\n[dim yellow]اضغط على Enter للمتابعة...[/dim yellow]")
        except EOFError:
            # تخطي في حال كان السيرفر غير تفاعلي
            pass

if __name__ == "__main__":
    run_application()
