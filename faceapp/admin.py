from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Teacher, Student, Class, AttendanceSession, AttendanceRecord, AIQuery

# Register Teacher with UserAdmin so you can manage them in admin
@admin.register(Teacher)
class TeacherAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone', 'department', 'employee_id', 'is_admin')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone', 'department', 'employee_id', 'is_admin')}),
    )

# Register the other models normally
admin.site.register(Student)
admin.site.register(Class)
admin.site.register(AttendanceSession)
admin.site.register(AttendanceRecord)
admin.site.register(AIQuery)
