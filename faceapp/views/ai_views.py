"""
AI Assistant views for querying attendance data
"""
from .common_imports import *
from .dashboard_views import get_complete_attendance_data

# Global conversation contexts storage
conversation_contexts = {}


def format_attendance_data_for_ai(data: dict) -> str:
    """Format complete attendance data into a readable string for the AI"""
    
    formatted = []
    
    # Student Information
    formatted.append("=== STUDENT ROSTER ===")
    for student in data['all_students']:
        formatted.append(f"• {student['name']} (ID: {student['student_id']}, Email: {student['email']})")
    
    formatted.append("\n=== STUDENT STATISTICS ===")
    for student_name, stats in data['student_statistics'].items():
        formatted.append(
            f"• {student_name}: "
            f"{stats['total_sessions_attended']}/{stats['available_sessions']} sessions attended "
            f"({stats['attendance_percentage']}%), "
            f"Late: {stats['times_late']} times, "
            f"On-time: {stats['times_on_time']} times"
        )
    
    # Session Information
    formatted.append("\n=== ALL SESSIONS ===")
    for session in data['all_sessions']:
        class_name = session.get('class_session__name', 'No Class')
        end_time = session.get('end_time', 'Not ended')
        formatted.append(
            f"• {session['name']} ({class_name}) - "
            f"Date: {session['date']}, "
            f"Time: {session['start_time']} to {end_time}"
        )
    
    # Detailed Session Records
    formatted.append("\n=== SESSION ATTENDANCE DETAILS ===")
    for session_key, details in data['session_details'].items():
        session_info = details['session_info']
        class_name = session_info.get('class_session__name', 'No Class')
        end_time = session_info.get('end_time', 'Not ended')
        
        formatted.append(
            f"\n{session_info['name']} ({class_name})"
        )
        formatted.append(f"  Date: {session_info['date']}")
        formatted.append(f"  Time: {session_info['start_time']} to {end_time}")
        formatted.append(f"  Present ({details['present_count']}): {', '.join(details['present_students']) if details['present_students'] else 'None'}")
        formatted.append(f"  Absent ({details['absent_count']}): {', '.join(details['absent_students']) if details['absent_students'] else 'None'}")
        formatted.append(f"  Late: {', '.join(details['late_students']) if details['late_students'] else 'None'}")
        formatted.append(f"  On-time: {', '.join(details['on_time_students']) if details['on_time_students'] else 'None'}")
    
    # Individual Attendance Records
    formatted.append("\n=== DETAILED ATTENDANCE RECORDS ===")
    for record in data['all_attendance_records']:
        arrival = record.get('arrival_time', 'Not recorded')
        late_status = "LATE" if record['is_late'] else "On-time"
        formatted.append(
            f"• {record['student__name']} - {record['session__name']} - "
            f"{record['date']} at {record['time']} "
            f"(Arrival: {arrival}) [{late_status}]"
        )
    
    return "\n".join(formatted)


def query_attendance_data_with_context(user_query: str, session_id: str, teacher=None) -> str:
    """Enhanced AI query with conversation context and FULL data access"""
    
    data = get_complete_attendance_data(teacher)
    
    if session_id not in conversation_contexts:
        conversation_contexts[session_id] = []
    
    conversation_history = conversation_contexts[session_id]
    conversation_history.append({"role": "user", "content": user_query})
    
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    teacher_info = ""
    if teacher:
        teacher_info = f"""
TEACHER CONTEXT:
You are responding to {teacher.get_full_name()} ({teacher.username}).
Department: {teacher.department or 'Not specified'}
This teacher can only see their own students and classes.
"""
    else:
        teacher_info = """
ADMIN CONTEXT:
You are responding to a system administrator who can see all students and classes.
"""

    # Format complete attendance data
    detailed_data = format_attendance_data_for_ai(data)

    system_prompt = f"""
You are a specialized AI assistant EXCLUSIVELY for a student attendance tracking system.

{teacher_info}

COMPLETE ATTENDANCE DATA:
{detailed_data}

SUMMARY STATISTICS:
- Total Students: {data['total_students']}
- Total Sessions: {data['total_sessions']}
- Current Date: {data['today_date']}

STRICT INSTRUCTIONS:
- ONLY answer questions about attendance, absences, late arrivals, student records, class sessions, and attendance statistics.
- You have access to ALL student names, session details, times, dates, and attendance records above.
- When asked about specific sessions, provide the complete information including date AND time.
- When asked about students, provide their names and relevant statistics.
- When asked about who was present/absent/late, refer to the detailed session information.
- Be conversational and helpful while being accurate with the data.
- If asked about a specific date or session, reference the exact data from the records above.

CRITICAL BOUNDARY RULE:
- If asked about ANY topic unrelated to attendance, students, classes, or this system (such as sports, weather, news, general knowledge, etc.), politely respond:
  "I'm specialized in helping with attendance and student records only. Please ask me questions about attendance, students, classes, or session data."
- Do NOT engage with off-topic questions. Stay strictly within your attendance system domain.
"""

    try:
        # Initialize OpenAI client if needed
        global client
        if not OPENAI_AVAILABLE:
            return "AI assistant is currently unavailable. Please try again later."
        
        if client is None:
            try:
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                return f"AI initialization error: {str(e)}"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-6:])
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_response})
        conversation_contexts[session_id] = conversation_history
        
        AIQuery.objects.create(query=user_query, response=ai_response)
        
        return ai_response
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"


@login_required
@csrf_exempt
def ai_assistant(request):
    """AI Assistant view"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_query = data.get("query", "").strip()
            session_id = data.get("session_id", "default")

            if not user_query:
                return JsonResponse({"error": "No query provided"}, status=400)

            teacher = None if request.user.is_admin else request.user
            ai_response = query_attendance_data_with_context(user_query, session_id, teacher)

            return JsonResponse({
                "query": user_query,
                "response": ai_response,
                "session_id": session_id
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, 'ai_assistant.html')