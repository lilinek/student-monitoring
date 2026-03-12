import pandas as pd
import django
import os
import sys
import json
from datetime import datetime, timedelta

# Добавляем путь к проекту в sys.path
sys.path.append('C:\\Users\\Лилия\\student-monitoring')

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.backend.settings')
django.setup()

from backend.api.models import Student, Event, StudentFeatures

def load_students():
    """Загружаем студентов из CSV файла"""
    print("Загружаем студентов...")
    
    # Проверяем, существует ли файл
    if not os.path.exists('students.csv'):
        print("❌ Файл students.csv не найден!")
        return False
    
    # Читаем CSV
    students_df = pd.read_csv('students.csv')
    count = 0
    
    for _, row in students_df.iterrows():
        student, created = Student.objects.get_or_create(
            student_id=row['student_id'],
            defaults={
                'name': row['name'],
                'course': row['course'],
                'semester': int(row['semester']) if str(row['semester']).isdigit() else 1
            }
        )
        if created:
            count += 1
    
    print(f"✅ Загружено {count} новых студентов")
    print(f"📊 Всего студентов в БД: {Student.objects.count()}")
    return True

def load_events():
    """Загружаем события из CSV файла"""
    print("\nЗагружаем события...")
    
    # Проверяем, существует ли файл
    if not os.path.exists('events.csv'):
        print("❌ Файл events.csv не найден!")
        return False
    
    # Читаем CSV
    events_df = pd.read_csv('events.csv')
    count = 0
    errors = 0
    
    for _, row in events_df.iterrows():
        try:
            # Ищем студента
            student = Student.objects.get(student_id=row['student_id'])
            
            # Преобразуем строку с деталями в словарь
            details = row['details']
            if isinstance(details, str):
                try:
                    # Убираем лишние кавычки и преобразуем
                    details_str = details.strip('"').replace('\\"', '"')
                    details = json.loads(details_str)
                except:
                    details = {}
            elif pd.isna(details):
                details = {}
            
            # Создаем событие
            Event.objects.create(
                student=student,
                timestamp=row['timestamp'],
                event_type=row['event_type'],
                details=details
            )
            count += 1
            
        except Student.DoesNotExist:
            errors += 1
            print(f"  ⚠️ Студент {row['student_id']} не найден")
        except Exception as e:
            errors += 1
            print(f"  ⚠️ Ошибка: {e}")
    
    print(f"✅ Загружено {count} событий")
    if errors > 0:
        print(f"⚠️ Пропущено {errors} записей с ошибками")
    return True

def calculate_features():
    """Рассчитываем признаки для ML для всех студентов"""
    print("\nРассчитываем признаки для ML...")
    
    students = Student.objects.all()
    total = students.count()
    
    for i, student in enumerate(students, 1):
        events = Event.objects.filter(student=student)
        
        if not events.exists():
            continue
        
        now = datetime.now()
        
        # Средняя задержка сдачи заданий
        assignments = events.filter(event_type='submit_assignment')
        delays = []
        for e in assignments:
            if e.details and 'delay_hours' in e.details:
                delays.append(float(e.details['delay_hours']))
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        # Дней с последнего входа
        last_login = events.filter(event_type='login').order_by('-timestamp').first()
        if last_login:
            last_login_time = last_login.timestamp.replace(tzinfo=None)
            days_since_login = (now - last_login_time).days
        else:
            days_since_login = 999
        
        # Активность за последнюю неделю
        week_ago = now - timedelta(days=7)
        activity_last_week = events.filter(timestamp__gte=week_ago).count()
        
        # Количество пропущенных дедлайнов
        missed_deadlines = events.filter(event_type='miss_deadline').count()
        
        # Успеваемость (средние оценки)
        scores = []
        for e in events:
            if e.details:
                if 'grade' in e.details:
                    scores.append(float(e.details['grade']))
                if 'score' in e.details:
                    scores.append(float(e.details['score']))
        avg_score = sum(scores) / len(scores) if scores else 50
        
        # Рассчитываем риск
        risk_score = 0
        risk_score += min(missed_deadlines / 10, 0.4)
        risk_score += max(0, (30 - activity_last_week) / 30) * 0.3
        risk_score += max(0, (60 - avg_score) / 60) * 0.3
        risk_score = min(risk_score, 1.0)
        
        # Определяем уровень риска
        if risk_score < 0.3:
            risk_level = 'low'
        elif risk_score < 0.6:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        # Сохраняем признаки
        StudentFeatures.objects.update_or_create(
            student=student,
            defaults={
                'avg_assignment_delay': avg_delay,
                'success_rate_midterms': avg_score,
                'days_since_last_login': days_since_login,
                'activity_count_last_week': activity_last_week,
                'missed_deadlines_count': missed_deadlines,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'explanation': {
                    'avg_delay': avg_delay,
                    'avg_score': avg_score,
                    'days_since_login': days_since_login,
                    'activity': activity_last_week,
                    'missed': missed_deadlines
                }
            }
        )
        
        if i % 10 == 0:
            print(f"  Обработано {i} из {total} студентов...")
    
    print(f"✅ Рассчитаны признаки для {total} студентов")

def main():
    print("\n" + "="*60)
    print("📥 ЗАГРУЗКА ДАННЫХ И РАСЧЕТ ПРИЗНАКОВ")
    print("="*60)
    
    if load_students():
        load_events()
        calculate_features()
    
    print("\n" + "="*60)
    print("✅ РАБОТА ЗАВЕРШЕНА")
    print(f"📊 Итог:")
    print(f"   - Студентов: {Student.objects.count()}")
    print(f"   - Событий: {Event.objects.count()}")
    print(f"   - Признаков: {StudentFeatures.objects.count()}")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()