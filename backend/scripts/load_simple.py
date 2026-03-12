import os
import sys
import django

# Добавляем путь к проекту
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))

print(f"BASE_DIR: {BASE_DIR}")
print(f"Python path: {sys.path}")

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.backend.settings')

try:
    django.setup()
    print("✅ Django настроен успешно!")
except Exception as e:
    print(f"❌ Ошибка настройки Django: {e}")
    sys.exit(1)

# Импортируем модели
try:
    from api.models import Student
    print("✅ Модели импортированы успешно!")
    print(f"📊 Текущее количество студентов: {Student.objects.count()}")
except Exception as e:
    print(f"❌ Ошибка импорта моделей: {e}")
    sys.exit(1)

print("\n✅ Скрипт работает!")
