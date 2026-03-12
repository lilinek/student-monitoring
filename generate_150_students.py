"""
Генерация 150 студентов с реалистичными данными
Запуск: python generate_150_students.py
"""

import os
import sys
import django
import random
import numpy as np
from datetime import datetime, timedelta
from faker import Faker

# Настройка Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Student, Event, StudentFeatures
import django.db.models as models

fake = Faker('ru_RU')  # Русские имена

def print_progress(current, total, message=""):
    """Выводит прогресс-бар"""
    percent = (current / total) * 100
    bar = '█' * int(percent // 2) + '░' * (50 - int(percent // 2))
    print(f"\r{message} [{bar}] {percent:.1f}% ({current}/{total})", end="")
    if current == total:
        print()

def generate_students(count=150):
    """Генерирует указанное количество студентов"""
    print("\n" + "="*70)
    print(f"👥 ГЕНЕРАЦИЯ {count} СТУДЕНТОВ")
    print("="*70)
    
    courses = ['Прикладная математика', 'Программная инженерия', 'Бизнес-аналитика', 
               'Информационная безопасность', 'Веб-дизайн', 'Искусственный интеллект',
               'Кибербезопасность', 'Управление проектами']
    
    students = []
    
    for i in range(1, count + 1):
        student = Student.objects.create(
            student_id=f's{str(i).zfill(4)}',
            name=fake.name(),
            course=random.choice(courses),
            semester=random.randint(1, 4)
        )
        students.append(student)
        
        if i % 10 == 0:
            print_progress(i, count, "Создание студентов")
    
    print(f"\n✅ Создано {len(students)} студентов")
    return students

def generate_events(students):
    """Генерирует события для студентов"""
    print("\n" + "="*70)
    print("📊 ГЕНЕРАЦИЯ СОБЫТИЙ")
    print("="*70)
    
    event_types = ['login', 'view_lecture', 'submit_assignment', 'miss_deadline', 'take_test']
    total_events = 0
    
    for i, student in enumerate(students, 1):
        # Определяем тип студента с реалистичным распределением
        student_type = random.choices(
            ['good', 'medium', 'poor'],
            weights=[0.35, 0.45, 0.20]  # 35% хороших, 45% средних, 20% проблемных
        )[0]
        
        # Количество событий зависит от типа
        if student_type == 'good':
            num_events = random.randint(120, 200)
            miss_prob = 0.05
            grade_min = 75
            grade_max = 100
            delay_range = (-48, 12)  # сдает заранее или вовремя
        elif student_type == 'medium':
            num_events = random.randint(60, 130)
            miss_prob = 0.15
            grade_min = 55
            grade_max = 85
            delay_range = (-12, 48)  # иногда опаздывает
        else:  # poor
            num_events = random.randint(20, 70)
            miss_prob = 0.35
            grade_min = 30
            grade_max = 70
            delay_range = (12, 120)  # часто опаздывает
        
        student_events = 0
        
        for _ in range(num_events):
            # Случайная дата за последние 90 дней
            days_ago = random.randint(0, 90)
            hours_ago = random.randint(0, 23)
            mins_ago = random.randint(0, 59)
            event_date = datetime.now() - timedelta(
                days=days_ago, 
                hours=hours_ago, 
                minutes=mins_ago
            )
            
            # Выбираем тип события
            if random.random() < miss_prob:
                event_type = 'miss_deadline'
            else:
                event_type = random.choice(event_types)
                if event_type == 'miss_deadline':  # если выпал miss_deadline, но мы уже учли вероятность
                    event_type = random.choice(['login', 'view_lecture', 'submit_assignment', 'take_test'])
            
            # Детали события
            details = {}
            
            if event_type == 'submit_assignment':
                details['grade'] = random.randint(grade_min, grade_max)
                details['delay_hours'] = random.randint(delay_range[0], delay_range[1])
                details['assignment_name'] = f"Лабораторная работа {random.randint(1,15)}"
                details['max_score'] = 100
                
            elif event_type == 'take_test':
                details['score'] = random.randint(grade_min, grade_max)
                details['test_name'] = f"Тест {random.randint(1,8)}"
                details['time_spent'] = random.randint(15, 120)
                details['max_score'] = 100
                
            elif event_type == 'view_lecture':
                details['lecture_name'] = f"Лекция {random.randint(1,20)}"
                details['duration'] = random.randint(5, 90)
                details['watched_percent'] = random.randint(30, 100)
                
            elif event_type == 'login':
                details['ip'] = fake.ipv4()
                details['device'] = random.choice(['desktop', 'mobile', 'tablet'])
                
            elif event_type == 'miss_deadline':
                details['assignment_name'] = f"Задание {random.randint(1,15)}"
                details['days_late'] = random.randint(1, 21)
                details['penalty'] = random.randint(10, 50)
            
            # Создаем событие
            Event.objects.create(
                student=student,
                timestamp=event_date,
                event_type=event_type,
                details=details
            )
            student_events += 1
            total_events += 1
        
        print_progress(i, len(students), f"Генерация событий (всего: {total_events})")
    
    print(f"\n✅ Создано {total_events} событий")
    return total_events

def calculate_features():
    """Рассчитывает признаки для всех студентов"""
    print("\n" + "="*70)
    print("🧮 РАСЧЕТ ПРИЗНАКОВ ДЛЯ ML")
    print("="*70)
    
    students = Student.objects.all()
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    calculated = 0
    features_data = []
    
    for i, student in enumerate(students, 1):
        events = Event.objects.filter(student=student)
        
        if events.count() < 5:
            continue
        
        # Собираем статистику
        total_events = events.count()
        missed = events.filter(event_type='miss_deadline').count()
        logins = events.filter(event_type='login').count()
        assignments = events.filter(event_type='submit_assignment')
        tests = events.filter(event_type='take_test')
        lectures = events.filter(event_type='view_lecture')
        
        # Активность по периодам
        activity_week = events.filter(timestamp__gte=week_ago).count()
        activity_month = events.filter(timestamp__gte=month_ago).count()
        activity_3months = events.filter(timestamp__gte=now - timedelta(days=90)).count()
        
        # Разнообразие активностей
        unique_event_types = events.values_list('event_type', flat=True).distinct().count()
        
        # Последний вход
        last_login = events.filter(event_type='login').order_by('-timestamp').first()
        if last_login:
            days_since_login = (now - last_login.timestamp.replace(tzinfo=None)).days
        else:
            days_since_login = 999
        
        # Оценки и задержки
        scores = []
        delays = []
        
        for e in assignments:
            if e.details:
                if 'grade' in e.details:
                    scores.append(e.details['grade'])
                if 'delay_hours' in e.details:
                    delays.append(e.details['delay_hours'])
        
        for e in tests:
            if e.details and 'score' in e.details:
                scores.append(e.details['score'])
        
        avg_score = sum(scores) / len(scores) if scores else 50
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        # Максимальные и минимальные оценки
        max_score = max(scores) if scores else 0
        min_score = min(scores) if scores else 0
        
        # Регулярность (стандартное отклонение интервалов)
        if events.count() > 1:
            timestamps = [e.timestamp for e in events]
            intervals = [(timestamps[j] - timestamps[j-1]).total_seconds() / 3600 
                        for j in range(1, len(timestamps))]
            regularity = np.std(intervals) if intervals else 0
        else:
            regularity = 0
        
        # Расчет риска (усовершенствованная формула)
        risk_score = 0
        
        # Фактор пропусков (0-0.3)
        risk_score += min(missed / 10, 0.3)
        
        # Фактор активности (0-0.25)
        if activity_week == 0:
            risk_score += 0.25
        elif activity_week < 3:
            risk_score += 0.15
        elif activity_week < 7:
            risk_score += 0.05
        
        # Фактор успеваемости (0-0.3)
        if avg_score < 40:
            risk_score += 0.3
        elif avg_score < 60:
            risk_score += 0.2
        elif avg_score < 75:
            risk_score += 0.1
        
        # Фактор давности входа (0-0.15)
        if days_since_login > 21:
            risk_score += 0.15
        elif days_since_login > 14:
            risk_score += 0.1
        elif days_since_login > 7:
            risk_score += 0.05
        
        # Разнообразие активностей (чем меньше, тем выше риск)
        if unique_event_types < 3:
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
                'avg_assignment_delay': float(avg_delay),
                'success_rate_midterms': float(avg_score),
                'days_since_last_login': days_since_login,
                'activity_count_last_week': activity_week,
                'missed_deadlines_count': missed,
                'risk_score': float(risk_score),
                'risk_level': risk_level,
                'explanation': {
                    'total_events': total_events,
                    'activity_month': activity_month,
                    'activity_3months': activity_3months,
                    'logins': logins,
                    'lectures': lectures.count(),
                    'assignments': assignments.count(),
                    'tests': tests.count(),
                    'avg_score': avg_score,
                    'max_score': max_score,
                    'min_score': min_score,
                    'missed': missed,
                    'days_since_login': days_since_login,
                    'unique_event_types': unique_event_types,
                    'regularity': float(regularity),
                    'risk_components': {
                        'missed_penalty': min(missed / 10, 0.3),
                        'activity_penalty': 0.25 if activity_week == 0 else 0.15 if activity_week < 3 else 0.05 if activity_week < 7 else 0,
                        'score_penalty': 0.3 if avg_score < 40 else 0.2 if avg_score < 60 else 0.1 if avg_score < 75 else 0,
                        'login_penalty': 0.15 if days_since_login > 21 else 0.1 if days_since_login > 14 else 0.05 if days_since_login > 7 else 0,
                        'diversity_penalty': 0.1 if unique_event_types < 3 else 0
                    }
                }
            }
        )
        calculated += 1
        print_progress(i, len(students), "Расчет признаков")
    
    print(f"\n✅ Рассчитаны признаки для {calculated} студентов")
    return calculated

