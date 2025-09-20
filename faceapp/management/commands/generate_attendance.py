import random
from datetime import datetime, timedelta, time
from django.core.management.base import BaseCommand
from django.utils import timezone

from faceapp.models import Student, AttendanceSession, AttendanceRecord


class Command(BaseCommand):
    help = "Generate fake attendance data for the last week"

    def handle(self, *args, **kwargs):
        # Students
        student_names = ["kanye", "rich", "samuel", "dwayne", "kendal",
                         "beast", "sarah", "snoop", "bill", "david"]

        # Ensure students exist
        students = []
        for name in student_names:
            student, _ = Student.objects.get_or_create(
                name=name,
                defaults={"image_path": f"images/{name}.jpg"}
            )
            students.append(student)

        today = timezone.now().date()
        # Last Monday (start of last week)
        start_of_week = today - timedelta(days=today.weekday() + 7)

        session_names = ["Math", "Science", "Art", "Chemistry", "Biology", "History"]

        for i, session_name in enumerate(session_names):
            for day in range(5):  # Mon-Fri
                session_date = start_of_week + timedelta(days=day)
                start_time = time(9 + i, 0)     # Stagger sessions by hour
                end_time = time(10 + i, 0)

                session, _ = AttendanceSession.objects.get_or_create(
                    name=session_name,
                    date=session_date,
                    defaults={"start_time": start_time, "end_time": end_time}
                )

                self.stdout.write(self.style.SUCCESS(f"Created session {session}"))

                # Generate attendance for each student
                for student in students:
                    # 20% chance absent
                    if random.random() < 0.2:
                        continue

                    # Generate arrival time (some late, some on time, some early)
                    scheduled_dt = datetime.combine(session_date, start_time)
                    arrival_variation = random.randint(-5, 20)  # -5 min early to +20 min late
                    arrival_dt = scheduled_dt + timedelta(minutes=arrival_variation)

                    is_late = arrival_dt.time() > start_time

                    AttendanceRecord.objects.get_or_create(
                        student=student,
                        session=session,
                        defaults={
                            "arrival_time": arrival_dt.time(),
                            "is_late": is_late,
                        }
                    )

        self.stdout.write(self.style.SUCCESS("✅ Fake attendance generated for last week!"))
