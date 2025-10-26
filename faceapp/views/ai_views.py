"""
AI Assistant views for querying attendance data
"""
from .common_imports import *
from .dashboard_views import get_complete_attendance_data

# Global conversation contexts storage
conversation_contexts = {}


def query_attendance_data_with_context(user_query: str, session_id: str, teacher=None) -> str:
    """Enhanced AI query with conversation context"""
    
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
"""

    data_summary = f"""
ATTENDANCE SYSTEM SUMMARY:
- Total Students: {data['total_students']}
- Total Sessions: {data['total_sessions']}
- Current Date: {data['today_date']}
"""

    system_prompt = f"""
You are a helpful AI assistant for a student attendance tracking system.

{teacher_info}
{data_summary}

Answer questions about attendance, absences, late arrivals, and student records professionally.
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
