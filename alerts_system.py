"""
Система оповещений о студентах группы риска
Запуск: python alerts_system.py
"""

import os
import sys
import django
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Настройка Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Student, Event, StudentFeatures

class AlertSystem:
    def __init__(self):
        self.red_threshold = 0.7  # Красный уровень: риск > 70%
        self.yellow_threshold = 0.4  # Желтый уровень: риск > 40%
        
    def check_red_alerts(self):
        """Проверка красного уровня (срочное вмешательство)"""
        red_students = StudentFeatures.objects.filter(
            risk_level='high',
            risk_score__gte=self.red_threshold
        ).select_related('student')
        
        alerts = []
        for student in red_students:
            alerts.append({
                'student': student.student,
                'risk_score': student.risk_score,
                'reason': 'Высокий риск отчисления',
                'level': '🔴 КРАСНЫЙ',
                'actions': [
                    'Немедленно связаться с куратором',
                    'Назначить встречу с тьютором',
                    'Проверить академические задолженности'
                ]
            })
        return alerts
    
    def check_yellow_alerts(self):
        """Проверка желтого уровня (повышенное внимание)"""
        alerts = []
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        # Студенты со средним риском
        medium_students = StudentFeatures.objects.filter(
            risk_level='medium'
        ).select_related('student')
        
        for student in medium_students:
            alerts.append({
                'student': student.student,
                'risk_score': student.risk_score,
                'reason': 'Средний уровень риска',
                'level': '🟡 ЖЕЛТЫЙ',
                'actions': [
                    'Увеличить частоту коммуникации',
                    'Проверить посещаемость',
                    'Рекомендовать консультации'
                ]
            })
        
        # Студенты со снижением активности
        inactive_students = StudentFeatures.objects.filter(
            activity_count_last_week__lt=3,
            risk_level__in=['low', 'medium']
        ).select_related('student')
        
        for student in inactive_students:
            alerts.append({
                'student': student.student,
                'risk_score': student.risk_score,
                'reason': f'Низкая активность ({student.activity_count_last_week} событий за неделю)',
                'level': '🟡 ЖЕЛТЫЙ',
                'actions': [
                    'Проверить причины снижения активности',
                    'Мотивировать к участию'
                ]
            })
        
        return alerts
    
    def send_email_alert(self, recipient_email, alert):
        """Отправка email уведомления"""
        msg = MIMEMultipart()
        msg['From'] = 'monitoring@university.ru'
        msg['To'] = recipient_email
        msg['Subject'] = f"{alert['level']} Оповещение: {alert['student'].name}"
        
        body = f"""
        <h2>{alert['level']} Оповещение о студенте</h2>
        
        <p><b>Студент:</b> {alert['student'].name}</p>
        <p><b>ID:</b> {alert['student'].student_id}</p>
        <p><b>Курс:</b> {alert['student'].course}</p>
        <p><b>Семестр:</b> {alert['student'].semester}</p>
        <p><b>Оценка риска:</b> {alert['risk_score']:.2f}</p>
        <p><b>Причина:</b> {alert['reason']}</p>
        
        <h3>Рекомендуемые действия:</h3>
        <ul>
        """
        
        for action in alert['actions']:
            body += f"<li>{action}</li>"
        
        body += """
        </ul>
        
        <p>Дата: {date}</p>
        """.format(date=datetime.now().strftime('%d.%m.%Y %H:%M'))
        
        msg.attach(MIMEText(body, 'html'))
        
        # Здесь нужно настроить SMTP сервер
        # Для теста просто сохраняем в файл
        with open(f"alert_{alert['student'].student_id}.html", 'w', encoding='utf-8') as f:
            f.write(body)
        
        print(f"✅ Email сохранен в файл alert_{alert['student'].student_id}.html")
    
    def generate_report(self):
        """Генерация отчета для куратора"""
        print("\n" + "="*70)
        print("📊 ЕЖЕДНЕВНЫЙ ОТЧЕТ ПО РИСКАМ")
        print("="*70)
        print(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        red_alerts = self.check_red_alerts()
        yellow_alerts = self.check_yellow_alerts()
        
        print(f"\n🔴 КРАСНЫЙ УРОВЕНЬ (срочное вмешательство): {len(red_alerts)}")
        for alert in red_alerts:
            print(f"   - {alert['student'].name} ({alert['student'].course}): риск {alert['risk_score']:.2f}")
        
        print(f"\n🟡 ЖЕЛТЫЙ УРОВЕНЬ (повышенное внимание): {len(yellow_alerts)}")
        for alert in yellow_alerts[:10]:  # Покажем первые 10
            print(f"   - {alert['student'].name}: {alert['reason']}")
        
        print(f"\n📊 Статистика:")
        total = StudentFeatures.objects.count()
        high = StudentFeatures.objects.filter(risk_level='high').count()
        medium = StudentFeatures.objects.filter(risk_level='medium').count()
        low = StudentFeatures.objects.filter(risk_level='low').count()
        
        print(f"   Всего студентов: {total}")
        print(f"   🔴 Высокий риск: {high} ({high/total*100:.1f}%)")
        print(f"   🟡 Средний риск: {medium} ({medium/total*100:.1f}%)")
        print(f"   🟢 Низкий риск: {low} ({low/total*100:.1f}%)")
        
        print("\n" + "="*70)
        
        # Сохраняем отчет в файл
        with open(f"report_{datetime.now().strftime('%Y%m%d')}.txt", 'w', encoding='utf-8') as f:
            f.write(f"Отчет по рискам от {datetime.now().strftime('%d.%m.%Y')}\n")
            f.write("="*50 + "\n")
            f.write(f"Красный уровень: {len(red_alerts)}\n")
            f.write(f"Желтый уровень: {len(yellow_alerts)}\n")
        
        return red_alerts, yellow_alerts

if __name__ == "__main__":
    alerts = AlertSystem()
    alerts.generate_report()
    
    # Для теста отправим одно уведомление
    red = alerts.check_red_alerts()
    if red:
        alerts.send_email_alert('curator@university.ru', red[0])