"""
Финальный скрипт загрузки данных
Запуск: python backend/scripts/load_final.py
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random
import json

# Добавляем пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))

# Настраиваем Django (правильный путь!)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Импортируем модели
from api.models import Student, Event, StudentFeatures

def create_students():
    """Создаем студентов"""
    print("\n=== СОЗДАНИЕ СТУДЕНТОВ ===")
    
    students_data = [
        {'student_id': 's0001', 'name': 'Иван Петров', 'course': 'ИТ', 'semester': 2},
        {'student_id': 's0002', 'name': 'Мария Иванова', 'course': 'Бизнес', 'semester': 3},
        {'student_id': 's0003', 'name': 'Алексей Сидоров', 'course': 'Дизайн', 'semester': 1},
        {'student_id': 's0004', 'name': 'Елена Козлова', 'course': 'ИТ', 'semester': 2},
        {'student_id': 's0005', 'name': 'Дмитрий Смирнов', 'course': 'Бизнес', 'semester': 3},
        {'student_id': 's0006', 'name': 'Анна Попова', 'course': 'Дизайн', 'semester': 1},
        {'student_id': 's0007', 'name': 'Сергей Васильев', 'course': 'ИТ', 'semester': 4},
        {'student_id': 's0008', 'name': 'Ольга Новикова', 'course': 'Бизнес', 'semester': 2},
        {'student_id': 's0009', 'name': 'Павел Морозов', 'course': 'Дизайн', 'semester': 3},
        {'student_id': 's0010', 'name': 'Татьяна Волкова', 'course': 'ИТ', 'semester': 1},
    ]
    
    students = []
    for data in students_data:
        student, created = Student.objects.get_or_create(
            student_id=data['student_id'],
            defaults={
                'name': data['name'],
                'course': data['course'],
                'semester': data['semester']
            }
        )
        students.append(student)
        if created:
            print(f"  ✅ Создан: {data['name']} ({data['course']})")
        else:
            print(f"  ⏩ Уже существует: {data['name']}")
    
    print(f"📊 Всего студентов: {len(students)}")
    return students

def create_events(students):
    """Создаем события для студентов"""
    print("\n=== СОЗДАНИЕ СОБЫТИЙ ===")
    
    event_types = ['login', 'view_lecture', 'submit_assignment', 'miss_deadline', 'take_test']
    total_events = 0
    
    for student in students:
        # Определяем "тип" студента (хороший/плохой)
        is_good = random.random() > 0.3  # 70% хороших
        
        # Генерируем разное количество событий
        num_events = random.randint(40, 80) if is_good else random.randint(15, 40)
        student_events = 0
        
        for _ in range(num_events):
            # Случайная дата за последние 60 дней
            days_ago = random.randint(0, 60)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            event_date = datetime.now() - timedelta(
                days=days_ago, 
                hours=hours_ago, 
                minutes=minutes_ago
            )
            
            # Выбираем тип события с учетом "хорошести"
            if is_good:
                # У хороших студентов меньше пропусков
                event_type = random.choice(event_types)
                if event_type == 'miss_deadline' and random.random() < 0.7:
                    event_type = random.choice(['login', 'view_lecture', 'submit_assignment'])
            else:
                event_type = random.choice(event_types)
            
            # Детали события
            details = {}
            if event_type == 'submit_assignment':
                details = {
                    'grade': random.randint(60, 100) if is_good else random.randint(30, 80),
                    'delay_hours': random.randint(-48, 0) if is_good else random.randint(0, 120),
                    'assignment_name': f'Лабораторная работа {random.randint(1,10)}'
                }
            elif event_type == 'take_test':
                details = {
                    'score': random.randint(70, 100) if is_good else random.randint(40, 75),
                    'test_name': f'Тест {random.randint(1,5)}',
                    'time_spent': random.randint(20, 90)
                }
            elif event_type == 'view_lecture':
                details = {
                    'lecture_name': f'Лекция {random.randint(1,15)}',
                    'duration_minutes': random.randint(10, 90)
                }
            elif event_type == 'miss_deadline':
                details = {
                    'assignment_name': f'Задание {random.randint(1,10)}',
                    'days_late': random.randint(1, 14)
                }
            
            # Создаем событие
            Event.objects.create(
                student=student,
                timestamp=event_date,
                event_type=event_type,
                details=details
            )
            student_events += 1
            total_events += 1
        
        print(f"  📊 {student.name}: {student_events} событий")
    
    print(f"✅ Всего создано событий: {total_events}")
    return total_events

def calculate_risks(students):
    """Рассчитываем риски для студентов"""
    print("\n=== РАСЧЕТ РИСКОВ ===")
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    for student in students:
        events = Event.objects.filter(student=student)
        
        if not events.exists():
            print(f"  ⚠️ {student.name}: нет событий")
            continue
        
        # Собираем статистику
        total_events = events.count()
        missed = events.filter(event_type='miss_deadline').count()
        assignments = events.filter(event_type='submit_assignment')
        tests = events.filter(event_type='take_test')
        logins = events.filter(event_type='login')
        
        # Активность
        activity_week = events.filter(timestamp__gte=week_ago).count()
        activity_month = events.filter(timestamp__gte=month_ago).count()
        
        # Последний вход
        last_login = logins.order_by('-timestamp').first()
        if last_login:
            days_since_login = (now - last_login.timestamp.replace(tzinfo=None)).days
        else:
            days_since_login = 999
        
        # Средние оценки
        scores = []
        for e in assignments:
            if 'grade' in e.details:
                scores.append(e.details['grade'])
        for e in tests:
            if 'score' in e.details:
                scores.append(e.details['score'])
        
        avg_score = sum(scores) / len(scores) if scores else 50
        
        # Средняя задержка
        delays = []
        for e in assignments:
            if 'delay_hours' in e.details:
                delays.append(e.details['delay_hours'])
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        # Расчет риска
        risk_score = 0
        
        # Пропуски дедлайнов
        risk_score += min(missed / 8, 0.3)
        
        # Низкая активность
        if activity_week < 3:
            risk_score += 0.2
        elif activity_week < 7:
            risk_score += 0.1
        
        # Низкие оценки
        if avg_score < 40:
            risk_score += 0.3
        elif avg_score < 60:
            risk_score += 0.2
        elif avg_score < 75:
            risk_score += 0.1
        
        # Давно не заходил
        if days_since_login > 14:
            risk_score += 0.2
        elif days_since_login > 7:
            risk_score += 0.1
        
        risk_score = min(risk_score, 1.0)
        
        # Уровень риска
        if risk_score < 0.25:
            risk_level = 'low'
        elif risk_score < 0.5:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        # Сохраняем
        StudentFeatures.objects.update_or_create(
            student=student,
            defaults={
                'avg_assignment_delay': avg_delay,
                'success_rate_midterms': avg_score,
                'days_since_last_login': days_since_login,
                'activity_count_last_week': activity_week,
                'missed_deadlines_count': missed,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'explanation': {
                    'total_events': total_events,
                    'avg_score': avg_score,
                    'activity_week': activity_week,
                    'missed': missed,
                    'days_since_login': days_since_login,
                    'risk_components': {
                        'missed_penalty': min(missed / 8, 0.3),
                        'inactivity_penalty': 0.2 if activity_week < 3 else 0.1 if activity_week < 7 else 0,
                        'score_penalty': 0.3 if avg_score < 40 else 0.2 if avg_score < 60 else 0.1 if avg_score < 75 else 0,
                        'login_penalty': 0.2 if days_since_login > 14 else 0.1 if days_since_login > 7 else 0
                    }
                }
            }
        )
        
        # Выводим результат
        risk_emoji = '🟢' if risk_level == 'low' else '🟡' if risk_level == 'medium' else '🔴'
        print(f"  {risk_emoji} {student.name}: {risk_level} (риск: {risk_score:.2f})")
    
    print(f"\n📊 Итог по рискам:")
    print(f"   🟢 Низкий: {StudentFeatures.objects.filter(risk_level='low').count()}")
    print(f"   🟡 Средний: {StudentFeatures.objects.filter(risk_level='medium').count()}")
    print(f"   🔴 Высокий: {StudentFeatures.objects.filter(risk_level='high').count()}")

def main():
    """Главная функция"""
    print("\n" + "="*70)
    print("📊 ЗАГРУЗКА ДАННЫХ В СИСТЕМУ МОНИТОРИНГА СТУДЕНТОВ")
    print("="*70)
    
    # Очищаем старые данные
    print("\nОчищаем старые данные...")
    Event.objects.all().delete()
    StudentFeatures.objects.all().delete()
    Student.objects.all().delete()
    print("✅ Старые данные удалены")
    
    # Создаем новые
    students = create_students()
    create_events(students)
    calculate_risks(students)
    
    print("\n" + "="*70)
    print("✅ ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО!")
    print(f"📊 Студентов: {Student.objects.count()}")
    print(f"📊 Событий: {Event.objects.count()}")
    print(f"📊 Признаков: {StudentFeatures.objects.count()}")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()