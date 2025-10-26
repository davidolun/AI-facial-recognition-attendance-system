"""
Class management views for creating and managing classes
"""
from .common_imports import *


@login_required
def class_management(request):
    """Render the class management page"""
    return render(request, 'class_management.html')


@login_required
@csrf_exempt
def create_class(request):
    """Create a new class"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            code = data.get('code', '').strip()
            description = data.get('description', '').strip()
            academic_year = data.get('academic_year', '2024-2025').strip()
            semester = data.get('semester', 'Fall').strip()
            
            if not name or not code:
                return JsonResponse({'error': 'Class name and code are required'}, status=400)
            
            if Class.objects.filter(teacher=request.user, code=code).exists():
                return JsonResponse({'error': 'You already have a class with this code'}, status=400)
            
            new_class = Class.objects.create(
                name=name,
                code=code,
                teacher=request.user,
                description=description,
                academic_year=academic_year,
                semester=semester
            )

            existing_students = Student.objects.filter(classes__teacher=request.user).distinct()
            if existing_students.exists():
                new_class.students.add(*existing_students)
            
            return JsonResponse({
                'message': f'Class "{name}" created successfully!',
                'class_id': new_class.id,
                'class_data': {
                    'id': new_class.id,
                    'name': new_class.name,
                    'code': new_class.code,
                    'student_count': new_class.students.count()
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def get_teacher_classes(request):
    """Get classes for the logged-in teacher"""
    try:
        classes = Class.objects.filter(teacher=request.user, is_active=True)
        classes_data = []
        
        for cls in classes:
            student_count = cls.students.filter(is_active=True).count()
            session_count = cls.sessions.count()
            
            classes_data.append({
                'id': cls.id,
                'name': cls.name,
                'code': cls.code,
                'description': cls.description,
                'academic_year': cls.academic_year,
                'semester': cls.semester,
                'student_count': student_count,
                'session_count': session_count,
                'created_at': cls.created_at.strftime('%Y-%m-%d')
            })
        
        return JsonResponse({
            'classes': classes_data,
            'teacher': {
                'name': request.user.get_full_name(),
                'username': request.user.username,
                'department': request.user.department
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def assign_student_to_class(request):
    """Assign a student to one of teacher's classes"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            class_id = data.get('class_id')
            
            if not student_id or not class_id:
                return JsonResponse({'error': 'Student ID and Class ID are required'}, status=400)
            
            try:
                class_obj = Class.objects.get(id=class_id, teacher=request.user)
            except Class.DoesNotExist:
                return JsonResponse({'error': 'Class not found or you do not have permission'}, status=404)
            
            try:
                student = Student.objects.get(id=student_id, is_active=True)
            except Student.DoesNotExist:
                return JsonResponse({'error': 'Student not found'}, status=404)
            
            class_obj.students.add(student)
            
            return JsonResponse({
                'message': f'{student.name} assigned to {class_obj.name} successfully!',
                'class_name': class_obj.name,
                'student_name': student.name
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@csrf_exempt
def remove_student_from_class(request):
    """Remove a student from teacher's classes"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            class_id = data.get('class_id')
            
            if not student_id:
                return JsonResponse({'error': 'Student ID is required'}, status=400)
            
            try:
                student = Student.objects.get(id=student_id, is_active=True)
            except Student.DoesNotExist:
                return JsonResponse({'error': 'Student not found'}, status=404)
            
            if class_id:
                try:
                    class_obj = Class.objects.get(id=class_id, teacher=request.user)
                    class_obj.students.remove(student)
                    return JsonResponse({
                        'message': f'{student.name} removed from {class_obj.name} successfully!'
                    })
                except Class.DoesNotExist:
                    return JsonResponse({'error': 'Class not found'}, status=404)
            else:
                teacher_classes = Class.objects.filter(teacher=request.user, students=student)
                removed_classes = []
                
                for class_obj in teacher_classes:
                    class_obj.students.remove(student)
                    removed_classes.append(class_obj.name)
                
                if removed_classes:
                    return JsonResponse({
                        'message': f'{student.name} removed from classes: {", ".join(removed_classes)}'
                    })
                else:
                    return JsonResponse({
                        'message': f'{student.name} was not in any of your classes'
                    })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
