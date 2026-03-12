import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"BASE_DIR: {BASE_DIR}")

# Проверяем содержимое папки backend
backend_path = os.path.join(BASE_DIR, 'backend')
print(f"\nСодержимое папки backend ({backend_path}):")
if os.path.exists(backend_path):
    for item in os.listdir(backend_path):
        item_path = os.path.join(backend_path, item)
        if os.path.isdir(item_path):
            print(f"  📁 {item}/")
        else:
            print(f"  📄 {item}")
else:
    print("  Папка не найдена!")

# Проверяем содержимое папки backend/backend
backend_settings_path = os.path.join(backend_path, 'backend')
print(f"\nСодержимое папки backend/backend ({backend_settings_path}):")
if os.path.exists(backend_settings_path):
    for item in os.listdir(backend_settings_path):
        print(f"  📄 {item}")
else:
    print("  Папка не найдена!")

# Проверяем файл settings.py
settings_py = os.path.join(backend_settings_path, 'settings.py')
print(f"\nФайл settings.py существует: {os.path.exists(settings_py)}")

# Добавляем пути
sys.path.append(BASE_DIR)
sys.path.append(backend_path)
sys.path.append(backend_settings_path)

print(f"\nPython path includes:")
for p in sys.path[-3:]:
    print(f"  {p}")

# Пробуем разные варианты настройки Django
print("\nПробуем разные варианты DJANGO_SETTINGS_MODULE:")

variants = [
    'backend.settings',
    'backend.backend.settings',
    'settings',
    'backend/backend/settings'
]

for variant in variants:
    print(f"\nПробуем: {variant}")
    os.environ['DJANGO_SETTINGS_MODULE'] = variant
    try:
        django.setup()
        print(f"  ✅ УСПЕХ с {variant}!")
        break
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")