from django.core.management.base import BaseCommand

import os
import django
from datetime import date, time, datetime, timedelta
import random

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')  # Replace with your actual settings module
django.setup()

from faceapp.models import Student, Teacher, Class, AttendanceSession, AttendanceRecord  # Replace 'your_app' with actual app name

def generate_realistic_attendance_data():
    """
    Generate realistic attendance data from August 1 to September 1, 2025
    """
    print("Starting attendance data generation...")
    
    # Get all active students and teachers
    students = Student.objects.filter(is_active=True)
    teachers = Teacher.objects.all()
    classes = Class.objects.filter(is_active=True)
    
    if not students.exists():
        print("No students found in database!")
        return
    
    if not classes.exists():
        print("No classes found in database!")
        return
    
    print(f"Found {students.count()} students and {classes.count()} classes")
    
    # Date range: August 1 to September 1, 2025
    start_date = date(2025, 8, 1)
    end_date = date(2025, 9, 1)
    
    # Define realistic session times for different types of classes
    session_times = [
        ("Morning Lecture", time(9, 0), time(10, 30)),
        ("Mid-Morning Class", time(10, 45), time(12, 15)),
        ("Afternoon Lab", time(14, 0), time(15, 30)),
        ("Late Afternoon", time(15, 45), time(17, 15)),
        ("Evening Class", time(18, 0), time(19, 30)),
    ]
    
    # Student attendance patterns (realistic variations)
    student_patterns = {}
    for student in students:
        # Assign each student a realistic attendance pattern
        pattern_type = random.choices([
            'excellent',      # 95-98% attendance
            'good',          # 85-92% attendance  
            'average',       # 75-84% attendance
            'poor',          # 60-74% attendance
            'irregular'      # Very inconsistent
        ], weights=[20, 40, 25, 10, 5])[0]
        
        student_patterns[student.id] = {
            'pattern': pattern_type,
            'base_probability': {
                'excellent': 0.96,
                'good': 0.88,
                'average': 0.79,
                'poor': 0.67,
                'irregular': 0.55
            }[pattern_type],
            'consistency': random.uniform(0.7, 1.0),  # How consistent they are
            'morning_preference': random.uniform(0.8, 1.2),  # Prefer morning/afternoon
            'weekly_fatigue': random.uniform(0.85, 0.98)  # Get tired toward week end
        }
    
    generated_sessions = 0
    generated_records = 0
    
    # Generate sessions and attendance for each weekday in the date range
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            
            # Each class might have 1-3 sessions per week
            for cls in classes:
                # Determine if this class has a session today
                sessions_per_week = random.choices([1, 2, 3], weights=[30, 50, 20])[0]
                
                # Simple logic: spread sessions across the week
                if sessions_per_week == 1:
                    session_days = [2]  # Wednesday only
                elif sessions_per_week == 2:
                    session_days = [1, 4]  # Tuesday and Friday
                else:
                    session_days = [0, 2, 4]  # Monday, Wednesday, Friday
                
                if current_date.weekday() in session_days:
                    # Choose a random session time
                    session_name, start_time, end_time = random.choice(session_times)
                    
                    # Create session
                    session = AttendanceSession.objects.create(
                        name=f"{cls.name} - {session_name}",
                        date=current_date,
                        start_time=start_time,
                        end_time=end_time,
                        teacher=cls.teacher,
                        class_session=cls
                    )
                    generated_sessions += 1
                    
                    # Get students enrolled in this class
                    class_students = cls.students.filter(is_active=True)
                    
                    # Generate attendance for each student
                    for student in class_students:
                        pattern = student_patterns[student.id]
                        
                        # Calculate attendance probability based on various factors
                        base_prob = pattern['base_probability']
                        
                        # Time of day factor
                        if start_time.hour < 12:
                            time_factor = pattern['morning_preference']
                        else:
                            time_factor = 2.0 - pattern['morning_preference']
                        
                        # Day of week factor (students get tired toward end of week)
                        day_factor = pattern['weekly_fatigue'] ** current_date.weekday()
                        
                        # Month progress factor (slight decrease in attendance over time)
                        days_since_start = (current_date - start_date).days
                        month_factor = 1.0 - (days_since_start * 0.002)  # Small decline
                        
                        # Random variation
                        random_factor = random.uniform(0.8, 1.2)
                        
                        # Final probability
                        attend_probability = base_prob * time_factor * day_factor * month_factor * random_factor
                        attend_probability = max(0.1, min(0.99, attend_probability))  # Keep in bounds
                        
                        # Decide if student attends
                        if random.random() < attend_probability:
                            # Student attends - determine if late
                            
                            # Late probability based on pattern and time
                            if pattern['pattern'] == 'excellent':
                                late_prob = 0.05
                            elif pattern['pattern'] == 'good':
                                late_prob = 0.12
                            elif pattern['pattern'] == 'average':
                                late_prob = 0.20
                            elif pattern['pattern'] == 'poor':
                                late_prob = 0.35
                            else:  # irregular
                                late_prob = 0.45
                            
                            # Higher late probability for early morning classes
                            if start_time.hour < 10:
                                late_prob *= 1.5
                            
                            is_late = random.random() < late_prob
                            
                            # Generate arrival time
                            if is_late:
                                # Arrive 1-30 minutes late
                                late_minutes = random.randint(1, 30)
                                arrival_datetime = datetime.combine(current_date, start_time) + timedelta(minutes=late_minutes)
                                arrival_time = arrival_datetime.time()
                            else:
                                # Arrive on time or slightly early
                                early_minutes = random.randint(-10, 5)  # Can be up to 10 min early
                                arrival_datetime = datetime.combine(current_date, start_time) + timedelta(minutes=early_minutes)
                                arrival_time = max(arrival_datetime.time(), start_time)  # Don't arrive before start time
                            
                            # Create attendance record
                            AttendanceRecord.objects.create(
                                student=student,
                                session=session,
                                arrival_time=arrival_time,
                                is_late=is_late
                            )
                            generated_records += 1
        
        current_date += timedelta(days=1)
        
        # Progress indicator
        if generated_sessions % 10 == 0:
            print(f"Generated {generated_sessions} sessions, {generated_records} attendance records...")
    
    print(f"\n✅ Generation complete!")
    print(f"📊 Created {generated_sessions} sessions")
    print(f"👥 Created {generated_records} attendance records")
    print(f"📅 Date range: {start_date} to {end_date}")
    
    # Generate summary statistics
    print("\n📈 Summary Statistics:")
    
    for student in students[:5]:  # Show first 5 students
        student_records = AttendanceRecord.objects.filter(student=student).count()
        late_records = AttendanceRecord.objects.filter(student=student, is_late=True).count()
        
        if student_records > 0:
            attendance_rate = (student_records / AttendanceSession.objects.filter(
                class_session__students=student
            ).count()) * 100
            late_rate = (late_records / student_records) * 100
            
            print(f"  {student.name}: {student_records} sessions attended, "
                  f"{attendance_rate:.1f}% attendance rate, {late_rate:.1f}% late rate")

if __name__ == "__main__":
    generate_realistic_attendance_data()
    
class Command(BaseCommand):
    help = 'Generate realistic attendance data'
    
    def handle(self, *args, **options):
        generate_realistic_attendance_data()