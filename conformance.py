"""
Расчет конформности - сравнение траектории студента с эталонными моделями
"""

import os
import sys
import django
from collections import Counter
import numpy as np

# Настройка Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Student, Event, StudentFeatures

class ConformanceCalculator:
    def __init__(self):
        # Строим эталонные модели на основе исторических данных
        self.build_reference_models()
    
    def build_reference_models(self):
        """Строит эталонные модели успешных и проблемных студентов"""
        
        # Успешные студенты (low risk)
        successful = StudentFeatures.objects.filter(risk_level='low')[:20]
        self.successful_patterns = self.extract_patterns(successful)
        
        # Проблемные студенты (high risk)
        problematic = StudentFeatures.objects.filter(risk_level='high')[:20]
        self.problematic_patterns = self.extract_patterns(problematic)
        
        print(f"✅ Построены эталонные модели:")
        print(f"   - Успешных студентов: {len(successful)}")
        print(f"   - Проблемных студентов: {len(problematic)}")
    
    def extract_patterns(self, students_features):
        """Извлекает паттерны поведения из группы студентов"""
        
        patterns = {
            'avg_activity': [],
            'avg_score': [],
            'missed_ratio': [],
            'login_frequency': [],
            'transition_patterns': Counter()
        }
        
        for sf in students_features:
            student = sf.student
            events = Event.objects.filter(student=student)
            
            if events.count() < 5:
                continue
            
            # Средняя активность
            patterns['avg_activity'].append(sf.activity_count_last_week)
            
            # Средний балл
            patterns['avg_score'].append(sf.success_rate_midterms)
            
            # Доля пропусков
            total = events.count()
            missed = sf.missed_deadlines_count
            patterns['missed_ratio'].append(missed / total if total > 0 else 0)
            
            # Частота входов
            logins = events.filter(event_type='login').count()
            patterns['login_frequency'].append(logins / 30 if logins > 0 else 0)  # в день
            
            # Паттерны переходов
            events_list = list(events.order_by('timestamp'))
            for i in range(len(events_list) - 1):
                patterns['transition_patterns'][
                    (events_list[i].event_type, events_list[i+1].event_type)
                ] += 1
        
        # Усредняем
        for key in ['avg_activity', 'avg_score', 'missed_ratio', 'login_frequency']:
            if patterns[key]:
                patterns[key] = np.mean(patterns[key])
            else:
                patterns[key] = 0
        
        return patterns
    
    def calculate_conformance(self, student):
        """Рассчитывает конформность студента к эталонным моделям"""
        
        features = StudentFeatures.objects.get(student=student)
        events = Event.objects.filter(student=student)
        
        if events.count() < 5:
            return 0.5, 0.5  # нейтральное значение
        
        # Сходство с успешной моделью
        successful_score = 0
        successful_score += 1 - min(abs(features.activity_count_last_week - 
                                       self.successful_patterns['avg_activity']) / 20, 1)
        successful_score += 1 - min(abs(features.success_rate_midterms - 
                                       self.successful_patterns['avg_score']) / 50, 1)
        
        # Сходство с проблемной моделью
        problematic_score = 0
        problematic_score += 1 - min(abs(features.activity_count_last_week - 
                                        self.problematic_patterns['avg_activity']) / 20, 1)
        problematic_score += 1 - min(abs(features.success_rate_midterms - 
                                        self.problematic_patterns['avg_score']) / 50, 1)
        
        # Нормализуем
        successful_score = successful_score / 2
        problematic_score = problematic_score / 2
        
        return successful_score, problematic_score
    
    def analyze_student(self, student_id):
        """Анализирует конкретного студента"""
        
        student = Student.objects.get(student_id=student_id)
        features = StudentFeatures.objects.get(student=student)
        
        successful, problematic = self.calculate_conformance(student)
        
        print(f"\n📊 Анализ студента: {student.name}")
        print(f"   ID: {student.student_id}")
        print(f"   Курс: {student.course}")
        print(f"   Текущий риск: {features.risk_level} ({features.risk_score:.2f})")
        print(f"\n   Конформность к успешной модели: {successful:.2f}")
        print(f"   Конформность к проблемной модели: {problematic:.2f}")
        
        if successful > problematic + 0.2:
            print("   ✅ Траектория ближе к успешным студентам")
        elif problematic > successful + 0.2:
            print("   ⚠️ Траектория ближе к проблемным студентам")
        else:
            print("   ➡️ Смешанная траектория")
        
        return successful, problematic

if __name__ == "__main__":
    calculator = ConformanceCalculator()
    
    # Анализируем несколько студентов
    students = Student.objects.all()[:5]
    for student in students:
        calculator.analyze_student(student.student_id)