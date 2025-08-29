from django.contrib import admin
from .models import Student, AttendanceSession, AttendanceRecord, AIQuery

admin.site.register(Student)
admin.site.register(AttendanceSession)
admin.site.register(AttendanceRecord)
admin.site.register(AIQuery)
