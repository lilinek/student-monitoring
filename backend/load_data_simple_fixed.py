import pandas as pd
import django
import os
import sys

# Настраиваем Django правильно для папки backend
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Теперь импортируем модели из api (не из backend.api)
from api.models import Student, Event

# Загружаем студентов
print("Загружаем студентов...")
try:
    # Пробуем прочитать файл из родительской папки
    students_df = pd.read_csv('../students.csv', encoding='utf-8')
    
    for _, row in students_df.iterrows():
        Student.objects.get_or_create(
            student_id=row['student_id'],
            defaults={
                'name': row['name'],
                'course': row['course'],
                'semester': int(row['semester'])
            }
        )
    print(f"✅ Загружено студентов: {Student.objects.count()}")
except FileNotFoundError:
    print("❌ Файл students.csv не найден в папке выше")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# Загружаем события
print("\nЗагружаем события...")
try:
    events_df = pd.read_csv('../events.csv', encoding='utf-8')
    count = 0
    
    for _, row in events_df.iterrows():
        try:
            student = Student.objects.get(student_id=row['student_id'])
            Event.objects.create(
                student=student,
                timestamp=row['timestamp'],
                event_type=row['event_type'],
                details={}  # упрощаем для теста
            )
            count += 1
        except Student.DoesNotExist:
            print(f"  ⚠️ Студент {row['student_id']} не найден")
        except Exception as e:
            print(f"  ⚠️ Ошибка: {e}")
    
    print(f"✅ Загружено событий: {count}")
except FileNotFoundError:
    print("❌ Файл events.csv не найден в папке выше")
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\n✅ Скрипт выполнен!")