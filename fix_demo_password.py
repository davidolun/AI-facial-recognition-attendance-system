#!/usr/bin/env python
"""
One-time script to fix demo account password
Run: python fix_demo_password.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from faceapp.models import Teacher

# Find or create demo teacher
user, created = Teacher.objects.get_or_create(
    username='demo_teacher',
    defaults={
        'first_name': 'Demo',
        'last_name': 'Teacher',
        'email': 'demo@example.com',
        'department': 'Computer Science',
        'is_admin': False,
        'onboarding_completed': False
    }
)

# Set the password correctly
user.set_password('demo123456')
user.onboarding_completed = False
user.save()

if created:
    print('✅ Demo user created with password demo123456')
else:
    print('🔄 Demo user password reset to demo123456')

print(f'Username: demo_teacher')
print(f'Password: demo123456')
print(f'Onboarding: {user.onboarding_completed}')

