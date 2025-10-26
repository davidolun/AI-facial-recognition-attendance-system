"""
Authentication views for teacher login, signup, and logout
"""
from .common_imports import (
    JsonResponse, render, csrf_exempt, login_required, redirect,
    json, transaction, logger, security_logger, Teacher, login, logout, authenticate
)


@csrf_exempt
def signup_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
            confirm_password = data.get('confirm_password', '').strip()
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            phone = data.get('phone', '').strip()
            department = data.get('department', '').strip()
            employee_id = data.get('employee_id', '').strip()
            
            validation_errors = []
            
            if not username:
                validation_errors.append('Username is required')
            elif len(username) < 3:
                validation_errors.append('Username must be at least 3 characters long')
            
            if not email or '@' not in email:
                validation_errors.append('Valid email address is required')
            
            if not first_name or len(first_name.strip()) < 2:
                validation_errors.append('First name must be at least 2 characters long')
            
            if not last_name or len(last_name.strip()) < 2:
                validation_errors.append('Last name must be at least 2 characters long')
            
            if not department or len(department.strip()) < 2:
                validation_errors.append('Department is required')
            
            if not password:
                validation_errors.append('Password is required')
            elif len(password) < 8:
                validation_errors.append('Password must be at least 8 characters long')
            
            if password != confirm_password:
                validation_errors.append('Passwords do not match')
            
            if username and Teacher.objects.filter(username=username).exists():
                validation_errors.append('Username already exists')
            
            if email and Teacher.objects.filter(email=email).exists():
                validation_errors.append('Email address is already registered')
            
            if employee_id and Teacher.objects.filter(employee_id=employee_id).exists():
                validation_errors.append('Employee ID already exists')
            
            if validation_errors:
                return JsonResponse({'error': validation_errors[0]}, status=400)
            
            with transaction.atomic():
                teacher = Teacher.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    department=department,
                    employee_id=employee_id if employee_id else None
                )
                
                login(request, teacher)
                
            return JsonResponse({
                'message': 'Account created successfully!',
                'redirect': '/dashboard/'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return render(request, 'auth/signup.html')


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            if not username or not password:
                security_logger.warning(f"Login attempt failed: Missing credentials")
                return JsonResponse({'error': 'Please enter both username and password'}, status=400)

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                logger.info(f"User {username} logged in successfully")
                return JsonResponse({
                    'message': 'Login successful!',
                    'redirect': '/dashboard/',
                    'user': {
                        'name': user.get_full_name(),
                        'username': user.username,
                        'is_admin': user.is_admin
                    }
                })
            else:
                security_logger.warning(f"Login attempt failed: Invalid credentials for '{username}'")
                return JsonResponse({'error': 'Invalid username or password'}, status=400)

        except Exception as e:
            security_logger.error(f"Login error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    
    return render(request, 'auth/login.html')


@login_required
def logout_view(request):
    logger.info(f"User {request.user.username} logged out")
    logout(request)
    return redirect('/login/')
