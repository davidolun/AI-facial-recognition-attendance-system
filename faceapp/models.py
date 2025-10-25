# models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from datetime import date

class Teacher(AbstractUser):
    """Custom user model for teachers with additional fields"""
    phone = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    is_admin = models.BooleanField(default=False)  # For system administrators
    onboarding_completed = models.BooleanField(default=False)  # Track if user completed onboarding
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

class Class(models.Model):
    """Represents a class/course that a teacher manages"""
    name = models.CharField(max_length=100)  # e.g., "Physics 101", "Math Grade 10"
    code = models.CharField(max_length=20, unique=True)  # e.g., "PHY101", "MATH10A"
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='classes')
    description = models.TextField(blank=True, null=True)
    academic_year = models.CharField(max_length=20, default="2024-2025")
    semester = models.CharField(max_length=20, default="Fall")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Classes"
        unique_together = ['teacher', 'code']
    
    def __str__(self):
        return f"{self.name} ({self.code}) - {self.teacher.get_full_name()}"


class Student(models.Model):
    name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    image_path = models.CharField(max_length=255)
    face_encoding = models.TextField(null=True, blank=True, help_text="DeepFace face embedding stored as JSON")
    classes = models.ManyToManyField(Class, related_name='students', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

# Helper function to get today's date (not datetime)
def get_today():
    return date.today()

class AttendanceSession(models.Model):
    name = models.CharField(max_length=100)
    # FIXED: Use date.today instead of timezone.now for DateField
    date = models.DateField(default=get_today)
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True
    )
    class_session = models.ForeignKey(
        'Class',
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        class_name = self.class_session.name if self.class_session else "No Class"
        return f"{self.name} - {class_name} - {self.date}"


class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)  # This is when the record was created
    arrival_time = models.TimeField(null=True, blank=True)  # NEW: This is the exact time student arrived
    is_late = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['student', 'session']  # Prevent duplicate attendance per session
    
    def __str__(self):
        arrival_str = f" (arrived at {self.arrival_time})" if self.arrival_time else ""
        return f"{self.student.name} - {self.date} {self.time}{arrival_str}"

class AIQuery(models.Model):
    query = models.TextField()
    response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Query at {self.timestamp}"