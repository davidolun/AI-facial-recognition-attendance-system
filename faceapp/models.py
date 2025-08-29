# models.py
from django.db import models
from django.utils import timezone

class Student(models.Model):
    name = models.CharField(max_length=100, unique=True)
    student_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    image_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class AttendanceSession(models.Model):
    name = models.CharField(max_length=100)  # e.g., "Morning Class", "Physics Lecture"
    date = models.DateField(default=timezone.now)
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.date}"

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