def show_statistics():
    """Показывает статистику по сгенерированным данным"""
    print("\n" + "="*70)
    print("📊 СТАТИСТИКА СГЕНЕРИРОВАННЫХ ДАННЫХ")
    print("="*70)
    
    total_students = Student.objects.count()
    total_events = Event.objects.count()
    total_features = StudentFeatures.objects.count()
    
    print(f"\n👥 Всего студентов: {total_students}")
    print(f"📊 Всего событий: {total_events}")
    print(f"🧮 Студентов с признаками: {total_features}")
    
    if total_events > 0:
        print(f"\n📈 Среднее событий на студента: {total_events/total_students:.1f}")
    
    # Распределение по курсам
    print("\n📚 Распределение по курсам:")
    courses = Student.objects.values('course').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    for course in courses:
        print(f"   {course['course']}: {course['count']} студентов")
    
    # Распределение по уровням риска
    if total_features > 0:
        print("\n🎯 Распределение по уровням риска:")
        risk_dist = StudentFeatures.objects.values('risk_level').annotate(
            count=models.Count('id')
        ).order_by('risk_level')
        
        for item in risk_dist:
            emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}.get(item['risk_level'], '⚪')
            percentage = (item['count'] / total_features) * 100
            print(f"   {emoji} {item['risk_level']}: {item['count']} ({percentage:.1f}%)")
        
        # Средний риск по группам
        print(f"\n📉 Средний риск: {StudentFeatures.objects.aggregate(avg=models.Avg('risk_score'))['avg']:.3f}")

def main():
    """Главная функция"""
    print("\n" + "="*70)
    print("🌟 ГЕНЕРАЦИЯ 150 СТУДЕНТОВ ДЛЯ ML МОДЕЛИ")
    print("="*70)
    
    # Очищаем старые данные
    print("\n🧹 Очистка старых данных...")
    Event.objects.all().delete()
    StudentFeatures.objects.all().delete()
    Student.objects.all().delete()
    print("✅ Старые данные удалены")
    
    # Генерируем новые
    students = generate_students(150)
    generate_events(students)
    calculate_features()
    
    # Показываем статистику
    show_statistics()
    
    print("\n" + "="*70)
    print("✅ ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
    print("="*70)
    print("\n👉 Теперь запустите обучение модели:")
    print("   python train_ml_model.py")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()