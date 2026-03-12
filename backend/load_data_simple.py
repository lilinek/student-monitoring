import pandas as pd
import django
import os
import sys

# Добавляем путь к проекту
sys.path.append('C:\\Users\\Лилия\\student-monitoring')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.backend.settings')
django.setup()

from backend.api.models import Student, Event

# Загружаем студентов с указанием кодировки
print("Загружаем студентов...")
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
print(f"Загружено студентов: {Student.objects.count()}")

# Загружаем события
print("Загружаем события...")
events_df = pd.read_csv('../events.csv', encoding='utf-8')
for _, row in events_df.iterrows():
    try:
        student = Student.objects.get(student_id=row['student_id'])
        Event.objects.create(
            student=student,
            timestamp=row['timestamp'],
            event_type=row['event_type'],
            details={}
        )
    except Exception as e:
        print(f"Ошибка: {e}")
print(f"Загружено событий: {Event.objects.count()}")