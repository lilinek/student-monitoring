import random
import datetime
import os
import django
from django.utils import timezone
import datetime

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Student, Event, StudentFeatures

def generate_students():
    """Создаем 100 студентов"""
    print("Создаем студентов...")
    students = []
    
    for i in range(1, 101):
        student = Student.objects.create(
            student_id=f's{i:04d}',
            name=f'Студент {i}',
            course=random.choice(['ИТ', 'Бизнес', 'Дизайн']),
            semester=random.randint(1, 4)
        )
        students.append(student)
        if i % 10 == 0:
            print(f"  Создано {i} студентов...")
    
    print(f"✅ Создано {len(students)} студентов")
    return students

def generate_events(students):
    """Генерируем события за последние 90 дней"""
    print("Генерируем события...")
    events_count = 0
    
    event_types = ['login', 'view_lecture', 'submit_assignment', 'miss_deadline', 'take_test']
    
    for student in students:
        # Определяем "хорошесть" студента
        is_good = random.random() > 0.3  # 70% хороших
        
        # У хороших студентов больше событий
        num_events = random.randint(50, 200) if is_good else random.randint(10, 80)
        
        for _ in range(num_events):
            days_ago = random.randint(0, 90)
            event_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
            
            # Выбираем тип события
            if is_good:
                event_type = random.choice(event_types)
                if event_type == 'miss_deadline' and random.random() < 0.8:
                    event_type = 'submit_assignment'
            else:
                event_type = random.choice(event_types)
            
            # Детали события
            details = {}
            if event_type == 'submit_assignment':
                details['grade'] = random.randint(60, 100) if is_good else random.randint(30, 80)
                delay = random.randint(-48, 0) if is_good else random.randint(0, 168)
                details['delay_hours'] = delay
            elif event_type == 'take_test':
                details['score'] = random.randint(70, 100) if is_good else random.randint(40, 80)
            
            # Создаем событие
            Event.objects.create(
                student=student,
                timestamp=event_date,
                event_type=event_type,
                details=details
            )
            events_count += 1
    
    print(f"✅ Всего создано {events_count} событий")
    return events_count

def generate_features(students):
    """Рассчитываем признаки для ML"""
    print("Рассчитываем признаки для ML...")
    
    from django.utils import timezone
    
    for i, student in enumerate(students, 1):
        events = Event.objects.filter(student=student)
        
        if not events.exists():
            continue
        
        now = timezone.now()  # используем timezone.now() вместо datetime.datetime.now()
        
        # Последний вход
        last_login = events.filter(event_type='login').order_by('-timestamp').first()
        if last_login:
            # Оба времени теперь с часовым поясом
            days_since_last_login = (now - last_login.timestamp).days
        else:
            days_since_last_login = 999
        
        # Активность за последнюю неделю
        week_ago = now - datetime.timedelta(days=7)
        activity_last_week = events.filter(timestamp__gte=week_ago).count()
        
        # Пропущенные дедлайны
        missed_deadlines = events.filter(event_type='miss_deadline').count()
        
        # Средняя задержка сдачи заданий
        assignments = events.filter(event_type='submit_assignment')
        if assignments.exists():
            delays = []
            for a in assignments:
                if 'delay_hours' in a.details:
                    delays.append(a.details['delay_hours'])
            avg_delay = sum(delays) / len(delays) if delays else 0
        else:
            avg_delay = 0
        
        # Успеваемость (средняя оценка)
        scores = []
        for e in events:
            if 'grade' in e.details:
                scores.append(e.details['grade'])
            if 'score' in e.details:
                scores.append(e.details['score'])
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
        
        # Создаем признаки
        StudentFeatures.objects.update_or_create(
            student=student,
            defaults={
                'avg_assignment_delay': avg_delay,
                'success_rate_midterms': avg_score,
                'days_since_last_login': days_since_last_login,
                'activity_count_last_week': activity_last_week,
                'missed_deadlines_count': missed_deadlines,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'explanation': {
                    'avg_delay': avg_delay,
                    'avg_score': avg_score,
                    'days_since_login': days_since_last_login,
                    'activity': activity_last_week,
                    'missed': missed_deadlines
                }
            }
        )
        
        if i % 10 == 0:
            print(f"  Обработано {i} студентов...")
    
    print(f"✅ Признаки рассчитаны для {len(students)} студентов")

def main():
    print("\n" + "="*60)
    print("📊 ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ ДЛЯ МОНИТОРИНГА СТУДЕНТОВ")
    print("="*60 + "\n")
    
    # Очищаем старые данные
    print("Очищаем старые данные...")
    Event.objects.all().delete()
    StudentFeatures.objects.all().delete()
    Student.objects.all().delete()
    print("✅ Старые данные удалены\n")
    
    # Генерируем новые
    students = generate_students()
    print()
    generate_events(students)
    print()
    generate_features(students)
    print()
    
    print("="*60)
    print("✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
    print(f"📌 Студентов: {Student.objects.count()}")
    print(f"📌 Событий: {Event.objects.count()}")
    print(f"📌 Признаков: {StudentFeatures.objects.count()}")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
