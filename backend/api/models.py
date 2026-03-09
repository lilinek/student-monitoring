from django.db import models

class Student(models.Model):
    student_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=50)
    semester = models.IntegerField(default=1)
    
    def __str__(self):
        return self.name

class Event(models.Model):
    EVENT_TYPES = [
        ('login', 'Вход в систему'),
        ('view_lecture', 'Просмотр лекции'),
        ('submit_assignment', 'Сдача задания'),
        ('miss_deadline', 'Пропуск дедлайна'),
        ('take_test', 'Прохождение теста'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    details = models.JSONField(default=dict)  # для доп.информации
    
    class Meta:
        ordering = ['-timestamp']

class StudentFeatures(models.Model):
    """Вектор признаков для ML"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    calculated_at = models.DateTimeField(auto_now=True)
    
    # Признаки
    avg_assignment_delay = models.FloatField(default=0)  # средняя задержка сдачи
    success_rate_midterms = models.FloatField(default=0)  # успеваемость
    days_since_last_login = models.IntegerField(default=0)
    activity_count_last_week = models.IntegerField(default=0)
    missed_deadlines_count = models.IntegerField(default=0)
    
    # Результат ML
    risk_score = models.FloatField(default=0)  # 0-1, где 1 - высокий риск
    risk_level = models.CharField(max_length=20, default='low')  # low/medium/high
    explanation = models.JSONField(default=dict)  # SHAP объяснения