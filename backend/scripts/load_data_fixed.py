"""
Скрипт для загрузки данных в БД
Запуск: python backend/scripts/load_data_fixed.py
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime, timedelta
import random
import json

# Добавляем путь к проекту
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.backend.settings')
django.setup()

# Импортируем модели после настройки Django
from api.models import Student, Event, StudentFeatures

def load_students():
    """Загружаем студентов из CSV"""
    print("\n=== ЗАГРУЗКА СТУДЕНТОВ ===")
    
    # Путь к файлу данных
    csv_path = os.path.join(BASE_DIR, 'data', 'raw', 'students.csv')
    
    # Если файла нет, создаем тестовые данные
    if not os.path.exists(csv_path):
        print("Файл не найден. Создаем тестовые данные...")
        return create_test_students()
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        count = 0
        
        for _, row in df.iterrows():
            student, created = Student.objects.get_or_create(
                student_id=str(row['student_id']),
                defaults={
                    'name': str(row['name']),
                    'course': str(row['course']),
                    'semester': int(row['semester'])
                }
            )
            if created:
                count += 1
        
        print(f"✅ Загружено {count} новых студентов")
        print(f"📊 Всего студентов: {Student.objects.count()}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при загрузке студентов: {e}")
        return False

def create_test_students():
    """Создаем тестовых студентов"""
    print("Создаем тестовых студентов...")
    
    test_students = [
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
    
    count = 0
    for s in test_students:
        student, created = Student.objects.get_or_create(
            student_id=s['student_id'],
            defaults=s
        )
        if created:
            count += 1
    
    print(f"✅ Создано {count} тестовых студентов")
    print(f"📊 Всего студентов: {Student.objects.count()}")
    return True

def load_events():
    """Загружаем события"""
    print("\n=== ЗАГРУЗКА СОБЫТИЙ ===")
    
    csv_path = os.path.join(BASE_DIR, 'data', 'raw', 'events.csv')
    
    if not os.path.exists(csv_path):
        print("Файл событий не найден. Создаем тестовые события...")
        return create_test_events()
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        count = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                # Ищем студента
                student = Student.objects.get(student_id=str(row['student_id']))
                
                # Преобразуем строку с деталями
                details = {}
                if 'details' in row and pd.notna(row['details']):
                    try:
                        details_str = str(row['details'])
                        # Заменяем одинарные кавычки на двойные для JSON
                        details_str = details_str.replace("'", '"')
                        details = json.loads(details_str)
                    except:
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
            except Exception as e:
                errors += 1
                print(f"  ⚠️ Ошибка в строке: {e}")
        
        print(f"✅ Загружено {count} событий")
        if errors:
            print(f"⚠️ Пропущено {errors} записей")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке событий: {e}")
        return False

def create_test_events():
    """Создаем тестовые события"""
    print("Создаем тестовые события...")
    
    students = Student.objects.all()
    if not students.exists():
        print("❌ Нет студентов для создания событий")
        return False
    
    event_types = ['login', 'view_lecture', 'submit_assignment', 'miss_deadline', 'take_test']
    count = 0
    
    for student in students:
        # Для каждого студента создаем 20-50 событий
        num_events = random.randint(20, 50)
        
        for i in range(num_events):
            # Случайная дата за последние 60 дней
            days_ago = random.randint(0, 60)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            event_date = datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # Выбираем тип события
            event_type = random.choice(event_types)
            
            # Детали для разных типов событий
            details = {}
            if event_type == 'submit_assignment':
                details['grade'] = random.randint(40, 100)
                details['delay_hours'] = random.randint(-48, 72)
                details['assignment_name'] = f"Лабораторная работа {random.randint(1,10)}"
            elif event_type == 'take_test':
                details['score'] = random.randint(30, 100)
                details['test_name'] = f"Тест {random.randint(1,5)}"
                details['time_spent_minutes'] = random.randint(10, 120)
            elif event_type == 'view_lecture':
                details['lecture_name'] = f"Лекция {random.randint(1,15)}"
                details['watch_duration_minutes'] = random.randint(5, 90)
            elif event_type == 'miss_deadline':
                details['assignment_name'] = f"Задание {random.randint(1,10)}"
                details['days_late'] = random.randint(1, 14)
            
            Event.objects.create(
                student=student,
                timestamp=event_date,
                event_type=event_type,
                details=details
            )
            count += 1
    
    print(f"✅ Создано {count} тестовых событий")
    return True

def calculate_risk_features():
    """Рассчитываем признаки риска для всех студентов"""
    print("\n=== РАСЧЕТ ПРИЗНАКОВ РИСКА ===")
    
    students = Student.objects.all()
    if not students.exists():
        print("❌ Нет студентов для расчета признаков")
        return False
    
    calculated = 0
    now = datetime.now()
    
    for student in students:
        events = Event.objects.filter(student=student)
        
        if not events.exists():
            continue
        
        # 1. Средняя задержка сдачи заданий
        assignments = events.filter(event_type='submit_assignment')
        delays = []
        for e in assignments:
            if e.details and 'delay_hours' in e.details:
                try:
                    delays.append(float(e.details['delay_hours']))
                except:
                    pass
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        # 2. Дней с последнего входа
        last_login = events.filter(event_type='login').order_by('-timestamp').first()
        if last_login:
            last_login_time = last_login.timestamp.replace(tzinfo=None)
            days_since_login = (now - last_login_time).days
        else:
            days_since_login = 999
        
        # 3. Активность за последнюю неделю
        week_ago = now - timedelta(days=7)
        activity_last_week = events.filter(timestamp__gte=week_ago).count()
        
        # 4. Активность за последний месяц
        month_ago = now - timedelta(days=30)
        activity_last_month = events.filter(timestamp__gte=month_ago).count()
        
        # 5. Пропущенные дедлайны
        missed_deadlines = events.filter(event_type='miss_deadline').count()
        
        # 6. Успеваемость (средние оценки)
        scores = []
        for e in events:
            if e.details:
                if 'grade' in e.details:
                    try:
                        scores.append(float(e.details['grade']))
                    except:
                        pass
                if 'score' in e.details:
                    try:
                        scores.append(float(e.details['score']))
                    except:
                        pass
        avg_score = sum(scores) / len(scores) if scores else 50
        
        # Расчет риска
        risk_score = 0
        # Пропуски дедлайнов (0-0.4)
        risk_score += min(missed_deadlines / 10, 0.4)
        
        # Низкая активность (0-0.3)
        risk_score += max(0, (10 - activity_last_week) / 10) * 0.3
        
        # Низкие оценки (0-0.3)
        risk_score += max(0, (70 - avg_score) / 70) * 0.3
        
        # Давно не заходил (0-0.2)
        if days_since_login > 14:
            risk_score += 0.2
        elif days_since_login > 7:
            risk_score += 0.1
        
        risk_score = min(risk_score, 1.0)
        
        # Уровень риска
        if risk_score < 0.3:
            risk_level = 'low'
        elif risk_score < 0.6:
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
                'activity_count_last_week': activity_last_week,
                'missed_deadlines_count': missed_deadlines,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'explanation': {
                    'avg_delay': avg_delay,
                    'avg_score': avg_score,
                    'days_since_login': days_since_login,
                    'activity_week': activity_last_week,
                    'activity_month': activity_last_month,
                    'missed_deadlines': missed_deadlines,
                    'risk_components': {
                        'missed_penalty': min(missed_deadlines / 10, 0.4),
                        'inactivity_penalty': max(0, (10 - activity_last_week) / 10) * 0.3,
                        'low_scores_penalty': max(0, (70 - avg_score) / 70) * 0.3,
                        'login_penalty': 0.2 if days_since_login > 14 else 0.1 if days_since_login > 7 else 0
                    }
                }
            }
        )
        calculated += 1
        
        if calculated % 10 == 0:
            print(f"  Обработано {calculated} студентов...")
    
    print(f"✅ Рассчитаны признаки для {calculated} студентов")
    return True

def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("📥 ЗАГРУЗКА ДАННЫХ В БАЗУ ДАННЫХ")
    print("="*60)
    
    # Очищаем старые данные (опционально)
    print("\nОчищаем старые данные...")
    try:
        Event.objects.all().delete()
        StudentFeatures.objects.all().delete()
        Student.objects.all().delete()
        print("✅ Старые данные удалены")
    except Exception as e:
        print(f"⚠️ Ошибка при очистке: {e}")
    
    # Загружаем новые
    if load_students():
        load_events()
        calculate_risk_features()
    
    print("\n" + "="*60)
    print("✅ РАБОТА ЗАВЕРШЕНА")
    print(f"📊 Студентов: {Student.objects.count()}")
    print(f"📊 Событий: {Event.objects.count()}")
    print(f"📊 Признаков: {StudentFeatures.objects.count()}")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()