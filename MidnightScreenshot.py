import os
import sys
import platform
import time
import pyautogui
import tkinter as tk
import ctypes
from datetime import datetime, timedelta
from PIL import Image, ImageTk

# --- НАСТРОЙКИ ---
TEST_MODE = False  # True = 30 секунд, False = Хардкор (до полуночи)
CONFIG_FILE = "config.txt"
PHOTO_DIR = "PHOTOS"
TEMP_SHOT = "temp_full.png"

def get_dpi_scale():
    """Получить масштаб DPI для Windows"""
    os_name = platform.system()
    if os_name == "Windows":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return 1.0
        except:
            return 1.0
    return 1.0

def check_wayland():
    """Проверить, используется ли Wayland вместо X11 на Linux"""
    if platform.system() == "Linux":
        return os.environ.get("WAYLAND_DISPLAY") is not None
    return False

def register_autostart():
    current_path = os.path.realpath(sys.argv[0])
    os_name = platform.system()
    try:
        if os_name == "Windows":
            os.system(f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "MidnightScreenshot" /t REG_SZ /d "{current_path}" /f')
        elif os_name == "Linux":
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            with open(os.path.join(autostart_dir, "midnight.desktop"), "w") as f:
                f.write(f"[Desktop Entry]\nType=Application\nExec=python3 {current_path}\nName=MidnightScreenshot\nX-GNOME-Autostart-enabled=true")
        elif os_name == "Darwin":  # macOS
            launch_agent_dir = os.path.expanduser("~/Library/LaunchAgents")
            os.makedirs(launch_agent_dir, exist_ok=True)
            plist_path = os.path.join(launch_agent_dir, "com.midnightscreenshot.plist")
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.midnightscreenshot</string>
    <key>ProgramArguments</key>
    <array>
        <string>python3</string>
        <string>{current_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""
            with open(plist_path, "w") as f:
                f.write(plist_content)
    except Exception as e:
        print(f"Ошибка регистрации автозапуска: {e}")

def setup_coordinates():
    """Интерактивное выбор области скриншота"""
    if check_wayland():
        print("⚠️  Обнаружен Wayland! pyautogui может работать нестабильно.")
        print("Рекомендуется переключиться на X11 для лучшей совместимости.")
    
    try:
        pyautogui.screenshot(TEMP_SHOT)
    except Exception as e:
        print(f"Ошибка при получении скриншота: {e}")
        return None
    
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    
    try:
        img = Image.open(TEMP_SHOT)
        photo = ImageTk.PhotoImage(img)
        canvas = tk.Canvas(root, width=img.size[0], height=img.size[1])
        canvas.pack()
        canvas.create_image(0, 0, image=photo, anchor="nw")
        
        label = canvas.create_text(img.size[0]/2, img.size[1]/2, text="Нажмите ЛЕВЫЙ ВЕРХНИЙ угол", font=("Arial", 40), fill="red")
        
        coords = []
        def on_click(event):
            coords.append((event.x_root, event.y_root))
            if len(coords) == 1:
                canvas.itemconfig(label, text="Теперь нажмите ПРАВЫЙ НИЖНИЙ угол")
            else:
                root.destroy()
                
        canvas.bind("<Button-1>", on_click)
        root.mainloop()
        
        if os.path.exists(TEMP_SHOT): 
            os.remove(TEMP_SHOT)
        
        return coords[0], coords[1] if len(coords) == 2 else None
    except Exception as e:
        print(f"Ошибка в setup_coordinates: {e}")
        if os.path.exists(TEMP_SHOT): 
            os.remove(TEMP_SHOT)
        return None

def run():
    if not os.path.exists(PHOTO_DIR): 
        os.makedirs(PHOTO_DIR)
    
    # Конфигурация
    if not os.path.exists(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
        register_autostart()
        coords = setup_coordinates()
        if coords is None:
            print("Ошибка: не удалось получить координаты")
            return
        
        p1, p2 = coords
        with open(CONFIG_FILE, "w") as f:
            f.write(f"{p1[0]},{p1[1]}\n{p2[0]},{p2[1]}")
        print(f"✓ Координаты сохранены: {p1} до {p2}")
    
    # Чтение конфига
    try:
        with open(CONFIG_FILE, "r") as f:
            lines = f.readlines()
            if len(lines) < 2:
                print("Ошибка: некорректный config.txt")
                return
            x1, y1 = map(int, lines[0].strip().split(','))
            x2, y2 = map(int, lines[1].strip().split(','))
    except Exception as e:
        print(f"Ошибка чтения конфига: {e}")
        return

    # Расчет координат для жесткой обрезки
    x_start, x_end = min(x1, x2), max(x1, x2)
    y_start, y_end = min(y1, y2), max(y1, y2)

    # Логика времени
    if TEST_MODE:
        target = datetime.now() + timedelta(seconds=3)
        print(f"🧪 Тестовый режим: скриншот через 3 сек")
    else:
        # Хардкор: точно в 00:00:00
        target = datetime.combine(datetime.now().date() + timedelta(days=1), datetime.min.time())
        print(f"🌙 Режим полночь: скриншот в {target.strftime('%H:%M:%S')}")
    
    wait = (target - datetime.now()).total_seconds()
    if wait > 0:
        print(f"⏳ Ожидание {wait:.1f} сек...")
        time.sleep(wait)

    # Скриншот строго заданной области
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = os.path.join(PHOTO_DIR, f"shot_{timestamp}.png")
        
        print(f"📸 Получение скриншота...")
        full_screenshot = pyautogui.screenshot()
        
        cropped = full_screenshot.crop((x_start, y_start, x_end, y_end))
        cropped.save(filename)
        
        print(f"✓ Скриншот сохранен: {filename}")
        print(f"  Размер: {cropped.size[0]}x{cropped.size[1]} пикс")
    except Exception as e:
        print(f"❌ Ошибка при сохранении скриншота: {e}")

if __name__ == "__main__":
    get_dpi_scale()  # Инициализация DPI на Windows
    os_name = platform.system()
    print(f"🖥️  ОС: {os_name}")
    print(f"📍 Рабочая директория: {os.getcwd()}")
    run()