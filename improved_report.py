"""
Улучшенная система генерации подробных отчетов
Запуск: python improved_report.py
"""

import os
import sys
import django
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Используем бэкенд без графического вывода
import matplotlib.pyplot as plt
import seaborn as sns
import io
from collections import Counter
import base64

# Настройка Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Student, Event, StudentFeatures
import django.db.models as models

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class ImprovedReportGenerator:
    """Генератор подробных отчетов"""
    
    def __init__(self):
        self.stats = self.collect_statistics()
    
    def collect_statistics(self):
        """Собирает полную статистику для отчета"""
        stats = {}
        
        # ===== 1. ОСНОВНЫЕ МЕТРИКИ =====
        stats['total_students'] = Student.objects.count()
        stats['total_events'] = Event.objects.count()
        stats['students_with_features'] = StudentFeatures.objects.count()
        
        # ===== 2. РАСПРЕДЕЛЕНИЕ ПО РИСКАМ =====
        risk_counts = StudentFeatures.objects.values('risk_level').annotate(
            count=models.Count('id')
        ).order_by('risk_level')
        
        stats['risk_distribution'] = {
            item['risk_level']: item['count'] 
            for item in risk_counts
        }
        
        # Добавляем проценты
        total = stats['total_students']
        stats['risk_percentages'] = {}
        for level, count in stats['risk_distribution'].items():
            stats['risk_percentages'][level] = (count / total * 100) if total > 0 else 0
        
        # ===== 3. СРЕДНИЕ ПОКАЗАТЕЛИ =====
        features = StudentFeatures.objects.all()
        if features.exists():
            stats['avg_risk'] = sum(f.risk_score for f in features) / features.count()
            stats['avg_activity'] = sum(f.activity_count_last_week for f in features) / features.count()
            stats['avg_missed'] = sum(f.missed_deadlines_count for f in features) / features.count()
            stats['avg_score'] = sum(f.success_rate_midterms for f in features) / features.count()
            stats['avg_days_since_login'] = sum(f.days_since_last_login for f in features) / features.count()
        else:
            stats['avg_risk'] = 0
            stats['avg_activity'] = 0
            stats['avg_missed'] = 0
            stats['avg_score'] = 0
            stats['avg_days_since_login'] = 0
        
        # ===== 4. СТАТИСТИКА ПО КУРСАМ =====
        courses = Student.objects.values_list('course', flat=True).distinct()
        course_stats = []
        
        for course in courses:
            students_in_course = Student.objects.filter(course=course)
            features_in_course = StudentFeatures.objects.filter(student__in=students_in_course)
            
            if features_in_course.exists():
                course_features = list(features_in_course)
                course_stats.append({
                    'course': course,
                    'count': students_in_course.count(),
                    'avg_risk': sum(f.risk_score for f in course_features) / len(course_features),
                    'avg_activity': sum(f.activity_count_last_week for f in course_features) / len(course_features),
                    'avg_score': sum(f.success_rate_midterms for f in course_features) / len(course_features),
                    'avg_missed': sum(f.missed_deadlines_count for f in course_features) / len(course_features),
                    'high_risk': features_in_course.filter(risk_level='high').count(),
                    'medium_risk': features_in_course.filter(risk_level='medium').count(),
                    'low_risk': features_in_course.filter(risk_level='low').count(),
                    'high_risk_pct': features_in_course.filter(risk_level='high').count() / len(course_features) * 100 if course_features else 0,
                })
        
        stats['course_stats'] = sorted(course_stats, key=lambda x: x['avg_risk'], reverse=True)
        
        # ===== 5. СТУДЕНТЫ С ВЫСОКИМ РИСКОМ =====
        high_risk_students = StudentFeatures.objects.filter(
            risk_level='high'
        ).select_related('student').order_by('-risk_score')
        
        stats['high_risk'] = []
        for fs in high_risk_students:
            recent_events = Event.objects.filter(student=fs.student).order_by('-timestamp')[:5]
            recent_events_list = [
                f"{e.timestamp.strftime('%d.%m')} - {e.event_type}" 
                for e in recent_events
            ]
            
            stats['high_risk'].append({
                'name': fs.student.name,
                'student_id': fs.student.student_id,
                'course': fs.student.course,
                'semester': fs.student.semester,
                'risk_score': fs.risk_score,
                'activity': fs.activity_count_last_week,
                'missed': fs.missed_deadlines_count,
                'avg_score': fs.success_rate_midterms,
                'days_since_login': fs.days_since_last_login,
                'avg_delay': fs.avg_assignment_delay,
                'recent_events': recent_events_list
            })
        
        stats['high_risk_count'] = len(stats['high_risk'])
        
        # ===== 6. СТУДЕНТЫ СО СРЕДНИМ РИСКОМ =====
        medium_risk_students = StudentFeatures.objects.filter(
            risk_level='medium'
        ).select_related('student').order_by('-risk_score')[:20]
        
        stats['medium_risk'] = [
            {
                'name': fs.student.name,
                'course': fs.student.course,
                'risk_score': fs.risk_score,
                'activity': fs.activity_count_last_week,
                'missed': fs.missed_deadlines_count,
                'avg_score': fs.success_rate_midterms,
            }
            for fs in medium_risk_students
        ]
        
        stats['medium_risk_count'] = StudentFeatures.objects.filter(risk_level='medium').count()
        
        # ===== 7. СТУДЕНТЫ С НИЗКИМ РИСКОМ =====
        low_risk_students = StudentFeatures.objects.filter(
            risk_level='low'
        ).select_related('student').order_by('risk_score')[:10]
        
        stats['low_risk'] = [
            {
                'name': fs.student.name,
                'course': fs.student.course,
                'risk_score': fs.risk_score,
                'avg_score': fs.success_rate_midterms,
                'activity': fs.activity_count_last_week,
            }
            for fs in low_risk_students
        ]
        
        stats['low_risk_count'] = StudentFeatures.objects.filter(risk_level='low').count()
        
        # ===== 8. СТАТИСТИКА ПО СОБЫТИЯМ =====
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        stats['events_last_week'] = Event.objects.filter(timestamp__gte=week_ago).count()
        stats['events_last_month'] = Event.objects.filter(timestamp__gte=month_ago).count()
        
        # Типы событий
        event_types = Event.objects.values('event_type').annotate(
            count=models.Count('id')
        ).order_by('-count')
        
        stats['event_types'] = {e['event_type']: e['count'] for e in event_types}
        
        # ===== 9. АКТИВНОСТЬ ПО ДНЯМ =====
        daily_activity = []
        for i in range(30):
            date = now - timedelta(days=i)
            next_date = date + timedelta(days=1)
            count = Event.objects.filter(
                timestamp__gte=date,
                timestamp__lt=next_date
            ).count()
            daily_activity.append({
                'date': date.strftime('%d.%m'),
                'count': count
            })
        
        stats['daily_activity'] = list(reversed(daily_activity))
        
        # ===== 10. ДИНАМИКА РИСКА =====
        risk_ranges = [
            {'min': 0, 'max': 0.2, 'label': '0-0.2'},
            {'min': 0.2, 'max': 0.4, 'label': '0.2-0.4'},
            {'min': 0.4, 'max': 0.6, 'label': '0.4-0.6'},
            {'min': 0.6, 'max': 0.8, 'label': '0.6-0.8'},
            {'min': 0.8, 'max': 1.0, 'label': '0.8-1.0'},
        ]
        
        risk_distribution_detailed = []
        for r in risk_ranges:
            count = StudentFeatures.objects.filter(
                risk_score__gte=r['min'],
                risk_score__lt=r['max']
            ).count()
            risk_distribution_detailed.append({
                'range': r['label'],
                'count': count,
                'percentage': (count / stats['total_students'] * 100) if stats['total_students'] > 0 else 0
            })
        
        stats['risk_distribution_detailed'] = risk_distribution_detailed
        
        return stats
    
    def generate_text_report(self, filename=None):
        """Генерирует подробный текстовый отчет"""
        if not filename:
            filename = f"detailed_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        
        stats = self.stats
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(" " * 25 + "ПОДРОБНЫЙ ОТЧЕТ ПО МОНИТОРИНГУ СТУДЕНТОВ\n")
            f.write("="*80 + "\n")
            f.write(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write(f"Период анализа: последние 30 дней\n")
            f.write("="*80 + "\n\n")
            
            # ===== 1. ОБЩАЯ СТАТИСТИКА =====
            f.write("1. ОБЩАЯ СТАТИСТИКА\n")
            f.write("-" * 40 + "\n")
            f.write(f"   Всего студентов: {stats['total_students']}\n")
            f.write(f"   Всего событий: {stats['total_events']}\n")
            f.write(f"   Событий за неделю: {stats['events_last_week']}\n")
            f.write(f"   Событий за месяц: {stats['events_last_month']}\n")
            f.write(f"   Средний риск: {stats['avg_risk']:.3f}\n")
            f.write(f"   Средняя активность (нед): {stats['avg_activity']:.1f}\n")
            f.write(f"   Средний балл: {stats['avg_score']:.1f}\n")
            f.write(f"   Среднее количество пропусков: {stats['avg_missed']:.1f}\n")
            f.write(f"   Среднее дней без входа: {stats['avg_days_since_login']:.1f}\n\n")
            
            # ===== 2. РАСПРЕДЕЛЕНИЕ ПО РИСКАМ =====
            f.write("2. РАСПРЕДЕЛЕНИЕ ПО УРОВНЯМ РИСКА\n")
            f.write("-" * 40 + "\n")
            
            risk_names = {'high': 'ВЫСОКИЙ риск', 'medium': 'СРЕДНИЙ риск', 'low': 'НИЗКИЙ риск'}
            
            for level in ['high', 'medium', 'low']:
                if level in stats['risk_distribution']:
                    count = stats['risk_distribution'][level]
                    percentage = stats['risk_percentages'][level]
                    name = risk_names.get(level, level)
                    f.write(f"   {name}: {count} чел. ({percentage:.1f}%)\n")
            
            f.write("\n   Детальное распределение по диапазонам:\n")
            for item in stats['risk_distribution_detailed']:
                bar = "#" * int(item['percentage'] / 2)
                f.write(f"   {item['range']}: {item['count']:3d} чел. ({item['percentage']:5.1f}%) {bar}\n")
            f.write("\n")
            
            # ===== 3. СТАТИСТИКА ПО КУРСАМ =====
            f.write("3. СТАТИСТИКА ПО КУРСАМ\n")
            f.write("-" * 40 + "\n")
            
            for course in stats['course_stats']:
                f.write(f"\n   {course['course']}:\n")
                f.write(f"      Студентов: {course['count']}\n")
                f.write(f"      Средний риск: {course['avg_risk']:.3f}\n")
                f.write(f"      Средний балл: {course['avg_score']:.1f}\n")
                f.write(f"      Активность: {course['avg_activity']:.1f} соб/нед\n")
                f.write(f"      Пропуски: {course['avg_missed']:.1f}\n")
                f.write(f"      Высокий риск: {course['high_risk']} чел. ({course['high_risk_pct']:.1f}%)\n")
            
            f.write("\n")
            
            # ===== 4. ТИПЫ СОБЫТИЙ =====
            f.write("4. РАСПРЕДЕЛЕНИЕ ТИПОВ СОБЫТИЙ\n")
            f.write("-" * 40 + "\n")
            
            event_names = {
                'login': 'Вход в систему',
                'view_lecture': 'Просмотр лекции',
                'submit_assignment': 'Сдача задания',
                'miss_deadline': 'Пропуск дедлайна',
                'take_test': 'Прохождение теста'
            }
            
            total_events = stats['total_events']
            for event_type, count in sorted(stats['event_types'].items(), key=lambda x: x[1], reverse=True):
                name = event_names.get(event_type, event_type)
                percentage = (count / total_events * 100) if total_events > 0 else 0
                bar = "#" * int(percentage / 2)
                f.write(f"   {name}: {count:6d} ({percentage:5.1f}%) {bar}\n")
            
            f.write("\n")
            
            # ===== 5. АКТИВНОСТЬ ПО ДНЯМ =====
            f.write("5. АКТИВНОСТЬ ЗА ПОСЛЕДНИЕ 30 ДНЕЙ\n")
            f.write("-" * 40 + "\n")
            
            max_count = max(item['count'] for item in stats['daily_activity']) if stats['daily_activity'] else 1
            for item in stats['daily_activity']:
                bar_length = int(item['count'] / max_count * 50) if max_count > 0 else 0
                bar = "#" * bar_length
                f.write(f"   {item['date']}: {item['count']:4d} {bar}\n")
            
            f.write("\n")
            
            # ===== 6. СТУДЕНТЫ С ВЫСОКИМ РИСКОМ =====
            f.write("6. СТУДЕНТЫ С ВЫСОКИМ РИСКОМ\n")
            f.write("-" * 40 + "\n")
            f.write(f"   Всего: {stats['high_risk_count']} студентов\n\n")
            
            for i, student in enumerate(stats['high_risk'][:20], 1):
                f.write(f"   {i:2d}. {student['name']}\n")
                f.write(f"       ID: {student['student_id']}\n")
                f.write(f"       Курс: {student['course']}, Семестр: {student['semester']}\n")
                f.write(f"       Риск: {student['risk_score']:.3f}\n")
                f.write(f"       Средний балл: {student['avg_score']:.1f}\n")
                f.write(f"       Активность: {student['activity']} соб/нед\n")
                f.write(f"       Пропуски: {student['missed']}\n")
                f.write(f"       Дней без входа: {student['days_since_login']}\n")
                f.write(f"       Последние события:\n")
                for event in student['recent_events'][:3]:
                    f.write(f"         • {event}\n")
                f.write("\n")
            
            # ===== 7. СТУДЕНТЫ СО СРЕДНИМ РИСКОМ =====
            f.write("7. СТУДЕНТЫ СО СРЕДНИМ РИСКОМ\n")
            f.write("-" * 40 + "\n")
            f.write(f"   Всего: {stats['medium_risk_count']} студентов\n")
            f.write("   Топ-20:\n\n")
            
            for i, student in enumerate(stats['medium_risk'][:20], 1):
                f.write(f"   {i:2d}. {student['name']} - {student['course']}\n")
                f.write(f"       Риск: {student['risk_score']:.3f}, Балл: {student['avg_score']:.1f}, ")
                f.write(f"Активность: {student['activity']}, Пропуски: {student['missed']}\n")
            
            f.write("\n")
            
            # ===== 8. СТУДЕНТЫ С НИЗКИМ РИСКОМ =====
            f.write("8. СТУДЕНТЫ С НИЗКИМ РИСКОМ\n")
            f.write("-" * 40 + "\n")
            f.write(f"   Всего: {stats['low_risk_count']} студентов\n")
            f.write("   Топ-10:\n\n")
            
            for i, student in enumerate(stats['low_risk'], 1):
                f.write(f"   {i:2d}. {student['name']} - {student['course']}\n")
                f.write(f"       Риск: {student['risk_score']:.3f}, Балл: {student['avg_score']:.1f}, ")
                f.write(f"Активность: {student['activity']}\n")
            
            f.write("\n")
            
            # ===== 9. РЕКОМЕНДАЦИИ =====
            f.write("9. РЕКОМЕНДАЦИИ\n")
            f.write("-" * 40 + "\n")
            
            f.write("   СТУДЕНТЫ С ВЫСОКИМ РИСКОМ:\n")
            f.write("      • Немедленно связаться с кураторами\n")
            f.write("      • Назначить встречи с тьюторами\n")
            f.write("      • Проверить академические задолженности\n")
            f.write("      • Рассмотреть возможность дополнительных занятий\n\n")
            
            f.write("   СТУДЕНТЫ СО СРЕДНИМ РИСКОМ:\n")
            f.write("      • Увеличить частоту коммуникации\n")
            f.write("      • Проверить посещаемость занятий\n")
            f.write("      • Рекомендовать консультации\n")
            f.write("      • Мотивировать к повышению активности\n\n")
            
            f.write("   СТУДЕНТЫ С НИЗКИМ РИСКОМ:\n")
            f.write("      • Привлекать как наставников\n")
            f.write("      • Предложить участие в олимпиадах\n")
            f.write("      • Поощрить за успехи\n\n")
            
            # ===== 10. КУРСЫ С НАИБОЛЬШИМ РИСКОМ =====
            f.write("10. КУРСЫ, ТРЕБУЮЩИЕ ВНИМАНИЯ\n")
            f.write("-" * 40 + "\n")
            
            high_risk_courses = [c for c in stats['course_stats'] if c['avg_risk'] > 0.5]
            if high_risk_courses:
                for course in high_risk_courses[:3]:
                    f.write(f"   • {course['course']}: ср.риск {course['avg_risk']:.2f}, ")
                    f.write(f"высокий риск у {course['high_risk']} чел. ({course['high_risk_pct']:.1f}%)\n")
            else:
                f.write("   • Курсов с высоким риском не обнаружено\n")
            
            f.write("\n")
            f.write("="*80 + "\n")
            f.write(f"Отчет сгенерирован автоматически системой мониторинга\n")
            f.write("="*80 + "\n")
        
        print(f"✅ Подробный текстовый отчет сохранен: {filename}")
        return filename
    
    def generate_html_report(self, filename=None):
        """Генерирует HTML отчет с графиками"""
        if not filename:
            filename = f"detailed_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        
        stats = self.stats
        
        try:
            # Создаем графики
            plt.style.use('ggplot')
            
            # График 1: Распределение риска
            fig1, ax1 = plt.subplots(figsize=(10, 6))
            risk_data = [
                stats['risk_distribution'].get('low', 0),
                stats['risk_distribution'].get('medium', 0),
                stats['risk_distribution'].get('high', 0)
            ]
            labels = ['Низкий риск', 'Средний риск', 'Высокий риск']
            colors = ['green', 'orange', 'red']
            ax1.pie(risk_data, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title('Распределение студентов по уровням риска')
            
            # Сохраняем график в base64
            img1 = io.BytesIO()
            fig1.savefig(img1, format='png', dpi=100, bbox_inches='tight')
            img1.seek(0)
            img1_base64 = base64.b64encode(img1.getvalue()).decode()
            plt.close(fig1)
            
            # График 2: Активность по дням
            fig2, ax2 = plt.subplots(figsize=(12, 6))
            dates = [item['date'] for item in stats['daily_activity']]
            counts = [item['count'] for item in stats['daily_activity']]
            ax2.plot(dates, counts, marker='o', linestyle='-', color='blue', linewidth=2)
            ax2.set_xlabel('Дата')
            ax2.set_ylabel('Количество событий')
            ax2.set_title('Динамика активности за последние 30 дней')
            ax2.tick_params(axis='x', rotation=45)
            ax2.grid(True, alpha=0.3)
            
            img2 = io.BytesIO()
            fig2.savefig(img2, format='png', dpi=100, bbox_inches='tight')
            img2.seek(0)
            img2_base64 = base64.b64encode(img2.getvalue()).decode()
            plt.close(fig2)
            
            # График 3: Распределение типов событий
            fig3, ax3 = plt.subplots(figsize=(10, 6))
            event_types = list(stats['event_types'].keys())
            event_counts = list(stats['event_types'].values())
            event_names_short = {
                'login': 'Вход',
                'view_lecture': 'Лекции',
                'submit_assignment': 'Сдача',
                'miss_deadline': 'Пропуски',
                'take_test': 'Тесты'
            }
            event_labels = [event_names_short.get(et, et) for et in event_types]
            ax3.bar(event_labels, event_counts, color='skyblue', edgecolor='navy')
            ax3.set_xlabel('Тип события')
            ax3.set_ylabel('Количество')
            ax3.set_title('Распределение типов событий')
            ax3.tick_params(axis='x', rotation=45)
            
            img3 = io.BytesIO()
            fig3.savefig(img3, format='png', dpi=100, bbox_inches='tight')
            img3.seek(0)
            img3_base64 = base64.b64encode(img3.getvalue()).decode()
            plt.close(fig3)
        except Exception as e:
            print(f"Ошибка при создании графиков: {e}")
            img1_base64 = img2_base64 = img3_base64 = ""
        
        # HTML шаблон
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Подробный отчет по мониторингу студентов</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    text-align: center;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                    border-left: 5px solid #3498db;
                    padding-left: 15px;
                }}
                .date {{
                    text-align: right;
                    color: #7f8c8d;
                    font-size: 0.9em;
                    margin-bottom: 30px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }}
                .stat-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .stat-value {{
                    font-size: 2.5em;
                    font-weight: bold;
                }}
                .stat-label {{
                    font-size: 0.9em;
                    opacity: 0.9;
                }}
                .chart-container {{
                    margin: 30px 0;
                    text-align: center;
                }}
                .chart-container img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    background-color: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                th {{
                    background-color: #3498db;
                    color: white;
                    padding: 12px;
                    font-weight: bold;
                }}
                td {{
                    padding: 10px;
                    border-bottom: 1px solid #ecf0f1;
                }}
                tr:hover {{
                    background-color: #f8f9fa;
                }}
                .risk-high {{ color: #e74c3c; font-weight: bold; }}
                .risk-medium {{ color: #f39c12; font-weight: bold; }}
                .risk-low {{ color: #27ae60; font-weight: bold; }}
                .recommendations {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 30px 0;
                    border-left: 5px solid #3498db;
                }}
                .footer {{
                    text-align: center;
                    color: #7f8c8d;
                    font-size: 0.8em;
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 1px solid #ecf0f1;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 0.8em;
                    font-weight: bold;
                }}
                .badge-high {{ background-color: #e74c3c; color: white; }}
                .badge-medium {{ background-color: #f39c12; color: white; }}
                .badge-low {{ background-color: #27ae60; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>ПОДРОБНЫЙ ОТЧЕТ ПО МОНИТОРИНГУ УСПЕВАЕМОСТИ СТУДЕНТОВ</h1>
                <div class="date">Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_students']}</div>
                        <div class="stat-label">Всего студентов</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_events']}</div>
                        <div class="stat-label">Всего событий</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['events_last_week']}</div>
                        <div class="stat-label">Событий за неделю</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['avg_risk']:.2f}</div>
                        <div class="stat-label">Средний риск</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['avg_score']:.1f}</div>
                        <div class="stat-label">Средний балл</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['avg_activity']:.1f}</div>
                        <div class="stat-label">Активность (нед)</div>
                    </div>
                </div>
                
                <h2>Распределение рисков</h2>
        """
        
        if img1_base64:
            html += f"""
                <div class="chart-container">
                    <img src="data:image/png;base64,{img1_base64}" alt="Распределение рисков">
                </div>
            """
        
        html += """
                <table>
                    <tr>
                        <th>Уровень риска</th>
                        <th>Количество</th>
                        <th>Процент</th>
                    </tr>
        """
        
        for level in ['high', 'medium', 'low']:
            if level in stats['risk_distribution']:
                count = stats['risk_distribution'][level]
                percentage = stats['risk_percentages'][level]
                
                if level == 'high':
                    level_display = 'Высокий риск'
                    level_class = 'risk-high'
                elif level == 'medium':
                    level_display = 'Средний риск'
                    level_class = 'risk-medium'
                else:
                    level_display = 'Низкий риск'
                    level_class = 'risk-low'
                
                html += f"""
                    <tr>
                        <td class="{level_class}">{level_display}</td>
                        <td>{count}</td>
                        <td>{percentage:.1f}%</td>
                    </tr>
                """
        
        html += f"""
                </table>
                
                <h2>Статистика по курсам</h2>
                <table>
                    <tr>
                        <th>Курс</th>
                        <th>Студентов</th>
                        <th>Ср. риск</th>
                        <th>Ср. балл</th>
                        <th>Активность</th>
                        <th>Высокий</th>
                        <th>Средний</th>
                        <th>Низкий</th>
                    </tr>
        """
        
        for course in stats['course_stats'][:10]:
            html += f"""
                    <tr>
                        <td><b>{course['course']}</b></td>
                        <td>{course['count']}</td>
                        <td>{course['avg_risk']:.2f}</td>
                        <td>{course['avg_score']:.1f}</td>
                        <td>{course['avg_activity']:.1f}</td>
                        <td class="risk-high">{course['high_risk']}</td>
                        <td class="risk-medium">{course['medium_risk']}</td>
                        <td class="risk-low">{course['low_risk']}</td>
                    </tr>
            """
        
        html += f"""
                </table>
                
                <h2>Динамика активности</h2>
        """
        
        if img2_base64:
            html += f"""
                <div class="chart-container">
                    <img src="data:image/png;base64,{img2_base64}" alt="Динамика активности">
                </div>
            """
        
        html += f"""
                <h2>Типы событий</h2>
        """
        
        if img3_base64:
            html += f"""
                <div class="chart-container">
                    <img src="data:image/png;base64,{img3_base64}" alt="Типы событий">
                </div>
            """
        
        html += f"""
                <h2>Студенты с высоким риском (топ-10)</h2>
                <table>
                    <tr>
                        <th>№</th>
                        <th>Имя</th>
                        <th>Курс</th>
                        <th>Риск</th>
                        <th>Балл</th>
                        <th>Активность</th>
                        <th>Пропуски</th>
                        <th>Дней без входа</th>
                    </tr>
        """
        
        for i, student in enumerate(stats['high_risk'][:10], 1):
            html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><b>{student['name'][:30]}</b></td>
                        <td>{student['course'][:15]}</td>
                        <td class="risk-high">{student['risk_score']:.2f}</td>
                        <td>{student['avg_score']:.1f}</td>
                        <td>{student['activity']}</td>
                        <td>{student['missed']}</td>
                        <td>{student['days_since_login']}</td>
                    </tr>
            """
        
        html += f"""
                </table>
                
                <div class="recommendations">
                    <h2>Рекомендации</h2>
                    <p><span class="badge badge-high">ВЫСОКИЙ РИСК</span> ({stats['high_risk_count']} студентов)</p>
                    <ul>
                        <li>Немедленно связаться с кураторами</li>
                        <li>Назначить встречи с тьюторами</li>
                        <li>Проверить академические задолженности</li>
                        <li>Организовать дополнительные консультации</li>
                    </ul>
                    
                    <p><span class="badge badge-medium">СРЕДНИЙ РИСК</span> ({stats['medium_risk_count']} студентов)</p>
                    <ul>
                        <li>Увеличить частоту коммуникации</li>
                        <li>Проверить посещаемость занятий</li>
                        <li>Рекомендовать консультации</li>
                        <li>Мотивировать к повышению активности</li>
                    </ul>
                    
                    <p><span class="badge badge-low">НИЗКИЙ РИСК</span> ({stats['low_risk_count']} студентов)</p>
                    <ul>
                        <li>Привлекать как наставников</li>
                        <li>Предложить участие в олимпиадах</li>
                        <li>Поощрить за успехи</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>Система мониторинга успеваемости v3.0</p>
                    <p>Отчет сгенерирован автоматически {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML отчет сохранен: {filename}")
        return filename

def main():
    print("\n" + "="*80)
    print("СОЗДАНИЕ ПОДРОБНОГО ОТЧЕТА")
    print("="*80)
    
    generator = ImprovedReportGenerator()
    
    # Генерируем текстовый отчет
    txt_file = generator.generate_text_report()
    
    # Генерируем HTML отчет
    html_file = generator.generate_html_report()
    
    print("\n" + "="*80)
    print("✅ ОТЧЕТЫ УСПЕШНО СОЗДАНЫ!")
    print(f"📄 Текстовый отчет: {txt_file}")
    print(f"🌐 HTML отчет: {html_file}")
    print("="*80)

if __name__ == "__main__":
    main()